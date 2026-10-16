"""Basic Bloxorz engine (task 2.1): roll, support checks, and victory.

Core data types are defined here so no separate models.py is needed.
Fragile tiles, switch activation, and split/merge are reserved for later tasks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


Position = tuple[int, int]


class Pose(Enum):
    STANDING = "standing"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class Direction(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True)
class Action:
    direction: Direction


@dataclass(frozen=True)
class State:
    pose: Pose | None
    pos: Position
    cube2: Position | None = None
    bridges_open: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        # A normalized, immutable bridge set keeps State hashable for BFS/A*.
        object.__setattr__(self, "bridges_open", frozenset(self.bridges_open))


@dataclass(frozen=True)
class Stage:
    id: str
    group: str
    grid: tuple[str, ...]
    start: Position
    goal: Position
    # Position -> bridge ID, so a switch can control multiple cells by ID.
    # A bridge's open/closed status overrides the grid character at that cell.
    bridge_cells: Mapping[Position, str] = field(default_factory=dict)
    open_bridges_at_start: frozenset[str] = field(default_factory=frozenset)

    def initial_bridges_open(self) -> frozenset[str]:
        return frozenset(self.open_bridges_at_start)


class Outcome(Enum):
    MOVED = "moved"
    ILLEGAL = "illegal"


@dataclass(frozen=True)
class StepResult:
    outcome: Outcome
    state: State | None
    reason: str | None = None


# (current pose, direction) -> (new pose, delta row, delta col)
# State.pos is the TOP-LEFT occupied square (not the geometric center).
ROLL: dict[tuple[Pose, Direction], tuple[Pose, int, int]] = {
    (Pose.STANDING, Direction.UP): (Pose.VERTICAL, -2, 0),
    (Pose.STANDING, Direction.DOWN): (Pose.VERTICAL, +1, 0),
    (Pose.STANDING, Direction.LEFT): (Pose.HORIZONTAL, 0, -2),
    (Pose.STANDING, Direction.RIGHT): (Pose.HORIZONTAL, 0, +1),
    (Pose.HORIZONTAL, Direction.UP): (Pose.HORIZONTAL, -1, 0),
    (Pose.HORIZONTAL, Direction.DOWN): (Pose.HORIZONTAL, +1, 0),
    (Pose.HORIZONTAL, Direction.LEFT): (Pose.STANDING, 0, -1),
    (Pose.HORIZONTAL, Direction.RIGHT): (Pose.STANDING, 0, +2),
    (Pose.VERTICAL, Direction.UP): (Pose.STANDING, -1, 0),
    (Pose.VERTICAL, Direction.DOWN): (Pose.STANDING, +2, 0),
    (Pose.VERTICAL, Direction.LEFT): (Pose.VERTICAL, 0, -1),
    (Pose.VERTICAL, Direction.RIGHT): (Pose.VERTICAL, 0, +1),
}


def footprint(state: State) -> tuple[Position, ...]:
    """Return the board squares occupied by the block (or split cubes)."""
    r, c = state.pos
    if state.pose is Pose.STANDING:
        return (state.pos,)
    if state.pose is Pose.HORIZONTAL:
        return (state.pos, (r, c + 1))
    if state.pose is Pose.VERTICAL:
        return (state.pos, (r + 1, c))
    if state.pose is None and state.cube2 is not None:
        return (state.pos, state.cube2)
    raise ValueError("Invalid state: split pose requires cube2")


def _check_support(
    stage: Stage, cells: tuple[Position, ...], bridges_open: frozenset[str]
) -> str | None:
    """Return 'fell' when any occupied cell is void/outside/a closed bridge.

    For this task, fragile 'F' and goal 'G' support the block. Fragile
    breakage is handled in task 2.2; switch activation in task 2.3.
    """
    for r, c in cells:
        if r < 0 or r >= len(stage.grid):
            return "fell"
        if c < 0 or c >= len(stage.grid[r]):
            return "fell"

        bridge_id = stage.bridge_cells.get((r, c))
        if bridge_id is not None:
            if bridge_id not in bridges_open:
                return "fell"
            # An open bridge supports the block even if its base grid is '.'.
            continue

        if stage.grid[r][c] == ".":
            return "fell"

    return None


def initial_state(stage: Stage) -> State:
    """Start with the intact block standing on the designated start tile."""
    return State(Pose.STANDING, stage.start, None, stage.initial_bridges_open())


def step(stage: Stage, state: State, action: Action) -> StepResult:
    """Perform one deterministic roll, or report a fall (without mutating state)."""
    if state.pose is None:
        raise NotImplementedError("tách/ghép: task 2.4")

    # Step 1: apply exactly one row of the pose/direction transition table.
    new_pose, dr, dc = ROLL[(state.pose, action.direction)]
    new = State(
        new_pose,
        (state.pos[0] + dr, state.pos[1] + dc),
        None,
        state.bridges_open,
    )

    # Step 2: the new footprint must be fully supported.
    reason = _check_support(stage, footprint(new), new.bridges_open)
    if reason:
        return StepResult(Outcome.ILLEGAL, None, reason)

    # Step 3: TODO task 2.2 - fragile tiles when the block stands on 'F'.
    # Steps 4-5: TODO task 2.3 - activate switches, update bridges, recheck.
    # Step 6: TODO task 2.4 - split/merge block and active cube control.

    # Step 7: valid normal roll.
    return StepResult(Outcome.MOVED, new)


def successors(stage: Stage, state: State) -> list[tuple[Action, State]]:
    """Return legal (action, state) successors in UP, DOWN, LEFT, RIGHT order."""
    result: list[tuple[Action, State]] = []
    for direction in (
        Direction.UP,
        Direction.DOWN,
        Direction.LEFT,
        Direction.RIGHT,
    ):
        action = Action(direction)
        transition = step(stage, state, action)
        if transition.outcome is Outcome.MOVED and transition.state is not None:
            result.append((action, transition.state))
    return result


def is_goal(stage: Stage, state: State) -> bool:
    """Only an intact, upright block over the target hole wins."""
    return state.pose is Pose.STANDING and state.cube2 is None and state.pos == stage.goal
