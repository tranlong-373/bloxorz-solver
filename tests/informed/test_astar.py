"""Tests for A*: astar (relaxed heuristic) and astar_manhattan. Owner: VT5 (task 5.2)."""
from pathlib import Path
import threading

import pytest

import bloxorz.search.base
from bloxorz.engine import initial_state, step
from bloxorz.loader import load_stage
from bloxorz.model import Direction
from bloxorz.search import ALGORITHMS, Limits, run
from bloxorz.search.cost import move_cost
from bloxorz.stage import Stage, Switch
from bloxorz.verify import verify_solution

STAGES = Path(__file__).resolve().parents[2] / "stages"
FIXTURES = STAGES / "fixtures"
ASTARS = ("astar", "astar_manhattan")

# Every fixture and bench stage, plus the original stages (stage_30 is not used, decision 2026-10-21)
STAGE_FILES = (
    sorted(FIXTURES.glob("*.json"))
    + sorted((STAGES / "bench").glob("*.json"))
    + sorted(p for p in (STAGES / "original").glob("*.json") if p.stem != "stage_30")
)

TWO_PATHS_GRID = (
    "......",
    ".##FG.",
    ".#####",
    ".#####",
    "......",
)


def counterexample_2_stage():
    # Same stage as counterexample 2 in test_heuristics.py (card 5.2 step 4)
    grid = ["####" + "." * 9] + ["." * 13] * 4 + ["." * 9 + "G###"]
    switch = Switch("sp1", "split", (0, 3), targets=((5, 10), (5, 12)))
    return Stage("ce2", "G4", tuple(grid), (0, 0), (5, 9), switches=(switch,))


def _replay(stage, actions):
    """Play the actions with the engine, return (total cost, events)."""
    s = initial_state(stage)
    total, events = 0.0, []
    for a in actions:
        r = step(stage, s, a)
        assert r.state is not None, r.reason
        total += move_cost(stage, s, a, r.state)
        events += r.events
        s = r.state
    return total, events


def test_both_names_registered():
    assert set(ASTARS) <= set(ALGORITHMS)


@pytest.mark.parametrize("algorithm", ASTARS)
@pytest.mark.parametrize("path", STAGE_FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_same_cost_as_ucs(path, algorithm):
    stage = load_stage(path)
    expected = run("ucs", stage)
    r = run(algorithm, stage)
    assert r.status == expected.status, r.message
    if r.status == "solved":
        assert r.cost == expected.cost
        valid, msg = verify_solution(stage, r.actions)
        assert valid, msg
        assert _replay(stage, r.actions)[0] == r.cost


@pytest.mark.parametrize("algorithm", ["ucs", *ASTARS])
@pytest.mark.parametrize("make_stage", [
    lambda: load_stage(FIXTURES / "split_01.json"),
    counterexample_2_stage,
    lambda: load_stage(STAGES / "original" / "stage_08.json"),
    lambda: load_stage(STAGES / "original" / "stage_16.json"),
], ids=["split_01", "ce2", "stage_08", "stage_16"])
def test_split_merge_from_engine_to_verify(make_stage, algorithm):
    # Real split/merge states from the engine (task 2.4), not built by hand
    stage = make_stage()
    r = run(algorithm, stage)
    assert r.status == "solved", r.message
    valid, msg = verify_solution(stage, r.actions)
    assert valid, msg
    total, events = _replay(stage, r.actions)
    assert total == r.cost
    assert "split" in events and "merge" in events
    assert any(a.cube is not None for a in r.actions)


@pytest.mark.parametrize("algorithm", ASTARS)
def test_counterexample_2_solution(algorithm):
    stage = counterexample_2_stage()
    r = run(algorithm, stage)
    assert r.cost == 4
    assert [(a.direction, a.cube) for a in r.actions] == [
        (Direction.RIGHT, None), (Direction.RIGHT, None), (Direction.LEFT, 1), (Direction.LEFT, None),
    ]


@pytest.mark.parametrize("algorithm", ASTARS)
def test_start_is_goal(algorithm):
    stage = Stage("here", "G1", ("G",), (0, 0), (0, 0))
    r = run(algorithm, stage)
    assert r.status == "solved"
    assert r.actions == ()
    assert r.cost == 0.0


@pytest.mark.parametrize("algorithm", ASTARS)
def test_two_paths_takes_the_cheap_path_like_ucs(algorithm):
    stage = Stage("two_paths", "G1", TWO_PATHS_GRID, start=(1, 1), goal=(1, 4))
    r = run(algorithm, stage)
    assert (r.length, r.cost) == (5, 5.0)
    assert run("bfs", stage).cost == 6.0


@pytest.mark.parametrize("algorithm", ASTARS)
def test_unsolvable(algorithm):
    stage = Stage("gap", "G1", ("##..G", "##..#"), (0, 0), (0, 4))
    r = run(algorithm, stage)
    assert r.status == "unsolvable"
    assert r.expanded > 0


@pytest.mark.parametrize("algorithm", ASTARS)
def test_unsolvable_when_relaxed_h_is_inf(algorithm):
    # 1-row board: the block never stands on (0,2), relaxed h is INF from the start
    stage = Stage("row", "G1", ("##G#",), (0, 0), (0, 2))
    r = run(algorithm, stage)
    assert r.status == "unsolvable"
    assert r.expanded == 3


@pytest.mark.parametrize("algorithm", ASTARS)
def test_timeout(algorithm, monkeypatch):
    monkeypatch.setattr(bloxorz.search.base, "_CHECK_EVERY", 1)
    stage = load_stage(FIXTURES / "basic_03.json")
    r = run(algorithm, stage, limits=Limits(timeout_s=0.0))
    assert r.status == "timeout"


@pytest.mark.parametrize("algorithm", ASTARS)
def test_cancel(algorithm, monkeypatch):
    monkeypatch.setattr(bloxorz.search.base, "_CHECK_EVERY", 1)
    cancel = threading.Event()
    cancel.set()
    stage = load_stage(FIXTURES / "basic_03.json")
    r = run(algorithm, stage, limits=Limits(cancel=cancel))
    assert r.status == "cancelled"
