
"""Colors, cell_to_world, block transform per pose. Owner: VT3 (task 3.1)."""

from ursina import color
from bloxorz.model import Pose, State

TILE_COLORS = {
    "#": color.rgb32(125, 132, 145),
    "F": color.rgb32(220, 170, 90),
    "G": color.rgb32(30, 30, 40),
    "B": color.rgb32(80, 165, 205),
}

SWITCH_COLORS = {
    # Soft: low, round plate; heavy: X; split: paired parallel bars.
    "soft": color.rgb32(100, 210, 120),
    "heavy": color.rgb32(230, 110, 85),
    "split": color.rgb32(175, 115, 225),
}

BLOCK_COLOR = color.rgb32(235, 190, 75)


def cell_to_world(r: int, c: int):
    return (float(c), -0.1, -float(r))


def block_transform(state: State):
    r, c = state.pos

    if state.pose == Pose.STANDING:
        return (c, 1.0, -r), (1, 2, 1)

    if state.pose == Pose.HORIZONTAL:
        return (c + 0.5, 0.5, -r), (2, 1, 1)

    if state.pose == Pose.VERTICAL:
        return (c, 0.5, -(r + 0.5)), (1, 1, 2)

    raise ValueError("Split block is not implemented in task 3.1")
