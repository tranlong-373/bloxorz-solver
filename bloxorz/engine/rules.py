"""Bloxorz rules engine: rolling, falling, goals, fragile tiles, and switches.

Use shared model types from bloxorz.model and Stage from bloxorz.stage.
Task 2.1 handles rolling, support, and goal checks; 
Task 2.2 handles fragile floor tiles; 
Task 2.3 handles soft/heavy switches and bridges. 
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from bloxorz.model import Action, Direction, Pos, Pose, State
from bloxorz.stage import Stage

from .switches import apply_switches
from .split import move_cube, split_on_landing



class Outcome(Enum):
    """Outcome of a single attempted move."""

    MOVED = "moved"
    ILLEGAL = "illegal"












@dataclass(frozen=True)
class StepResult:

    outcome: Outcome
    state: State | None
    reason: str = ""
    events: tuple[str, ...] = ()


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


def footprint(state: State) -> tuple[Pos, ...]:
    """Occupied cells for standing, lying, or (future) split states."""
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
    stage: Stage, cells: tuple[Pos, ...], bridges_open: frozenset[str]
) -> str | None:
    """Return 'fell' when any occupied cell lacks support.

    stage.cell(p) returns '.' for out-of-bounds and for normal void cells.
    Bridge locations use stage.bridge_at as an overlay: when open they
    support the block even if the underlying grid character is '.'.
    At this stage normal tiles '#', 'F', 'G' all support the block.
    """
    for p in cells:
        bridge_id = stage.bridge_at.get(p)
        if bridge_id is not None:
            if bridge_id not in bridges_open:
                return "fell"
            continue
        if stage.cell(p) == ".":
            return "fell"
    return None


def initial_state(stage: Stage) -> State:
    """Intact upright block at the stage start with initial bridge states."""
    return State(Pose.STANDING, stage.start, None, stage.initial_bridges_open())


def step(stage: Stage, state: State, action: Action) -> StepResult:
    """Move the block (or a selected cube), applying tiles and switches."""
    if state.pose is None:
        next_state, reason, events = move_cube(
            stage, state, action, _check_support
        )
        if reason:
            return StepResult(Outcome.ILLEGAL, None, reason, events)
        return StepResult(Outcome.MOVED, next_state, events=events)

    if action.cube is not None:
        raise ValueError("An intact block action must use cube=None")

    # Step 1: deterministic change of position and orientation.
    new_pose, dr, dc = ROLL[(state.pose, action.direction)]
    new = State(
        new_pose,
        (state.pos[0] + dr, state.pos[1] + dc),
        None,
        state.bridges_open,
    )

    # Step 2: support from floor, goal, fragile tiles, and open bridges.
    reason = _check_support(stage, footprint(new), new.bridges_open)
    if reason:
        return StepResult(Outcome.ILLEGAL, None, reason)

    # step 3: a block standing upright on a fragile tile breaks it and falls.
    # Lying across fragile tiles is safe (weight is spread over two cells).
    if new.pose is Pose.STANDING and stage.cell(new.pos) == "F":
        return StepResult(Outcome.ILLEGAL, None, "fragile_broke")
    
    # Steps 4-5: activate landed soft/heavy switches, then recheck support.
    piece = "standing" if new.pose is Pose.STANDING else "lying"
    updated_bridges, events = apply_switches(
        stage, footprint(new), piece, new.bridges_open
    )
    if _check_support(stage, footprint(new), updated_bridges):
        # The switch closed a bridge under the block. Retain events so
        # the GUI can show the switch/bridge change followed by the fall.
        return StepResult(Outcome.ILLEGAL, None, "bridge_closed", events)

    new = State(new.pose, new.pos, new.cube2, updated_bridges)

    
    # Step 6: standing on a split switch teleports into two unit cubes.
    # Teleport destinations do not activate further switches.
    
    split_state = split_on_landing(stage, new)

    if split_state is not None:
        return StepResult(
            Outcome.MOVED,
            split_state,
            events=events + ("split",)
        )

    # Step 7: valid roll. Goal detection is available via is_goal().
    return StepResult(Outcome.MOVED, new, events=events)


def successors(stage: Stage, state: State) -> list[tuple[Action, State]]:
    """All legal moves: U, D, L, R; cube 0 first, then cube 1."""
    result: list[tuple[Action, State]] = []
    directions = (
        Direction.UP,
        Direction.DOWN,
        Direction.LEFT,
        Direction.RIGHT,
    )
    cubes = (0, 1) if state.pose is None else (None,)
    for cube in cubes:
        for direction in directions:
            action = Action(direction, cube=cube)
            candidate = step(stage, state, action)
            if candidate.outcome is Outcome.MOVED and candidate.state is not None:
                result.append((action, candidate.state))
    return result


def is_goal(stage: Stage, state: State) -> bool:
    """Win only when the intact block stands upright on the goal."""
    return (
        state.pose is Pose.STANDING
        and state.cube2 is None
        and state.pos == stage.goal
    )
