"""Render Bloxorz stages and coordinate 3D animations.

Owner: VT3 | Tasks: 3.1, 3.2, 3.3a, 3.3b, 3.3c, 3.4.
"""

import logging
import math

from ursina import Sky, camera, destroy, scene

from bloxorz.engine.rules import ROLL, footprint
from bloxorz.model import Direction, Pose, State

from .animate import play_drop, play_fall, play_roll, play_split, play_win
from .block import BlockView
from .board import Board
from .textures import starfield_texture
from .theme import CAMERA_AZIMUTH_DEG, CAMERA_ELEVATION_DEG, CAMERA_FRAME

logger = logging.getLogger(__name__)

# One-cell offset of a split cube's roll, matching cell_to_world (x=c, z=-r).
_CUBE_STEP = {
    Direction.UP: (-1, 0),
    Direction.DOWN: (1, 0),
    Direction.LEFT: (0, -1),
    Direction.RIGHT: (0, 1),
}


def _cubes(state):
    return (state.pos, state.cube2)


class SceneView:
    def __init__(self):
        # Starry space backdrop; the sky dome follows the camera.
        self.backdrop = Sky(texture=starfield_texture())
        self.board = Board()
        self.block = BlockView()
        self.stage = None
        self.selected_cube = None
        self._selected_pos = None
        self._busy = False
        self._animation_id = 0
        self._state = None

    def _block_entities(self):
        entities = getattr(self.block, "entities", None)
        return entities() if entities else [self.block.entity]

    def _cancel_block_animations(self):
        """Stop the old stage's block animations before their callbacks run."""
        for entity in self._block_entities():
            for animation in list(getattr(entity, "animations", ())):
                if animation:
                    animation.kill()

            # play_roll/play_fall parent the entity to a temporary pivot.
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
        self._selected_pos = None
        self.selected_cube = None
        self.stage = stage
        self._state = state

        self.board.build(stage)
        self.show_state(state)
        self._frame_camera(stage)

    def _frame_camera(self, stage):
        """Look from the front-left, center the board and pull back until it fits."""
        center = ((stage.cols - 1) / 2, 0, -(stage.rows - 1) / 2)
        elevation = math.radians(CAMERA_ELEVATION_DEG)
        azimuth = math.radians(CAMERA_AZIMUTH_DEG)
        direction = (
            -math.cos(elevation) * math.sin(azimuth),
            math.sin(elevation),
            -math.cos(elevation) * math.cos(azimuth),
        )
        # Ground-plane axes for sliding the view: across and along the sightline.
        across = (math.cos(azimuth), 0, -math.sin(azimuth))
        along = (-math.sin(azimuth), 0, -math.cos(azimuth))
        size = max(stage.rows, stage.cols, 4)

        def place(distance, pan):
            target = tuple(
                c + pan[0] * a + pan[1] * b for c, a, b in zip(center, across, along)
            )
            camera.position = tuple(t + d * distance for t, d in zip(target, direction))
            camera.look_at(target)

        lens = getattr(camera, "lens", None)
        if lens is None:
            # No real lens (headless tests): distance from max(rows, cols).
            place(size * 2.5 + 4, (0.0, 0.0))
            return

        from panda3d.core import Point2, Point3

        # Board corners, including the top of a standing block.
        corners = [
            Point3(x, y, z)
            for x in (-0.5, stage.cols - 0.5)
            for z in (0.5, -(stage.rows - 0.5))
            for y in (0, 2)
        ]

        def extents(distance, pan):
            """(left, right, bottom, top) of the board on screen, or None."""
            place(distance, pan)
            xs, ys = [], []
            for corner in corners:
                projected = Point2()
                if not lens.project(camera.getRelativePoint(scene, corner), projected):
                    return None
                xs.append(projected.x)
                ys.append(projected.y)
            return min(xs), max(xs), min(ys), max(ys)

        def fit_distance(pan):
            near, far = 1.0, 10.0 * size
            for _ in range(30):
                middle = (near + far) / 2
                box = extents(middle, pan)
                if box is not None and (
                    box[0] >= CAMERA_FRAME["left"]
                    and box[1] <= CAMERA_FRAME["right"]
                    and box[2] >= CAMERA_FRAME["bottom"]
                    and box[3] <= CAMERA_FRAME["top"]
                ):
                    far = middle
                else:
                    near = middle
            return far

        def middle_of(box):
            return (box[0] + box[1]) / 2, (box[2] + box[3]) / 2

        goal = (
            (CAMERA_FRAME["left"] + CAMERA_FRAME["right"]) / 2,
            (CAMERA_FRAME["bottom"] + CAMERA_FRAME["top"]) / 2,
        )
        pan = (0.0, 0.0)
        for _ in range(3):
            distance = fit_distance(pan)
            here = middle_of(extents(distance, pan))
            # Screen shift per unit slide, measured with a small test slide.
            step_x = middle_of(extents(distance, (pan[0] + 0.5, pan[1])))[0] - here[0]
            step_y = middle_of(extents(distance, (pan[0], pan[1] + 0.5)))[1] - here[1]
            pan = (
                pan[0] + 0.5 * (goal[0] - here[0]) / step_x,
                pan[1] + 0.5 * (goal[1] - here[1]) / step_y,
            )
        place(fit_distance(pan), pan)

    def show_state(self, state):
        """Place the block or cubes and render bridges from the State."""
        self._state = state
        self.board.show_state(state)
        self.block.place(state)
        if state.pose is None:
            if self._selected_pos not in _cubes(state):
                self._selected_pos = None
            self.block.highlight(self._selected_pos)
        else:
            self._selected_pos = None

    def is_busy(self):
        """Return True while a scene animation is running."""
        return self._busy or self.board.is_busy()

    def _moving_entity(self, before, action):
        """The entity that rolls: the whole block, or the acting cube."""
        if action.cube is None:
            return self.block.entity
        return self.block.cubes[action.cube]

    def _follow_selection(self, before, action, after):
        """Keep the highlight on the physical cube that just moved."""
        if after.pose is not None:
            self._selected_pos = None
            return
        moving = _cubes(before)[action.cube]
        if self._selected_pos != moving:
            return
        stationary = _cubes(before)[1 - action.cube]
        self._selected_pos = after.cube2 if after.pos == stationary else after.pos

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
        moving = self._moving_entity(before, action)

        def done():
            if animation_id != self._animation_id:
                return
            self.show_state(result.state)
            self._busy = False
            on_done()

        def events_finished():
            if animation_id != self._animation_id:
                return
            if before.pose is not None and result.state.pose is None:
                # Engine split the block on a split switch: show both cubes.
                self.block.place(result.state)
                play_split(self.block.cubes, done)
                return
            done()

        def finish():
            # load_stage() already reset the scene for the new stage.
            if animation_id != self._animation_id:
                return

            if before.pose is None:
                # A cube moved; a merge shows the Engine's whole block.
                self._follow_selection(before, action, result.state)
                self.block.place(result.state)
                if result.state.pose is None:
                    # place() may have swapped which entity holds which cell;
                    # recolor now, before the switch/bridge events play.
                    self.block.highlight(self._selected_pos)
            elif result.state.pose is not None:
                # Vị trí thực tế của khối sau khi xoay,
                # trước khi place() đặt lại tọa độ.
                actual = moving.world_position

                # Đặt khối theo State chính thức. Cầu đổi trạng thái sau đó,
                # theo đúng thứ tự events do Engine trả về.
                self.block.place(result.state)
                expected = moving.world_position
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

            self.board.animate_events(result.events, events_finished)

        try:
            play_roll(moving, action.direction, finish)
        except Exception:
            self._busy = False
            raise

    def _fall_tip(self, before, action):
        """Floor edge a lying block tips over when only one landing cell is held.

        Returns (pivot_position, rotation_axis, angle) for play_fall, or None
        when the whole landing is unsupported (a plain roll-and-drop).
        """
        if action.cube is not None or before.pose is None:
            return None
        new_pose, dr, dc = ROLL[(before.pose, action.direction)]
        landing = footprint(State(new_pose, (before.pos[0] + dr, before.pos[1] + dc)))
        held = [cell for cell in landing if self.board.has_floor(cell)]
        if len(landing) != 2 or len(held) != 1:
            return None

        (held_r, held_c), = held
        (open_r, open_c), = [cell for cell in landing if cell not in held]
        # Same signs as play_roll: +90 about z leans toward +x (higher column),
        # +90 about x leans toward +z (lower row).
        if held_r == open_r:
            edge = ((held_c + open_c) / 2, 0, -held_r)
            return edge, "rotation_z", 90 if open_c > held_c else -90
        edge = (held_c, 0, -(held_r + open_r) / 2)
        return edge, "rotation_x", 90 if open_r < held_r else -90

    def show_fall(self, before, action, on_done):
        """Animate the block, or the acting cube, falling after an invalid move."""

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
            logger.debug("FALL FINISHED")

            self._busy = False
            on_done()

        try:
            play_fall(
                self._moving_entity(before, action),
                action.direction,
                finish,
                tip=self._fall_tip(before, action),
            )
        except Exception:
            self._busy = False
            raise

    def show_fragile_fall(self, before, action, cell, on_done):
        """Roll onto the Engine-reported fragile cell, break it, then drop."""
        self._show_landing_fall(
            before,
            action,
            lambda done: self.board.break_fragile(cell, on_done=done),
            on_done,
        )

    def _show_landing_fall(self, before, action, board_effect, on_done, drops=None):
        """Roll onto the landing cells, run board_effect(done), then drop.

        Shared by fragile_broke (F collapses) and bridge_closed (switch and
        bridge events play) so both keep the same busy/callback rules.
        drops() picks the entities that fall; by default the moving one.
        """
        if self.is_busy():
            raise RuntimeError("SceneView is already animating")

        self.show_state(before)
        self._busy = True
        animation_id = self._animation_id
        moving = self._moving_entity(before, action)
        callback_called = False
        roll_callback_called = False
        effect_callback_called = False

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

        def effect_finished():
            nonlocal effect_callback_called
            if effect_callback_called or not is_current():
                return
            effect_callback_called = True
            falling = drops() if drops is not None else [moving]
            remaining = len(falling)

            def one_dropped():
                nonlocal remaining
                remaining -= 1
                if remaining == 0:
                    finish()

            try:
                if not falling:
                    finish()
                for entity in falling:
                    play_drop(entity, one_dropped)
            except Exception:
                self._busy = False
                raise

        def roll_finished():
            nonlocal roll_callback_called
            if roll_callback_called or not is_current():
                return
            roll_callback_called = True
            try:
                board_effect(effect_finished)
            except Exception:
                self._busy = False
                raise

        try:
            play_roll(moving, action.direction, roll_finished)
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

    def _cubes_on_closed_bridges(self, before, action, events):
        """Cubes standing on a bridge that the Engine's events closed."""
        closed = {
            event.split(":")[1]
            for event in events
            if event.startswith("bridge:") and event.endswith(":close")
        }
        moving = _cubes(before)[action.cube]
        dr, dc = _CUBE_STEP[action.direction]
        cells = list(_cubes(before))
        cells[action.cube] = (moving[0] + dr, moving[1] + dc)
        return [
            cube
            for cube, cell in zip(self.block.cubes, cells)
            if self.stage.bridge_at.get(cell) in closed
        ]

    def show_illegal_step(self, before, action, result, on_done):
        """Animate an Engine-rejected move, chosen by result.reason.

        fell -> show_fall; fragile_broke -> show_fragile_fall;
        bridge_closed -> roll, play the switch/bridge events, then drop
        the block, or the cubes left on a closed bridge.
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

        if result.reason == "bridge_closed":
            drops = None
            if before.pose is None:
                drops = lambda: self._cubes_on_closed_bridges(
                    before, action, result.events
                )
            self._show_landing_fall(
                before,
                action,
                lambda done: self.board.animate_events(result.events, done),
                on_done,
                drops=drops,
            )
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
            logger.debug("WIN FINISHED")
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
        """Highlight split cube 0 or 1 of the current State; None clears it."""
        self.selected_cube = cube
        state = self._state
        if cube is None or state is None or state.pose is not None:
            self._selected_pos = None
        else:
            self._selected_pos = _cubes(state)[cube]
        if state is not None and state.pose is None:
            self.block.highlight(self._selected_pos)
