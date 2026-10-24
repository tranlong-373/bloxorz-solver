"""Task 3.3a: fragile scenes driven by real Engine results and stage files."""
from pathlib import Path

import pytest

from bloxorz.engine import Outcome, StepResult, initial_state, step
from bloxorz.engine.rules import footprint
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Stage

FRAGILE_01 = Path(__file__).resolve().parents[2] / "stages" / "fixtures" / "fragile_01.json"

# In fragile_01 ("#SFFG#"), lying on (1,3)-(1,4) and rolling LEFT stands on F (1,2).
BREAK_BEFORE = State(Pose.HORIZONTAL, (1, 3), None, frozenset())
BREAK_ACTION = Action(Direction.LEFT)


class _Vec(tuple):
    def __sub__(self, other):
        return _Vec(a - b for a, b in zip(self, other))

    def length(self):
        return sum(value * value for value in self) ** 0.5


class _FakeBlock:
    """BlockView stand-in exposing the world_position read by animate_step."""

    def __init__(self):
        self.entity = type("BlockEntity", (), {})()
        self.placed = []

    def place(self, state):
        self.placed.append(state)
        self.entity.world_position = _Vec((state.pos[1], 0, -state.pos[0]))


class _FakeSequence:
    def __init__(self):
        self.killed = False

    def kill(self):
        self.killed = True


def _scene(scene_modules, stage, state):
    scene = scene_modules.view.SceneView()
    scene.block = _FakeBlock()
    scene.load_stage(stage, state)
    return scene


def _capture_fragile_animations(monkeypatch, scene_modules):
    pending = {"roll": [], "tile": [], "drop": []}
    monkeypatch.setattr(
        scene_modules.view,
        "play_roll",
        lambda _block, _direction, on_done: pending["roll"].append(on_done),
    )
    monkeypatch.setattr(
        scene_modules.board,
        "play_fragile_break",
        lambda _tile, on_done: pending["tile"].append(on_done),
    )
    monkeypatch.setattr(
        scene_modules.view,
        "play_drop",
        lambda _block, on_done: pending["drop"].append(on_done),
    )
    return pending


def test_lying_across_fragile_rolls_without_breaking_tile(monkeypatch, scene_modules):
    stage = load_stage(FRAGILE_01)
    before = initial_state(stage)
    action = Action(Direction.RIGHT)
    result = step(stage, before, action)

    assert result.outcome is Outcome.MOVED
    assert result.state.pose is Pose.HORIZONTAL
    assert [stage.cell(cell) for cell in footprint(result.state)] == ["F", "F"]

    scene = _scene(scene_modules, stage, before)
    breaks = []
    monkeypatch.setattr(
        scene_modules.board,
        "play_fragile_break",
        lambda *args: breaks.append(args),
    )
    monkeypatch.setattr(
        scene_modules.view,
        "play_roll",
        lambda _block, _direction, on_done: on_done(),
    )
    done = []

    scene.animate_step(before, action, result, lambda: done.append("done"))

    assert done == ["done"]
    assert breaks == []
    assert not scene.board._broken_fragile
    assert scene.block.placed[-1] == result.state
    assert not scene.is_busy()


def test_split_cube_landing_on_fragile_is_a_normal_move():
    rows = [list("#######") for _ in range(7)]
    rows[3][1] = "F"
    rows[6][6] = "G"
    stage = Stage(
        id="cube_on_f",
        group="G4",
        grid=tuple("".join(row) for row in rows),
        start=(3, 3),
        goal=(6, 6),
    )
    before = State(None, (3, 0), (3, 6), frozenset())

    result = step(stage, before, Action(Direction.RIGHT, cube=0))

    # Engine never reports fragile_broke for a cube, so the scene receives
    # animate_step (task 3.3c) and never show_fragile_fall.
    assert result.outcome is Outcome.MOVED
    assert result.reason == ""
    assert result.state.pos == (3, 1)


def test_show_illegal_step_dispatches_on_engine_reason(monkeypatch, scene_modules):
    stage = load_stage(FRAGILE_01)
    scene = _scene(scene_modules, stage, initial_state(stage))
    calls = []
    monkeypatch.setattr(
        scene,
        "show_fall",
        lambda before, action, on_done: calls.append(("fall", action.direction)),
    )
    monkeypatch.setattr(
        scene,
        "show_fragile_fall",
        lambda before, action, cell, on_done: calls.append(("fragile", cell)),
    )
    # Task 3.3b: bridge_closed plays the board events between roll and drop.
    monkeypatch.setattr(
        scene,
        "_show_landing_fall",
        lambda before, action, board_effect, on_done: calls.append(
            ("landing", action.direction)
        ),
    )

    fragile = step(stage, BREAK_BEFORE, BREAK_ACTION)
    fell = step(stage, initial_state(stage), Action(Direction.UP))
    assert fragile.reason == "fragile_broke"
    assert fell.reason == "fell"

    scene.show_illegal_step(BREAK_BEFORE, BREAK_ACTION, fragile, lambda: None)
    scene.show_illegal_step(
        initial_state(stage), Action(Direction.UP), fell, lambda: None
    )
    scene.show_illegal_step(
        initial_state(stage),
        Action(Direction.UP),
        StepResult(Outcome.ILLEGAL, None, "bridge_closed", ("switch:s1",)),
        lambda: None,
    )

    assert calls == [
        ("fragile", (1, 2)),
        ("fall", Direction.UP),
        ("landing", Direction.UP),
    ]

    moved = step(stage, initial_state(stage), Action(Direction.RIGHT))
    with pytest.raises(ValueError, match="Not an illegal-move result"):
        scene.show_illegal_step(
            initial_state(stage), Action(Direction.RIGHT), moved, lambda: None
        )


@pytest.mark.parametrize("phase", ["roll", "tile", "drop"])
def test_load_stage_mid_fragile_fall_unlocks_and_ignores_stale_callbacks(
    monkeypatch, scene_modules, phase
):
    stage = load_stage(FRAGILE_01)
    result = step(stage, BREAK_BEFORE, BREAK_ACTION)
    assert result.reason == "fragile_broke"

    scene = _scene(scene_modules, stage, initial_state(stage))
    pending = _capture_fragile_animations(monkeypatch, scene_modules)
    done = []

    scene.show_illegal_step(
        BREAK_BEFORE, BREAK_ACTION, result, lambda: done.append("old")
    )
    # Advance the old animation to the phase under test.
    if phase in ("tile", "drop"):
        pending["roll"][0]()
    if phase == "drop":
        pending["tile"][0]()
    assert scene.is_busy()
    stale_callback = pending[phase][0]

    # Restart / New Game in the middle of the animation.
    scene.load_stage(stage, initial_state(stage))
    assert not scene.is_busy()
    assert scene.block.placed[-1] == initial_state(stage)

    # The new stage animates before the old callback arrives; the stale
    # callback must neither finish nor unlock the new animation.
    scene.show_illegal_step(
        BREAK_BEFORE, BREAK_ACTION, result, lambda: done.append("new")
    )
    stale_callback()
    assert scene.is_busy()
    assert done == []

    pending["roll"][-1]()
    pending["tile"][-1]()
    pending["drop"][-1]()
    pending["drop"][-1]()

    assert done == ["new"]
    assert not scene.is_busy()


def test_load_stage_kills_block_animations_and_removes_roll_pivot(
    monkeypatch, scene_modules
):
    stage = load_stage(FRAGILE_01)
    scene = _scene(scene_modules, stage, initial_state(stage))
    view_module = scene_modules.view

    drop = _FakeSequence()
    rotation = _FakeSequence()
    pivot = type("Pivot", (), {})()
    pivot.animations = [rotation]
    scene.block.entity.animations = [drop]
    scene.block.entity.parent = pivot
    destroyed = []
    monkeypatch.setattr(view_module, "destroy", destroyed.append)
    scene._busy = True

    scene.load_stage(stage, initial_state(stage))

    assert drop.killed
    assert rotation.killed
    assert scene.block.entity.world_parent is view_module.scene
    assert destroyed == [pivot]
    assert not scene.is_busy()
