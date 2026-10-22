"""Task 2.3: soft/heavy switches, bridge updates, and landing validation."""

import pytest

from bloxorz.engine import Outcome, StepResult, initial_state, step, successors
from bloxorz.engine.switches import apply_switches
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Bridge, Stage, Switch


def make_stage(*, bridges=(), switches=(), void=(), fragile=()):
    """Real 7x7 Stage with switches on floor and bridges marked 'B'."""
    grid = [list("#######") for _ in range(7)]
    grid[6][6] = "G"
    for bridge in bridges:
        for r, c in bridge.cells:
            grid[r][c] = "B"
    for r, c in void:
        grid[r][c] = "."
    for r, c in fragile:
        grid[r][c] = "F"
    return Stage(
        id="switch7", group="G3", grid=tuple("".join(row) for row in grid),
        start=(3, 3), goal=(6, 6), bridges=tuple(bridges), switches=tuple(switches),
    )


def toggle(kind="soft", *, pos=(3, 4), switch_id="sw1", links=("b1",), set_to="open"):
    return Switch(switch_id, kind, pos, "toggle", set_to=set_to, bridges=links)


def permanent(set_to, *, kind="soft", pos=(3, 4), switch_id="sw1", links=("b1",)):
    return Switch(switch_id, kind, pos, "permanent", set_to=set_to, bridges=links)


def bridge(*, bridge_id="b1", cell=(1, 1), initially_open=False):
    return Bridge(bridge_id, (cell,), initially_open)


@pytest.mark.parametrize("piece", ["standing", "lying", "cube"])
def test_soft_activates_for_all_piece_types(piece):
    stage = make_stage(bridges=(bridge(),), switches=(toggle(),))
    opened, events = apply_switches(stage, ((3, 4),), piece, frozenset())
    assert opened == frozenset({"b1"})
    assert events == ("switch:sw1", "bridge:b1:open")


@pytest.mark.parametrize("piece, activated", [
    ("standing", True), ("lying", False), ("cube", False),
])
def test_heavy_activates_only_for_intact_standing(piece, activated):
    stage = make_stage(bridges=(bridge(),), switches=(toggle("heavy"),))
    opened, events = apply_switches(stage, ((3, 4),), piece, frozenset())
    assert opened == (frozenset({"b1"}) if activated else frozenset())
    assert events == (("switch:sw1", "bridge:b1:open") if activated else ())


def test_split_switch_is_reserved_for_task_2_4():
    stage = make_stage(switches=(Switch("sp", "split", (3, 4), targets=((1, 1), (1, 2))),))
    assert apply_switches(stage, ((3, 4),), "standing", frozenset()) == (frozenset(), ())


def test_toggle_twice_restores_original_bridge_state():
    stage = make_stage(bridges=(bridge(),), switches=(toggle(),))
    first, first_events = apply_switches(stage, ((3, 4),), "lying", frozenset())
    second, second_events = apply_switches(stage, ((3, 4),), "lying", first)
    assert first == frozenset({"b1"})
    assert first_events == ("switch:sw1", "bridge:b1:open")
    assert second == frozenset()
    assert second_events == ("switch:sw1", "bridge:b1:close")


def test_toggle_ignores_set_to_close():
    stage = make_stage(bridges=(bridge(),), switches=(toggle(set_to="close"),))
    opened, events = apply_switches(stage, ((3, 4),), "standing", frozenset())
    assert opened == frozenset({"b1"})
    assert events == ("switch:sw1", "bridge:b1:open")


def test_permanent_open_twice_does_not_generate_duplicate_bridge_event():
    stage = make_stage(bridges=(bridge(),), switches=(permanent("open"),))
    first, e1 = apply_switches(stage, ((3, 4),), "lying", frozenset())
    second, e2 = apply_switches(stage, ((3, 4),), "lying", first)
    assert first == second == frozenset({"b1"})
    assert e1 == ("switch:sw1", "bridge:b1:open")
    assert e2 == ("switch:sw1",)


def test_permanent_close_changes_open_bridge_only_once():
    stage = make_stage(bridges=(bridge(initially_open=True),), switches=(permanent("close"),))
    first, e1 = apply_switches(stage, ((3, 4),), "standing", frozenset({"b1"}))
    second, e2 = apply_switches(stage, ((3, 4),), "standing", first)
    assert first == second == frozenset()
    assert e1 == ("switch:sw1", "bridge:b1:close")
    assert e2 == ("switch:sw1",)


def test_unoccupied_switch_is_not_triggered():
    stage = make_stage(bridges=(bridge(),), switches=(toggle(),))
    assert apply_switches(stage, ((2, 3), (2, 4)), "lying", frozenset()) == (
        frozenset(), ()
    )


def test_two_soft_switches_sorted_by_id_even_if_cells_reversed():
    switches = (
        toggle(pos=(3, 4), switch_id="z", links=("b1",)),
        toggle(pos=(3, 5), switch_id="a", links=("b1",)),
    )
    stage = make_stage(bridges=(bridge(),), switches=switches)
    opened, events = apply_switches(stage, ((3, 4), (3, 5)), "lying", frozenset())
    assert opened == frozenset()  # Two toggles of the same bridge cancel.
    assert events == (
        "switch:a", "bridge:b1:open", "switch:z", "bridge:b1:close",
    )


def test_multiple_linked_bridges_have_events_in_declared_order():
    stage = make_stage(
        bridges=(bridge(bridge_id="b1"), bridge(bridge_id="b2", cell=(1, 2), initially_open=True)),
        switches=(toggle(links=("b2", "b1")),),
    )
    opened, events = apply_switches(stage, ((3, 4),), "standing", frozenset({"b2"}))
    assert opened == frozenset({"b1"})
    assert events == ("switch:sw1", "bridge:b2:close", "bridge:b1:open")


def test_permanent_emits_only_bridges_that_actually_change():
    stage = make_stage(
        bridges=(bridge(bridge_id="b1", initially_open=True), bridge(bridge_id="b2", cell=(1, 2))),
        switches=(permanent("open", links=("b1", "b2")),),
    )
    opened, events = apply_switches(stage, ((3, 4),), "lying", frozenset({"b1"}))
    assert opened == frozenset({"b1", "b2"})
    assert events == ("switch:sw1", "bridge:b2:open")


@pytest.mark.parametrize("before, action, switch_pos, expected_pose, expected_pos", [
    (State(Pose.HORIZONTAL, (3, 3)), Direction.RIGHT, (3, 5), Pose.STANDING, (3, 5)),
    (State(Pose.STANDING, (3, 3)), Direction.RIGHT, (3, 4), Pose.HORIZONTAL, (3, 4)),
])
def test_step_soft_switch_works_while_standing_or_lying(
    before, action, switch_pos, expected_pose, expected_pos
):
    stage = make_stage(
        bridges=(bridge(),), switches=(toggle(pos=switch_pos),)
    )
    result = step(stage, before, Action(action))
    assert result == StepResult(
        Outcome.MOVED,
        State(expected_pose, expected_pos, None, frozenset({"b1"})),
        events=("switch:sw1", "bridge:b1:open"),
    )
    assert before.bridges_open == frozenset()  # State is immutable.


@pytest.mark.parametrize("before, switch_pos, expected_open, expected_events", [
    (
        State(Pose.HORIZONTAL, (3, 3)), (3, 5), frozenset({"b1"}),
        ("switch:sw1", "bridge:b1:open"),
    ),
    (State(Pose.STANDING, (3, 3)), (3, 4), frozenset(), ()),
])
def test_step_heavy_switch_activates_only_upright(
    before, switch_pos, expected_open, expected_events
):
    stage = make_stage(
        bridges=(bridge(),), switches=(toggle("heavy", pos=switch_pos),)
    )
    result = step(stage, before, Action(Direction.RIGHT))
    assert result.outcome is Outcome.MOVED
    assert result.state.bridges_open == expected_open
    assert result.events == expected_events


def test_step_lying_on_two_soft_switches_activates_in_id_order():
    stage = make_stage(
        bridges=(bridge(),),
        switches=(
            toggle(pos=(3, 4), switch_id="z"),
            toggle(pos=(3, 5), switch_id="a"),
        ),
    )
    result = step(stage, State(Pose.STANDING, (3, 3)), Action(Direction.RIGHT))
    assert result.outcome is Outcome.MOVED
    assert result.state.bridges_open == frozenset()
    assert result.events == (
        "switch:a", "bridge:b1:open", "switch:z", "bridge:b1:close",
    )


def test_step_soft_switch_permanent_open_then_no_bridge_change():
    stage = make_stage(
        bridges=(bridge(),), switches=(permanent("open"),)
    )
    before = State(Pose.STANDING, (3, 3))
    first = step(stage, before, Action(Direction.RIGHT))
    assert first.outcome is Outcome.MOVED
    assert first.state.bridges_open == frozenset({"b1"})
    assert first.events == ("switch:sw1", "bridge:b1:open")
    second = step(stage, State(Pose.STANDING, (3, 3), None, first.state.bridges_open),
                  Action(Direction.RIGHT))
    assert second.outcome is Outcome.MOVED
    assert second.state.bridges_open == frozenset({"b1"})
    assert second.events == ("switch:sw1",)


def test_step_permanent_close_removes_open_bridge():
    stage = make_stage(
        bridges=(bridge(initially_open=True),), switches=(permanent("close"),)
    )
    result = step(stage, initial_state(stage), Action(Direction.RIGHT))
    assert result.outcome is Outcome.MOVED
    assert result.state.bridges_open == frozenset()
    assert result.events == ("switch:sw1", "bridge:b1:close")


@pytest.mark.parametrize("initially_open, expected_outcome, expected_reason", [
    (False, Outcome.ILLEGAL, "fell"), (True, Outcome.MOVED, ""),
])
def test_rolling_onto_bridge_depends_on_open_state(
    initially_open, expected_outcome, expected_reason
):
    stage = make_stage(bridges=(bridge(cell=(3, 4), initially_open=initially_open),))
    assert stage.cell((3, 4)) == "B"
    assert stage.bridge_at[(3, 4)] == "b1"
    result = step(stage, initial_state(stage), Action(Direction.RIGHT))
    assert result.outcome is expected_outcome
    assert result.reason == expected_reason
    if initially_open:
        assert result.state == State(Pose.HORIZONTAL, (3, 4), None, frozenset({"b1"}))
    else:
        assert result.state is None
    assert result.events == ()


def test_bridge_closed_under_landed_lying_block_is_illegal():
    # Standing (3,3) -> horizontal (3,4) soft switch + (3,5) bridge.
    stage = make_stage(
        bridges=(bridge(cell=(3, 5), initially_open=True),),
        switches=(toggle(pos=(3, 4)),),
    )
    before = initial_state(stage)
    result = step(stage, before, Action(Direction.RIGHT))
    assert result.outcome is Outcome.ILLEGAL
    assert result.state is None
    assert result.reason == "bridge_closed"
    assert result.events == ("switch:sw1", "bridge:b1:close")
    assert before.bridges_open == frozenset({"b1"})


def test_permanent_close_under_landed_block_is_also_illegal():
    stage = make_stage(
        bridges=(bridge(cell=(3, 5), initially_open=True),),
        switches=(permanent("close", pos=(3, 4)),),
    )
    result = step(stage, initial_state(stage), Action(Direction.RIGHT))
    assert result.outcome is Outcome.ILLEGAL
    assert result.reason == "bridge_closed"
    assert result.state is None
    assert result.events == ("switch:sw1", "bridge:b1:close")


def test_switch_not_activated_when_leaving_its_tile():
    stage = make_stage(
        bridges=(bridge(),), switches=(toggle(pos=(3, 3)),)
    )
    result = step(stage, initial_state(stage), Action(Direction.RIGHT))
    assert result.outcome is Outcome.MOVED
    assert result.state.bridges_open == frozenset()
    assert result.events == ()


def test_fall_is_checked_before_switch_activation():
    stage = make_stage(
        bridges=(bridge(),), switches=(toggle(pos=(3, 4)),), void=((3, 5),)
    )
    result = step(stage, initial_state(stage), Action(Direction.RIGHT))
    assert result == StepResult(Outcome.ILLEGAL, None, "fell")
    assert result.events == ()


def test_fragile_check_kept_before_switch_activation():
    stage = make_stage(
        bridges=(bridge(),), fragile=((3, 5),), switches=(toggle(pos=(3, 4)),)
    )
    result = step(stage, State(Pose.HORIZONTAL, (3, 3)), Action(Direction.RIGHT))
    assert result == StepResult(Outcome.ILLEGAL, None, "fragile_broke")
    assert result.events == ()


def test_successors_omits_move_when_switch_closes_supporting_bridge():
    stage = make_stage(
        bridges=(bridge(cell=(3, 5), initially_open=True),),
        switches=(toggle(pos=(3, 4)),),
    )
    options = successors(stage, initial_state(stage))
    assert [action.direction for action, _ in options] == [
        Direction.UP, Direction.DOWN, Direction.LEFT,
    ]
    assert all(state.bridges_open == frozenset({"b1"}) for _, state in options)


def test_step_toggle_twice_opens_then_closes_bridge():
    stage = make_stage(bridges=(bridge(),), switches=(toggle(),))
    before = initial_state(stage)
    first = step(stage, before, Action(Direction.RIGHT))
    assert first.outcome is Outcome.MOVED
    assert first.state.bridges_open == frozenset({"b1"})
    assert first.events == ("switch:sw1", "bridge:b1:open")

    # Re-enter the switch from the same starting square with the updated bridge state.
    second_start = State(Pose.STANDING, (3, 3), None, first.state.bridges_open)
    second = step(stage, second_start, Action(Direction.RIGHT))
    assert second.outcome is Outcome.MOVED
    assert second.state.bridges_open == frozenset()
    assert second.events == ("switch:sw1", "bridge:b1:close")
    assert before.bridges_open == frozenset()


def test_initially_closed_bridge_causes_fall_before_soft_switch_can_open_it():
    stage = make_stage(
        bridges=(bridge(cell=(3, 5), initially_open=False),),
        switches=(toggle(pos=(3, 4)),),
    )
    result = step(stage, initial_state(stage), Action(Direction.RIGHT))
    assert result == StepResult(Outcome.ILLEGAL, None, "fell")
    assert result.events == ()


def test_landed_soft_and_heavy_switch_only_activates_soft_while_lying():
    stage = make_stage(
        bridges=(bridge(bridge_id="b1"), bridge(bridge_id="b2", cell=(1, 2))),
        switches=(
            toggle("heavy", pos=(3, 4), switch_id="a", links=("b1",)),
            toggle("soft", pos=(3, 5), switch_id="z", links=("b2",)),
        ),
    )
    result = step(stage, initial_state(stage), Action(Direction.RIGHT))
    assert result.outcome is Outcome.MOVED
    assert result.state.bridges_open == frozenset({"b2"})
    assert result.events == ("switch:z", "bridge:b2:open")
