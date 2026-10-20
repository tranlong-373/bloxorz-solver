"""Tests for stage loader and validator (task 4.1). Owner: VT4."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import pytest

from bloxorz.loader import LevelError, list_stages, load_stage, validate

# Build paths from the repo root so tests also work when run from tests/
REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "stages" / "fixtures"
BAD_DATA_DIR = REPO_ROOT / "tests" / "data"

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
        ("bad_14_unknown_field.json", "Trường lạ"),
    ],
)
def test_13_bad_stage_files_rejected(filename: str, expected_keyword: str):
    path = BAD_DATA_DIR / filename
    with pytest.raises(LevelError) as exc_info:
        load_stage(path)
    msg = str(exc_info.value)
    # Each bad file should only break one rule so the test is easy to read
    assert len(exc_info.value.errors) == 1
    assert filename in msg
    assert "hàng" in msg and "cột" in msg
    assert expected_keyword in msg


def test_non_utf8_file_gives_level_error(tmp_path: Path):
    path = tmp_path / "bad_utf8.json"
    path.write_bytes(b'{"id": "bad_utf8", \xff}')
    with pytest.raises(LevelError) as exc_info:
        load_stage(path)
    assert "bad_utf8.json" in str(exc_info.value)


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


def _switch_stage(switch: dict) -> dict:
    return {
        "id": "sw_stage",
        "group": "G2",
        "grid": ["######", "#S#BG#", "######"],
        "bridges": [{"id": "b1", "cells": [[1, 3]], "initially_open": False}],
        "switches": [switch],
    }


def _write_stage(tmp_path: Path, raw: dict) -> Path:
    path = tmp_path / f"{raw['id']}.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def test_missing_set_to_defaults_to_open(tmp_path: Path):
    raw = _switch_stage({"id": "sw1", "kind": "heavy", "pos": [0, 1], "mode": "permanent", "bridges": ["b1"]})
    stage = load_stage(_write_stage(tmp_path, raw))
    assert stage.switches[0].set_to == "open"


def test_permanent_set_to_close_is_kept(tmp_path: Path):
    raw = _switch_stage(
        {"id": "sw1", "kind": "heavy", "pos": [0, 1], "mode": "permanent", "set_to": "close", "bridges": ["b1"]}
    )
    stage = load_stage(_write_stage(tmp_path, raw))
    assert stage.switches[0].set_to == "close"


def test_null_set_to_rejected(tmp_path: Path):
    raw = _switch_stage(
        {"id": "sw1", "kind": "heavy", "pos": [0, 1], "mode": "permanent", "set_to": None, "bridges": ["b1"]}
    )
    with pytest.raises(LevelError) as exc_info:
        load_stage(_write_stage(tmp_path, raw))
    msg = str(exc_info.value)
    assert "sw_stage.json" in msg
    assert "set_to=None" in msg


@pytest.mark.parametrize(
    "switch",
    [
        {"id": "sw1", "kind": "soft", "pos": [0, 1], "mode": "toggle", "set_to": "open", "bridges": ["b1"]},
        {"id": "sp1", "kind": "split", "pos": [0, 1], "set_to": "open", "targets": [[0, 0], [2, 0]]},
    ],
)
def test_set_to_only_allowed_for_permanent(switch: dict):
    errs = validate(_switch_stage(switch), "stages/sw_stage.json")
    assert any("chỉ được ghi 'set_to'" in e for e in errs)


@pytest.mark.parametrize(("key", "value"), [("bridges", {}), ("mode", None)])
def test_split_must_not_declare_mode_or_bridges(key: str, value):
    switch = {"id": "sp1", "kind": "split", "pos": [0, 1], "targets": [[0, 0], [2, 0]], key: value}
    errs = validate(_switch_stage(switch), "stages/sw_stage.json")
    assert any("không được khai báo 'mode' hoặc 'bridges'" in e for e in errs)


@pytest.mark.parametrize("bad_value", [[], {}, ["G1"], {"a": 1}])
@pytest.mark.parametrize("field", ["group", "kind", "mode", "set_to"])
def test_wrong_type_fields_give_level_error(tmp_path: Path, field: str, bad_value):
    raw = _switch_stage({"id": "sw1", "kind": "heavy", "pos": [0, 1], "mode": "permanent", "bridges": ["b1"]})
    if field == "group":
        raw["group"] = bad_value
    else:
        raw["switches"][0][field] = bad_value

    # validate() should return messages, not raise TypeError
    errs = validate(raw, "stages/sw_stage.json")
    assert any(field in e for e in errs)

    with pytest.raises(LevelError) as exc_info:
        load_stage(_write_stage(tmp_path, raw))
    msg = str(exc_info.value)
    assert "sw_stage.json" in msg
    assert "hàng" in msg and "cột" in msg


@pytest.mark.parametrize("kind", ["soft", "heavy"])
def test_soft_and_heavy_must_not_declare_targets(kind: str):
    switch = {
        "id": "sw1",
        "kind": kind,
        "pos": [0, 1],
        "mode": "toggle" if kind == "soft" else "permanent",
        "bridges": ["b1"],
        "targets": [[0, 0], [2, 0]],
    }
    errs = validate(_switch_stage(switch), "stages/sw_stage.json")
    assert any("không được khai báo 'targets'" in e for e in errs)


def test_unknown_fields_in_bridge_and_switch():
    base = {
        "id": "sample",
        "group": "G3",
        "grid": ["######", "#S#BG#", "######"],
        "bridges": [{"id": "b1", "cells": [[1, 3]], "initially_open": False, "extra_b": 123}],
        "switches": [{"id": "sw1", "kind": "split", "pos": [0, 1], "targets": [[0, 0], [2, 0]], "extra_sw": True}],
    }
    errs = validate(base, "stages/sample.json")
    assert any("Cầu 'b1' có trường lạ không hợp lệ: 'extra_b'" in e for e in errs)
    assert any("Công tắc 'sw1' có trường lạ không hợp lệ: 'extra_sw'" in e for e in errs)


def test_split_target_on_start_tile():
    # split target can be on the start tile 'S'
    raw = {
        "id": "split_start",
        "group": "G4",
        "grid": ["######", "#S##G#", "######"],
        "bridges": [],
        "switches": [
            {
                "id": "sp1",
                "kind": "split",
                "pos": [0, 2],
                "targets": [[1, 1], [0, 4]],
            }
        ],
    }
    errs = validate(raw, "stages/split_start.json")
    assert not errs


def test_multiple_switches_at_same_position(tmp_path: Path):
    # multiple switches can share the same tile
    raw = {
        "id": "multi_sw",
        "group": "G3",
        "grid": ["###B##", "#S#BG#", "######"],
        "bridges": [
            {"id": "b1", "cells": [[1, 3]], "initially_open": False},
            {"id": "b2", "cells": [[0, 3]], "initially_open": False},
        ],
        "switches": [
            {
                "id": "sw1",
                "kind": "soft",
                "pos": [0, 2],
                "mode": "permanent",
                "set_to": "open",
                "bridges": ["b1"],
            },
            {
                "id": "sw2",
                "kind": "heavy",
                "pos": [0, 2],
                "mode": "permanent",
                "set_to": "close",
                "bridges": ["b2"],
            },
        ],
    }
    errs = validate(raw, "stages/multi_sw.json")
    assert not errs

    stage = load_stage(_write_stage(tmp_path, raw))
    assert (0, 2) in stage.switch_at
    assert len(stage.switch_at[(0, 2)]) == 2

