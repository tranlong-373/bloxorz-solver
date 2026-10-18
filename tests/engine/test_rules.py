"""Task 2.1 tests using the project's real shared model and stage classes."""

import pytest

import bloxorz.engine as engine
import bloxorz.model as model
import bloxorz.stage as stage_module
from bloxorz.engine import (
    Action,
    Direction,
    Outcome,
    Pose,
    Stage,
    State,
    initial_state,
    is_goal,
    step,
    successors,
)
from bloxorz.engine.rules import ROLL, StepResult, _check_support, footprint
from bloxorz.stage import Bridge


def open_stage():
    rows = ("#######",) * 6 + ("######G",)
    return Stage(id="open7", group="G1", grid=rows, start=(3, 3), goal=(6, 6))


def bridge_stage(*, initially_open=False):
    """One real bridge tile at (3,4), reached by rolling right from (3,3)."""
    rows = list(open_stage().grid)
    rows[3] = rows[3][:4] + "B" + rows[3][5:]
    return Stage(
        id="bridge7",
        group="G2",
        grid=tuple(rows),
        start=(3, 3),
        goal=(6, 6),
        bridges=(Bridge(id="A", cells=((3, 4),), initially_open=initially_open),),
    )


def test_12_rolls_and_shared_class_identity():
    assert len(ROLL) == 12
    assert set(ROLL) == {(p, d) for p in Pose for d in Direction}
    assert engine.Action is model.Action
    assert engine.Direction is model.Direction
    assert engine.Pose is model.Pose
    assert engine.State is model.State
    assert engine.Stage is stage_module.Stage


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


def test_split_footprint_uses_shared_state():
    assert footprint(State(None, (2, 2), (4, 4))) == ((2, 2), (4, 4))


def test_split_movement_reserved_for_task_2_4():
    with pytest.raises(NotImplementedError, match="task 2.4"):
        step(open_stage(), State(None, (2, 2), (4, 4)), Action(Direction.RIGHT))


def test_initial_state_from_real_stage():
    st = open_stage()
    assert initial_state(st) == model.State(Pose.STANDING, st.start, None, frozenset())


def test_initially_open_bridge_is_in_initial_state():
    st = bridge_stage(initially_open=True)
    assert st.cell((3, 4)) == "B"
    assert st.bridge_at.get((3, 4)) == "A"
    assert initial_state(st).bridges_open == frozenset({"A"})


def test_interior_void_causes_fall_using_stage_cell():
    rows = list(open_stage().grid)
    rows[3] = rows[3][:4] + "." + rows[3][5:]
    st = Stage("void7", "G1", tuple(rows), (3, 3), (6, 6))
    result = step(st, State(Pose.STANDING, (3, 3)), Action(Direction.RIGHT))
    assert result == StepResult(Outcome.ILLEGAL, None, reason="fell")
    assert result.events == ()


def test_outside_board_causes_fall_using_stage_cell():
    result = step(open_stage(), State(Pose.STANDING, (0, 0)), Action(Direction.LEFT))
    assert result.outcome is Outcome.ILLEGAL
    assert result.reason == "fell"
    assert result.events == ()


def test_open_real_bridge_supports_block_closed_real_bridge_falls():
    st = bridge_stage()
    assert isinstance(st.bridges[0], Bridge)
    assert st.bridge_at[(3, 4)] == "A"
    action = model.Action(model.Direction.RIGHT)

    closed = step(st, model.State(model.Pose.STANDING, (3, 3)), action)
    assert closed == StepResult(Outcome.ILLEGAL, None, "fell")

    opened = step(st, model.State(model.Pose.STANDING, (3, 3), None, frozenset({"A"})), action)
    assert opened.outcome is Outcome.MOVED
    assert opened.state == model.State(model.Pose.HORIZONTAL, (3, 4), None, frozenset({"A"}))
    assert opened.reason == ""
    assert opened.events == ()


def test_initially_open_real_bridge_works_through_step():
    st = bridge_stage(initially_open=True)
    result = step(st, initial_state(st), Action(Direction.RIGHT))
    assert result.outcome is Outcome.MOVED
    assert result.state.bridges_open == frozenset({"A"})


def test_fragile_is_support_only_in_task_2_1():
    rows = list(open_stage().grid)
    rows[3] = rows[3][:4] + "F" + rows[3][5:]
    st = Stage("fragile7", "G1", tuple(rows), (3, 3), (6, 6))
    result = step(st, State(Pose.STANDING, (3, 3)), Action(Direction.RIGHT))
    assert result.outcome is Outcome.MOVED


def test_goal_cell_has_support():
    st = open_stage()
    assert _check_support(st, (st.goal,), frozenset()) is None


def test_goal_only_when_shared_state_is_standing():
    st = open_stage()
    assert is_goal(st, model.State(model.Pose.STANDING, st.goal))


@pytest.mark.parametrize(
    "state",
    [
        State(Pose.HORIZONTAL, (6, 5)),
        State(Pose.VERTICAL, (5, 6)),
        State(None, (6, 5), (6, 6)),
        State(Pose.STANDING, (3, 3)),
    ],
)
def test_not_goal_if_lying_split_or_elsewhere(state):
    assert not is_goal(open_stage(), state)


def test_successors_corner_only_valid_order():
    st = open_stage()
    assert successors(st, State(Pose.STANDING, (0, 0))) == [
        (Action(Direction.DOWN), State(Pose.VERTICAL, (1, 0))),
        (Action(Direction.RIGHT), State(Pose.HORIZONTAL, (0, 1))),
    ]


def test_successors_up_down_left_right_order():
    result = successors(open_stage(), State(Pose.STANDING, (3, 3)))
    assert [action.direction for action, _ in result] == [
        Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT
    ]


def test_stepresult_reason_and_events_defaults():
    moved = StepResult(Outcome.MOVED, State(Pose.STANDING, (3, 3)))
    assert moved.reason == ""
    assert moved.events == ()
