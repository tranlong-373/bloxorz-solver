"""SceneView: the only interface between the app and the 3D scene. Owner: VT3 (task 3.1)."""


"""SceneView public interface for the app."""

from ursina import camera

from .board import Board
from .block import BlockView


class SceneView:
    def __init__(self):
        self.board = Board()
        self.block = BlockView()
        self.stage = None
        self.selected_cube = None

    def load_stage(self, stage, state):
        """Draw the level and initial block."""
        self.stage = stage

        self.board.build(stage)
        self.show_state(state)

        center_x = (stage.cols - 1) / 2
        center_z = -(stage.rows - 1) / 2
        size = max(stage.rows, stage.cols, 4)

        camera.position = (
            center_x + size * 2.2,
            size * 2.8,
            center_z + size * 2.2,
        )

        camera.look_at((center_x, 0, center_z))

    def show_state(self, state):
        """Place the block at the supplied State."""
        self.block.place(state)

    def is_busy(self):
        """Task 3.1 has no animation."""
        return False

    def animate_step(self, before, action, result, on_done):
        """Temporary stub. Animation comes in task 3.2."""
        on_done()

    def show_fall(self, before, action, on_done):
        """Temporary stub. Fall animation comes in task 3.2."""
        on_done()

    def show_win(self, on_done):
        """Temporary stub. Win animation comes in task 3.2."""
        on_done()

    def set_selected(self, cube):
        """Selection is implemented in a later task."""
        self.selected_cube = cube
