"""Task 2.4: split switches, individual cubes, merging, and a complete level."""

import pytest
import json


from bloxorz.engine import Outcome, initial_state, is_goal, step, successors
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Bridge, Stage, Switch


U, D, L, R = Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT


def stage_for_split(*, switches=(), bridges=(), void=(), fragile=(),
                    start=(3, 3), goal=(6, 7)):
    """Build a real 7x8 Stage; preserve the shared Stage/State/Action types."""
    grid = [list("########") for _ in range(7)]
    for bridge in bridges:
        for r, c in bridge.cells:
            grid[r][c] = "B"
    for r, c in void:
        grid[r][c] = "."
    for r, c in fragile:
        grid[r][c] = "F"
    grid[goal[0]][goal[1]] = "G"
    return Stage(
        id="split7", group="G4", grid=tuple("".join(row) for row in grid),
        start=start, goal=goal,
        bridges=tuple(bridges), switches=tuple(switches),
    )


def split_switch(*, pos=(3, 5), targets=((2, 2), (2, 5))):
    return Switch("split1", "split", pos, targets=targets)


def toggle(*, pos=(3, 3), kind="soft", bridge_id="b1"):
    return Switch("sw1", kind, pos, mode="toggle", bridges=(bridge_id,))


def move(state, stage, direction, cube):
    return step(stage, state, Action(direction, cube=cube))


def assert_moved(result, expected_state, events=()):
    assert result.outcome is Outcome.MOVED
    assert result.reason == ""
    assert result.state == expected_state
    assert result.events == events


def test_standing_on_split_teleports_sorts_cubes_and_keeps_bridges():
    stage = stage_for_split(
        switches=(split_switch(targets=((2, 5), (2, 2))),),
        bridges=(Bridge("b1", ((1, 1),), initially_open=True),),
    )
    before = State(Pose.HORIZONTAL, (3, 3), None, frozenset({"b1"}))
    result = step(stage, before, Action(R))
    assert_moved(result, State(None, (2, 2), (2, 5), frozenset({"b1"})), ("split",))
    assert result.state.pos < result.state.cube2
    assert before.pose is Pose.HORIZONTAL  # Immutable shared State.


def test_lying_on_split_switch_does_not_split():
    stage = stage_for_split(switches=(split_switch(pos=(3, 4)),))
    assert_moved(
        step(stage, State(Pose.STANDING, (3, 3)), Action(R)),
        State(Pose.HORIZONTAL, (3, 4)),
    )


def test_split_does_not_activate_switches_at_teleport_destinations():
    stage = stage_for_split(
        switches=(
            split_switch(),
            toggle(pos=(2, 2)),
            Switch("h1", "heavy", (2, 5), mode="toggle", bridges=("b1",)),
        ),
        bridges=(Bridge("b1", ((1, 1),)),),
    )
    result = step(stage, State(Pose.HORIZONTAL, (3, 3)), Action(R))
    assert_moved(result, State(None, (2, 2), (2, 5)), ("split",))


def test_split_preserves_switch_events_from_original_landing_tile():
    stage = stage_for_split(
        switches=(split_switch(), toggle(pos=(3, 5))),
        bridges=(Bridge("b1", ((1, 1),)),),
    )
    result = step(stage, State(Pose.HORIZONTAL, (3, 3)), Action(R))
    assert_moved(
        result, State(None, (2, 2), (2, 5), frozenset({"b1"})),
        ("switch:sw1", "bridge:b1:open", "split"),
    )


@pytest.mark.parametrize("cube,direction,dest", [
    (0, U, (2, 2)), (0, D, (4, 2)), (0, L, (3, 1)), (0, R, (3, 3)),
    (1, U, (2, 6)), (1, D, (4, 6)), (1, L, (3, 5)), (1, R, (3, 7)),
])
def test_each_cube_can_move_one_tile_in_four_directions(cube, direction, dest):
    stage = stage_for_split()
    before = State(None, (3, 2), (3, 6))
    result = move(before, stage, direction, cube)
    stationary = before.cube2 if cube == 0 else before.pos
    assert_moved(result, State(None, dest, stationary))
    assert before == State(None, (3, 2), (3, 6))


@pytest.mark.parametrize("state,direction,cube,void,bridges", [
    (State(None, (0, 2), (3, 6)), U, 0, (), ()),       # Off board.
    (State(None, (3, 2), (3, 6)), U, 0, ((2, 2),), ()), # Void.
    (State(None, (3, 2), (3, 6)), U, 0, (),
     (Bridge("b1", ((2, 2),), initially_open=False),)), # Closed bridge.
])
def test_cube_falls_from_void_edge_or_closed_bridge(state, direction, cube, void, bridges):
    stage = stage_for_split(void=void, bridges=bridges)
    result = move(state, stage, direction, cube)
    assert result.outcome is Outcome.ILLEGAL
    assert result.state is None
    assert result.reason == "fell"
    assert result.events == ()


def test_cube_can_land_on_open_bridge():
    stage = stage_for_split(bridges=(Bridge("b1", ((2, 2),)),))
    before = State(None, (3, 2), (3, 6), frozenset({"b1"}))
    assert_moved(
        move(before, stage, U, 0),
        State(None, (2, 2), (3, 6), frozenset({"b1"})),
    )


def test_cube_on_fragile_is_safe():
    stage = stage_for_split(fragile=((2, 2),))
    assert_moved(move(State(None, (3, 2), (3, 6)), stage, U, 0),
                 State(None, (2, 2), (3, 6)))


def test_cube_on_goal_never_wins():
    stage = stage_for_split(goal=(2, 2))
    result = move(State(None, (3, 2), (3, 6)), stage, U, 0)
    assert result.outcome is Outcome.MOVED
    assert result.state.pos == stage.goal
    assert not is_goal(stage, result.state)


def test_soft_switch_activated_by_moving_cube_only():
    stage = stage_for_split(
        switches=(toggle(pos=(3, 3)),), bridges=(Bridge("b1", ((1, 1),)),),
    )
    result = move(State(None, (3, 2), (3, 6)), stage, R, 0)
    assert_moved(
        result, State(None, (3, 3), (3, 6), frozenset({"b1"})),
        ("switch:sw1", "bridge:b1:open"),
    )


def test_stationary_cube_does_not_retrigger_its_soft_switch():
    stage = stage_for_split(
        switches=(toggle(pos=(3, 6)),), bridges=(Bridge("b1", ((1, 1),)),),
    )
    assert_moved(move(State(None, (3, 2), (3, 6)), stage, R, 0),
                 State(None, (3, 3), (3, 6)))


def test_heavy_switch_does_not_activate_from_cube():
    stage = stage_for_split(
        switches=(toggle(pos=(3, 3), kind="heavy"),),
        bridges=(Bridge("b1", ((1, 1),)),),
    )
    assert_moved(move(State(None, (3, 2), (3, 6)), stage, R, 0),
                 State(None, (3, 3), (3, 6)))


def test_cube_does_not_retrigger_split_switch():
    stage = stage_for_split(switches=(split_switch(pos=(3, 3)),))
    assert_moved(move(State(None, (3, 2), (3, 6)), stage, R, 0),
                 State(None, (3, 3), (3, 6)))


def test_closing_bridge_under_stationary_cube_is_illegal_and_keeps_events():
    stage = stage_for_split(
        switches=(toggle(pos=(3, 3)),),
        bridges=(Bridge("b1", ((3, 6),), initially_open=True),),
    )
    before = State(None, (3, 2), (3, 6), frozenset({"b1"}))
    result = move(before, stage, R, 0)
    assert result.outcome is Outcome.ILLEGAL
    assert result.state is None
    assert result.reason == "bridge_closed"
    assert result.events == ("switch:sw1", "bridge:b1:close")


def test_closing_bridge_under_moving_cube_is_illegal_and_keeps_events():
    stage = stage_for_split(
        switches=(toggle(pos=(3, 3)),),
        bridges=(Bridge("b1", ((3, 3),), initially_open=True),),
    )
    before = State(None, (3, 2), (3, 6), frozenset({"b1"}))
    result = move(before, stage, R, 0)
    assert result.outcome is Outcome.ILLEGAL
    assert result.reason == "bridge_closed"
    assert result.events == ("switch:sw1", "bridge:b1:close")


@pytest.mark.parametrize("before,action,expected", [
    (State(None, (3, 2), (3, 4)), Action(R, cube=0),
     State(Pose.HORIZONTAL, (3, 3))),
    (State(None, (2, 3), (4, 3)), Action(D, cube=0),
     State(Pose.VERTICAL, (3, 3))),
])
def test_merges_horizontal_or_vertical_when_adjacent(before, action, expected):
    stage = stage_for_split()
    assert_moved(step(stage, before, action), expected, ("merge",))


def test_merging_does_not_activate_switches_a_second_time():
    stage = stage_for_split(
        switches=(toggle(pos=(3, 3)),), bridges=(Bridge("b1", ((1, 1),)),),
    )
    result = move(State(None, (3, 2), (3, 4)), stage, R, 0)
    assert_moved(result, State(Pose.HORIZONTAL, (3, 3), None, frozenset({"b1"})),
                 ("switch:sw1", "bridge:b1:open", "merge"))


def test_cube1_overtakes_cube0_and_state_reorders_indices():
    stage = stage_for_split()
    before = State(None, (3, 2), (3, 6))
    result = move(before, stage, U, 1)
    assert_moved(result, State(None, (2, 6), (3, 2)))
    assert result.state.pos == (2, 6)
    assert result.state.cube2 == (3, 2)
    # After sorting, cube 1 now refers to the formerly lower-indexed cube.
    next_result = move(result.state, stage, L, 1)
    assert_moved(next_result, State(None, (2, 6), (3, 1)))


def test_successors_split_order_cube0_then_cube1_u_d_l_r():
    stage = stage_for_split()
    state = State(None, (3, 2), (3, 6))
    actions = [action for action, _ in successors(stage, state)]
    assert actions == [Action(d, cube=cube) for cube in (0, 1) for d in (U, D, L, R)]


def test_successors_skip_falls_in_correct_order():
    stage = stage_for_split()
    state = State(None, (0, 0), (6, 7))
    actions = [action for action, _ in successors(stage, state)]
    assert actions == [Action(D, cube=0), Action(R, cube=0),
                       Action(U, cube=1), Action(L, cube=1)]


def test_split_action_requires_explicit_cube_index():
    with pytest.raises(NotImplementedError, match="cube=0 or cube=1"):
        step(stage_for_split(), State(None, (3, 2), (3, 6)), Action(R))


@pytest.mark.parametrize("state,action", [
    (State(None, (3, 2), (3, 6)), Action(R, cube=2)),
    (State(Pose.STANDING, (3, 3)), Action(R, cube=0)),
])
def test_invalid_cube_selection_rejected(state, action):
    with pytest.raises(ValueError):
        step(stage_for_split(), state, action)


def test_complete_stage_split_move_merge_and_win():
    """Play an entire level from initial_state to goal using fixed actions."""
    stage = stage_for_split(
        start=(3, 3), goal=(2, 6),
        switches=(split_switch(pos=(3, 6), targets=((2, 2), (2, 5))),),
    )
    state = initial_state(stage)
    actions = (Action(R), Action(R), Action(R, cube=0),
               Action(R, cube=0), Action(R))
    all_events = []
    for i, action in enumerate(actions):
        result = step(stage, state, action)
        assert result.outcome is Outcome.MOVED, (i, result)
        assert result.state is not None
        all_events.extend(result.events)
        state = result.state
        if i < len(actions) - 1:
            assert not is_goal(stage, state)

    assert all_events == ["split", "merge"]
    assert state == State(Pose.STANDING, (2, 6))
    assert is_goal(stage, state)


def test_split_target_on_start_tile_is_normalized_by_json_loader(tmp_path):
    """A split target may refer to S; loader makes S a supporting # tile."""
    stage_data = {
        "id": "split_target_start",
        "group": "G4",
        "grid": [
            "########",
            "#S######",
            "########",
            "########",
            "########",
            "########",
            "#######G",
        ],
        "switches": [{
            "id": "split1",
            "kind": "split",
            "pos": [3, 4],
            "targets": [[2, 5], [1, 1]],
        }],
    }
    json_path = tmp_path / "split_target_start.json"
    json_path.write_text(json.dumps(stage_data), encoding="utf-8")

    stage = load_stage(json_path)
    assert stage.start == (1, 1)
    assert stage.cell(stage.start) == "#"
    assert all("S" not in row for row in stage.grid)
    assert stage.switch_at[(3, 4)][0].targets == ((2, 5), (1, 1))

    # Horizontal (3, 2) -> RIGHT -> standing (3, 4): activate split.
    result = step(stage, State(Pose.HORIZONTAL, (3, 2)), Action(R))
    assert_moved(result, State(None, (1, 1), (2, 5)), ("split",))
    assert result.state.pos < result.state.cube2


def test_cube_triggers_all_soft_switches_on_same_cell_in_id_order():
    """All same-cell switches fire in ID order, regardless of declaration order."""
    stage = stage_for_split(
        switches=(
            Switch("z_second", "soft", (3, 3), mode="toggle", bridges=("b2",)),
            Switch("a_first", "soft", (3, 3), mode="toggle", bridges=("b1",)),
        ),
        bridges=(
            Bridge("b1", ((1, 1),)),
            Bridge("b2", ((1, 2),)),
        ),
    )
    assert tuple(s.id for s in stage.switch_at[(3, 3)]) == ("a_first", "z_second")

    result = move(State(None, (3, 2), (3, 6)), stage, R, 0)
    assert_moved(
        result,
        State(None, (3, 3), (3, 6), frozenset({"b1", "b2"})),
        (
            "switch:a_first", "bridge:b1:open",
            "switch:z_second", "bridge:b2:open",
        ),
    )


def test_multiple_soft_switches_recheck_support_of_stationary_cube():
    """Closing a bridge under the OTHER cube rejects the move after all switches."""
    stage = stage_for_split(
        switches=(
            Switch("z_close", "soft", (3, 3), mode="toggle", bridges=("b2",)),
            Switch("a_open", "soft", (3, 3), mode="toggle", bridges=("b1",)),
        ),
        bridges=(
            Bridge("b1", ((1, 1),)),
            Bridge("b2", ((3, 6),), initially_open=True),
        ),
    )
    before = State(None, (3, 2), (3, 6), frozenset({"b2"}))
    result = move(before, stage, R, 0)

    assert result.outcome is Outcome.ILLEGAL
    assert result.state is None
    assert result.reason == "bridge_closed"
    assert result.events == (
        "switch:a_open", "bridge:b1:open",
        "switch:z_close", "bridge:b2:close",
    )
    # No state change on an illegal action, even though events describe switches.
    assert before.bridges_open == frozenset({"b2"})
