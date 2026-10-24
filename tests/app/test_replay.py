"""Replay and solver runner tests. Owner: VT4 (task 4.3)."""
from __future__ import annotations

import ast
import threading
import time
from pathlib import Path

from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import FakeScene
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


def test_pause_step_and_resume_replay():
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
    scheduled.pop(0)()
    assert controller.moves == 1

    controller.step_once()
    assert controller.status == "won"
    assert controller.moves == 2


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
