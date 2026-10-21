from pathlib import Path
import threading

import pytest

import bloxorz.search.base
from bloxorz.engine import initial_state, is_goal, successors
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.search import Limits, run
from bloxorz.search.cost import FRAGILE_PENALTY, move_cost
from bloxorz.stage import Stage
from bloxorz.verify import verify_solution

FIXTURES = Path(__file__).resolve().parents[2] / "stages" / "fixtures"


# ---------------------------------------------------------------------------
# Tests for move_cost
# ---------------------------------------------------------------------------

def test_move_cost_normal_floor():
    stage = Stage("test", "G1", ("####", "####"), (0, 0), (0, 3))
    s1 = State(Pose.STANDING, (0, 0))
    a = Action(Direction.RIGHT)
    s2 = State(Pose.HORIZONTAL, (0, 1))
    assert move_cost(stage, s1, a, s2) == 1.0


def test_move_cost_fragile_floor_penalized():
    # Landing on 'F' adds FRAGILE_PENALTY (4) -> total 5.0
    stage = Stage("test", "G1", ("##F#", "####"), (0, 0), (0, 3))
    s1 = State(Pose.STANDING, (0, 0))
    a = Action(Direction.RIGHT)
    s2 = State(Pose.HORIZONTAL, (0, 1))  # lands on (0, 1) and (0, 2) which is 'F'
    assert move_cost(stage, s1, a, s2) == 1.0 + FRAGILE_PENALTY


def test_move_cost_two_fragile_tiles_penalized_only_once():
    # Horizontal block lands across two 'F' tiles at (0, 1) and (0, 2)
    # Penalty is added only once per move (+4) -> total 5.0, not 9.0
    stage = Stage("test", "G1", ("#FF#", "####"), (0, 0), (0, 3))
    s1 = State(Pose.STANDING, (0, 0))
    a = Action(Direction.RIGHT)
    s2 = State(Pose.HORIZONTAL, (0, 1))
    assert move_cost(stage, s1, a, s2) == 1.0 + FRAGILE_PENALTY


def test_move_cost_leaving_fragile_not_penalized():
    # Starts lying horizontally on 'F' tiles, rolls onto normal floor '#' at (0, 3)
    stage = Stage("test", "G1", ("#FF#", "####"), (0, 0), (0, 3))
    s1 = State(Pose.HORIZONTAL, (0, 1))
    a = Action(Direction.RIGHT)
    s2 = State(Pose.STANDING, (0, 3))
    assert move_cost(stage, s1, a, s2) == 1.0


def test_move_cost_split_resting_cube_on_fragile_not_penalized():
    # Cube 0 rests on 'F' at (0, 0); Cube 1 moves on '#' from (3, 2) to (3, 3)
    # Cubes are not adjacent, so they remain split
    stage = Stage("test", "G1", ("F###", "####", "####", "####"), (0, 0), (3, 3))
    s1 = State(None, (0, 0), cube2=(3, 2))
    a = Action(Direction.RIGHT, cube=1)
    s2 = State(None, (0, 0), cube2=(3, 3))
    # Moved piece is cube 1 (at 3, 3 = '#'), resting cube is cube 0 (at 0, 0 = 'F')
    assert move_cost(stage, s1, a, s2) == 1.0


def test_move_cost_split_moved_cube_on_fragile_penalized():
    # Cube 0 moves onto 'F' at (0, 1); Cube 1 rests at (3, 3) (far away, not adjacent)
    stage = Stage("test", "G1", ("#F##", "####", "####", "####"), (0, 0), (3, 3))
    s1 = State(None, (0, 0), cube2=(3, 3))
    a = Action(Direction.RIGHT, cube=0)
    s2 = State(None, (0, 1), cube2=(3, 3))
    assert move_cost(stage, s1, a, s2) == 1.0 + FRAGILE_PENALTY


def test_move_cost_split_cubes_swap_order_in_state():
    # In State, pos < cube2 is always maintained.
    # Before: Cube 0 at (0, 5), Cube 1 at (2, 2) -> pos=(0, 5), cube2=(2, 2)
    # Cube 1 moves UP to (0, 1) on 'F'.
    # After: (0, 1) < (0, 5), so pos=(0, 1), cube2=(0, 5).
    # Moved cube (at 0, 1) swapped position in State tuple, but must be correctly identified!
    stage = Stage("test", "G1", ("#F###.", "######", "######"), (0, 0), (0, 5))
    s1 = State(None, (0, 5), cube2=(2, 2))
    a = Action(Direction.UP, cube=1)
    s2 = State(None, (0, 1), cube2=(0, 5))
    assert move_cost(stage, s1, a, s2) == 1.0 + FRAGILE_PENALTY


def test_move_cost_split_merge_onto_normal_floor_with_cube_resting_on_fragile():
    # Cube 0 rests on 'F' at (0, 0). Cube 1 is at (0, 2) on '#'.
    # Cube 1 moves LEFT to (0, 1) on '#', becoming adjacent to (0, 0).
    # They merge into State(Pose.HORIZONTAL, (0, 0)).
    # Moved cube 1 landed on '#' at (0, 1), so no penalty!
    stage = Stage("test", "G1", ("F###", "####"), (0, 0), (0, 3))
    s1 = State(None, (0, 0), cube2=(0, 2))
    a = Action(Direction.LEFT, cube=1)
    s2 = State(Pose.HORIZONTAL, (0, 0))
    assert move_cost(stage, s1, a, s2) == 1.0


def test_move_cost_split_merge_moving_cube_lands_on_fragile():
    # Cube 0 rests on '#' at (0, 0). Cube 1 is at (0, 2) on '#'.
    # Tile (0, 1) is 'F'. Cube 1 moves LEFT to (0, 1) on 'F', merging with cube 0.
    # Moved cube landed on 'F', so penalized!
    stage = Stage("test", "G1", ("#F##", "####"), (0, 0), (0, 3))
    s1 = State(None, (0, 0), cube2=(0, 2))
    a = Action(Direction.LEFT, cube=1)
    s2 = State(Pose.HORIZONTAL, (0, 0))
    assert move_cost(stage, s1, a, s2) == 1.0 + FRAGILE_PENALTY


# ---------------------------------------------------------------------------
# Tests for UCS
# ---------------------------------------------------------------------------

def test_ucs_start_is_goal():
    stage = Stage("here", "G1", ("G",), (0, 0), (0, 0))
    r = run("ucs", stage)
    assert r.status == "solved"
    assert r.actions == ()
    assert r.length == 0
    assert r.cost == 0.0


@pytest.mark.parametrize("name", ["basic_01", "basic_02", "basic_03"])
def test_ucs_solves_basic_fixtures(name):
    stage = load_stage(FIXTURES / f"{name}.json")
    r_ucs = run("ucs", stage)
    r_bfs = run("bfs", stage)

    assert r_ucs.status == "solved"
    valid, msg = verify_solution(stage, r_ucs.actions)
    assert valid, f"UCS solution invalid on {name}: {msg}"

    # On purely '#' stages, step cost is uniform (1.0 each), so UCS cost == BFS cost
    assert r_ucs.cost == r_bfs.cost
    assert r_ucs.length == r_bfs.length


def test_ucs_solves_fragile_fixture():
    stage = load_stage(FIXTURES / "fragile_01.json")
    r = run("ucs", stage)
    assert r.status == "solved"
    valid, msg = verify_solution(stage, r.actions)
    assert valid, f"UCS failed verification on fragile_01: {msg}"


def test_two_paths_ucs_vs_bfs():
    """Two-path stage:

    Path 1 (Upper, through fragile tile 'F' at (1, 3)):
      2 moves: ['R', 'R']
      Length = 2, Cost = 1.0 (lands on F: 5.0) + 1.0 (lands on G: 1.0) = 6.0
    Path 2 (Lower, detour via '#' floor on rows 2-3):
      5 moves: ['D', 'R', 'R', 'R', 'U']
      Length = 5, Cost = 5 * 1.0 = 5.0

    BFS optimizes steps -> chooses Path 1 (length 2, cost 6.0).
    UCS optimizes cost  -> chooses Path 2 (length 5, cost 5.0).
    """
    grid = (
        "......",
        ".##FG.",
        ".#####",
        ".#####",
        "......",
    )
    stage = Stage("two_paths", "G1", grid, start=(1, 1), goal=(1, 4))
    r_bfs = run("bfs", stage)
    r_ucs = run("ucs", stage)

    assert r_bfs.status == "solved"
    assert r_ucs.status == "solved"

    assert r_bfs.length == 2
    assert r_bfs.cost == 6.0

    assert r_ucs.length == 5
    assert r_ucs.cost == 5.0

    # Key properties of UCS vs BFS:
    assert r_bfs.length < r_ucs.length   # BFS finds strictly fewer steps
    assert r_ucs.cost < r_bfs.cost       # UCS finds strictly cheaper cost


def test_ucs_unsolvable():
    stage = Stage("gap", "G1", ("##..G", "##..#"), (0, 0), (0, 4))
    r = run("ucs", stage)
    assert r.status == "unsolvable"
    assert r.expanded > 0


def test_ucs_timeout(monkeypatch):
    monkeypatch.setattr(bloxorz.search.base, "_CHECK_EVERY", 1)
    stage = load_stage(FIXTURES / "basic_03.json")
    r = run("ucs", stage, limits=Limits(timeout_s=0.0))
    assert r.status == "timeout"


def test_ucs_cancel(monkeypatch):
    monkeypatch.setattr(bloxorz.search.base, "_CHECK_EVERY", 1)
    cancel = threading.Event()
    cancel.set()
    stage = load_stage(FIXTURES / "basic_03.json")
    r = run("ucs", stage, limits=Limits(cancel=cancel))
    assert r.status == "cancelled"


def _brute_force_min_cost(stage, max_depth=12):
    """Exhaustive search of all action paths up to max_depth."""
    min_cost = float("inf")

    def dfs_explore(state, current_cost, depth):
        nonlocal min_cost
        if is_goal(stage, state):
            if current_cost < min_cost:
                min_cost = current_cost
            return
        if depth >= max_depth or current_cost >= min_cost:
            return
        for a, nxt in successors(stage, state):
            cost = current_cost + move_cost(stage, state, a, nxt)
            dfs_explore(nxt, cost, depth + 1)

    dfs_explore(initial_state(stage), 0.0, 0)
    return min_cost if min_cost < float("inf") else None


@pytest.mark.parametrize("name", ["basic_01", "basic_02"])
def test_ucs_matches_brute_force_on_fixtures(name):
    stage = load_stage(FIXTURES / f"{name}.json")
    assert run("ucs", stage).cost == _brute_force_min_cost(stage, max_depth=12)


def test_ucs_matches_brute_force_on_two_paths():
    grid = (
        "......",
        ".##FG.",
        ".#####",
        ".#####",
        "......",
    )
    stage = Stage("two_paths", "G1", grid, start=(1, 1), goal=(1, 4))
    assert run("ucs", stage).cost == _brute_force_min_cost(stage, max_depth=12)
