"""BlockView: the 1x1x2 block or the two cubes. Owner: VT3 (tasks 3.1, 3.3)."""


"""Render the Bloxorz block from State."""

from ursina import Entity, destroy
from .theme import BLOCK_COLOR, block_transform


class BlockView:
    def __init__(self):
        self.entity = Entity(
            model="cube",
            color=BLOCK_COLOR,
            position=(0, 1, 0),
            scale=(1, 2, 1),
        )

    def place(self, state):
        """Update the block position and size."""
        if state.pose is None:
            raise NotImplementedError(
                "Split blocks belong to task 3.3"
            )

        position, scale = block_transform(state)

        self.entity.position = position
        self.entity.scale = scale
        self.entity.rotation = (0, 0, 0)

    def clear(self):
        destroy(self.entity)
