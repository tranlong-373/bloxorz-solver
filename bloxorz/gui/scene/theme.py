
"""Colors, camera, cell_to_world, block transform per pose. Owner: VT3 (tasks 3.1, 3.3c, 3.4)."""

from ursina import color
from ursina.shaders import lit_with_shadows_shader

from bloxorz.model import Pose, State

# Lit shader so the app's AmbientLight + DirectionalLight shade each face;
# Ursina's default unlit shader draws every face in one flat color.
SCENE_SHADER = lit_with_shadows_shader

# Camera: oblique view from the front-left like the original game.
# Azimuth is measured from straight in front (the last row) toward the left.
CAMERA_ELEVATION_DEG = 50
CAMERA_AZIMUTH_DEG = 35
# Screen area (-1..1 on each axis) the board must fit in; the top strip
# stays free for the app's status text and buttons.
CAMERA_FRAME = {"left": -0.92, "right": 0.92, "bottom": -0.9, "top": 0.62}

# Tones are a little darker than they should look: the lights brighten them.
TILE_COLORS = {
    "#": color.rgb32(112, 118, 130),
    "F": color.rgb32(235, 140, 50),
    "G": color.rgb32(8, 8, 12),
    "B": color.rgb32(80, 165, 205),
}

# Each soft/heavy switch gets its own hue and its bridges share it, so the
# player sees which switch drives which bridge. The symbol shape on the
# switch shows its kind (round = soft, X = heavy, bars = split).
LINK_PALETTE = [
    (70, 185, 230),
    (95, 205, 105),
    (235, 105, 165),
    (130, 130, 245),
    (70, 200, 180),
    (190, 215, 75),
]
SWITCH_SYMBOL_SHADE = 0.6

SWITCH_COLORS = {
    # Soft: low, round plate; heavy: X; split: paired parallel bars.
    "soft": color.rgb32(100, 210, 120),
    "heavy": color.rgb32(230, 110, 85),
    "split": color.rgb32(175, 115, 225),
}

BLOCK_COLOR = color.rgb32(235, 190, 75)
# Split cubes keep the block color; the controlled cube is brighter.
CUBE_COLOR = BLOCK_COLOR
SELECTED_CUBE_COLOR = color.rgb32(255, 240, 150)


def rgb(value, shade=1.0):
    """Ursina color from an (r, g, b) tuple, optionally darkened."""
    return color.rgb32(*(round(channel * shade) for channel in value))


def switch_link_colors(stage):
    """(switch id -> rgb, bridge id -> rgb) for soft/heavy switches and their bridges."""
    switch_rgb, bridge_rgb = {}, {}
    linked = sorted(
        (switch for switch in stage.switches if switch.kind in ("soft", "heavy")),
        key=lambda switch: switch.id,
    )
    for index, switch in enumerate(linked):
        value = LINK_PALETTE[index % len(LINK_PALETTE)]
        switch_rgb[switch.id] = value
        for bridge_id in switch.bridges:
            bridge_rgb.setdefault(bridge_id, value)
    return switch_rgb, bridge_rgb


def cell_to_world(r: int, c: int):
    return (float(c), -0.1, -float(r))


def block_transform(state: State):
    r, c = state.pos

    if state.pose == Pose.STANDING:
        return (c, 1.0, -r), (1, 2, 1)

    if state.pose == Pose.HORIZONTAL:
        return (c + 0.5, 0.5, -r), (2, 1, 1)

    if state.pose == Pose.VERTICAL:
        return (c, 0.5, -(r + 0.5)), (1, 1, 2)

    raise ValueError("A split State has two cubes; use cube_transform")


def cube_transform(pos):
    """Position and scale of one 1x1x1 cube resting on cell pos."""
    r, c = pos
    return (c, 0.5, -r), (1, 1, 1)
