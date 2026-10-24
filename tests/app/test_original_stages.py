"""Tests for 33 original stages converted from quick_bloxorz. Owner: VT4 (task 4.7)."""
from __future__ import annotations

from pathlib import Path
import pytest

from bloxorz.loader import list_stages, load_stage
from bloxorz.search import Limits, run
from bloxorz.verify import verify_solution

REPO_ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_DIR = REPO_ROOT / "stages" / "original"

# stage 30 is excluded because quick_bloxorz source map is missing floor tiles
EXCLUDED_STAGE_NUMBERS = {30}


def test_list_stages_loads_all_33_original_files():
    # check that list_stages finds all 33 original stages
    stages = list_stages(ORIGINAL_DIR)
    assert len(stages) == 33
    expected_ids = [f"stage_{i:02d}" for i in range(1, 34)]
    actual_ids = sorted(s.id for s in stages)
    assert actual_ids == expected_ids


@pytest.mark.parametrize("stage_num", list(range(1, 34)))
def test_original_stage_format_and_properties(stage_num: int):
    # verify stage json structure and grid limits
    stage_id = f"stage_{stage_num:02d}"
    stage_path = ORIGINAL_DIR / f"{stage_id}.json"
    assert stage_path.exists()

    stage = load_stage(stage_path)
    assert stage.id == stage_id
    assert stage.group in {"G1", "G2", "G3", "G4"}
    assert stage.rows <= 12
    assert stage.cols <= 20

    # start tile must be replaced with floor
    for row_str in stage.grid:
        assert "S" not in row_str

    assert stage.cell(stage.start) == "#"
    assert stage.cell(stage.goal) == "G"


@pytest.mark.parametrize("stage_num", list(range(1, 34)))
def test_bfs_solves_original_stages(stage_num: int):
    # skip excluded stages
    if stage_num in EXCLUDED_STAGE_NUMBERS:
        pytest.skip(f"Stage {stage_num} is excluded: quick_bloxorz map is missing floor tiles")

    stage_id = f"stage_{stage_num:02d}"
    stage = load_stage(ORIGINAL_DIR / f"{stage_id}.json")

    result = run("bfs", stage, limits=Limits(timeout_s=10.0))

    assert result.status == "solved"
    assert result.length > 0
    valid, message = verify_solution(stage, result.actions)
    assert valid, f"Verification failed for {stage_id}: {message}"


def test_stage_23_solves_with_reference_bridge_configuration():
    # test stage 23 using reference bridge configuration
    stage_path = ORIGINAL_DIR / "stage_23.json"
    stage = load_stage(stage_path)

    # bfs must find the 75-step reference solution
    bfs_result = run("bfs", stage, limits=Limits(timeout_s=15.0))
    assert bfs_result.status == "solved"
    assert bfs_result.length == 75
    valid_bfs, message_bfs = verify_solution(stage, bfs_result.actions)
    assert valid_bfs, f"Verification failed for stage_23 BFS: {message_bfs}"

    # ucs must also solve stage 23 and produce a valid path
    ucs_result = run("ucs", stage, limits=Limits(timeout_s=15.0))
    assert ucs_result.status == "solved"
    assert ucs_result.length > 0
    valid_ucs, message_ucs = verify_solution(stage, ucs_result.actions)
    assert valid_ucs, f"Verification failed for stage_23 UCS: {message_ucs}"

