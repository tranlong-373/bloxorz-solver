"""Split-switch teleportation, single-cube moves, and rejoining (task 2.4)."""

from __future__ import annotations

from collections.abc import Callable

from bloxorz.model import Action, Direction, Pos, Pose, State
from bloxorz.stage import Stage

from .switches import apply_switches


SupportCheck = Callable[[Stage, tuple[Pos, ...], frozenset[str]], str | None]

_CUBE_MOVE: dict[Direction, Pos] = {
    Direction.UP: (-1, 0),
    Direction.DOWN: (1, 0),
    Direction.LEFT: (0, -1),
    Direction.RIGHT: (0, 1),
}


def split_on_landing(stage: Stage, state: State) -> State | None:
    """Teleport an intact standing block from a split switch, if present.

    No switch at either destination is triggered during the teleport.
    Bridge states are preserved (split switches never control bridges).
    """
    if state.pose is not Pose.STANDING:
        return None

    for switch in stage.switch_at.get(state.pos, ()):
        if switch.kind == "split":
            if switch.targets is None:
                raise ValueError(f"Split switch {switch.id!r} has no targets")
            return State(None, switch.targets[0], switch.targets[1], state.bridges_open)

    return None


def merge_adjacent(state: State) -> State | None:
    """Rejoin two neighboring cubes with the top-left position convention."""
    if state.pose is not None or state.cube2 is None:
        return None

    r1, c1 = state.pos
    r2, c2 = state.cube2
    if abs(r1 - r2) + abs(c1 - c2) != 1:
        return None

    pose = Pose.HORIZONTAL if r1 == r2 else Pose.VERTICAL
    return State(pose, state.pos, None, state.bridges_open)


def move_cube(
    stage: Stage,
    state: State,
    action: Action,
    check_support: SupportCheck,
) -> tuple[State | None, str, tuple[str, ...]]:
    """Move one cube by one tile; return (next_state, reason, events).

    ``next_state`` is None for an illegal move. Only the moving cube presses
    landing switches; both cubes must remain supported after bridge changes.
    A merge does not activate switches again.
    """
    if state.pose is not None or state.cube2 is None:
        raise ValueError("A split state with two cubes is required")
    if action.cube is None:
        raise NotImplementedError(
            "task 2.4 requires an explicit cube=0 or cube=1 for split moves"
        )
    if action.cube not in (0, 1):
        raise ValueError("Split actions require cube=0 or cube=1")

    positions = (state.pos, state.cube2)
    moving = positions[action.cube]
    stationary = positions[1 - action.cube]
    dr, dc = _CUBE_MOVE[action.direction]
    landed = (moving[0] + dr, moving[1] + dc)

    # Valid play never overlaps cubes: they merge as soon as adjacent.
    if landed == stationary:
        raise ValueError("Two cubes cannot occupy the same cell")

    if check_support(stage, (landed,), state.bridges_open):
        return None, "fell", ()

    # A single cube does not break 'F' and can only trigger soft switches.
    updated_bridges, events = apply_switches(
        stage, (landed,), "cube", state.bridges_open
    )

    if check_support(stage, (landed, stationary), updated_bridges):
        return None, "bridge_closed", events

    next_state = State(None, landed, stationary, updated_bridges)
    merged = merge_adjacent(next_state)
    if merged is not None:
        return merged, "", events + ("merge",)

    return next_state, "", events
