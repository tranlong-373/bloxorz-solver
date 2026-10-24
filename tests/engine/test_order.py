"""Task 2.5: prove the seven engine phases execute in their agreed order.

Tests use the public shared Stage/State classes; no engine implementation is
mocked except the explicit guard proving fragile rejection precedes switches.
The two contributed bench stages are also loader/BFS/playthrough regression tests.
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import pytest

from bloxorz.engine import Outcome, initial_state, is_goal, step, successors
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Bridge, Stage, Switch


U, D, L, R = (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT)
BENCH = Path(__file__).resolve().parents[2] / "stages" / "bench"


def make_stage(*, void=(), fragile=(), bridges=(), switches=(), goal=(6, 8)):
    """A supporting 7x9 board; switches are placed only on ordinary floor."""
    grid = [list("#########") for _ in range(7)]
    for bridge in bridges:
        for r, c in bridge.cells:
            grid[r][c] = "B"
    for r, c in void:
        grid[r][c] = "."
    for r, c in fragile:
        grid[r][c] = "F"
    grid[goal[0]][goal[1]] = "G"
    for switch in switches:
        assert grid[switch.pos[0]][switch.pos[1]] == "#", (
            "Switch fixtures must comply with validator: only # can hold a switch"
        )
    return Stage(
        id="order", group="G4", grid=tuple("".join(row) for row in grid),
        start=(3, 3), goal=goal,
        bridges=tuple(bridges), switches=tuple(switches),
    )


def assert_illegal(result, reason, events=()):
    assert result.outcome is Outcome.ILLEGAL
    assert result.state is None
    assert result.reason == reason
    assert result.events == events


# 1. Roll first: calculate the NEW footprint before validating support.
def test_order_01_roll_before_support_checks_both_new_cells():
    stage = make_stage(void=((3, 5),))
    before = State(Pose.STANDING, (3, 3))
    # STANDING (3,3) -> RIGHT = HORIZONTAL at (3,4), covering (3,4)-(3,5).
    assert_illegal(step(stage, before, Action(R)), "fell")
    assert before == State(Pose.STANDING, (3, 3))
    # Both cells present: the exact same roll becomes a valid horizontal state.
    ok = step(make_stage(), before, Action(R))
    assert ok.outcome is Outcome.MOVED
    assert ok.state == State(Pose.HORIZONTAL, (3, 4))


# 2. Support before switches: one unsupported footprint cell cancels the press.
def test_order_02_support_failure_precedes_switch_activation():
    stage = make_stage(
        void=((2, 3),),
        switches=(Switch("sw", "soft", (2, 2), mode="toggle", bridges=("b",)),),
        bridges=(Bridge("b", ((5, 5),)),),
    )
    before = State(Pose.HORIZONTAL, (3, 2))
    # UP -> HORIZONTAL at (2,2); switch under the first cell, void under second.
    result = step(stage, before, Action(U))
    assert_illegal(result, "fell", ())
    assert before.bridges_open == frozenset()


def test_order_02_closed_bridge_prevents_activating_other_landing_switch():
    stage = make_stage(
        bridges=(Bridge("closed", ((3, 5),)), Bridge("controlled", ((5, 5),))),
        switches=(Switch("sw", "soft", (3, 4), mode="toggle", bridges=("controlled",)),),
    )
    # RIGHT lands across switch at (3,4) and the closed bridge at (3,5).
    result = step(stage, State(Pose.STANDING, (3, 3)), Action(R))
    assert_illegal(result, "fell", ())


# 3. Fragile before switches: failed upright landing must never call step 4.
def test_order_03_fragile_rejects_before_any_switch_processing(monkeypatch):
    from bloxorz.engine import rules

    stage = make_stage(
        fragile=((3, 4),),
        switches=(Switch("nearby", "soft", (3, 3), mode="toggle", bridges=("b",)),),
        bridges=(Bridge("b", ((5, 5),), initially_open=True),),
    )
    before = State(Pose.HORIZONTAL, (3, 2), bridges_open=frozenset({"b"}))

    def must_not_reach_step_four(*_args, **_kwargs):
        pytest.fail("Switch processing ran even though fragile landing was illegal")

    monkeypatch.setattr(rules, "apply_switches", must_not_reach_step_four)
    # HORIZONTAL (3,2) -> RIGHT = STANDING on F at (3,4).
    result = step(stage, before, Action(R))
    assert_illegal(result, "fragile_broke", ())
    assert before.bridges_open == frozenset({"b"})


# 4. Switches activate in ascending ID order, not physical cell order.
def test_order_04_switch_ids_precede_cell_order_and_update_same_bridge():
    stage = make_stage(
        bridges=(Bridge("b", ((5, 5),)),),
        switches=(
            Switch("z_close", "soft", (3, 4), "permanent", "close", ("b",)),
            Switch("a_toggle", "soft", (3, 5), "toggle", bridges=("b",)),
        ),
    )
    result = step(stage, State(Pose.STANDING, (3, 3)), Action(R))
    assert result.outcome is Outcome.MOVED
    assert result.state == State(Pose.HORIZONTAL, (3, 4))
    assert result.events == (
        "switch:a_toggle", "bridge:b:open",
        "switch:z_close", "bridge:b:close",
    )


# 5. Recheck support AFTER the switches have updated bridges.
def test_order_05_bridge_closed_after_switch_has_events_but_no_state():
    stage = make_stage(
        bridges=(Bridge("b", ((3, 5),), initially_open=True),),
        switches=(Switch("closer", "soft", (3, 4), "permanent", "close", ("b",)),),
    )
    before = State(Pose.STANDING, (3, 3), bridges_open=frozenset({"b"}))
    result = step(stage, before, Action(R))
    assert_illegal(result, "bridge_closed", ("switch:closer", "bridge:b:close"))
    assert before.bridges_open == frozenset({"b"})


# 6. Split runs AFTER switches; teleported cubes press no destination switch.
def test_order_06_switch_events_before_split_and_no_destination_activation():
    stage = make_stage(
        bridges=(Bridge("b", ((5, 5),)),),
        switches=(
            Switch("z_split", "split", (3, 5), targets=((2, 2), (2, 6))),
            Switch("a_open", "soft", (3, 5), "permanent", "open", ("b",)),
            Switch("destination", "soft", (2, 2), "toggle", bridges=("b",)),
        ),
    )
    result = step(stage, State(Pose.HORIZONTAL, (3, 3)), Action(R))
    assert result.outcome is Outcome.MOVED
    assert result.state == State(None, (2, 2), (2, 6), frozenset({"b"}))
    assert result.events == ("switch:a_open", "bridge:b:open", "split")
    assert not is_goal(stage, result.state)


def test_order_06_switch_before_merge_without_double_activation():
    stage = make_stage(
        bridges=(Bridge("b", ((5, 5),)),),
        switches=(Switch("sw", "soft", (3, 3), "toggle", bridges=("b",)),),
    )
    # Moving cube 0 to (3,3) makes it adjacent to cube 1 at (3,4).
    result = step(stage, State(None, (3, 2), (3, 4)), Action(R, cube=0))
    assert result.outcome is Outcome.MOVED
    assert result.state == State(Pose.HORIZONTAL, (3, 3), bridges_open=frozenset({"b"}))
    assert result.events == ("switch:sw", "bridge:b:open", "merge")


# 7. A goal is recognized only from the FINAL valid standing state.
def test_order_07_goal_only_after_successful_upright_roll():
    stage = make_stage(goal=(3, 4))
    before = State(Pose.HORIZONTAL, (3, 2))
    assert not is_goal(stage, before)
    result = step(stage, before, Action(R))
    assert result.outcome is Outcome.MOVED
    assert result.events == ()
    assert result.state == State(Pose.STANDING, (3, 4))
    assert is_goal(stage, result.state)
    assert not is_goal(stage, State(None, (3, 4), (3, 6)))
    assert not is_goal(stage, State(Pose.HORIZONTAL, (3, 3)))


def test_order_successors_cube_zero_before_cube_one_each_u_d_l_r():
    stage = make_stage()
    state = State(None, (2, 2), (4, 6))
    actions = [action for action, _ in successors(stage, state)]
    assert actions == [Action(direction, cube=cube) for cube in (0, 1) for direction in (U, D, L, R)]


# Bench stages: loader validation, fixed human playthrough and BFS solvability.
G2_HAND_PLAY = (Action(R),) * 6
G4_HAND_PLAY = (
    Action(R), Action(R), Action(R, cube=0), Action(R), Action(R), Action(R),
)


@pytest.mark.parametrize("stage_id,group,manual,expected_events", [
    ("g2_03", "G2", G2_HAND_PLAY, ()),
    ("g4_01", "G4", G4_HAND_PLAY, ("split", "merge")),
])
def test_bench_levels_validate_and_hand_play(stage_id, group, manual, expected_events):
    from bloxorz.loader import load_stage, validate

    path = BENCH / (stage_id + ".json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert validate(data, path) == [], f"Validator rejected {path.name}"
    stage = load_stage(path)
    assert stage.id == stage_id
    assert stage.group == group

    state = initial_state(stage)
    events = []
    for action in manual:
        result = step(stage, state, action)
        assert result.outcome is Outcome.MOVED, (stage_id, action, result)
        assert result.state is not None
        events.extend(result.events)
        state = result.state
    assert is_goal(stage, state)
    assert tuple(events) == expected_events


@pytest.mark.parametrize("stage_id", ["g2_03", "g4_01"])
def test_bench_levels_are_bfs_solvable(stage_id):
    """Independent small BFS using the engine's real successors, no solver mock."""
    from bloxorz.loader import load_stage

    stage = load_stage(BENCH / (stage_id + ".json"))
    root = initial_state(stage)
    queue = deque([root])
    previous = {root: None}
    goal = None

    while queue:
        state = queue.popleft()
        if is_goal(stage, state):
            goal = state
            break
        for action, next_state in successors(stage, state):
            if next_state not in previous:
                previous[next_state] = (state, action)
                queue.append(next_state)
        assert len(previous) < 10000, "Bench puzzle exceeded expected BFS search size"

    assert goal is not None, f"BFS could not solve {stage_id}"
    moves = []
    while previous[goal] is not None:
        parent, action = previous[goal]
        moves.append(action)
        goal = parent
    moves.reverse()
    assert len(moves) == 6, (stage_id, moves)


@pytest.mark.parametrize("stage_id", ["g2_03", "g4_01"])
def test_bench_levels_project_bfs_solver(stage_id):
    """Integration: the registered project BFS must return a replayable solution."""
    from bloxorz.loader import load_stage
    from bloxorz.search import run
    import bloxorz.search.bfs  # noqa: F401  - ensure BFS is registered

    stage = load_stage(BENCH / (stage_id + ".json"))
    search_result = run("bfs", stage)
    assert search_result.status == "solved", (stage_id, search_result.message)
    assert search_result.actions

    state = initial_state(stage)
    for action in search_result.actions:
        result = step(stage, state, action)
        assert result.outcome is Outcome.MOVED, (stage_id, action, result)
        state = result.state
    assert is_goal(stage, state)
