"""Board tiles, bridges, switch buttons and the goal portal. Owner: VT3 (tasks 3.1, 3.3, 3.4)."""

import math
import time

from ursina import Entity, color, destroy

from .animate import BRIDGE_DURATION, play_fragile_break
from .textures import portal_ring_texture, stone_texture
from .theme import (
    GLOW_SHADER,
    PORTAL_COLOR,
    PORTAL_STREAK_COLOR,
    PORTAL_STREAK_PERIOD,
    PORTAL_STREAKS,
    SCENE_SHADER,
    SWITCH_COLORS,
    SWITCH_SYMBOL_SHADE,
    TILE_COLORS,
    TILE_SIZE,
    TILE_THICKNESS,
    cell_to_world,
    rgb,
    switch_link_colors,
)

TILE_SCALE = (TILE_SIZE, TILE_THICKNESS, TILE_SIZE)


class Board:
    # Scale of an open bridge tile (and every floor tile).
    OPEN_SCALE = TILE_SCALE

    def __init__(self):
        # (row, col) -> floor or bridge Entity
        self.tiles = {}
        self.bridge_tiles = {}
        self.switch_entities = {}
        self._switch_rgb = {}
        self._open_bridges = set()
        self.fragile_tiles = {}
        self._fragile_defaults = {}
        self._broken_fragile = set()
        self._busy = False
        self._generation = 0
        # Goal portal ring, light streaks and the entity that moves them.
        self.decorations = []

    def clear(self):
        """Remove the previous stage and invalidate its animation callbacks."""
        self._generation += 1
        self._busy = False
        for tile in self.tiles.values():
            destroy(tile)
        for entities in self.switch_entities.values():
            for entity, _ in entities:
                destroy(entity)
        for entity in self.decorations:
            destroy(entity)

        self.decorations.clear()
        self.tiles.clear()
        self.bridge_tiles.clear()
        self.switch_entities.clear()
        self._open_bridges.clear()
        self.fragile_tiles.clear()
        self._fragile_defaults.clear()
        self._broken_fragile.clear()

    def build(self, stage):
        """Build floor, bridge overlays, and distinct switch models."""
        self.clear()
        self._switch_rgb, bridge_rgb = switch_link_colors(stage)

        for r, row in enumerate(stage.grid):
            for c, symbol in enumerate(row):
                cell = (r, c)
                bridge_id = stage.bridge_at.get(cell)

                # A bridge can occupy a void cell in the stage grid.
                if symbol == "." and bridge_id is None:
                    continue

                position = cell_to_world(r, c)
                scale = TILE_SCALE
                texture = stone_texture()
                if bridge_id is not None:
                    tile_color = (
                        rgb(bridge_rgb[bridge_id])
                        if bridge_id in bridge_rgb
                        else TILE_COLORS["B"]
                    )
                else:
                    tile_color = TILE_COLORS.get(symbol, TILE_COLORS["#"])

                if symbol == "G":
                    # A dark, sunken hole; the portal ring sits on its rim.
                    position = (c, -TILE_THICKNESS + 0.02, -r)
                    scale = (TILE_SIZE, 0.04, TILE_SIZE)
                    texture = None
                    self.decorations.extend(self._make_goal_portal(r, c))

                # Switch tiles stay plain stone; the button carries the color.
                tile = Entity(
                    model="cube",
                    position=position,
                    scale=scale,
                    color=tile_color,
                    texture=texture,
                    shader=SCENE_SHADER,
                )
                self.tiles[cell] = tile

                if symbol == "F":
                    self.fragile_tiles[cell] = tile
                    self._fragile_defaults[cell] = (tile.position, tile.scale)

                if bridge_id is not None:
                    self.bridge_tiles.setdefault(bridge_id, []).append(tile)

        for switches in stage.switches:
            self.switch_entities[switches.id] = self._make_switch_entities(switches)

        self._open_bridges = set(stage.initial_bridges_open())
        self._sync_bridge_visibility()

    def _make_goal_portal(self, r, c):
        """Glowing ring on the goal rim plus light streaks rising from it."""
        ring = Entity(
            model="quad",
            texture=portal_ring_texture(),
            color=PORTAL_COLOR,
            position=(c, 0.02, -r),
            rotation_x=90,
            scale=1.45,
            double_sided=True,
            shader=GLOW_SHADER,
        )
        streaks = []
        for index in range(PORTAL_STREAKS):
            angle = 2 * math.pi * index / PORTAL_STREAKS
            streaks.append(
                Entity(
                    model="quad",
                    color=PORTAL_STREAK_COLOR,
                    position=(c + 0.4 * math.cos(angle), 0.1, -r + 0.4 * math.sin(angle)),
                    scale=(0.04, 0.35),
                    billboard=True,
                    shader=GLOW_SHADER,
                )
            )

        def update():
            # Each streak rises and fades in a loop, staggered around the ring.
            now = time.perf_counter() / PORTAL_STREAK_PERIOD
            for index, streak in enumerate(streaks):
                progress = (now + index / PORTAL_STREAKS) % 1
                streak.y = 0.1 + 0.9 * progress
                streak.scale_y = 0.35 * (1 - progress) + 0.05

        mover = Entity(update=update)
        return [ring, *streaks, mover]

    def _make_switch_entities(self, switch):
        r, c = switch.pos
        y = 0.045
        if switch.id in self._switch_rgb:
            tint = rgb(self._switch_rgb[switch.id], SWITCH_SYMBOL_SHADE)
        else:
            tint = SWITCH_COLORS.get(switch.kind, color.white)

        if switch.kind == "soft":
            # A round push button.
            shapes = [((0, y + 0.02, 0), (0.56, 0.18, 0.56), 0)]
            model = "sphere"
        elif switch.kind == "heavy":
            # Two flat bars form an X when viewed from above.
            shapes = [
                ((0, y, 0), (0.72, 0.06, 0.18), angle)
                for angle in (45, -45)
            ]
            model = "cube"
        elif switch.kind == "split":
            # Two narrow parallel bars represent the paired curved marks.
            shapes = [
                ((offset, y, 0), (0.14, 0.06, 0.58), 0)
                for offset in (-0.2, 0.2)
            ]
            model = "cube"
        else:
            return []

        entities = []
        for offset, scale, angle in shapes:
            entity = Entity(
                model=model,
                position=(c + offset[0], y, -r + offset[2]),
                scale=scale,
                rotation_y=angle,
                color=tint,
                shader=SCENE_SHADER,
            )
            entities.append((entity, scale))
        return entities

    def _sync_bridge_visibility(self):
        for bridge_id, tiles in self.bridge_tiles.items():
            opened = bridge_id in self._open_bridges
            for tile in tiles:
                tile.enabled = opened
                tile.scale = TILE_SCALE if opened else (0, 0, 0)

    def show_state(self, state):
        """Set bridge visibility from the Engine's authoritative State."""
        self._open_bridges = set(state.bridges_open)
        self._sync_bridge_visibility()

    def _run_parallel(self, animations, on_done, generation):
        if not animations:
            on_done()
            return

        remaining = len(animations)
        completed = False

        def callback_for_one_animation():
            animation_finished = False

            def one_done():
                nonlocal remaining, completed, animation_finished
                if (
                    animation_finished
                    or completed
                    or generation != self._generation
                ):
                    return
                animation_finished = True
                remaining -= 1
                if remaining == 0:
                    completed = True
                    on_done()

            return one_done

        for animation in animations:
            animation.append(callback_for_one_animation())

    def _pulse_switch(self, switch_id, on_done, generation):
        entities = self.switch_entities.get(switch_id, ())
        animations = []
        for entity, base_scale in entities:
            entity.scale = base_scale
            animations.append(
                entity.animate_scale(
                    tuple(component * 1.2 for component in base_scale),
                    duration=BRIDGE_DURATION / 2,
                )
            )

        def restore():
            if generation != self._generation:
                return
            for entity, base_scale in entities:
                entity.scale = base_scale
            on_done()

        self._run_parallel(animations, restore, generation)

    def _animate_bridge(self, bridge_id, opened, on_done, generation):
        tiles = self.bridge_tiles.get(bridge_id, ())
        if not tiles:
            on_done()
            return

        if opened:
            self._open_bridges.add(bridge_id)
            for tile in tiles:
                tile.enabled = True
                tile.scale = (0, 0, 0)
            target = TILE_SCALE
        else:
            self._open_bridges.discard(bridge_id)
            target = (0, 0, 0)

        animations = [
            tile.animate_scale(target, duration=BRIDGE_DURATION)
            for tile in tiles
        ]

        def finish():
            if generation != self._generation:
                return
            if not opened:
                for tile in tiles:
                    tile.enabled = False
            on_done()

        self._run_parallel(animations, finish, generation)

    def animate_events(self, events, on_done):
        """Animate only switch and bridge changes confirmed by Engine events."""
        if self._busy:
            raise RuntimeError("Board is already animating")

        self._busy = True
        generation = self._generation
        transitions = []
        for event in events:
            if event.startswith("switch:"):
                transitions.append(("switch", event[len("switch:"):]))
            elif event.startswith("bridge:"):
                bridge_event = event[len("bridge:"):]
                bridge_id, separator, state = bridge_event.rpartition(":")
                if separator and state in ("open", "close"):
                    transitions.append(("bridge", bridge_id, state == "open"))

        def finish():
            if generation != self._generation:
                return
            self._busy = False
            on_done()

        def run_next(index=0):
            if generation != self._generation:
                return
            if index >= len(transitions):
                finish()
                return

            transition = transitions[index]
            next_step = lambda: run_next(index + 1)
            if transition[0] == "switch":
                self._pulse_switch(transition[1], next_step, generation)
            else:
                self._animate_bridge(
                    transition[1],
                    transition[2],
                    next_step,
                    generation,
                )

        try:
            run_next()
        except Exception:
            if generation == self._generation:
                self._busy = False
            raise

    def is_busy(self):
        """Return True while a bridge, switch or fragile animation runs."""
        return self._busy

    def has_floor(self, cell):
        """True when a visible tile is drawn under cell.

        Closed bridges and broken fragile tiles show no floor. Used only to
        shape the fall animation; Engine already decided the move failed.
        """
        tile = self.tiles.get(cell)
        return (
            tile is not None
            and getattr(tile, "enabled", True)
            and cell not in self._broken_fragile
        )

    def break_fragile(self, cell, on_done):
        """Animate the specified F tile after the Engine reports a break."""
        if self._busy:
            raise RuntimeError("Board is already animating")
        if cell not in self.fragile_tiles:
            raise ValueError(f"No fragile tile at {cell}")
        if cell in self._broken_fragile:
            on_done()
            return

        self._broken_fragile.add(cell)
        self._busy = True
        generation = self._generation
        callback_called = False

        def finish():
            nonlocal callback_called
            if callback_called:
                return
            if generation != self._generation:
                return
            callback_called = True
            self._busy = False
            on_done()

        try:
            play_fragile_break(self.fragile_tiles[cell], finish)
        except Exception:
            if not callback_called:
                self._busy = False
                self._broken_fragile.discard(cell)
            raise

    def reset_fragile(self):
        """Restore fragile tiles when the demo restarts the current stage."""
        if self._busy:
            raise RuntimeError("Cannot reset fragile tiles during animation")
        for cell, tile in self.fragile_tiles.items():
            position, scale = self._fragile_defaults[cell]
            tile.position = position
            tile.scale = scale
        self._broken_fragile.clear()
