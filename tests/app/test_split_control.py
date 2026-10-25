"""Split-cube control tests: selection by cell, Space switching. Owner: VT4 (task 4.4)."""
from __future__ import annotations

from pathlib import Path

from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import FakeScene
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, Pose

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "stages" / "fixtures"


def _split_game() -> tuple[GameController, FakeScene]:
    """Load split_01 and roll onto the split switch: cubes at (1, 2) and (1, 5)."""
    stage = load_stage(FIXTURES_DIR / "split_01.json")
    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage)
    controller.on_direction(Direction.RIGHT)
    controller.on_direction(Direction.RIGHT)
    return controller, scene


def test_split_selects_first_cube():
    controller, scene = _split_game()

    assert controller.state.pose is None
    assert (controller.state.pos, controller.state.cube2) == ((1, 2), (1, 5))
    assert controller.selected_pos == (1, 2)
    assert scene.selected_cube == 0
    assert controller.moves == 2


def test_space_twice_returns_to_first_cube_without_moves():
    controller, scene = _split_game()

    controller.switch_cube()
    assert controller.selected_pos == (1, 5)
    assert scene.selected_cube == 1
    assert controller.moves == 2

    controller.switch_cube()
    assert controller.selected_pos == (1, 2)
    assert scene.selected_cube == 0
    assert controller.moves == 2


def test_arrow_moves_only_selected_cube():
    controller, scene = _split_game()
    controller.switch_cube()

    controller.on_direction(Direction.RIGHT)

    assert (controller.state.pos, controller.state.cube2) == ((1, 2), (1, 6))
    assert controller.selected_pos == (1, 6)
    assert scene.selected_cube == 1
    moved = [e for e in scene.events if e[0] == "animate_step"][-1]
    assert moved[2] == Action(Direction.RIGHT, cube=1)


def test_selection_follows_cube_when_state_order_swaps():
    controller, scene = _split_game()
    controller.switch_cube()  # select (1, 5), which is cube 1

    controller.on_direction(Direction.UP)

    # (0, 5) now sorts before (1, 2), so the moved cube becomes cube 0.
    assert (controller.state.pos, controller.state.cube2) == ((0, 5), (1, 2))
    assert controller.selected_pos == (0, 5)
    assert scene.selected_cube == 0

    # The next arrow still moves the same physical cube.
    controller.on_direction(Direction.RIGHT)
    assert (controller.state.pos, controller.state.cube2) == ((0, 6), (1, 2))
    assert controller.selected_pos == (0, 6)


def test_merge_clears_selection_and_game_can_be_won():
    controller, scene = _split_game()

    controller.on_direction(Direction.RIGHT)  # (1, 2) -> (1, 3)
    controller.on_direction(Direction.RIGHT)  # (1, 3) -> (1, 4), next to (1, 5)

    assert controller.state.pose == Pose.HORIZONTAL
    assert controller.state.pos == (1, 4)
    assert controller.selected_pos is None
    assert scene.selected_cube is None

    controller.on_direction(Direction.RIGHT)
    assert controller.status == "won"
    assert controller.moves == 5


def test_space_ignored_when_not_split():
    stage = load_stage(FIXTURES_DIR / "split_01.json")
    scene = FakeScene()
    controller = GameController(scene)
    controller.load(stage)

    controller.switch_cube()

    assert controller.selected_pos is None
    assert ("set_selected", 0) not in scene.events
    assert ("set_selected", 1) not in scene.events


def test_space_ignored_while_scene_busy():
    controller, scene = _split_game()
    scene.busy = True

    controller.switch_cube()

    assert controller.selected_pos == (1, 2)
    assert scene.selected_cube == 0


def test_restart_clears_selection():
    controller, scene = _split_game()

    controller.restart()

    assert controller.selected_pos is None
    assert controller.state.pose == Pose.STANDING


def test_cube_fall_while_split_loses():
    controller, scene = _split_game()
    controller.on_direction(Direction.DOWN)  # (1, 2) -> (2, 2)

    controller.on_direction(Direction.DOWN)  # off the board

    assert controller.status == "lost"
    assert controller.moves == 3
    fall = [e for e in scene.events if e[0] == "show_fall"][-1]
    # (2, 2) sorts after (1, 5), so the same physical cube is now cube 1.
    assert fall[2] == Action(Direction.DOWN, cube=1)
