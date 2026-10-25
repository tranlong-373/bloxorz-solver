
"""Colors, camera, cell_to_world, block transform per pose. Owner: VT3 (tasks 3.1, 3.3c, 3.4)."""

from ursina import color
from ursina.shaders import lit_with_shadows_shader, unlit_shader

from bloxorz.model import Pose, State

# Lit shader so the app's AmbientLight + DirectionalLight shade each face;
# Ursina's default unlit shader draws every face in one flat color.
SCENE_SHADER = lit_with_shadows_shader
# Glowing parts (block edges, goal portal) ignore the lights.
GLOW_SHADER = unlit_shader

# Camera: oblique view from the front-left like the original game.
# Azimuth is measured from straight in front (the last row) toward the left.
CAMERA_ELEVATION_DEG = 50
CAMERA_AZIMUTH_DEG = 35
# Screen area (-1..1 on each axis) the board must fit in; the top strip
# stays free for the app's status text and buttons.
CAMERA_FRAME = {"left": -0.92, "right": 0.92, "bottom": -0.9, "top": 0.62}

# Space theme: dark stone tiles floating among stars. Tile colors tint the
# grayscale stone texture, so they are brighter than they end up looking.
TILE_COLORS = {
    "#": color.rgb32(62, 68, 84),
    "F": color.rgb32(245, 140, 50),
    "G": color.rgb32(4, 4, 8),
    "B": color.rgb32(80, 165, 205),
}
TILE_SIZE = 0.94
TILE_THICKNESS = 0.3

# Each bridge gets its own hue and every switch that drives it shares it,
# so the player sees which buttons act on which bridge (several switches
# may drive one bridge). The symbol shape on the switch shows its kind
# (round = soft, X = heavy, bars = split).
LINK_PALETTE = [
    (70, 185, 230),
    (95, 205, 105),
    (235, 105, 165),
    (130, 130, 245),
    (70, 200, 180),
    (190, 215, 75),
]
# Switch buttons sit on plain stone and carry the full link color.
BUTTON_BASE_COLOR = color.rgb32(70, 74, 84)
SWITCH_SYMBOL_SHADE = 1.0

SWITCH_COLORS = {
    # Soft: low, round plate; heavy: X; split: paired parallel bars.
    "soft": color.rgb32(100, 210, 120),
    "heavy": color.rgb32(230, 110, 85),
    "split": color.rgb32(175, 115, 225),
}

# Silver block with glowing cyan edges and a faint halo.
BLOCK_COLOR = color.rgb32(185, 196, 212)
# Split cubes keep the block color; the controlled cube is brighter and
# glows, the other one dims.
CUBE_COLOR = BLOCK_COLOR
SELECTED_CUBE_COLOR = color.rgb32(235, 245, 255)
# Glowing edges: a solid wireframe plus fainter, slightly larger copies
# fake the bloom Ursina does not have. (scale, alpha) per layer.
EDGE_GLOW_RGB = (90, 240, 255)
EDGE_DIM_RGB = (40, 105, 125)
EDGE_GLOW_LAYERS = ((1.0, 255), (1.035, 120), (1.07, 50))
EDGE_THICKNESS = 3
# Cyan light the block casts on the floor under it.
FLOOR_GLOW = color.rgba32(80, 230, 255, 235)
FLOOR_GLOW_MARGIN = 1.6

# Goal: a dark hole ringed by a cyan portal with rising light streaks.
PORTAL_COLOR = color.rgb32(60, 230, 255)
PORTAL_STREAK_COLOR = color.rgba32(140, 250, 255, 230)
PORTAL_STREAKS = 18
PORTAL_STREAK_PERIOD = 1.6


def rgb(value, shade=1.0):
    """Ursina color from an (r, g, b) tuple, optionally darkened."""
    return color.rgb32(*(round(channel * shade) for channel in value))


def switch_link_colors(stage):
    """(switch id -> rgb, bridge id -> rgb): one hue per bridge, shared by its switches.

    A switch that drives several bridges takes the hue of the first one.
    """
    bridge_rgb = {
        bridge.id: LINK_PALETTE[index % len(LINK_PALETTE)]
        for index, bridge in enumerate(sorted(stage.bridges, key=lambda bridge: bridge.id))
    }
    switch_rgb = {
        switch.id: bridge_rgb[switch.bridges[0]]
        for switch in stage.switches
        if switch.kind in ("soft", "heavy") and switch.bridges and switch.bridges[0] in bridge_rgb
    }
    return switch_rgb, bridge_rgb


def cell_to_world(r: int, c: int):
    """Tile center; the tile's top face is the floor at y = 0."""
    return (float(c), -TILE_THICKNESS / 2, -float(r))


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
