"""Replay and solver runner tests. Owner: VT4 (task 4.3)."""
from __future__ import annotations

import ast
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import FakeScene
from bloxorz.gui.ui import UI, format_solver_result
from bloxorz.engine import initial_state, step
from bloxorz.loader import load_stage
from bloxorz.search import SearchResult, run
from bloxorz.gui.solver_runner import SolverRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "stages" / "fixtures"


def test_bfs_solution_replays_to_win():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    result = run("bfs", stage)
    assert result.status == "solved"

    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage)
    controller.start_replay(result.actions)

    assert controller.status == "won"
    assert controller.moves == result.length
    assert scene.state == controller.state


def test_pause_resume_replay_ignores_stale_callback():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    result = run("bfs", stage)
    scene = FakeScene()
    scheduled = []
    controller = GameController(scene, schedule=lambda fn, delay: scheduled.append(fn))
    controller.load(stage)
    controller.start_replay(result.actions)

    scheduled.pop(0)()
    assert controller.moves == 1
    controller.pause()
    controller.resume()

    stale_callback = scheduled.pop(0)
    resumed_callback = scheduled.pop(0)
    stale_callback()
    assert controller.moves == 1
    resumed_callback()
    assert controller.status == "won"
    assert controller.moves == 2
    resumed_callback()
    assert controller.moves == 2


def test_step_once_advances_while_paused():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    result = run("bfs", stage)
    scene = FakeScene()
    scheduled = []
    controller = GameController(scene, schedule=lambda fn, delay: scheduled.append(fn))
    controller.load(stage)
    controller.start_replay(result.actions)

    scheduled.pop(0)()
    controller.pause()
    controller.step_once()

    assert controller.status == "won"
    assert controller.moves == result.length


def test_controller_replay_speed_presets():
    controller = GameController(FakeScene())
    for multiplier, delay in ((1, 0.25), (2, 0.125), (4, 0.0625)):
        controller.set_speed(multiplier)
        assert controller.speed == multiplier
        assert controller.delay == delay


def test_restart_invalidates_pending_replay_callback():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    result = run("bfs", stage)
    scene = FakeScene()
    scheduled = []
    controller = GameController(scene, schedule=lambda fn, delay: scheduled.append(fn))
    controller.load(stage)
    controller.start_replay(result.actions)

    scheduled.pop(0)()
    stale_callback = scheduled.pop(0)
    controller.restart()
    stale_callback()

    assert controller.moves == 0
    assert controller.state == initial_state(stage)
    assert controller.status == "playing"


def test_stage_change_invalidates_pending_replay_callback():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    other_stage = load_stage(FIXTURES_DIR / "basic_02.json")
    result = run("bfs", stage)
    scene = FakeScene()
    scheduled = []
    controller = GameController(scene, schedule=lambda fn, delay: scheduled.append(fn))
    controller.load(stage)
    controller.start_replay(result.actions)

    scheduled.pop(0)()
    stale_callback = scheduled.pop(0)
    controller.load(other_stage)
    stale_callback()

    assert controller.stage is other_stage
    assert controller.moves == 0
    assert controller.state == initial_state(other_stage)
    assert controller.status == "playing"


def test_g4_split_solution_replays_through_merge_and_win():
    stage = load_stage(REPO_ROOT / "stages" / "bench" / "g4_02.json")
    result = run("astar", stage)
    assert result.status == "solved", result.message

    state = initial_state(stage)
    events = set()
    for action in result.actions:
        transition = step(stage, state, action)
        assert transition.state is not None
        events.update(transition.events)
        state = transition.state
    assert {"split", "merge"}.issubset(events)
    assert any(action.cube in (0, 1) for action in result.actions)

    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage)
    controller.start_replay(result.actions)

    assert controller.status == "won"
    assert controller.moves == result.length
    assert scene.state == controller.state


def test_solver_runner_can_cancel_real_search_within_one_second():
    stage = load_stage(REPO_ROOT / "stages" / "bench" / "g5_02.json")
    runner = SolverRunner()
    runner.start("bfs", stage)
    started = time.perf_counter()
    runner.cancel()

    result = None
    while result is None and time.perf_counter() - started < 1.0:
        result = runner.poll()
        time.sleep(0.005)

    assert result is not None
    assert result.status == "cancelled"
    assert time.perf_counter() - started < 1.0


def test_solver_runner_supports_all_solver_methods():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    for algorithm in ("bfs", "dfs", "ucs", "astar"):
        runner = SolverRunner()
        runner.start(algorithm, stage)
        deadline = time.perf_counter() + 2.0
        result = None
        while result is None and time.perf_counter() < deadline:
            result = runner.poll()
            time.sleep(0.005)
        assert result is not None, algorithm
        assert result.status == "solved", (algorithm, result.message)


def test_non_solution_stats_use_dashes_and_kib():
    for status in ("timeout", "cancelled", "unsolvable", "error"):
        result = SearchResult(
            "bfs", "test", status, length=0, cost=0, peak_mem_bytes=1024
        )
        text = format_solver_result(result)
        assert "moves —" in text
        assert "cost —" in text
        assert "1.0 KiB" in text


def test_cancelled_ui_result_does_not_start_replay(monkeypatch):
    import bloxorz.gui.ui as ui_module

    result = SearchResult("bfs", "basic_01", "cancelled")

    class CompletedRunner:
        def poll(self):
            return result

        @property
        def running(self):
            return False

    controller = SimpleNamespace(
        stage=None,
        moves=0,
        status="solving",
        start_replay=lambda actions: (_ for _ in ()).throw(AssertionError("replayed after cancel")),
        paused=False,
        replaying=False,
    )
    ui = UI.__new__(UI)
    ui._layout_aspect = None
    ui.runner = CompletedRunner()
    ui._result_handled = False
    ui._cancel_requested = True
    ui.solver_text = SimpleNamespace(text="")
    ui.controller = controller
    ui.reset_solver_action = lambda: None
    ui.cancel_button = SimpleNamespace(enabled=True)
    ui.pause_button = SimpleNamespace(enabled=True)
    ui.step_button = SimpleNamespace(enabled=True)
    ui.resume_button = SimpleNamespace(enabled=True)
    ui.info_text = SimpleNamespace(text="")
    ui.status_text = SimpleNamespace(text="")
    monkeypatch.setattr(ui_module, "color", None)
    monkeypatch.setattr(ui_module, "window", None)

    ui.update()

    assert "cancelled" in ui.solver_text.text
    assert "moves —" in ui.solver_text.text
    assert controller.status == "playing"


def test_solver_runner_cancels_worker(monkeypatch):
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    worker_started = threading.Event()
    worker_thread = []

    def wait_for_cancel(algorithm, loaded_stage, limits, measure_memory=False):
        worker_thread.append(threading.current_thread())
        worker_started.set()
        limits.cancel.wait(1)
        return SearchResult(algorithm, loaded_stage.id, "cancelled")

    monkeypatch.setattr("bloxorz.gui.solver_runner.run", wait_for_cancel)
    runner = SolverRunner()
    runner.start("bfs", stage)
    assert worker_started.wait(1)
    assert worker_thread[0] is not threading.current_thread()

    runner.cancel()
    deadline = time.perf_counter() + 1
    result = None
    while result is None and time.perf_counter() < deadline:
        result = runner.poll()
        time.sleep(0.005)

    assert result is not None
    assert result.status == "cancelled"


def test_controller_and_runner_do_not_import_ursina():
    for module in ("controller.py", "solver_runner.py", "fake_scene.py"):
        path = REPO_ROOT / "bloxorz" / "gui" / module
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] != "ursina" for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert not node.module or node.module.split(".")[0] != "ursina"
