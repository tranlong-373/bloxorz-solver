"""Board tiles, bridges, and switch visuals. Owner: VT3 (tasks 3.1, 3.3)."""

from ursina import Entity, color, destroy

from .animate import BRIDGE_DURATION
from .theme import TILE_COLORS, SWITCH_COLORS, cell_to_world


class Board:
    def __init__(self):
        # (row, col) -> floor or bridge Entity
        self.tiles = {}
        self.bridge_tiles = {}
        self.switch_entities = {}
        self._open_bridges = set()
        self._busy = False
        self._generation = 0

    def clear(self):
        """Remove the previous stage and invalidate its animation callbacks."""
        self._generation += 1
        self._busy = False
        for tile in self.tiles.values():
            destroy(tile)
        for entities in self.switch_entities.values():
            for entity, _ in entities:
                destroy(entity)

        self.tiles.clear()
        self.bridge_tiles.clear()
        self.switch_entities.clear()
        self._open_bridges.clear()

    def build(self, stage):
        """Build floor, bridge overlays, and distinct switch models."""
        self.clear()

        for r, row in enumerate(stage.grid):
            for c, symbol in enumerate(row):
                cell = (r, c)
                bridge_id = stage.bridge_at.get(cell)

                # A bridge can occupy a void cell in the stage grid.
                if symbol == "." and bridge_id is None:
                    continue

                position = cell_to_world(r, c)
                scale = (0.95, 0.2, 0.95)
                fallback = TILE_COLORS["B"] if bridge_id else TILE_COLORS["#"]
                tile_color = TILE_COLORS.get(symbol, fallback)

                if symbol == "G":
                    position = (c, -0.16, -r)
                    scale = (0.95, 0.06, 0.95)

                switches = stage.switch_at.get(cell, ())
                if switches:
                    tile_color = SWITCH_COLORS.get(switches[0].kind, tile_color)

                tile = Entity(
                    model="cube",
                    position=position,
                    scale=scale,
                    color=tile_color,
                )
                self.tiles[cell] = tile

                if bridge_id is not None:
                    self.bridge_tiles.setdefault(bridge_id, []).append(tile)

        for switches in stage.switches:
            self.switch_entities[switches.id] = self._make_switch_entities(switches)

        self._open_bridges = set(stage.initial_bridges_open())
        self._sync_bridge_visibility()

    def _make_switch_entities(self, switch):
        r, c = switch.pos
        y = 0.045
        tint = SWITCH_COLORS.get(switch.kind, color.white)

        if switch.kind == "soft":
            shapes = [((0, y, 0), (0.6, 0.08, 0.6), 0)]
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
            )
            entities.append((entity, scale))
        return entities

    def _sync_bridge_visibility(self):
        for bridge_id, tiles in self.bridge_tiles.items():
            opened = bridge_id in self._open_bridges
            for tile in tiles:
                tile.enabled = opened
                tile.scale = (0.95, 0.2, 0.95) if opened else (0, 0, 0)

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
            target = (0.95, 0.2, 0.95)
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
        return self._busy
