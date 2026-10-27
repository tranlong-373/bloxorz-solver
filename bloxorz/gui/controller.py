"""GameController: manual play, split control, replay. Must not import ursina. Owner: VT4 (tasks 4.2-4.4)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bloxorz.engine import Outcome, StepResult, initial_state, is_goal, step
from bloxorz.model import Action, Direction, Pos, State
from bloxorz.stage import Stage


class GameController:
    """Coordinates gameplay logic, moves counter, and communicates with SceneView."""

    def __init__(
        self,
        scene: Any,
        schedule: Callable[[Callable[[], None], float], Any] | None = None,
    ) -> None:
        self.scene = scene
        self.schedule = schedule or (lambda fn, delay: fn())
        self.stage: Stage | None = None
        self.state: State | None = None
        self.moves: int = 0
        self.status: str = "playing"  # playing, solving, replaying, falling, lost, winning, won, error
        # Engine reason of the last loss ("fell", "fragile_broke", "bridge_closed") or replay error.
        self.fail_reason: str = ""
        # Selected split cube, kept by cell: State reorders cubes so pos < cube2.
        self.selected_pos: Pos | None = None
        self._session = 0
        self.replaying = False
        self.paused = False
        self.delay = 0.25
        self.speed = 1
        self._replay_actions: tuple[Action, ...] = ()
        self._replay_index = 0
        self._replay_token = 0

    def load(self, stage: Stage) -> None:
        """Load a stage, initialize state, reset moves and status."""
        self._session += 1
        self.replaying = False
        self.paused = False
        self._replay_actions = ()
        self._replay_index = 0
        self.stage = stage
        self.state = initial_state(stage)
        self.moves = 0
        self.status = "playing"
        self.fail_reason = ""
        self.selected_pos = None
        self.scene.load_stage(stage, self.state)
        if hasattr(self.scene, "set_selected"):
            self.scene.set_selected(None)

    def restart(self) -> None:
        """Reload current stage to start over."""
        if self.stage is not None:
            self.load(self.stage)

    def _can_play(self) -> bool:
        return (
            not self.replaying
            and not self.scene.is_busy()
            and self.status == "playing"
            and self.stage is not None
            and self.state is not None
        )

    def _selected_index(self) -> int | None:
        """Index (0/1) of the selected cube in the current State, None if not split."""
        if self.state is None or self.state.pose is not None:
            return None
        return 0 if self.selected_pos == self.state.pos else 1

    def _ensure_selection(self) -> None:
        """Default to cube 0 if the selection is missing or stale."""
        state = self.state
        if state is None or state.pose is not None:
            return
        if self.selected_pos not in (state.pos, state.cube2):
            self.selected_pos = state.pos
            self.scene.set_selected(0)

    def switch_cube(self) -> None:
        """Space key: select the other split cube. Does not count as a move."""
        if not self._can_play() or self.state.pose is not None:
            return
        self._ensure_selection()
        state = self.state
        self.selected_pos = state.cube2 if self.selected_pos == state.pos else state.pos
        self.scene.set_selected(self._selected_index())

    def on_direction(self, d: Direction) -> None:
        """Handle directional movement input from the player."""
        if not self._can_play():
            return

        if self.state.pose is None:
            self._ensure_selection()
            action = Action(direction=d, cube=self._selected_index())
        else:
            action = Action(direction=d)
        res = step(self.stage, self.state, action)

        if res.outcome == Outcome.MOVED:
            before = self.state
            self.moves += 1
            self.state = res.state
            self._update_selection(before, action, res)
            # Split, cube move or merge: the highlight must follow.
            sync = before.pose is None or res.state.pose is None
            session = self._session
            self.scene.animate_step(
                before, action, res, on_done=lambda: self._after_move(session, sync)
            )
        elif res.outcome == Outcome.ILLEGAL:
            before = self.state
            self.status = "falling"
            self.fail_reason = res.reason
            session = self._session

            def lost() -> None:
                self._set_if_current(session, "lost")

            if res.reason in ("fell", "fragile_broke", "bridge_closed"):
                self.scene.show_illegal_step(before, action, res, on_done=lost)
            else:
                self.scene.show_fall(before, action, on_done=lost)

    def _update_selection(self, before: State, action: Action, res: StepResult) -> None:
        """Move the selection with the cube that just moved."""
        after = res.state
        if after is None or after.pose is not None:
            # Whole block (including a merge): nothing to select.
            self.selected_pos = None
        elif "split" in res.events:
            self.selected_pos = after.pos
        else:
            # The moved cube is whichever new cell is not the stationary one.
            stationary = (before.pos, before.cube2)[1 - action.cube]
            self.selected_pos = after.cube2 if after.pos == stationary else after.pos

    def _after_move(self, session: int, sync_selection: bool = False) -> None:
        """Sync the highlight and check victory after a valid move finishes animating."""
        if session != self._session:
            return
        if sync_selection:
            self.scene.set_selected(self._selected_index())
        if self.stage is not None and self.state is not None and is_goal(self.stage, self.state):
            self.status = "winning"
            self.scene.show_win(
                on_done=lambda: self._set_if_current(session, "won")
            )
        else:
            self.status = "playing"

    def _set_if_current(self, session: int, status: str) -> None:
        if session == self._session:
            self.status = status

    def start_replay(self, actions: tuple[Action, ...] | list[Action]) -> None:
        """Replay actions from the start of the loaded stage."""
        if self.stage is None:
            return
        self.load(self.stage)
        self._replay_actions = tuple(actions)
        self._replay_index = 0
        self.replaying = True
        self.paused = False
        self.status = "replaying"
        session = self._session
        self._queue_replay(session, 0)

    def pause(self) -> None:
        if self.replaying:
            self.paused = True
            self._replay_token += 1

    def resume(self) -> None:
        if self.replaying and self.paused:
            self.paused = False
            session = self._session
            self._queue_replay(session, self.delay)

    def step_once(self) -> None:
        if self.replaying and self.paused and not self.scene.is_busy():
            self._replay_token += 1
            self._replay_step(self._session, self._replay_token, force=True)

    def set_delay(self, delay: float) -> None:
        self.delay = max(0.01, float(delay))

    def set_speed(self, multiplier: int) -> None:
        delays = {1: 0.25, 2: 0.125, 4: 0.0625}
        if multiplier not in delays:
            raise ValueError("Replay speed must be 1, 2, or 4")
        self.speed = multiplier
        self.delay = delays[multiplier]

    def _queue_replay(self, session: int, delay: float) -> None:
        self._replay_token += 1
        token = self._replay_token
        self.schedule(lambda: self._replay_step(session, token), delay)

    def _replay_step(self, session: int, token: int | None = None, force: bool = False) -> None:
        if token is not None and token != self._replay_token:
            return
        if session != self._session or not self.replaying or (self.paused and not force):
            return
        if self.scene.is_busy():
            self._queue_replay(session, self.delay)
            return
        if self._replay_index >= len(self._replay_actions):
            self.replaying = False
            if self.stage is not None and self.state is not None and is_goal(self.stage, self.state):
                self.status = "winning"
                self.scene.show_win(on_done=lambda: self._set_if_current(session, "won"))
            else:
                self.status = "playing"
            return
        if self.stage is None or self.state is None:
            self.replaying = False
            self.status = "playing"
            return

        action = self._replay_actions[self._replay_index]
        before = self.state
        result = step(self.stage, before, action)
        if result.outcome != Outcome.MOVED or result.state is None:
            self.replaying = False
            self.status = "error"
            self.fail_reason = result.reason or "illegal"
            return

        self._replay_index += 1
        self.moves += 1
        self.state = result.state

        def after_step() -> None:
            if session != self._session:
                return
            if is_goal(self.stage, self.state):
                self.replaying = False
                self.status = "winning"
                self.scene.show_win(on_done=lambda: self._set_if_current(session, "won"))
                return
            if self._replay_index >= len(self._replay_actions):
                self.replaying = False
                self.status = "playing"
                return
            if not self.paused:
                self._queue_replay(session, self.delay)

        self.scene.animate_step(before, action, result, on_done=after_step)
