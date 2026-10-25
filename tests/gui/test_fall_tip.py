"""Task 3.4: a lying block that lands half on the floor tips over that edge."""
import pytest

from bloxorz.engine import step
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Bridge, Stage

U, D, L, R = Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT

# One hole at (3,3); everything else is floor.
HOLE = Stage(
    id="hole",
    group="G1",
    grid=("#######", "#######", "#######", "###.###", "#######", "#######", "######G"),
    start=(0, 0),
    goal=(6, 6),
)


@pytest.fixture
def scene(scene_modules):
    def make(stage):
        view = scene_modules.view.SceneView()
        view.block = type("Block", (), {"place": lambda self, state: None})()
        view.block.entity = object()
        view.load_stage(stage, State(Pose.STANDING, stage.start))
        return view

    return make


@pytest.mark.parametrize(
    "before, direction, expected",
    [
        # Standing -> lying across the hole: held cell left / right of it.
        (State(Pose.STANDING, (3, 1)), R, ((2.5, 0, -3), "rotation_z", 90)),
        (State(Pose.STANDING, (3, 2)), R, ((3.5, 0, -3), "rotation_z", -90)),
        (State(Pose.STANDING, (3, 5)), L, ((3.5, 0, -3), "rotation_z", -90)),
        # Standing -> vertical: held cell above / below the hole.
        (State(Pose.STANDING, (1, 3)), D, ((3, 0, -2.5), "rotation_x", -90)),
        (State(Pose.STANDING, (5, 3)), U, ((3, 0, -3.5), "rotation_x", 90)),
        # Lying blocks rolled sideways onto the hole.
        (State(Pose.HORIZONTAL, (2, 2)), D, ((2.5, 0, -3), "rotation_z", 90)),
        (State(Pose.VERTICAL, (2, 4)), L, ((3, 0, -2.5), "rotation_x", -90)),
    ],
)
def test_half_held_landing_tips_toward_the_hole(scene, before, direction, expected):
    assert step(HOLE, before, Action(direction)).reason == "fell"
    view = scene(HOLE)

    assert view._fall_tip(before, Action(direction)) == expected


def test_fully_unsupported_landing_keeps_plain_roll_and_drop(scene):
    cliff = Stage(id="cliff", group="G1", grid=("###..", "###.G"), start=(0, 0), goal=(1, 4))
    before = State(Pose.STANDING, (0, 2))
    assert step(cliff, before, Action(R)).reason == "fell"

    assert scene(cliff)._fall_tip(before, Action(R)) is None


def test_split_cube_fall_never_tips(scene):
    view = scene(HOLE)
    before = State(None, (3, 2), (0, 0))

    assert view._fall_tip(before, Action(R, cube=1)) is None


def test_closed_bridge_and_broken_fragile_show_no_floor(scene):
    stage = Stage(
        id="floor_kinds",
        group="G3",
        grid=("#B#", "#FG"),
        start=(0, 0),
        goal=(1, 2),
        bridges=(Bridge("b1", ((0, 1),), initially_open=False),),
    )
    view = scene(stage)

    assert view.board.has_floor((0, 0))
    assert not view.board.has_floor((0, 1))  # closed bridge
    assert not view.board.has_floor((5, 5))  # outside the stage
    assert view.board.has_floor((1, 1))
    view.board._broken_fragile.add((1, 1))
    assert not view.board.has_floor((1, 1))


def test_show_fall_passes_the_tip_to_play_fall(monkeypatch, scene, scene_modules):
    view = scene(HOLE)
    calls = []
    monkeypatch.setattr(
        scene_modules.view,
        "play_fall",
        lambda entity, direction, on_done, tip=None: calls.append(tip) or on_done(),
    )
    before = State(Pose.STANDING, (3, 1))
    result = step(HOLE, before, Action(R))
    done = []

    view.show_illegal_step(before, Action(R), result, lambda: done.append(1))

    assert calls == [((2.5, 0, -3), "rotation_z", 90)]
    assert done == [1]
    assert not view.is_busy()
