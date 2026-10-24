"""Task 3.3a: fragile scenes driven by real Engine results and stage files."""
from pathlib import Path

from bloxorz.engine import Outcome, initial_state, step
from bloxorz.engine.rules import footprint
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Stage

FRAGILE_01 = Path(__file__).resolve().parents[2] / "stages" / "fixtures" / "fragile_01.json"


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


def _scene(scene_modules, stage, state):
    scene = scene_modules.view.SceneView()
    scene.block = _FakeBlock()
    scene.load_stage(stage, state)
    return scene


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


def test_load_stage_during_tile_break_unlocks_and_ignores_stale_callbacks(
    monkeypatch, scene_modules
):
    stage = load_stage(FRAGILE_01)
    before = State(Pose.HORIZONTAL, (1, 3), None, frozenset())
    action = Action(Direction.LEFT)
    result = step(stage, before, action)
    assert result.reason == "fragile_broke"

    scene = _scene(scene_modules, stage, initial_state(stage))
    tile_callbacks = []
    drops = []
    monkeypatch.setattr(
        scene_modules.view,
        "play_roll",
        lambda _block, _direction, on_done: on_done(),
    )
    monkeypatch.setattr(
        scene_modules.board,
        "play_fragile_break",
        lambda _tile, on_done: tile_callbacks.append(on_done),
    )
    monkeypatch.setattr(
        scene_modules.view,
        "play_drop",
        lambda _block, on_done: drops.append(on_done),
    )
    done = []

    scene.show_fragile_fall(before, action, (1, 2), lambda: done.append("old"))
    assert scene.is_busy()

    # Restart while F is collapsing: Ursina's destroy() kills the tile
    # animation, so the scene must unlock without waiting for it.
    scene.load_stage(stage, initial_state(stage))
    assert not scene.is_busy()
    assert scene.block.placed[-1] == initial_state(stage)

    tile_callbacks[0]()
    assert drops == []
    assert done == []

    # The rebuilt F tile is intact and the new stage animates normally.
    scene.show_fragile_fall(before, action, (1, 2), lambda: done.append("new"))
    tile_callbacks[1]()
    drops[0]()
    drops[0]()

    assert done == ["new"]
    assert not scene.is_busy()
