"""Board: one entity per tile, bridges shown or hidden. Owner: VT3 (tasks 3.1, 3.3)."""


"""Render a Stage as a 3D board."""

from ursina import Entity, destroy
from .animate import play_fragile_break
from .theme import TILE_COLORS, SWITCH_COLORS, cell_to_world


class Board:
    def __init__(self):
        # (row, col) -> Entity
        self.tiles = {}
        self.fragile_tiles = {}
        self._fragile_defaults = {}
        self._broken_fragile = set()
        self._busy = False
        self._generation = 0

    def clear(self):
        """Remove previously created tiles."""
        self._generation += 1
        self._busy = False
        for tile in self.tiles.values():
            destroy(tile)

        self.tiles.clear()
        self.fragile_tiles.clear()
        self._fragile_defaults.clear()
        self._broken_fragile.clear()

    def build(self, stage):
        """Build the board from stage.grid."""
        self.clear()

        for r, row in enumerate(stage.grid):
            for c, symbol in enumerate(row):

                # A dot means there is no floor.
                if symbol == ".":
                    continue

                position = cell_to_world(r, c)
                scale = (0.95, 0.2, 0.95)

                tile_color = TILE_COLORS.get(
                    symbol, TILE_COLORS["#"]
                )

                # A lower dark tile represents the goal hole.
                if symbol == "G":
                    position = (c, -0.16, -r)
                    scale = (0.95, 0.06, 0.95)

                switches = stage.switch_at.get((r, c), ())
                if switches:
                    tile_color = SWITCH_COLORS.get(
                        switches[0].kind,
                        TILE_COLORS["#"],
                    )

                tile = Entity(
                    model="cube",
                    position=position,
                    scale=scale,
                    color=tile_color,
                )

                self.tiles[(r, c)] = tile

                if symbol == "F":
                    self.fragile_tiles[(r, c)] = tile
                    self._fragile_defaults[(r, c)] = (
                        tile.position,
                        tile.scale,
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

    def is_busy(self):
        """Return True while a fragile tile animation is running."""
        return self._busy

    def reset_fragile(self):
        """Restore fragile tiles when the demo restarts the current stage."""
        if self._busy:
            raise RuntimeError("Cannot reset fragile tiles during animation")
        for cell, tile in self.fragile_tiles.items():
            position, scale = self._fragile_defaults[cell]
            tile.position = position
            tile.scale = scale
        self._broken_fragile.clear()
