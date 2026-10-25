"""Task 3.3c: two cubes, selection, split and merge driven by real Engine results."""
import importlib
from pathlib import Path

import pytest

from bloxorz.engine import Outcome, initial_state, step
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Bridge, Stage, Switch

SPLIT_01 = Path(__file__).resolve().parents[2] / "stages" / "fixtures" / "split_01.json"
U, D, L, R = Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT


def _theme():
    return importlib.import_module("bloxorz.gui.scene.theme")


class _Vec(tuple):
    def __sub__(self, other):
        return _Vec(a - b for a, b in zip(self, other))

    def length(self):
        return sum(value * value for value in self) ** 0.5


class _Animation:
    def __init__(self, entity, target):
        self.entity = entity
        self.target = tuple(target)
        self.callbacks = []
        self.killed = False

    def append(self, callback):
        self.callbacks.append(callback)

    def kill(self):
        self.killed = True

    def finish(self):
        self.entity.scale = self.target
        for callback in tuple(self.callbacks):
            callback()


@pytest.fixture
def env(monkeypatch, scene_modules):
    """Real SceneView/BlockView/Board with recorded fake Ursina animations."""
    animations = []
    timeline = []

    class Entity:
        def __init__(self, **kwargs):
            self.enabled = True
            self.animations = []
            self.parent = None
            self.__dict__.update(kwargs)

        @property
        def world_position(self):
            return _Vec(self.position)

        def animate_scale(self, target, duration=None, **_kwargs):
            animation = _Animation(self, target)
            animations.append(animation)
            self.animations.append(animation)
            return animation

    block_module = importlib.import_module("bloxorz.gui.scene.block")
    monkeypatch.setattr(block_module, "Entity", Entity)
    monkeypatch.setattr(scene_modules.board, "Entity", Entity)

    def recorder(name):
        def play(entity, *args, **_kwargs):
            timeline.append((name, entity))
            args[-1]()

        return play

    monkeypatch.setattr(scene_modules.view, "play_roll", recorder("roll"))
    monkeypatch.setattr(scene_modules.view, "play_fall", recorder("fall"))
    monkeypatch.setattr(scene_modules.view, "play_drop", recorder("drop"))

    def make_scene(stage, state):
        scene = scene_modules.view.SceneView()
        scene.load_stage(stage, state)
        return scene

    def drain():
        while animations:
            animations.pop(0).finish()

    return make_scene, timeline, drain


def _play(scene, drain, stage, state, action):
    result = step(stage, state, action)
    assert result.outcome is Outcome.MOVED, result
    done = []
    scene.animate_step(state, action, result, lambda: done.append(True))
    drain()
    assert done == [True]
    assert not scene.is_busy()
    return result


def _split_state(scene, drain, stage):
    state = initial_state(stage)
    for direction in (R, R):
        state = _play(scene, drain, stage, state, Action(direction)).state
    return state


def _visible_cubes(scene):
    return {
        (round(-cube.position[2]), round(cube.position[0]))
        for cube in scene.block.cubes
        if cube.enabled
    }


def test_standing_on_split_switch_rolls_then_shows_two_cubes(env):
    make_scene, timeline, drain = env
    stage = load_stage(SPLIT_01)
    scene = make_scene(stage, initial_state(stage))
    before = _play(scene, drain, stage, initial_state(stage), Action(R)).state
    timeline.clear()

    result = _play(scene, drain, stage, before, Action(R))

    assert result.events == ("split",)
    assert result.state == State(None, (1, 2), (1, 5), frozenset())
    assert timeline == [("roll", scene.block.entity)]
    assert not scene.block.entity.enabled
    assert _visible_cubes(scene) == {(1, 2), (1, 5)}
    # play_split grew both cubes from zero to full size.
    assert all(cube.animations for cube in scene.block.cubes)
    assert all(cube.scale == (1, 1, 1) for cube in scene.block.cubes)


def test_only_selected_cube_rolls_and_highlight_follows_index_swap(env):
    make_scene, timeline, drain = env
    stage = load_stage(SPLIT_01)
    scene = make_scene(stage, initial_state(stage))
    state = _split_state(scene, drain, stage)
    theme = _theme()

    scene.set_selected(1)
    assert scene.block.cubes[1].color == theme.SELECTED_CUBE_COLOR
    timeline.clear()

    # Cube 1 at (1,5) moves UP to (0,5), which now sorts first: index 0.
    result = _play(scene, drain, stage, state, Action(U, cube=1))

    assert result.state == State(None, (0, 5), (1, 2), frozenset())
    assert [entry[0] for entry in timeline] == ["roll"]
    assert timeline[0][1] is scene.block.cubes[1]
    assert _visible_cubes(scene) == {(0, 5), (1, 2)}
    assert scene.block.cube_cells == [(0, 5), (1, 2)]
    assert scene.block.cubes[0].color == theme.SELECTED_CUBE_COLOR
    assert scene.block.cubes[1].color == theme.CUBE_COLOR


@pytest.mark.parametrize(
    "moves, merged",
    [
        ([(L, 1), (L, 1)], State(Pose.HORIZONTAL, (1, 2), None, frozenset())),
        ([(U, 1), (R, 1), (R, 1), (R, 1)], State(Pose.VERTICAL, (0, 5), None, frozenset())),
    ],
)
def test_merge_shows_whole_block_with_engine_pose(env, moves, merged):
    make_scene, timeline, drain = env
    stage = load_stage(SPLIT_01)
    scene = make_scene(stage, initial_state(stage))
    state = _split_state(scene, drain, stage)
    scene.set_selected(0)
    merges = 0

    for direction, cube in moves:
        result = _play(scene, drain, stage, state, Action(direction, cube=cube))
        merges += result.events.count("merge")
        state = result.state

    assert state == merged
    assert merges == 1
    assert scene.block.entity.enabled
    assert _visible_cubes(scene) == set()
    position, scale = _theme().block_transform(merged)
    assert scene.block.entity.position == position
    assert scene.block.entity.scale == scale


def test_split_cube_fall_drops_only_the_moving_cube(env):
    make_scene, timeline, drain = env
    stage = load_stage(SPLIT_01)
    scene = make_scene(stage, initial_state(stage))
    state = _split_state(scene, drain, stage)
    state = _play(scene, drain, stage, state, Action(U, cube=1)).state
    timeline.clear()

    # Cube 0 is now at (0,5); UP leaves the board.
    result = step(stage, state, Action(U, cube=0))
    assert result.reason == "fell"
    done = []
    scene.show_illegal_step(state, Action(U, cube=0), result, lambda: done.append(1))

    assert timeline == [("fall", scene.block.cubes[0])]
    assert done == [1]


def test_split_bridge_closed_drops_only_cube_on_closed_bridge(env):
    make_scene, timeline, drain = env
    # Moving cube (1,4) -> soft toggle at (1,3) closes b1 under cube (1,1).
    stage = Stage(
        id="split_bridge_closed",
        group="G4",
        grid=("######", "#B####", "#####G"),
        start=(2, 1),
        goal=(2, 5),
        bridges=(Bridge("b1", ((1, 1),), initially_open=True),),
        switches=(Switch("sw1", "soft", (1, 3), mode="toggle", bridges=("b1",)),),
    )
    before = State(None, (1, 1), (1, 4), frozenset({"b1"}))
    action = Action(L, cube=1)
    result = step(stage, before, action)
    assert result.reason == "bridge_closed"
    assert result.events == ("switch:sw1", "bridge:b1:close")

    scene = make_scene(stage, initial_state(stage))
    timeline.clear()
    done = []
    scene.show_illegal_step(before, action, result, lambda: done.append(1))
    drain()

    assert timeline == [
        ("roll", scene.block.cubes[1]),
        ("drop", scene.block.cubes[0]),
    ]
    assert done == [1]
    assert not scene.board.bridge_tiles["b1"][0].enabled
    assert not scene.is_busy()


def test_restart_while_split_kills_cube_animations_and_clears_selection(env):
    make_scene, timeline, drain = env
    stage = load_stage(SPLIT_01)
    scene = make_scene(stage, initial_state(stage))
    state = _split_state(scene, drain, stage)
    scene.set_selected(1)

    pending = scene.block.cubes[1].animate_scale((1, 1, 1))
    scene._busy = True

    scene.load_stage(stage, initial_state(stage))

    assert pending.killed
    assert not scene.is_busy()
    assert scene.block.entity.enabled
    assert _visible_cubes(scene) == set()
    assert scene._selected_pos is None
    assert scene.selected_cube is None


def test_block_view_toggles_between_block_and_cubes(env):
    make_scene, *_ = env
    stage = load_stage(SPLIT_01)
    scene = make_scene(stage, initial_state(stage))
    block = scene.block

    block.place(State(None, (1, 2), (1, 5)))
    assert not block.entity.enabled
    assert [cube.position for cube in block.cubes] == [(2, 0.5, -1), (5, 0.5, -1)]

    block.place(initial_state(stage))
    assert block.entity.enabled
    assert not any(cube.enabled for cube in block.cubes)


def test_highlight_follows_swapped_cube_before_switch_events_finish(env):
    make_scene, timeline, drain = env
    # Cube 1 at (1,4) moves UP onto soft switch sw1 at (0,4): it now sorts
    # first, and the move opens bridge b1, so board events are still running.
    stage = Stage(
        id="swap_on_switch",
        group="G4",
        grid=("######", "######", "B####G"),
        start=(1, 2),
        goal=(2, 5),
        bridges=(Bridge("b1", ((2, 0),)),),
        switches=(Switch("sw1", "soft", (0, 4), mode="toggle", bridges=("b1",)),),
    )
    before = State(None, (1, 1), (1, 4), frozenset())
    action = Action(U, cube=1)
    result = step(stage, before, action)
    assert result.state == State(None, (0, 4), (1, 1), frozenset({"b1"}))
    assert result.events == ("switch:sw1", "bridge:b1:open")

    scene = make_scene(stage, initial_state(stage))
    scene.show_state(before)
    scene.set_selected(1)
    done = []

    scene.animate_step(before, action, result, lambda: done.append(True))

    # Switch/bridge animations have not finished yet.
    assert scene.is_busy()
    assert done == []
    assert scene.block.cube_cells == [(0, 4), (1, 1)]
    assert scene.block.cubes[0].color == _theme().SELECTED_CUBE_COLOR
    assert scene.block.cubes[1].color == _theme().CUBE_COLOR

    drain()
    assert done == [True]
    assert scene.block.cubes[0].color == _theme().SELECTED_CUBE_COLOR


def test_play_split_ignores_repeated_callback_from_one_cube(env):
    make_scene, *_ = env
    stage = load_stage(SPLIT_01)
    scene = make_scene(stage, initial_state(stage))
    cubes = scene.block.cubes
    scene.block.place(State(None, (1, 2), (1, 5)))
    animate = importlib.import_module("bloxorz.gui.scene.animate")
    finished = []

    animate.play_split(cubes, lambda: finished.append(True))
    first, second = cubes[0].animations[-1], cubes[1].animations[-1]

    first.finish()
    first.finish()
    assert finished == []

    second.finish()
    second.finish()
    assert finished == [True]


def test_restart_while_cubes_grow_after_split(env):
    make_scene, timeline, drain = env
    stage = load_stage(SPLIT_01)
    scene = make_scene(stage, initial_state(stage))
    before = _play(scene, drain, stage, initial_state(stage), Action(R)).state
    result = step(stage, before, Action(R))
    assert result.events == ("split",)
    done = []

    scene.animate_step(before, Action(R), result, lambda: done.append("old"))
    growing = [cube.animations[-1] for cube in scene.block.cubes]
    assert scene.is_busy()

    # Restart while both cubes are still growing in.
    scene.load_stage(stage, initial_state(stage))

    assert not scene.is_busy()
    assert all(animation.killed for animation in growing)
    assert scene.block.entity.enabled
    assert _visible_cubes(scene) == set()

    for animation in growing:
        animation.finish()
    assert done == []
    assert not scene.is_busy()

    # The same split plays normally on the new stage.
    scene.animate_step(before, Action(R), result, lambda: done.append("new"))
    drain()
    assert done == ["new"]
    assert _visible_cubes(scene) == {(1, 2), (1, 5)}
