"""BlockView: the 1x1x2 block or the two cubes. Owner: VT3 (tasks 3.1, 3.3c)."""

from ursina import Entity, destroy

from .theme import (
    BLOCK_COLOR,
    CUBE_COLOR,
    SELECTED_CUBE_COLOR,
    block_transform,
    cube_transform,
)


class BlockView:
    def __init__(self):
        self.entity = Entity(
            model="cube",
            color=BLOCK_COLOR,
            position=(0, 1, 0),
            scale=(1, 2, 1),
        )
        # Created once and only enabled while split; cubes[i] sits on the
        # i-th position of the last placed State (pos, then cube2).
        self.cubes = [
            Entity(model="cube", color=CUBE_COLOR, scale=(1, 1, 1), enabled=False)
            for _ in range(2)
        ]
        self.cube_cells = [None, None]

    def entities(self):
        """Every entity this view may animate."""
        return [self.entity, *self.cubes]

    def place(self, state):
        """Show the whole block or the two cubes exactly at the State."""
        if state.pose is None:
            self.entity.enabled = False
            for cube, pos in zip(self.cubes, (state.pos, state.cube2)):
                position, scale = cube_transform(pos)
                cube.enabled = True
                cube.position = position
                cube.scale = scale
                cube.rotation = (0, 0, 0)
            self.cube_cells = [state.pos, state.cube2]
            return

        for cube in self.cubes:
            cube.enabled = False
        self.cube_cells = [None, None]

        position, scale = block_transform(state)

        self.entity.enabled = True
        self.entity.position = position
        self.entity.scale = scale
        self.entity.rotation = (0, 0, 0)

    def highlight(self, pos):
        """Brighten the cube resting on pos; None clears the highlight."""
        for cube, cell in zip(self.cubes, self.cube_cells):
            selected = pos is not None and cell == pos
            cube.color = SELECTED_CUBE_COLOR if selected else CUBE_COLOR

    def clear(self):
        for entity in self.entities():
            destroy(entity)
