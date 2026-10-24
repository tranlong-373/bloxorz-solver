"""Task 3.3b: switches and bridges driven by real Engine results."""
from pathlib import Path

import pytest

from bloxorz.engine import Outcome, StepResult, initial_state, step
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Bridge, Stage, Switch

FIXTURES = Path(__file__).resolve().parents[2] / "stages" / "fixtures"
OPEN_SCALE = (0.95, 0.2, 0.95)


class _Vec(tuple):
    def __sub__(self, other):
        return _Vec(a - b for a, b in zip(self, other))

    def length(self):
        return sum(value * value for value in self) ** 0.5


class _FakeBlock:
    def __init__(self):
        self.entity = type("BlockEntity", (), {})()
        self.placed = []

    def place(self, state):
        self.placed.append(state)
        self.entity.world_position = _Vec((state.pos[1], 0, -state.pos[0]))


class _Animation:
    def __init__(self, log, entity, target):
        self.callbacks = []
        self.entity = entity
        self.target = tuple(target)
        log.append(self)

    def append(self, callback):
        self.callbacks.append(callback)

    def finish(self):
        self.entity.scale = self.target
        for callback in tuple(self.callbacks):
            callback()


@pytest.fixture
def scene_env(monkeypatch, scene_modules):
    """SceneView with real Board logic, fake Ursina entities and animations."""
    animations = []
    timeline = []

    class Entity:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.enabled = True

        def animate_scale(self, target, duration=None, **_kwargs):
            return _Animation(animations, self, target)

    monkeypatch.setattr(scene_modules.board, "Entity", Entity)

    def roll(_block, direction, on_done):
        timeline.append(("roll", direction))
        on_done()

    def drop(_block, on_done):
        timeline.append("drop")
        on_done()

    monkeypatch.setattr(scene_modules.view, "play_roll", roll)
    monkeypatch.setattr(scene_modules.view, "play_drop", drop)

    def make_scene(stage, state):
        scene = scene_modules.view.SceneView()
        scene.block = _FakeBlock()
        scene.load_stage(stage, state)
        return scene

    def drain():
        """Finish pending animations in start order, like Ursina's update loop."""
        while animations:
            animation = animations.pop(0)
            timeline.append(("anim", animation.target))
            animation.finish()

    return make_scene, animations, timeline, drain


def _bridge_closing_stage():
    # Lying on (1,2)-(1,3) presses soft toggle sw1, which closes b1 at (1,3).
    return Stage(
        id="bridge_closed_test",
        group="G3",
        grid=("#######", "###B#G#", "#######"),
        start=(1, 1),
        goal=(1, 5),
        bridges=(Bridge("b1", ((1, 3),), initially_open=True),),
        switches=(
            Switch("sw1", "soft", (1, 2), mode="toggle", bridges=("b1",)),
        ),
    )


def test_soft_switch_event_opens_whole_bridge_then_finishes_once(scene_env):
    make_scene, animations, timeline, drain = scene_env
    stage = load_stage(FIXTURES / "soft_toggle_01.json")
    before = initial_state(stage)
    action = Action(Direction.RIGHT)
    result = step(stage, before, action)
    assert result.events == ("switch:sw1", "bridge:b1:open")

    scene = make_scene(stage, before)
    tiles = scene.board.bridge_tiles["b1"]
    assert [tile.enabled for tile in tiles] == [False, False]
    done = []

    scene.animate_step(before, action, result, lambda: done.append("done"))
    assert scene.is_busy()
    drain()

    assert done == ["done"]
    assert not scene.is_busy()
    assert all(tile.enabled and tile.scale == OPEN_SCALE for tile in tiles)
    # Switch pulse first, then both bridge tiles together.
    assert [entry[0] for entry in timeline] == ["roll", "anim", "anim", "anim"]


def test_heavy_permanent_ignores_lying_and_never_fakes_a_bridge_change(scene_env):
    make_scene, animations, timeline, drain = scene_env
    stage = load_stage(FIXTURES / "heavy_permanent_01.json")
    moves = [Direction.RIGHT, Direction.RIGHT, Direction.LEFT, Direction.RIGHT]
    state = initial_state(stage)
    scene = make_scene(stage, state)
    tiles = scene.board.bridge_tiles["b1"]
    seen_events = []

    for direction in moves:
        result = step(stage, state, Action(direction))
        assert result.outcome is Outcome.MOVED
        seen_events.append(result.events)
        before_count = len(timeline)
        scene.animate_step(state, Action(direction), result, lambda: None)
        drain()
        bridge_animations = [
            entry for entry in timeline[before_count:]
            if entry[0] == "anim" and entry[1] in (OPEN_SCALE, (0, 0, 0))
        ]
        if "bridge:b1:open" not in result.events:
            assert bridge_animations == []
        state = result.state

    assert seen_events == [
        (),
        ("switch:sw1", "bridge:b1:open"),
        (),
        ("switch:sw1",),
    ]
    assert all(tile.enabled for tile in tiles)
    assert not scene.is_busy()


def test_two_switches_on_one_cell_are_both_drawn(scene_env):
    make_scene, *_ = scene_env
    stage = Stage(
        id="shared_cell",
        group="G3",
        grid=("#####", "###B#", "##G##"),
        start=(1, 1),
        goal=(2, 2),
        bridges=(Bridge("b1", ((1, 3),)),),
        switches=(
            Switch("sw_a", "soft", (1, 2), mode="toggle", bridges=("b1",)),
            Switch("sw_b", "heavy", (1, 2), mode="toggle", bridges=("b1",)),
        ),
    )
    assert len(stage.switch_at[(1, 2)]) == 2

    scene = make_scene(stage, initial_state(stage))

    assert set(scene.board.switch_entities) == {"sw_a", "sw_b"}
    assert all(scene.board.switch_entities[sid] for sid in ("sw_a", "sw_b"))


def test_bridge_closed_rolls_then_plays_events_then_drops(scene_env):
    make_scene, animations, timeline, drain = scene_env
    stage = _bridge_closing_stage()
    before = initial_state(stage)
    action = Action(Direction.RIGHT)
    result = step(stage, before, action)
    assert result.outcome is Outcome.ILLEGAL
    assert result.reason == "bridge_closed"
    assert result.events == ("switch:sw1", "bridge:b1:close")

    scene = make_scene(stage, before)
    bridge_tile = scene.board.bridge_tiles["b1"][0]
    assert bridge_tile.enabled
    done = []

    scene.show_illegal_step(before, action, result, lambda: done.append("done"))
    drain()
    drain()

    assert done == ["done"]
    assert not scene.is_busy()
    assert not bridge_tile.enabled
    steps = [entry if isinstance(entry, str) else entry[0] for entry in timeline]
    # roll -> switch pulse -> bridge closes -> block drops.
    assert steps == ["roll", "anim", "anim", "drop"]
    assert timeline[2][1] == (0, 0, 0)


def test_bridge_closed_for_split_cubes_is_left_to_task_3_3c(scene_env):
    make_scene, *_ = scene_env
    stage = _bridge_closing_stage()
    scene = make_scene(stage, initial_state(stage))
    split = State(None, (1, 1), (1, 5), frozenset({"b1"}))

    with pytest.raises(NotImplementedError, match="3.3c"):
        scene.show_illegal_step(
            split,
            Action(Direction.RIGHT, cube=0),
            StepResult(Outcome.ILLEGAL, None, "bridge_closed", ("switch:sw1",)),
            lambda: None,
        )


@pytest.mark.parametrize("move", ["animate_step", "bridge_closed"])
def test_restart_during_bridge_animation_unlocks_scene(scene_env, move):
    make_scene, animations, timeline, drain = scene_env
    if move == "animate_step":
        stage = load_stage(FIXTURES / "soft_toggle_01.json")
    else:
        stage = _bridge_closing_stage()
    before = initial_state(stage)
    action = Action(Direction.RIGHT)
    result = step(stage, before, action)

    scene = make_scene(stage, before)
    done = []
    if move == "animate_step":
        scene.animate_step(before, action, result, lambda: done.append("old"))
    else:
        scene.show_illegal_step(before, action, result, lambda: done.append("old"))
    assert scene.is_busy()
    stale = list(animations)
    animations.clear()

    # Restart while the switch/bridge animation runs (Ursina's destroy()
    # kills those sequences, so their callbacks may never arrive).
    scene.load_stage(stage, initial_state(stage))
    assert not scene.is_busy()
    tiles = scene.board.bridge_tiles["b1"]
    initially_open = "b1" in stage.initial_bridges_open()
    assert all(tile.enabled is initially_open for tile in tiles)

    # Even if a stale callback does arrive, it must not finish anything.
    for animation in stale:
        animation.finish()
    assert done == []
    assert not scene.is_busy()

    # The new stage plays the same move normally.
    if move == "animate_step":
        scene.animate_step(before, action, result, lambda: done.append("new"))
    else:
        scene.show_illegal_step(before, action, result, lambda: done.append("new"))
    drain()
    assert done == ["new"]
    assert not scene.is_busy()
