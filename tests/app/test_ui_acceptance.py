"""Acceptance unit tests for UI helpers, stage title formatting, and GameController state reset.

Owner: VT4 (tasks 4.2, 4.3, 4.5).
"""
from __future__ import annotations

from pathlib import Path
from bloxorz.engine import initial_state
from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import FakeScene
from bloxorz.gui.ui import (
    GROUP_INFO,
    NOT_AVAILABLE,
    end_screen_text,
    format_stage_title,
    get_menu_stages,
    group_caption,
    solver_metric_rows,
)
from bloxorz.loader import load_stage
from bloxorz.model import Direction, Pose
from bloxorz.search import SearchResult

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "stages" / "fixtures"


def test_format_stage_title_original_and_bench():
    # Menu format for original stages: "Màn gốc số N"
    assert format_stage_title("stage_01", menu=True) == "Màn gốc số 1"
    assert format_stage_title("stage_07", menu=True) == "Màn gốc số 7"
    assert format_stage_title("stage_33", menu=True) == "Màn gốc số 33"

    # Default format preserves backward compatibility for existing tests
    assert format_stage_title("stage_07") == "Màn 07"
    assert format_stage_title("stage_bonus") == "Stage Bonus"

    # Bench stage format
    assert format_stage_title("g1_02", menu=True) == "Bench G1-02"
    assert format_stage_title("g4_01", menu=True) == "Bench G4-01"


def test_group_captions_cover_all_tabs():
    for group in ("G1", "G2", "G3", "G4", "G5", "ALL"):
        caption = group_caption(group)
        assert len(caption) > 10
        if group != "ALL":
            assert group in caption
            assert GROUP_INFO[group][0] in caption


def test_end_screen_messages():
    # Won manually
    title, sub = end_screen_text("won", moves=12, algorithm=None)
    assert title == "HOÀN THÀNH!"
    assert "12 bước" in sub

    # Won via solver replay
    title, sub = end_screen_text("won", moves=8, algorithm="bfs")
    assert title == "HOÀN THÀNH!"
    assert "BFS" in sub
    assert "8 nước" in sub

    # Lost due to falling off board
    title, sub = end_screen_text("lost", moves=3, fail_reason="fell")
    assert title == "THUA RỒI!"
    assert "Khối rơi khỏi bàn" in sub

    # Lost due to fragile tile break
    title, sub = end_screen_text("lost", moves=5, fail_reason="fragile_broke")
    assert title == "THUA RỒI!"
    assert "Ô dễ vỡ" in sub

    # Lost due to bridge closing
    title, sub = end_screen_text("lost", moves=4, fail_reason="bridge_closed")
    assert title == "THUA RỒI!"
    assert "Cầu đóng" in sub


def test_solver_metric_rows_unmeasured_show_not_available():
    # An unsolved/timeout result should show "chưa có" for length/cost, not 0
    result = SearchResult(
        algorithm="bfs",
        stage_id="test",
        status="timeout",
        length=0,
        cost=0.0,
        expanded=450,
        time_s=60.01,
        peak_mem_bytes=None,
    )
    rows = dict(solver_metric_rows(result))
    assert rows["Trạng thái"] == "Hết giờ (timeout)"
    assert rows["Số nước"] == NOT_AVAILABLE
    assert rows["Chi phí"] == NOT_AVAILABLE
    assert "450" in rows["Nút mở rộng"]
    assert "60010.0 ms" in rows["Thời gian"]
    assert rows["Bộ nhớ đỉnh"] == NOT_AVAILABLE


def test_restart_after_split_resets_full_state():
    stage = load_stage(FIXTURES_DIR / "split_01.json")
    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage)

    # Roll onto split switch at (1, 3)
    controller.on_direction(Direction.RIGHT)
    controller.on_direction(Direction.RIGHT)
    assert controller.state.pose is None
    assert controller.selected_pos is not None
    assert scene.selected_cube == 0
    assert controller.moves == 2

    # Restart must clear split, reset cube selection and restore initial standing block
    controller.restart()
    assert controller.state.pose == Pose.STANDING
    assert controller.state.pos == stage.start
    assert controller.selected_pos is None
    assert scene.selected_cube is None
    assert controller.moves == 0
    assert controller.status == "playing"
    assert controller.fail_reason == ""


def test_restart_after_win_resets_full_state():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage)

    controller.on_direction(Direction.RIGHT)
    controller.on_direction(Direction.RIGHT)
    assert controller.status == "won"
    assert controller.moves == 2

    controller.restart()
    assert controller.status == "playing"
    assert controller.moves == 0
    assert controller.state == initial_state(stage)


def test_restart_after_fall_resets_full_state_and_reason():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage)

    controller.on_direction(Direction.LEFT)
    assert controller.status == "lost"
    assert controller.fail_reason == "fell"

    controller.restart()
    assert controller.status == "playing"
    assert controller.fail_reason == ""
    assert controller.moves == 0
    assert controller.state == initial_state(stage)


def test_select_stage_after_loss_loads_new_stage_cleanly():
    stage1 = load_stage(FIXTURES_DIR / "basic_01.json")
    stage2 = load_stage(FIXTURES_DIR / "fragile_01.json")
    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage1)

    controller.on_direction(Direction.LEFT)
    assert controller.status == "lost"

    controller.load(stage2)
    assert controller.stage is stage2
    assert controller.status == "playing"
    assert controller.fail_reason == ""
    assert controller.moves == 0
    assert controller.state == initial_state(stage2)
