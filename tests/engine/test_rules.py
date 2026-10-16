"""Task 2.1 tests: falls, victory, footprints, successor order, and bridges."""

import pytest

from bloxorz.engine import (
    Action, Direction, Outcome, Pose, Stage, State,
    initial_state, is_goal, step, successors,
)
from bloxorz.engine.rules import ROLL, footprint


def open_stage(**kwargs):
    rows = ("#######",) * 6 + ("######G",)
    return Stage(
        id="open7", group="G1", grid=rows,
        start=(3, 3), goal=(6, 6), **kwargs,
    )


def test_transition_table_has_exactly_twelve_entries():
    assert len(ROLL) == 12
    assert set(ROLL) == {(p, d) for p in Pose for d in Direction}


@pytest.mark.parametrize(
    "pose, expected",
    [
        (Pose.STANDING, ((3, 3),)),
        (Pose.HORIZONTAL, ((3, 3), (3, 4))),
        (Pose.VERTICAL, ((3, 3), (4, 3))),
    ],
)
def test_footprint(pose, expected):
    assert footprint(State(pose, (3, 3))) == expected


def test_split_footprint_only():
    assert footprint(State(None, (2, 2), (4, 4))) == ((2, 2), (4, 4))


def test_split_step_is_explicitly_not_implemented():
    with pytest.raises(NotImplementedError, match="task 2.4"):
        step(open_stage(), State(None, (2, 2), (4, 4)), Action(Direction.RIGHT))


def test_initial_state_standing_with_initial_bridges():
    stage = open_stage(open_bridges_at_start=frozenset({"bridge_A"}))
    assert initial_state(stage) == State(
        Pose.STANDING, (3, 3), None, frozenset({"bridge_A"})
    )


def test_void_tile_inside_board_causes_fall():
    rows = list(open_stage().grid)
    rows[3] = rows[3][:4] + "." + rows[3][5:]
    stage = Stage("void7", "G1", tuple(rows), (3, 3), (6, 6))
    result = step(stage, State(Pose.STANDING, (3, 3)), Action(Direction.RIGHT))
    assert result.outcome is Outcome.ILLEGAL
    assert result.state is None
    assert result.reason == "fell"


def test_fragile_tile_is_supported_for_now():
    rows = list(open_stage().grid)
    rows[3] = rows[3][:4] + "F" + rows[3][5:]
    stage = Stage("fragile", "G1", tuple(rows), (3, 3), (6, 6))
    result = step(stage, State(Pose.STANDING, (3, 3)), Action(Direction.RIGHT))
    assert result.outcome is Outcome.MOVED  # Fragile breakage: future task 2.2.


def test_closed_bridge_causes_fall_and_open_bridge_supports():
    stage = open_stage(bridge_cells={(3, 4): "bridge_A"})
    action = Action(Direction.RIGHT)
    closed = step(stage, State(Pose.STANDING, (3, 3)), action)
    assert closed.outcome is Outcome.ILLEGAL
    assert closed.reason == "fell"

    opened = step(
        stage,
        State(Pose.STANDING, (3, 3), None, frozenset({"bridge_A"})),
        action,
    )
    assert opened.outcome is Outcome.MOVED
    assert opened.state.bridges_open == frozenset({"bridge_A"})


def test_open_bridge_can_cover_void_cell():
    rows = list(open_stage().grid)
    rows[3] = rows[3][:4] + "." + rows[3][5:]
    stage = Stage(
        "bridge7", "G1", tuple(rows), (3, 3), (6, 6),
        bridge_cells={(3, 4): "A"},
        open_bridges_at_start=frozenset({"A"}),
    )
    result = step(stage, initial_state(stage), Action(Direction.RIGHT))
    assert result.outcome is Outcome.MOVED


def test_standing_on_goal_wins():
    assert is_goal(open_stage(), State(Pose.STANDING, (6, 6)))


@pytest.mark.parametrize(
    "state", [
        State(Pose.HORIZONTAL, (6, 5)),
        State(Pose.VERTICAL, (5, 6)),
        State(None, (6, 6), (6, 5)),
        State(Pose.STANDING, (3, 3)),
    ],
)
def test_not_won_when_lying_split_or_elsewhere(state):
    assert not is_goal(open_stage(), state)


def test_successors_corner_order_and_states():
    stage = open_stage()
    result = successors(stage, State(Pose.STANDING, (0, 0)))
    assert result == [
        (Action(Direction.DOWN), State(Pose.VERTICAL, (1, 0))),
        (Action(Direction.RIGHT), State(Pose.HORIZONTAL, (0, 1))),
    ]


def test_successors_all_four_order():
    stage = open_stage()
    result = successors(stage, initial_state(stage))
    assert [a.direction for a, _ in result] == list(Direction)
