"""Render Bloxorz stages and coordinate 3D animations.

Owner: VT3 | Tasks: 3.1, 3.2, 3.3a.
"""

import logging

from ursina import camera, destroy, scene

from bloxorz.engine.rules import ROLL
from bloxorz.model import Pose

from .animate import play_drop, play_fall, play_roll, play_win
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

    def _cancel_block_animations(self):
        """Stop the old stage's block animations before their callbacks run."""
        entity = self.block.entity
        for animation in list(getattr(entity, "animations", ())):
            if animation:
                animation.kill()

        # play_roll/play_fall parent the block to a temporary pivot.
        pivot = getattr(entity, "parent", None)
        if pivot is not None and pivot is not scene:
            for animation in list(getattr(pivot, "animations", ())):
                if animation:
                    animation.kill()
            entity.world_parent = scene
            destroy(pivot)

    def load_stage(self, stage, state):
        """Draw the level and initial block, cancelling any running animation."""
        self._animation_id += 1
        self._cancel_block_animations()
        self._busy = False
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
        """Place the block at the supplied State."""
        self._state = state
        self.block.place(state)

    def is_busy(self):
        """Return True while a scene animation is running."""
        return self._busy or self.board.is_busy()

    def animate_step(self, before, action, result, on_done):
        """Animate an already validated move from Engine."""
        if self.is_busy():
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
            # load_stage() already reset the scene for the new stage.
            if animation_id != self._animation_id:
                return

            self.show_state(result.state)

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

            self._busy = False
            on_done()

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

        if self.is_busy():
            raise RuntimeError("SceneView is already animating")

        # Restore the block to its position before falling.
        self.show_state(before)
        self._busy = True
        animation_id = self._animation_id

        def finish():
            # load_stage() already reset the scene for the new stage.
            if animation_id != self._animation_id:
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

    def show_fragile_fall(self, before, action, cell, on_done):
        """Roll onto the Engine-reported fragile cell, break it, then drop."""
        if self.is_busy():
            raise RuntimeError("SceneView is already animating")

        self.show_state(before)
        self._busy = True
        animation_id = self._animation_id
        callback_called = False
        roll_callback_called = False
        tile_callback_called = False

        def is_current():
            # A stale callback must not touch the busy flag or State of the
            # new stage; load_stage() already reset both.
            return animation_id == self._animation_id

        def finish():
            nonlocal callback_called
            if callback_called or not is_current():
                return
            callback_called = True
            self._busy = False
            on_done()

        def tile_finished():
            nonlocal tile_callback_called
            if tile_callback_called or not is_current():
                return
            tile_callback_called = True
            try:
                play_drop(self.block.entity, finish)
            except Exception:
                self._busy = False
                raise

        def roll_finished():
            nonlocal roll_callback_called
            if roll_callback_called or not is_current():
                return
            roll_callback_called = True
            try:
                self.board.break_fragile(cell, on_done=tile_finished)
            except Exception:
                self._busy = False
                raise

        try:
            play_roll(self.block.entity, action.direction, roll_finished)
        except Exception:
            self._busy = False
            raise

    def _fragile_cell(self, before, action):
        """Landing cell of a fragile_broke move, from Engine's ROLL table."""
        if before.pose is None:
            raise ValueError("fragile_broke requires the intact block")
        new_pose, dr, dc = ROLL[(before.pose, action.direction)]
        cell = (before.pos[0] + dr, before.pos[1] + dc)
        if new_pose is not Pose.STANDING or self.stage.cell(cell) != "F":
            raise ValueError(f"fragile_broke does not land upright on F: {cell}")
        return cell

    def show_illegal_step(self, before, action, result, on_done):
        """Animate an Engine-rejected move, chosen by result.reason.

        fell -> show_fall; fragile_broke -> show_fragile_fall;
        bridge_closed -> show_fall until task 3.3b adds the bridge effect.
        """
        if result.state is not None or result.reason not in (
            "fell",
            "fragile_broke",
            "bridge_closed",
        ):
            raise ValueError(f"Not an illegal-move result: {result!r}")

        if result.reason == "fragile_broke":
            cell = self._fragile_cell(before, action)
            self.show_fragile_fall(before, action, cell, on_done)
            return

        self.show_fall(before, action, on_done)

    def show_win(self, on_done):
        """Animate the block sinking into the goal."""

        if self.is_busy():
            raise RuntimeError("SceneView is already animating")

        self._busy = True
        animation_id = self._animation_id

        def finish():
            # load_stage() already reset the scene for the new stage.
            if animation_id != self._animation_id:
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
