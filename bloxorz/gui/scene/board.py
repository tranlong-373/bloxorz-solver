"""Board: one entity per tile, bridges shown or hidden. Owner: VT3 (tasks 3.1, 3.3)."""


"""Render a Stage as a 3D board."""

from ursina import Entity, destroy
from .theme import TILE_COLORS, SWITCH_COLORS, cell_to_world


class Board:
    def __init__(self):
        # (row, col) -> Entity
        self.tiles = {}

    def clear(self):
        """Remove previously created tiles."""
        for tile in self.tiles.values():
            destroy(tile)

        self.tiles.clear()

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
