"""Tests for the benchmark stages in stages/bench. Owner: VT5 (task 5.3)."""
import json
import re
from pathlib import Path

import pytest

from bloxorz.engine import initial_state, step
from bloxorz.engine.rules import footprint
from bloxorz.loader import load_stage
from bloxorz.search import ALGORITHMS, Limits, run
from bloxorz.verify import verify_solution

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = REPO_ROOT / "stages" / "bench"
ORIGINAL_DIR = REPO_ROOT / "stages" / "original"

# Number of stages planned for each group (task 5.0), 17 in total
PLANNED = {"G1": 4, "G2": 3, "G3": 4, "G4": 3, "G5": 3}

BENCH_IDS = sorted(p.stem for p in BENCH_DIR.glob("*.json"))

# Updated the list to include new benchmark stages.
EXPECTED_IDS = [
    "g1_01", "g1_02", "g1_03", "g1_04",
    "g2_01", "g2_02", "g2_03",
    "g3_01", "g3_02", "g3_03", "g3_04",
    "g4_01", "g4_02", "g4_03",
    "g5_01", "g5_02", "g5_03",
]

# The 5 solver configurations of the benchmark
SOLVERS = {"bfs", "dfs", "ucs", "astar", "astar_manhattan"}


def _raw(stage_id):
    return json.loads((BENCH_DIR / f"{stage_id}.json").read_text(encoding="utf-8"))


def _ids_in(group):
    return [i for i in BENCH_IDS if _raw(i)["group"] == group]


def _replay(stage, actions):
    """Play the actions from the start, return the list of StepResult."""
    s = initial_state(stage)
    results = []
    for a in actions:
        r = step(stage, s, a)
        results.append(r)
        s = r.state
    return results


def _fired_switches(stage, results):
    by_id = {sw.id: sw for sw in stage.switches}
    return [by_id[e.split(":")[1]] for r in results for e in r.events if e.startswith("switch:")]


def _used_mechanisms(stage, results):
    """Mechanisms the solution really uses: fragile, switch (switch or bridge), split."""
    used = set()
    for r in results:
        cells = footprint(r.state)
        if any(stage.cell(p) == "F" for p in cells):
            used.add("fragile")
        if any(stage.bridge_at.get(p) for p in cells) or any(e.startswith("switch:") for e in r.events):
            used.add("switch")
        if "split" in r.events or "merge" in r.events:
            used.add("split")
    return used


# ---------------------------------------------------------------------------
# File format: id, group, source, note
# ---------------------------------------------------------------------------

def test_bench_ids_match_expected():
    # A missing or unexpected stage file must fail here
    missing = sorted(set(EXPECTED_IDS) - set(BENCH_IDS))
    extra = sorted(set(BENCH_IDS) - set(EXPECTED_IDS))
    assert not missing and not extra, f"missing={missing} extra={extra}"


def test_group_sizes_do_not_exceed_plan():
    assert sum(PLANNED.values()) == 17
    for group, n in PLANNED.items():
        assert len(_ids_in(group)) <= n, group


@pytest.mark.parametrize("stage_id", BENCH_IDS)
def test_stage_loads_and_matches_file_name(stage_id):
    stage = load_stage(BENCH_DIR / f"{stage_id}.json")
    assert stage.id == stage_id
    assert re.fullmatch(r"g[1-5]_\d\d", stage_id)
    assert stage.group == stage_id[:2].upper()


@pytest.mark.parametrize("stage_id", BENCH_IDS)
def test_stage_has_source_and_note(stage_id):
    raw = _raw(stage_id)
    assert isinstance(raw.get("note"), str) and raw["note"].strip()
    assert raw.get("source") == "team" or re.fullmatch(r"original-\d+", raw.get("source", ""))
    # stage 30 was dropped by the team (2026-10-21), it must not be in the benchmark
    assert raw["source"] != "original-30"


@pytest.mark.parametrize("stage_id", [i for i in BENCH_IDS if _raw(i)["source"] != "team"])
def test_original_stage_data_is_unchanged(stage_id):
    raw = _raw(stage_id)
    n = int(raw["source"].split("-")[1])
    src = json.loads((ORIGINAL_DIR / f"stage_{n:02d}.json").read_text(encoding="utf-8"))
    for key in ("grid", "bridges", "switches"):
        assert raw[key] == src[key], key
    # Task 4.7 lets VT5 change the group: a G3/G4 original level with 2+ mechanisms can go to G5
    if raw["group"] == "G5":
        assert src["group"] in ("G3", "G4")
    else:
        assert raw["group"] == src["group"]


# ---------------------------------------------------------------------------
# Each group only has the mechanisms it is meant to test
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stage_id", BENCH_IDS)
def test_group_mechanisms(stage_id):
    stage = load_stage(BENCH_DIR / f"{stage_id}.json")
    cells = "".join(stage.grid)
    kinds = {sw.kind for sw in stage.switches}
    if stage.group == "G1":
        assert "F" not in cells and "B" not in cells and not stage.switches
    elif stage.group == "G2":
        assert "F" in cells and not stage.switches and not stage.bridges
    elif stage.group == "G3":
        assert stage.switches and stage.bridges and "split" not in kinds
    elif stage.group == "G4":
        # only split switches: no F, no bridge, no soft/heavy switch
        assert kinds == {"split"} and "F" not in cells and not stage.bridges
    else:
        has = {"fragile": "F" in cells, "switch": bool(stage.bridges or kinds - {"split"}), "split": "split" in kinds}
        assert sum(has.values()) >= 2, has


# ---------------------------------------------------------------------------
# Solvable, and the solution really uses the mechanism of the group
# ---------------------------------------------------------------------------

def test_all_five_solvers_are_registered():
    assert SOLVERS <= set(ALGORITHMS)


@pytest.mark.parametrize("algorithm", sorted(SOLVERS))
@pytest.mark.parametrize("stage_id", BENCH_IDS)
def test_every_solver_solves_and_solution_is_valid(stage_id, algorithm):
    stage = load_stage(BENCH_DIR / f"{stage_id}.json")
    r = run(algorithm, stage, limits=Limits(timeout_s=60.0))
    assert r.status == "solved"
    valid, msg = verify_solution(stage, r.actions)
    assert valid, msg


@pytest.mark.parametrize("stage_id", _ids_in("G2"))
def test_g2_solution_crosses_fragile_tile(stage_id):
    stage = load_stage(BENCH_DIR / f"{stage_id}.json")
    results = _replay(stage, run("bfs", stage).actions)
    assert any(stage.cell(p) == "F" for r in results for p in footprint(r.state))


@pytest.mark.parametrize("stage_id", _ids_in("G3"))
def test_g3_solution_presses_switch_and_crosses_bridge(stage_id):
    stage = load_stage(BENCH_DIR / f"{stage_id}.json")
    results = _replay(stage, run("bfs", stage).actions)
    assert _fired_switches(stage, results)
    assert any(stage.bridge_at.get(p) for r in results for p in footprint(r.state))


def test_g3_covers_soft_heavy_toggle_permanent():
    fired = []
    for stage_id in _ids_in("G3"):
        stage = load_stage(BENCH_DIR / f"{stage_id}.json")
        fired += _fired_switches(stage, _replay(stage, run("bfs", stage).actions))
    assert {sw.kind for sw in fired} >= {"soft", "heavy"}
    assert {sw.mode for sw in fired} >= {"toggle", "permanent"}
    assert {sw.set_to for sw in fired if sw.mode == "permanent"} >= {"open", "close"}


@pytest.mark.parametrize("stage_id", _ids_in("G4"))
def test_g4_solution_splits_and_merges(stage_id):
    stage = load_stage(BENCH_DIR / f"{stage_id}.json")
    r = run("bfs", stage)
    results = _replay(stage, r.actions)
    events = [e for res in results for e in res.events]
    assert "split" in events and "merge" in events
    assert any(a.cube is not None for a in r.actions)
    assert _used_mechanisms(stage, results) == {"split"}


@pytest.mark.parametrize("stage_id", _ids_in("G5"))
def test_g5_solution_uses_two_mechanisms(stage_id):
    stage = load_stage(BENCH_DIR / f"{stage_id}.json")
    used = _used_mechanisms(stage, _replay(stage, run("bfs", stage).actions))
    assert len(used) >= 2, used


@pytest.mark.parametrize("algorithm", ["bfs", "ucs"])
def test_g5_02_splits_twice_and_fires_heavy_and_soft(algorithm):
    # Check the note of g5_02 (original level 26) against the real solution
    stage = load_stage(BENCH_DIR / "g5_02.json")
    results = _replay(stage, run(algorithm, stage).actions)
    events = [e for r in results for e in r.events]
    assert events.count("split") == 2 and events.count("merge") == 2
    assert {sw.kind for sw in _fired_switches(stage, results)} == {"heavy", "soft"}


def test_g5_has_a_stage_using_fragile_and_split():
    # BFS and UCS both have to cross F and split/merge on the same stage
    found = []
    for stage_id in _ids_in("G5"):
        stage = load_stage(BENCH_DIR / f"{stage_id}.json")
        if all(_used_mechanisms(stage, _replay(stage, run(algo, stage).actions)) >= {"fragile", "split"}
               for algo in ("bfs", "ucs")):
            found.append(stage_id)
    assert found


def test_whole_bench_covers_every_mechanism():
    fired, used = [], set()
    for stage_id in BENCH_IDS:
        stage = load_stage(BENCH_DIR / f"{stage_id}.json")
        results = _replay(stage, run("bfs", stage).actions)
        fired += _fired_switches(stage, results)
        used |= _used_mechanisms(stage, results)
    assert used == {"fragile", "switch", "split"}
    assert {sw.kind for sw in fired} >= {"soft", "heavy"}
    assert {sw.mode for sw in fired} >= {"toggle", "permanent"}
    assert {sw.set_to for sw in fired if sw.mode == "permanent"} >= {"open", "close"}


# ---------------------------------------------------------------------------
# Two-path stages: BFS has fewer moves, UCS has lower cost
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stage_id, bfs_len, bfs_cost, ucs_len, ucs_cost", [
    ("g2_01", 8, 12.0, 10, 10.0),   # team level: top row crosses F once (+4)
    ("g2_02", 46, 90.0, 49, 77.0),  # original level 13
    ("g5_03", 26, 30.0, 28, 28.0),  # team level: heavy switch, then the same idea as g2_01
])
def test_two_path_stage(stage_id, bfs_len, bfs_cost, ucs_len, ucs_cost):
    stage = load_stage(BENCH_DIR / f"{stage_id}.json")
    r_bfs = run("bfs", stage)
    r_ucs = run("ucs", stage)

    assert (r_bfs.length, r_bfs.cost) == (bfs_len, bfs_cost)
    assert (r_ucs.length, r_ucs.cost) == (ucs_len, ucs_cost)
    assert r_bfs.length < r_ucs.length
    assert r_ucs.cost < r_bfs.cost
    assert verify_solution(stage, r_ucs.actions)[0]


@pytest.mark.parametrize("stage_id", ["g2_01", "g5_03"])
def test_team_two_path_ucs_goes_around_fragile_tiles(stage_id):
    # Team levels: UCS takes the bottom row and never touches F, so every move costs 1.
    # The detour must be 1-3 moves longer than BFS, 4 or more would cost as much as the +4 penalty
    stage = load_stage(BENCH_DIR / f"{stage_id}.json")
    r_bfs = run("bfs", stage)
    r_ucs = run("ucs", stage)

    results = _replay(stage, r_ucs.actions)
    assert not any(stage.cell(p) == "F" for r in results for p in footprint(r.state))
    assert r_ucs.cost == r_ucs.length
    assert 1 <= r_ucs.length - r_bfs.length <= 3


def test_g5_03_both_paths_need_the_heavy_switch():
    # The bridge only opens after standing on the heavy switch, BFS and UCS both have to do it
    stage = load_stage(BENCH_DIR / "g5_03.json")
    for algo in ("bfs", "ucs"):
        results = _replay(stage, run(algo, stage).actions)
        assert [sw.kind for sw in _fired_switches(stage, results)] == ["heavy"]
        assert any(stage.bridge_at.get(p) for r in results for p in footprint(r.state))


def test_at_least_two_two_path_stages():
    found = []
    for stage_id in BENCH_IDS:
        stage = load_stage(BENCH_DIR / f"{stage_id}.json")
        r_bfs, r_ucs = run("bfs", stage), run("ucs", stage)
        if r_bfs.length < r_ucs.length and r_ucs.cost < r_bfs.cost:
            found.append(stage_id)
    assert len(found) >= 2, found
