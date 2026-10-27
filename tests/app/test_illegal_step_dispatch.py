"""Controller must animate a lost move according to the engine's reason."""
from __future__ import annotations

from pathlib import Path

import pytest

import bloxorz.gui.controller as controller_module
from bloxorz.engine import Outcome, StepResult
from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import FakeScene
from bloxorz.loader import load_stage
from bloxorz.model import Direction

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "stages" / "fixtures"


def _game():
    stage = load_stage(FIXTURES_DIR / "basic_01.json")
    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage)
    return controller, scene


def test_real_fall_goes_through_show_fall():
    controller, scene = _game()

    controller.on_direction(Direction.LEFT)

    assert controller.status == "lost"
    assert controller.fail_reason == "fell"
    assert [e for e in scene.events if e[0] == "show_fall"]


@pytest.mark.parametrize("reason", ["fragile_broke", "bridge_closed"])
def test_illegal_reason_uses_show_illegal_step(monkeypatch, reason):
    controller, scene = _game()
    monkeypatch.setattr(
        controller_module,
        "step",
        lambda stage, state, action: StepResult(Outcome.ILLEGAL, None, reason),
    )

    controller.on_direction(Direction.RIGHT)

    illegal = [e for e in scene.events if e[0] == "show_illegal_step"]
    assert len(illegal) == 1
    assert illegal[0][3] == reason
    assert not [e for e in scene.events if e[0] == "show_fall"]
    assert controller.fail_reason == reason
    assert controller.status == "lost"


def test_unknown_reason_falls_back_to_show_fall(monkeypatch):
    controller, scene = _game()
    monkeypatch.setattr(
        controller_module,
        "step",
        lambda stage, state, action: StepResult(Outcome.ILLEGAL, None, "weird"),
    )

    controller.on_direction(Direction.RIGHT)

    assert [e for e in scene.events if e[0] == "show_fall"]
    assert controller.status == "lost"


def test_old_illegal_callback_does_not_lose_restarted_game(monkeypatch):
    controller, scene = _game()
    monkeypatch.setattr(
        controller_module,
        "step",
        lambda stage, state, action: StepResult(Outcome.ILLEGAL, None, "bridge_closed"),
    )
    callbacks = []
    scene.show_illegal_step = lambda before, action, result, on_done: callbacks.append(on_done)

    controller.on_direction(Direction.RIGHT)
    assert controller.status == "falling"
    controller.restart()
    callbacks[0]()

    assert controller.status == "playing"
