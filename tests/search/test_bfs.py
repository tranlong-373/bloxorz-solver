from itertools import product
from pathlib import Path

import pytest

from bloxorz.engine import Outcome, initial_state, is_goal, step
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction
from bloxorz.search import run
from bloxorz.stage import Stage
from bloxorz.verify import verify_solution

FIXTURES = Path(__file__).resolve().parents[2] / "stages" / "fixtures"
EXPECTED_LEN = {"basic_01": 2, "basic_02": 4, "basic_03": 6}
UNSOLVABLE = [
    Stage("gap", "G1", ("##.G",), (0, 0), (0, 3)),
    # 2x2 floor has cycles: BFS needs `visited` to stop
    Stage("gap2", "G1", ("##..G", "##..#"), (0, 0), (0, 4)),
]


def fixture(name):
    return load_stage(FIXTURES / f"{name}.json")


def reaches_goal(stage, actions):
    """Independent replay; False if any move is illegal."""
    s = initial_state(stage)
    for a in actions:
        r = step(stage, s, a)
        if r.outcome is Outcome.ILLEGAL:
            return False
        s = r.state
    return is_goal(stage, s)


def test_one_row_stage():
    r = run("bfs", Stage("one", "G1", ("###G",), (0, 0), (0, 3)))
    assert r.status == "solved" and r.length == 2
    assert all(a == Action(Direction.RIGHT) for a in r.actions)


def test_start_is_goal():
    stage = Stage("here", "G1", ("G",), (0, 0), (0, 0))
    r = run("bfs", stage)
    assert r.status == "solved" and r.actions == ()
    assert verify_solution(stage, ()) == (True, "")


@pytest.mark.parametrize("stage", UNSOLVABLE, ids=lambda s: s.id)
def test_unsolvable_stage(stage):
    r = run("bfs", stage)
    assert r.status == "unsolvable" and r.expanded > 0


@pytest.mark.parametrize("name", EXPECTED_LEN)
def test_fixture_shortest_and_valid(name):
    stage = fixture(name)
    r = run("bfs", stage)
    assert r.status == "solved" and r.length == EXPECTED_LEN[name]
    assert verify_solution(stage, r.actions) == (True, "")


@pytest.mark.parametrize("name", EXPECTED_LEN)
def test_no_shorter_plan_exists(name):
    # Independent of BFS: try every action sequence shorter than the BFS answer.
    stage = fixture(name)
    for n in range(1, EXPECTED_LEN[name]):
        for seq in product(Direction, repeat=n):
            assert not reaches_goal(stage, [Action(d) for d in seq])


@pytest.mark.parametrize("name", EXPECTED_LEN)
def test_bfs_not_longer_than_dfs(name):
    stage = fixture(name)
    assert run("bfs", stage).length <= run("dfs", stage).length


def test_bfs_is_deterministic():
    stage = fixture("basic_03")
    assert run("bfs", stage).actions == run("bfs", stage).actions


def test_verify_rejects_changed_action():
    stage = fixture("basic_01")
    actions = list(run("bfs", stage).actions)
    actions[0] = Action(Direction.UP)
    ok, _ = verify_solution(stage, actions)
    assert ok is False


def test_verify_reports_fall():
    ok, msg = verify_solution(fixture("basic_01"), [Action(Direction.UP)])
    assert ok is False and msg.startswith("bước") and "fell" in msg


def test_verify_not_at_goal():
    stage = fixture("basic_01")
    assert verify_solution(stage, [Action(Direction.RIGHT)]) == (False, "chưa tới đích")
    assert verify_solution(stage, []) == (False, "chưa tới đích")
