"""Render Bloxorz stages and coordinate 3D animations.

Owner: VT3 | Tasks: 3.1, 3.2.
"""

import logging

from ursina import camera

from .animate import play_fall, play_roll, play_win
from .block import BlockView
from .board import Board

logger = logging.getLogger(__name__)


class SceneView:
    def __init__(self):
        self.board = Board()
        self.block = BlockView()
        self.stage = None
        self.selected_cube = None
        self._busy = False
        self._animation_id = 0
        self._state = None

    def load_stage(self, stage, state):
        """Draw the level and initial block."""
        self._animation_id += 1
        self.stage = stage
        self._state = state

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
        """Place the block and render bridges from the supplied State."""
        self._state = state
        self.board.show_state(state)
        self.block.place(state)

    def is_busy(self):
        """Return True while a scene animation is running."""
        return self._busy or self.board.is_busy()

    def animate_step(self, before, action, result, on_done):
        """Animate an already validated move from Engine."""
        if self._busy:
            raise RuntimeError("SceneView is already animating")

        if result.state is None:
            raise ValueError("animate_step requires a valid next State")

        animation_id = self._animation_id

        # Always start at the exact old State.
        self.show_state(before)
        self._state = result.state
        self._busy = True

        def finish():
            # Vị trí thực tế của khối sau khi xoay,
            # trước khi show_state() đặt lại tọa độ.
            actual = self.block.entity.world_position

            # Đặt theo State chính thức của Engine.
            if animation_id != self._animation_id:
                if self._state is not None:
                    self.show_state(self._state)
                self._busy = False
                return

            # Đặt khối theo State chính thức. Cầu đổi trạng thái sau đó,
            # theo đúng thứ tự events do Engine trả về.
            self.block.place(result.state)

            expected = self.block.entity.world_position

            error = (actual - expected).length()

            status = "PASS" if error < 0.01 else "FAIL"
            logger.debug(
                "ROLL TEST: %s | direction=%s | actual=%s | "
                "expected=%s | error=%.8f",
                status,
                action.direction.name,
                actual,
                expected,
                error,
            )

            def events_finished():
                self.board.show_state(result.state)
                self._busy = False
                on_done()

            self.board.animate_events(result.events, events_finished)

        try:
            play_roll(
                self.block.entity,
                action.direction,
                finish,
            )
        except Exception:
            self._busy = False
            raise

    def show_fall(self, before, action, on_done):
        """Animate the block falling after an invalid move."""

        if self._busy:
            raise RuntimeError("SceneView is already animating")

        # Restore the block to its position before falling.
        self.show_state(before)
        self._busy = True
        animation_id = self._animation_id

        def finish():
            if animation_id != self._animation_id:
                if self._state is not None:
                    self.show_state(self._state)
                self._busy = False
                return
            print("FALL FINISHED:", self.block.entity.position)

            self._busy = False
            on_done()

        try:
            play_fall(
                self.block.entity,
                action.direction,
                finish,
            )
        except Exception:
            self._busy = False
            raise

    def show_win(self, on_done):
        """Animate the block sinking into the goal."""

        if self._busy:
            raise RuntimeError("SceneView is already animating")

        self._busy = True
        animation_id = self._animation_id

        def finish():
            if animation_id != self._animation_id:
                if self._state is not None:
                    self.show_state(self._state)
                self._busy = False
                return
            print("WIN FINISHED:", self.block.entity.position)
            self._busy = False
            on_done()

        try:
            play_win(
                self.block.entity,
                finish,
            )
        except Exception:
            self._busy = False
            raise

    def set_selected(self, cube):
        """Selection is implemented in a later task."""
        self.selected_cube = cube
