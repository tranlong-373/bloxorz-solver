"""Unit tests for GameController using FakeScene. Owner: VT4 (task 4.2)."""
from __future__ import annotations

from pathlib import Path
import sys

from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import FakeScene
from bloxorz.loader import load_stage
from bloxorz.model import Direction, Pose

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "stages" / "fixtures"


import ast

def _get_imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    return imported


def test_no_ursina_imported_in_controller():
    """Verify controller and fake_scene do not import ursina."""
    import bloxorz.gui.controller as ctrl
    import bloxorz.gui.fake_scene as fake

    assert "ursina" not in _get_imported_modules(Path(ctrl.__file__))
    assert "ursina" not in _get_imported_modules(Path(fake.__file__))



def test_controller_initial_load():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    scene = FakeScene()
    controller = GameController(scene)

    controller.load(stage)

    assert controller.stage is stage
    assert controller.moves == 0
    assert controller.status == "playing"
    assert controller.state is not None
    assert controller.state.pose == Pose.STANDING
    assert controller.state.pos == stage.start
    assert scene.stage is stage
    assert scene.state == controller.state


def test_controller_valid_moves_and_win():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage)

    # First move: Right -> Horizontal
    controller.on_direction(Direction.RIGHT)
    assert controller.moves == 1
    assert controller.status == "playing"
    assert controller.state is not None
    assert controller.state.pose == Pose.HORIZONTAL

    # Second move: Right -> Standing on goal
    controller.on_direction(Direction.RIGHT)
    assert controller.moves == 2
    assert controller.status == "won"
    assert controller.state.pose == Pose.STANDING
    assert controller.state.pos == stage.goal


def test_controller_fall_and_lost():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage)

    # Rolling LEFT from (1, 1) goes off the board -> ILLEGAL
    controller.on_direction(Direction.LEFT)
    assert controller.status == "lost"
    assert controller.moves == 0

    # Once lost, pressing further keys must have no effect
    controller.on_direction(Direction.RIGHT)
    assert controller.status == "lost"
    assert controller.moves == 0


def test_controller_restart():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage)

    controller.on_direction(Direction.LEFT)
    assert controller.status == "lost"

    controller.restart()
    assert controller.moves == 0
    assert controller.status == "playing"
    assert controller.state is not None
    assert controller.state.pose == Pose.STANDING
    assert controller.state.pos == stage.start


def test_controller_ignores_input_when_scene_busy():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage)

    scene.busy = True
    controller.on_direction(Direction.RIGHT)
    assert controller.moves == 0
    assert controller.status == "playing"

    scene.busy = False
    controller.on_direction(Direction.RIGHT)
    assert controller.moves == 1


def test_menu_stages_excludes_stage_30():
    from bloxorz.gui.ui import get_menu_stages

    stages = get_menu_stages(REPO_ROOT)
    stage_ids = [s.id for s in stages]

    # Must exclude stage_30
    assert "stage_30" not in stage_ids

    # Must keep the other 32 original stages without re-indexing
    original_ids = {s_id for s_id in stage_ids if s_id.startswith("stage_")}
    expected_original = {f"stage_{i:02d}" for i in range(1, 34) if i != 30}
    assert original_ids == expected_original

    # Must include fixture stages
    assert "basic_01" in stage_ids


def test_controller_unloaded_safeguards():
    scene = FakeScene()
    controller = GameController(scene)
    # Calling on_direction or restart before load() should safely do nothing
    controller.on_direction(Direction.UP)
    assert controller.moves == 0
    assert controller.status == "playing"
    controller.restart()
    assert controller.stage is None


def test_fake_scene_methods():
    scene = FakeScene()
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    scene.load_stage(stage, FakeScene())
    assert scene.stage is stage
    scene.set_selected(1)
    assert scene.selected_cube == 1
    scene.show_state(None)
    assert scene.state is None


