"""Tests for the benchmark stages in stages/bench. Owner: VT5 (task 5.3)."""
import json
import re
from pathlib import Path

import pytest

from bloxorz.engine import initial_state, step
from bloxorz.engine.rules import footprint
from bloxorz.loader import load_stage
from bloxorz.search import Limits, run
from bloxorz.verify import verify_solution

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = REPO_ROOT / "stages" / "bench"
ORIGINAL_DIR = REPO_ROOT / "stages" / "original"

# Number of stages planned for each group (task 5.0), 17 in total
PLANNED = {"G1": 4, "G2": 3, "G3": 4, "G4": 3, "G5": 3}

BENCH_IDS = sorted(p.stem for p in BENCH_DIR.glob("*.json"))


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


# ---------------------------------------------------------------------------
# File format: id, group, source, note
# ---------------------------------------------------------------------------

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
    for key in ("group", "grid", "bridges", "switches"):
        assert raw[key] == src[key], key


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


# ---------------------------------------------------------------------------
# Solvable, and the solution really uses the mechanism of the group
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stage_id", BENCH_IDS)
def test_bfs_solves_and_solution_is_valid(stage_id):
    stage = load_stage(BENCH_DIR / f"{stage_id}.json")
    r = run("bfs", stage, limits=Limits(timeout_s=60.0))
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


# ---------------------------------------------------------------------------
# Two-path stages: BFS has fewer moves, UCS has lower cost
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stage_id, bfs_len, bfs_cost, ucs_len, ucs_cost", [
    ("g2_01", 8, 12.0, 10, 10.0),   # team level: top row crosses F once (+4)
    ("g2_02", 46, 90.0, 49, 77.0),  # original level 13
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


def test_at_least_two_two_path_stages():
    found = []
    for stage_id in BENCH_IDS:
        stage = load_stage(BENCH_DIR / f"{stage_id}.json")
        r_bfs, r_ucs = run("bfs", stage), run("ucs", stage)
        if r_bfs.length < r_ucs.length and r_ucs.cost < r_bfs.cost:
            found.append(stage_id)
    assert len(found) >= 2, found
