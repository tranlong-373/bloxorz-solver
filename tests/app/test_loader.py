"""Tests for stage loader and validator (task 4.1). Owner: VT4."""
from __future__ import annotations

import copy
from pathlib import Path
import pytest

from bloxorz.loader import LevelError, list_stages, load_stage, validate

FIXTURES_DIR = Path("stages/fixtures")
BAD_DATA_DIR = Path("tests/data")

EXPECTED_FIXTURES = [
    "basic_01",
    "basic_02",
    "basic_03",
    "fragile_01",
    "soft_toggle_01",
    "heavy_permanent_01",
    "split_01",
    "full_01",
]


@pytest.mark.parametrize("stage_name", EXPECTED_FIXTURES)
def test_load_each_fixture_stage(stage_name: str):
    path = FIXTURES_DIR / f"{stage_name}.json"
    stage = load_stage(path)
    assert stage.id == stage_name
    assert stage.group in {"G1", "G2", "G3", "G4", "G5"}
    # 'S' must be replaced by '#'
    for row in stage.grid:
        assert "S" not in row
    assert stage.cell(stage.start) == "#"
    assert stage.cell(stage.goal) == "G"


def test_list_stages_returns_sorted_8_fixtures():
    stages = list_stages(FIXTURES_DIR)
    assert len(stages) == 8
    keys = [(s.group, s.id) for s in stages]
    assert keys == sorted(keys)


@pytest.mark.parametrize(
    ("filename", "expected_keyword"),
    [
        ("bad_01_syntax.json", "JSON sai cú pháp"),
        ("bad_02_ragged_grid.json", "dài khác nhau"),
        ("bad_03_invalid_char.json", "Ký tự lạ"),
        ("bad_04_no_goal.json", "Không có ô đích G"),
        ("bad_05_multi_goal.json", "2 G trở lên"),
        ("bad_06_bad_start.json", "2 S trở lên"),
        ("bad_07_unknown_bridge.json", "id cầu không tồn tại"),
        ("bad_08_switch_not_on_floor.json", "không nằm trên ô #"),
        ("bad_09_bridge_cell_mismatch.json", "không phải B"),
        ("bad_10_bad_split_targets.json", "targets kề nhau"),
        ("bad_11_duplicate_id.json", "bị trùng"),
        ("bad_12_grid_too_large.json", "vượt quá giới hạn"),
        ("bad_13_bad_switch_fields.json", "mode="),
    ],
)
def test_13_bad_stage_files_rejected(filename: str, expected_keyword: str):
    path = BAD_DATA_DIR / filename
    with pytest.raises(LevelError) as exc_info:
        load_stage(path)
    msg = str(exc_info.value)
    assert filename in msg
    assert "hàng" in msg and "cột" in msg
    assert expected_keyword in msg


def test_validator_extra_subcases():
    base = {
        "id": "sample",
        "group": "G3",
        "source": "original-12",
        "note": "ignored optional fields",
        "grid": ["######", "#S#BG#", "######"],
        "bridges": [{"id": "b1", "cells": [[1, 3]], "initially_open": False}],
        "switches": [],
    }
    assert validate(base, "stages/sample.json") == []

    # Missing start position S
    no_s = copy.deepcopy(base)
    no_s["grid"] = ["######", "###BG#", "######"]
    errs = validate(no_s, "stages/sample.json")
    assert any("Không có ô xuất phát S" in e for e in errs)

    # Grid tile B not in any bridge
    unclaimed_b = copy.deepcopy(base)
    unclaimed_b["bridges"] = []
    errs = validate(unclaimed_b, "stages/sample.json")
    assert any("Ô B trên grid không thuộc cầu nào" in e for e in errs)

    # Split targets out of bounds, not on '#', or identical
    split_err = copy.deepcopy(base)
    split_err["switches"] = [
        {"id": "sp1", "kind": "split", "pos": [1, 2], "targets": [[99, 99], [1, 4]]},
        {"id": "sp2", "kind": "split", "pos": [0, 1], "targets": [[0, 0], [0, 0]]},
    ]
    errs = validate(split_err, "stages/sample.json")
    assert any("nằm ngoài bàn" in e for e in errs)
    assert any("không phải ô #" in e for e in errs)
    assert any("trùng nhau" in e for e in errs)

    # Invalid kind, invalid set_to, missing bridges, missing targets
    sw_err = copy.deepcopy(base)
    sw_err["switches"] = [
        {"id": "sw1", "kind": "magic", "pos": [0, 0]},
        {"id": "sw2", "kind": "heavy", "pos": [0, 1], "mode": "permanent", "set_to": "half"},
        {"id": "sw3", "kind": "split", "pos": [0, 2]},
    ]
    errs = validate(sw_err, "stages/sample.json")
    assert any("kind='magic'" in e for e in errs)
    assert any("set_to='half'" in e for e in errs)
    assert any("thiếu trường 'bridges'" in e for e in errs)
    assert any("thiếu trường 'targets'" in e for e in errs)