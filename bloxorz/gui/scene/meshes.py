"""Procedural meshes for the space theme. Owner: VT3 | Task: 3.4."""

import math

from ursina import Mesh

# Bevel of a floor slab in the unit box (-0.5..0.5): the top face is inset
# by BEVEL_INSET on x/z and the slanted rim drops BEVEL_DROP on y.
BEVEL_INSET = 0.07
BEVEL_DROP = 0.22


def _slab_geometry():
    vertices, triangles, normals, uvs = [], [], [], []

    def face(corners, normal, face_uvs):
        # Ursina draws a triangle when cross(edge1, edge2) points against
        # its normal; flip the quad's order when it does not.
        a, b, c = corners[0], corners[1], corners[2]
        e1 = [b[i] - a[i] for i in range(3)]
        e2 = [c[i] - a[i] for i in range(3)]
        cross = (
            e1[1] * e2[2] - e1[2] * e2[1],
            e1[2] * e2[0] - e1[0] * e2[2],
            e1[0] * e2[1] - e1[1] * e2[0],
        )
        if sum(cross[i] * normal[i] for i in range(3)) > 0:
            corners, face_uvs = corners[::-1], face_uvs[::-1]
        start = len(vertices)
        vertices.extend(corners)
        normals.extend([normal] * 4)
        uvs.extend(face_uvs)
        triangles.extend([(start, start + 1, start + 2), (start, start + 2, start + 3)])

    inner, top, rim = 0.5 - BEVEL_INSET, 0.5, 0.5 - BEVEL_DROP
    full_uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    strip_uv = [(0, 0), (1, 0), (1, 0.08), (0, 0.08)]

    face(
        [(-inner, top, -inner), (inner, top, -inner), (inner, top, inner), (-inner, top, inner)],
        (0, 1, 0),
        [(BEVEL_INSET, BEVEL_INSET), (1 - BEVEL_INSET, BEVEL_INSET),
         (1 - BEVEL_INSET, 1 - BEVEL_INSET), (BEVEL_INSET, 1 - BEVEL_INSET)],
    )

    slant = math.hypot(BEVEL_DROP, BEVEL_INSET)
    up, out = BEVEL_INSET / slant, BEVEL_DROP / slant
    # (outward axis, sign) for the four sides, walked so every quad faces out.
    for axis, sign in (("x", 1), ("z", 1), ("x", -1), ("z", -1)):
        def point(along, height, reach):
            return (sign * reach, height, -sign * along) if axis == "x" else (sign * along, height, sign * reach)

        normal_out = (sign * out, up, 0) if axis == "x" else (0, up, sign * out)
        face(
            [point(-inner, top, inner), point(-0.5, rim, 0.5), point(0.5, rim, 0.5), point(inner, top, inner)],
            normal_out,
            strip_uv,
        )
        side_normal = (sign, 0, 0) if axis == "x" else (0, 0, sign)
        face(
            [point(-0.5, rim, 0.5), point(-0.5, -0.5, 0.5), point(0.5, -0.5, 0.5), point(0.5, rim, 0.5)],
            side_normal,
            strip_uv,
        )

    face(
        [(-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, -0.5, -0.5)],
        (0, -1, 0),
        full_uv,
    )
    return vertices, triangles, normals, uvs


_SLAB = _slab_geometry()


def slab_mesh():
    """A new bevelled floor-slab Mesh (each Entity needs its own copy)."""
    vertices, triangles, normals, uvs = _SLAB
    return Mesh(vertices=vertices, triangles=triangles, normals=normals, uvs=uvs)
