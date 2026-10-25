"""Task 3.4: camera framing with a real Panda3D lens (not the headless fallback).

CI installs only pytest, so these tests skip there; they run wherever
Panda3D (shipped with Ursina) is installed.
"""
import math
from pathlib import Path

import pytest

panda3d_core = pytest.importorskip("panda3d.core")

from bloxorz.engine import initial_state  # noqa: E402
from bloxorz.loader import load_stage  # noqa: E402

# Ursina's world: y up, left-handed. Must be set before any Panda3D node is made.
panda3d_core.loadPrcFileData("", "coordinate-system y-up-left")

FIXTURES = Path(__file__).resolve().parents[2] / "stages"
STAGES = [
    "fixtures/basic_01.json",
    "fixtures/soft_toggle_01.json",
    "fixtures/full_01.json",
    "fixtures/split_01.json",
    "fixtures/heavy_permanent_01.json",
    "bench/g1_04.json",  # 12x20, the largest the loader allows
]
ASPECTS = {"16:9": 16 / 9, "4:3": 4 / 3, "1:1": 1.0}
# Ursina at 16:9 has a 40 deg horizontal / ~23.1 deg vertical field of view.
# Other window shapes may keep either one, so test both.
FOV_MODES = ("keep-horizontal", "keep-vertical")


class RealLensCamera:
    """The bits of Ursina's camera SceneView uses, on a real Panda3D lens."""

    def __init__(self, aspect, fov_mode):
        self.root = panda3d_core.NodePath("render")
        self.node = self.root.attachNewNode("camera")
        self.lens = panda3d_core.PerspectiveLens()
        vertical_16_9 = 2 * math.degrees(math.atan(math.tan(math.radians(20)) * 9 / 16))
        if fov_mode == "keep-horizontal":
            horizontal = 40.0
            vertical = 2 * math.degrees(math.atan(math.tan(math.radians(20)) / aspect))
        else:
            vertical = vertical_16_9
            horizontal = 2 * math.degrees(math.atan(math.tan(math.radians(vertical / 2)) * aspect))
        self.lens.setFov(horizontal, vertical)

    @property
    def position(self):
        return self.node.getPos(self.root)

    @position.setter
    def position(self, value):
        self.node.setPos(self.root, *value)

    def look_at(self, target):
        self.node.lookAt(self.root, panda3d_core.Point3(*target))

    def getRelativePoint(self, _scene, point):
        return self.node.getRelativePoint(self.root, point)


def _screen_box(camera, stage):
    """Screen extents of every drawn tile, including a standing block's top."""
    xs, ys = [], []
    for r, row in enumerate(stage.grid):
        for c, symbol in enumerate(row):
            if symbol == "." and (r, c) not in stage.bridge_at:
                continue
            for dx in (-0.5, 0.5):
                for dz in (-0.5, 0.5):
                    for y in (0.0, 2.0):
                        point = camera.getRelativePoint(None, panda3d_core.Point3(c + dx, y, -r + dz))
                        projected = panda3d_core.Point2()
                        assert camera.lens.project(point, projected), (stage.id, r, c)
                        xs.append(projected.x)
                        ys.append(projected.y)
    return min(xs), max(xs), min(ys), max(ys)


@pytest.mark.parametrize("fov_mode", FOV_MODES)
@pytest.mark.parametrize("aspect_name", ASPECTS)
@pytest.mark.parametrize("stage_path", STAGES)
def test_board_fits_the_frame_with_a_real_lens(
    monkeypatch, scene_modules, stage_path, aspect_name, fov_mode
):
    view = scene_modules.view
    camera = RealLensCamera(ASPECTS[aspect_name], fov_mode)
    monkeypatch.setattr(view, "camera", camera)
    stage = load_stage(FIXTURES / stage_path)

    scene = view.SceneView()
    scene.load_stage(stage, initial_state(stage))  # must not raise

    frame = view.CAMERA_FRAME
    left, right, bottom, top = _screen_box(camera, stage)
    tolerance = 1e-3
    assert left >= frame["left"] - tolerance
    assert right <= frame["right"] + tolerance
    assert bottom >= frame["bottom"] - tolerance
    assert top <= frame["top"] + tolerance
    # The camera looks from the front-left and above the board.
    x, y, z = camera.position
    assert y > 0


def test_unmeasurable_lens_still_loads_and_places_the_camera(monkeypatch, scene_modules):
    """If no framing can be measured, loading keeps a safe camera instead of raising."""
    view = scene_modules.view

    class BehindEverything:
        def xform(self, _vector):
            return panda3d_core.LVecBase4f(0, 0, 0, -1)  # every point behind the camera

    class Lens:
        def getProjectionMat(self):
            return BehindEverything()

    camera = RealLensCamera(16 / 9, "keep-horizontal")
    camera.lens = Lens()
    monkeypatch.setattr(view, "camera", camera)
    stage = load_stage(FIXTURES / "fixtures/basic_01.json")

    view.SceneView().load_stage(stage, initial_state(stage))  # must not raise

    x, y, z = camera.position
    assert y > 0  # pulled back to the far, safe distance
