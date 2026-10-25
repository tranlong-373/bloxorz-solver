"""BlockView: the 1x1x2 block or the two cubes. Owner: VT3 (tasks 3.1, 3.3c, 3.4)."""

from ursina import Entity, color, destroy

from .textures import glow_disk_texture

from .theme import (
    BLOCK_COLOR,
    CUBE_COLOR,
    EDGE_DIM_RGB,
    EDGE_GLOW_LAYERS,
    EDGE_GLOW_RGB,
    EDGE_THICKNESS,
    FLOOR_GLOW,
    FLOOR_GLOW_MARGIN,
    GLOW_SHADER,
    SCENE_SHADER,
    SELECTED_CUBE_COLOR,
    block_transform,
    cube_transform,
)


def _glow_colors(rgb):
    return [color.rgba32(*rgb, alpha) for _, alpha in EDGE_GLOW_LAYERS]


def _add_glow(body):
    """Layered cyan edge lines that follow body as children."""
    layers = []
    for (scale, _), tint in zip(EDGE_GLOW_LAYERS, _glow_colors(EDGE_GLOW_RGB)):
        edges = Entity(
            parent=body,
            model="wireframe_cube",
            scale=scale,
            color=tint,
            shader=GLOW_SHADER,
        )
        # Thicker lines; headless test doubles load no real Mesh.
        if hasattr(edges.model, "thickness"):
            edges.model.thickness = EDGE_THICKNESS
        layers.append(edges)
    return layers


class BlockView:
    def __init__(self):
        self.entity = Entity(
            model="cube",
            color=BLOCK_COLOR,
            position=(0, 1, 0),
            scale=(1, 2, 1),
            shader=SCENE_SHADER,
        )
        _add_glow(self.entity)
        # Created once and only enabled while split; cubes[i] sits on the
        # i-th position of the last placed State (pos, then cube2).
        self.cubes = [
            Entity(
                model="cube",
                color=CUBE_COLOR,
                scale=(1, 1, 1),
                shader=SCENE_SHADER,
                enabled=False,
            )
            for _ in range(2)
        ]
        self.cube_glow = [_add_glow(cube) for cube in self.cubes]
        self.cube_cells = [None, None]
        self._floor_glows = self._add_floor_glows()

    def _add_floor_glows(self):
        """A soft cyan pool of light on the floor under the block and each cube."""
        glows = [
            Entity(
                model="quad",
                texture=glow_disk_texture(),
                color=FLOOR_GLOW,
                rotation_x=90,
                y=0.01,
                double_sided=True,
                shader=GLOW_SHADER,
            )
            for _ in self.entities()
        ]

        def update():
            # Follow each body; hide while it is hidden or has fallen away.
            for body, glow in zip(self.entities(), glows):
                glow.enabled = body.enabled and body.world_y > -0.2
                if glow.enabled:
                    glow.x, glow.z = body.world_x, body.world_z
                    glow.scale = (
                        body.world_scale_x + FLOOR_GLOW_MARGIN,
                        body.world_scale_z + FLOOR_GLOW_MARGIN,
                    )

        follower = Entity(update=update)
        return [*glows, follower]

    def entities(self):
        """Every entity this view may animate."""
        return [self.entity, *self.cubes]

    def place(self, state):
        """Show the whole block or the two cubes exactly at the State."""
        if state.pose is None:
            self.entity.enabled = False
            for cube, pos in zip(self.cubes, (state.pos, state.cube2)):
                position, scale = cube_transform(pos)
                cube.enabled = True
                cube.position = position
                cube.scale = scale
                cube.rotation = (0, 0, 0)
            self.cube_cells = [state.pos, state.cube2]
            return

        for cube in self.cubes:
            cube.enabled = False
        self.cube_cells = [None, None]

        position, scale = block_transform(state)

        self.entity.enabled = True
        self.entity.position = position
        self.entity.scale = scale
        self.entity.rotation = (0, 0, 0)

    def highlight(self, pos):
        """Brighten the cube resting on pos and dim the other; None shows both normally."""
        for cube, layers, cell in zip(self.cubes, self.cube_glow, self.cube_cells):
            selected = pos is not None and cell == pos
            dimmed = pos is not None and not selected
            cube.color = SELECTED_CUBE_COLOR if selected else CUBE_COLOR
            tints = _glow_colors(EDGE_DIM_RGB if dimmed else EDGE_GLOW_RGB)
            for edges, tint in zip(layers, tints):
                edges.color = tint

    def clear(self):
        for entity in [*self.entities(), *self._floor_glows]:
            destroy(entity)
