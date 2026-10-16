"""Shared data types: Pos, Direction, Pose, State, Action. Owner: VT1 (task 1.2)."""
from dataclasses import dataclass
from enum import Enum

Pos = tuple[int, int]  # (row, col), (0, 0) is top-left


class Direction(Enum):
    UP = "U"
    DOWN = "D"
    LEFT = "L"
    RIGHT = "R"


class Pose(Enum):
    STANDING = 0
    HORIZONTAL = 1
    VERTICAL = 2


@dataclass(frozen=True, slots=True)
class State:
    pose: Pose | None  # None while split
    pos: Pos  # top-left cell of the block, or first cube when split
    cube2: Pos | None = None  # second cube; always pos < cube2
    bridges_open: frozenset[str] = frozenset()

    def __post_init__(self):
        if self.cube2 is not None and self.cube2 < self.pos:
            first, second = self.cube2, self.pos
            object.__setattr__(self, "pos", first)
            object.__setattr__(self, "cube2", second)


@dataclass(frozen=True, slots=True)
class Action:
    direction: Direction
    cube: int | None = None  # None = whole block; 0 or 1 while split
