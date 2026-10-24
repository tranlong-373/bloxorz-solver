"""Tests for the two A* heuristics, relaxed and manhattan. Owner: VT5 (task 5.2)."""
import heapq
import itertools
from collections import deque
from pathlib import Path

import pytest

from bloxorz.engine import initial_state, is_goal, step, successors
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.search import run
from bloxorz.search.cost import move_cost
from bloxorz.search.heuristics import (
    INF, make_heuristic, manhattan, relaxed_distances, split_switch_positions,
)
from bloxorz.stage import Stage, Switch

FIXTURES = Path(__file__).resolve().parents[2] / "stages" / "fixtures"
HEURISTICS = ("relaxed", "manhattan")
L, R = Direction.LEFT, Direction.RIGHT

# Standing at (0,0), goal at (0,3) on the same row: solution R, R (cost 2)
LINE_STAGE = Stage("line", "G1", ("###G",), (0, 0), (0, 3))
# 1-row board: the block can only stand on columns 0, 3, 6, ... so never on the goal (0,2)
ROW_STAGE = Stage("row", "G1", ("##G#",), (0, 0), (0, 2))


def counterexample_2_stage():
    # Card 5.2 step 4: split switch at (0,3) sends the cubes to (5,10), (5,12)
    # next to the goal (5,9). Solution R, R, cube 1 L (merge), L = 4 moves
    grid = ["####" + "." * 9] + ["." * 13] * 4 + ["." * 9 + "G###"]
    switch = Switch("sp1", "split", (0, 3), targets=((5, 10), (5, 12)))
    return Stage("ce2", "G4", tuple(grid), (0, 0), (5, 9), switches=(switch,))


def merge_counterexample_stage():
    # Card 5.2: 6x8 floor, start (0,0), goal (3,2), split at (0,3) to (3,3), (3,5)
    grid = ["########"] * 6
    grid[3] = "##G#####"
    switch = Switch("sp1", "split", (0, 3), targets=((3, 3), (3, 5)))
    return Stage("merge_ce", "G4", tuple(grid), (0, 0), (3, 2), switches=(switch,))


def _fixture(name):
    return load_stage(FIXTURES / f"{name}.json")


# Small stages for the admissible/consistent checks over every reachable state.
# split_01, full_01, ce2 and merge_ce have split/merge.
SMALL_STAGES = {
    "basic_01": lambda: _fixture("basic_01"),
    "fragile_01": lambda: _fixture("fragile_01"),
    "soft_toggle_01": lambda: _fixture("soft_toggle_01"),
    "heavy_permanent_01": lambda: _fixture("heavy_permanent_01"),
    "split_01": lambda: _fixture("split_01"),
    "full_01": lambda: _fixture("full_01"),
    "ce2": counterexample_2_stage,
    "merge_ce": merge_counterexample_stage,
}


def _state_graph(stage):
    """Every state reachable from the start, with its successor edges and costs."""
    start = initial_state(stage)
    edges = {}
    queue = deque([start])
    while queue:
        s = queue.popleft()
        if s in edges:
            continue
        edges[s] = [(a, s2, move_cost(stage, s, a, s2)) for a, s2 in successors(stage, s)]
        queue.extend(s2 for _, s2, _ in edges[s] if s2 not in edges)
    return edges


def _true_costs(stage, edges):
    """Real min cost from each state to the goal (INF if none), Dijkstra backwards from the goals."""
    back = {s: [] for s in edges}
    for s, out in edges.items():
        for _, s2, c in out:
            back[s2].append((s, c))
    cost = {s: 0.0 for s in edges if is_goal(stage, s)}
    tie = itertools.count()
    heap = [(0.0, next(tie), s) for s in cost]
    while heap:
        c, _, s = heapq.heappop(heap)
        if c > cost[s]:
            continue
        for prev, step_cost in back[s]:
            if c + step_cost < cost.get(prev, INF):
                cost[prev] = c + step_cost
                heapq.heappush(heap, (c + step_cost, next(tie), prev))
    return {s: cost.get(s, INF) for s in edges}


def _ucs_from(stage, edges, start):
    """Plain UCS starting from any state (goal checked on pop), INF if no goal."""
    g = {start: 0.0}
    tie = itertools.count()
    heap = [(0.0, next(tie), start)]
    closed = set()
    while heap:
        c, _, s = heapq.heappop(heap)
        if s in closed:
            continue
        if is_goal(stage, s):
            return c
        closed.add(s)
        for _, s2, step_cost in edges[s]:
            if c + step_cost < g.get(s2, INF):
                g[s2] = c + step_cost
                heapq.heappush(heap, (c + step_cost, next(tie), s2))
    return INF


def _play(stage, actions):
    s = initial_state(stage)
    events = []
    for a in actions:
        r = step(stage, s, a)
        assert r.state is not None, r.reason
        events += r.events
        s = r.state
    return s, events


# ---------------------------------------------------------------------------
# The "naive" heuristics from the hints in the assignment (only used here)
# ---------------------------------------------------------------------------

def naive_plus_one_when_lying(stage):
    # Hint 1 + 2: Manhattan/2, plus 1 while lying
    return lambda s: manhattan(s.pos, stage.goal) / 2 + (s.pose is not Pose.STANDING)


def naive_without_split(stage):
    # Hint 1: Manhattan/2 that ignores split switches
    return lambda s: manhattan(s.pos, stage.goal) / 2


def naive_not_halved(stage):
    # Hint 3: point distance on the grid, not divided by 2
    return lambda s: manhattan(s.pos, stage.goal)


def old_manhattan(stage):
    # Old formula before the fix: no max(best, 1) for a lying block
    splits = split_switch_positions(stage)

    def h(s):
        if s.pose is None:
            return 2
        best = manhattan(s.pos, stage.goal) / 2
        for p in splits:
            best = min(best, manhattan(s.pos, p) / 2 + 2)
        return best
    return h


# ---------------------------------------------------------------------------
# relaxed_distances / helpers
# ---------------------------------------------------------------------------

def test_split_switch_positions():
    assert split_switch_positions(_fixture("full_01")) == [(3, 4)]
    assert split_switch_positions(_fixture("soft_toggle_01")) == []


def test_relaxed_distances_ignore_void_and_keep_board_edge():
    # Goal behind a void gap: the real block can never get there,
    # but on the relaxed board the gap is floor, so the distance is 2
    stage = Stage("gap", "G1", ("#..G",), (0, 0), (0, 3))
    d = relaxed_distances(stage, [stage.goal])
    assert d[(Pose.STANDING, (0, 0))] == 2
    # 1-row board: vertical states are outside the board
    assert not any(pose is Pose.VERTICAL for pose, _ in d)


def test_relaxed_distances_match_bfs_on_open_board():
    # On a board with only floor, relaxed distance to the goal == BFS solution length
    grid = ["#######"] * 7
    grid[6] = "######G"
    for start in [(0, 0), (3, 3), (5, 1), (0, 6)]:
        stage = Stage("open7", "G1", tuple(grid), start, (6, 6))
        d = relaxed_distances(stage, [stage.goal])
        assert d[(Pose.STANDING, start)] == run("bfs", stage).length


def test_relaxed_distances_no_source():
    assert relaxed_distances(LINE_STAGE, []) == {}


def test_unknown_heuristic_name():
    with pytest.raises(ValueError):
        make_heuristic(LINE_STAGE, "euclid")


# ---------------------------------------------------------------------------
# h(goal) = 0, split state = 2
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", HEURISTICS)
@pytest.mark.parametrize("stage_key", sorted(SMALL_STAGES))
def test_h_goal_is_zero(stage_key, name):
    stage = SMALL_STAGES[stage_key]()
    h = make_heuristic(stage, name)
    goals = [s for s in _state_graph(stage) if is_goal(stage, s)]
    assert goals
    assert all(h(s) == 0 for s in goals)


@pytest.mark.parametrize("name", HEURISTICS)
def test_h_split_state_is_two(name):
    stage = _fixture("split_01")
    assert make_heuristic(stage, name)(State(None, (1, 2), (1, 5))) == 2


# ---------------------------------------------------------------------------
# Admissible and consistent on every reachable state of the small stages
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", HEURISTICS)
@pytest.mark.parametrize("stage_key", sorted(SMALL_STAGES))
def test_admissible_on_all_reachable_states(stage_key, name):
    stage = SMALL_STAGES[stage_key]()
    edges = _state_graph(stage)
    real = _true_costs(stage, edges)
    h = make_heuristic(stage, name)
    over = [(s, h(s), real[s]) for s in edges if h(s) > real[s]]
    assert not over, over[:3]


@pytest.mark.parametrize("name", HEURISTICS)
@pytest.mark.parametrize("stage_key", sorted(SMALL_STAGES))
def test_consistent_on_all_edges(stage_key, name):
    # h(s) <= move_cost + h(s2) for roll, split, cube move and merge edges
    stage = SMALL_STAGES[stage_key]()
    h = make_heuristic(stage, name)
    bad = [(s, a, s2) for s, out in _state_graph(stage).items()
           for a, s2, c in out if h(s) > c + h(s2)]
    assert not bad, bad[:3]


@pytest.mark.parametrize("stage_key", ["split_01", "full_01", "ce2", "merge_ce"])
def test_split_stages_really_split_and_merge(stage_key):
    # The split stages above must contain split and merge edges, otherwise
    # the consistency test does not cover these edge types
    stage = SMALL_STAGES[stage_key]()
    edges = _state_graph(stage)
    kinds = {(s.pose is None, s2.pose is None) for s, out in edges.items() for _, s2, _ in out}
    assert (False, True) in kinds   # split
    assert (True, True) in kinds    # cube move
    assert (True, False) in kinds   # merge


def test_true_cost_of_start_matches_ucs():
    for stage_key in SMALL_STAGES:
        stage = SMALL_STAGES[stage_key]()
        real = _true_costs(stage, _state_graph(stage))
        assert real[initial_state(stage)] == run("ucs", stage).cost, stage_key


@pytest.mark.parametrize("stage_key", sorted(SMALL_STAGES))
def test_true_costs_match_ucs_from_each_state(stage_key):
    # The reversed Dijkstra above must give the same number as UCS started from s.
    # Check every state on the small graphs, every 10th state on the 2 bigger ones
    stage = SMALL_STAGES[stage_key]()
    edges = _state_graph(stage)
    real = _true_costs(stage, edges)
    states = list(edges)
    if len(states) > 500:
        states = states[::10]
    assert all(_ucs_from(stage, edges, s) == real[s] for s in states)


def test_relaxed_is_inf_when_goal_cannot_be_reached_even_on_empty_board():
    h = make_heuristic(ROW_STAGE, "relaxed")
    states = list(_state_graph(ROW_STAGE))
    assert len(states) == 3
    assert all(h(s) == INF for s in states)
    assert run("ucs", ROW_STAGE).status == "unsolvable"


# ---------------------------------------------------------------------------
# 3 counterexamples for the hints of the assignment
# ---------------------------------------------------------------------------

def test_counterexample_1_plus_one_when_lying_overestimates():
    # Lying at (0,1),(0,2), goal at (0,3): one roll R wins, real cost 1
    stage = LINE_STAGE
    s, _ = _play(stage, [Action(R)])
    assert s == State(Pose.HORIZONTAL, (0, 1))
    real = _ucs_from(stage, _state_graph(stage), s)
    assert real == 1
    assert naive_plus_one_when_lying(stage)(s) == 2 > real
    for name in HEURISTICS:
        assert make_heuristic(stage, name)(s) <= real


def test_counterexample_2_split_switch_next_to_goal():
    stage = counterexample_2_stage()
    r = run("ucs", stage)
    assert r.cost == 4
    assert [(a.direction, a.cube) for a in r.actions] == [(R, None), (R, None), (L, 1), (L, None)]
    _, events = _play(stage, r.actions)
    assert "split" in events and "merge" in events

    start = initial_state(stage)
    assert naive_without_split(stage)(start) == 7 > r.cost
    for name in HEURISTICS:
        assert make_heuristic(stage, name)(start) <= r.cost
    assert make_heuristic(stage, "relaxed")(start) == 4  # R, R to the switch + 2


def test_counterexample_3_point_distance_not_halved():
    # Standing 3 cells left of the goal on the same row: real cost 2 (R, R)
    stage = LINE_STAGE
    start = initial_state(stage)
    real = run("ucs", stage).cost
    assert real == 2
    assert naive_not_halved(stage)(start) == 3 > real
    for name in HEURISTICS:
        assert make_heuristic(stage, name)(start) <= real


# ---------------------------------------------------------------------------
# Merge counterexample: old manhattan formula is not consistent
# ---------------------------------------------------------------------------

def test_merge_next_to_goal_old_formula_inconsistent_new_formula_consistent():
    stage = merge_counterexample_stage()
    before, events = _play(stage, [
        Action(R), Action(R),        # stand on the split switch -> cubes (3,3), (3,5)
        Action(L, cube=0),           # cube 0 to the goal cell (3,2)
        Action(L, cube=1),           # cube 1 to (3,4)
    ])
    assert events == ["split"]
    assert before == State(None, (3, 2), (3, 4))

    a = Action(L, cube=1)            # cube 1 to (3,3) -> merge on top of the goal
    r = step(stage, before, a)
    after = r.state
    assert r.events == ("merge",)
    assert after == State(Pose.HORIZONTAL, (3, 2))
    c = move_cost(stage, before, a, after)
    assert c == 1

    old = old_manhattan(stage)
    assert (old(before), old(after)) == (2, 0)
    assert old(before) > c + old(after)          # 2 > 1 + 0

    new = make_heuristic(stage, "manhattan")
    assert (new(before), new(after)) == (2, 1)
    assert new(before) <= c + new(after)         # 2 <= 1 + 1

    relaxed = make_heuristic(stage, "relaxed")
    assert relaxed(before) <= c + relaxed(after)


def test_old_formula_also_fails_the_full_edge_check():
    # Same stage, every edge: the old formula has at least one bad edge, the new one none
    stage = merge_counterexample_stage()
    edges = _state_graph(stage)

    def bad_edges(h):
        return [(s, s2) for s, out in edges.items() for _, s2, c in out if h(s) > c + h(s2)]

    assert bad_edges(old_manhattan(stage))
    assert not bad_edges(make_heuristic(stage, "manhattan"))
