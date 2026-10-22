"""Standalone scene demo: python -m bloxorz.gui.scene.demo <stage.json>. Owner: VT3 (task 3.1)."""

"""Standalone SceneView demo for task 3.1.

Run:
    python -m bloxorz.gui.scene.demo stages/fixtures/basic_01.json

Keys:
    1 = STANDING
    2 = HORIZONTAL
    3 = VERTICAL
"""

import sys

from ursina import Ursina, Text, window, AmbientLight, DirectionalLight
from bloxorz.loader import load_stage
from bloxorz.model import Pose, State
from .view import SceneView


stage = None
scene_view = None


def input(key):
    """Change only the displayed pose for testing."""
    if key not in ("1", "2", "3"):
        return

    poses = {
        "1": Pose.STANDING,
        "2": Pose.HORIZONTAL,
        "3": Pose.VERTICAL,
    }

    sample_state = State(
        pose=poses[key],
        pos=stage.start,
        bridges_open=stage.initial_bridges_open(),
    )

    scene_view.show_state(sample_state)
    print("Displaying:", poses[key].name)


def main():
    global stage, scene_view

    if len(sys.argv) != 2:
        print(
            "Usage: python -m bloxorz.gui.scene.demo "
            "stages/fixtures/basic_01.json"
        )
        return

    # Load an actual stage using VT4's loader.
    stage = load_stage(sys.argv[1])

    # The standalone demo owns the Ursina application.
    app = Ursina()
    AmbientLight(color=(0.65, 0.65, 0.65, 1))

    sun = DirectionalLight()
    sun.look_at((1, -2, -1))
    window.title = f"Bloxorz Scene Demo - {stage.id}"

    scene_view = SceneView()

    initial_state = State(
        pose=Pose.STANDING,
        pos=stage.start,
        bridges_open=stage.initial_bridges_open(),
    )

    scene_view.load_stage(stage, initial_state)

    Text(
        text="1: Standing | 2: Horizontal | 3: Vertical",
        position=(-0.85, 0.45),
        scale=1,
    )

    print("Loaded stage:", stage.id)
    print("Press 1, 2 or 3 to change block pose.")

    app.run()


if __name__ == "__main__":
    main()
