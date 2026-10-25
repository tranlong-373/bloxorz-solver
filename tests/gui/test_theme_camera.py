"""Task 3.4: switch/bridge color links and the front-left camera."""
import importlib
from pathlib import Path

from bloxorz.engine import initial_state
from bloxorz.loader import load_stage
from bloxorz.stage import Bridge, Stage, Switch

STAGE_20 = Path(__file__).resolve().parents[2] / "stages" / "original" / "stage_20.json"


def test_each_switch_shares_its_color_with_the_bridges_it_drives(scene_modules):
    theme = importlib.import_module("bloxorz.gui.scene.theme")
    stage = Stage(
        id="links",
        group="G3",
        grid=("#BB#", "##.G"),
        start=(0, 0),
        goal=(1, 3),
        bridges=(Bridge("b1", ((0, 1),)), Bridge("b2", ((0, 2),))),
        switches=(
            Switch("sw_b", "heavy", (1, 1), mode="toggle", bridges=("b2",)),
            Switch("sw_a", "soft", (1, 0), mode="toggle", bridges=("b1", "b2")),
            Switch("split1", "split", (0, 3), targets=((0, 0), (1, 0))),
        ),
    )

    switch_rgb, bridge_rgb = theme.switch_link_colors(stage)

    assert set(switch_rgb) == {"sw_a", "sw_b"}  # split switches drive no bridge
    assert switch_rgb["sw_a"] != switch_rgb["sw_b"]
    assert bridge_rgb["b1"] == switch_rgb["sw_a"]
    # b2 is driven by both; it takes the first switch by id.
    assert bridge_rgb["b2"] == switch_rgb["sw_a"]


def test_board_paints_bridges_and_switch_buttons_with_the_linked_color(scene_modules):
    theme = importlib.import_module("bloxorz.gui.scene.theme")
    stage = load_stage(STAGE_20)
    board = scene_modules.board.Board()
    board.build(stage)
    switch_rgb, bridge_rgb = theme.switch_link_colors(stage)

    for bridge_id, tiles in board.bridge_tiles.items():
        assert all(tile.color == theme.rgb(bridge_rgb[bridge_id]) for tile in tiles)
    for switch in stage.switches:
        if switch.id in switch_rgb:
            # The tile stays plain stone; the button on it carries the color.
            assert board.tiles[switch.pos].color == theme.TILE_COLORS["#"]
            buttons = [entity for entity, _ in board.switch_entities[switch.id]]
            linked = theme.rgb(switch_rgb[switch.id], theme.SWITCH_SYMBOL_SHADE)
            assert buttons and all(button.color == linked for button in buttons)


def test_goal_gets_a_portal_that_is_removed_with_the_board(scene_modules):
    stage = load_stage(STAGE_20)
    board = scene_modules.board.Board()
    board.build(stage)

    assert board.decorations  # ring, streaks and their mover

    destroyed = []
    scene_modules.board.destroy = destroyed.append
    board.clear()
    assert board.decorations == []
    assert len(destroyed) >= 1


def test_camera_looks_from_the_front_left_and_backs_off_for_big_stages(scene_modules):
    view = scene_modules.view
    small = Stage(id="s", group="G1", grid=("###", "##G"), start=(0, 0), goal=(1, 2))
    big = load_stage(Path(__file__).resolve().parents[2] / "stages" / "bench" / "g1_04.json")
    positions = []

    for stage in (small, big):
        scene = view.SceneView()
        scene.load_stage(stage, initial_state(stage))
        x, y, z = view.camera.position
        center_x, center_z = (stage.cols - 1) / 2, -(stage.rows - 1) / 2
        assert x < center_x  # left of the board
        assert z < center_z  # in front of the last row
        assert y > 0
        positions.append((x - center_x, y, z - center_z))

    distance = [sum(v * v for v in p) ** 0.5 for p in positions]
    assert distance[1] > distance[0]
