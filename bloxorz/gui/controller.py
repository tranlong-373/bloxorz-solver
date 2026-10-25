"""GameController: manual play, split control, replay. Must not import ursina. Owner: VT4 (tasks 4.2-4.4)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bloxorz.engine import Outcome, initial_state, is_goal, step
from bloxorz.model import Action, Direction, State
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
        self.status: str = "playing"  # playing, solving, replaying, falling, lost, winning, won
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
        self.scene.load_stage(stage, self.state)

    def restart(self) -> None:
        """Reload current stage to start over."""
        if self.stage is not None:
            self.load(self.stage)

    def on_direction(self, d: Direction) -> None:
        """Handle directional movement input from the player."""
        if self.replaying or self.scene.is_busy() or self.status != "playing":
            return
        if self.stage is None or self.state is None:
            return

        action = Action(direction=d)
        res = step(self.stage, self.state, action)

        if res.outcome == Outcome.MOVED:
            before = self.state
            self.moves += 1
            self.state = res.state
            session = self._session
            self.scene.animate_step(
                before, action, res, on_done=lambda: self._after_move(session)
            )
        elif res.outcome == Outcome.ILLEGAL:
            before = self.state
            self.status = "falling"
            session = self._session
            self.scene.show_fall(
                before, action, on_done=lambda: self._set_if_current(session, "lost")
            )

    def _after_move(self, session: int) -> None:
        """Check victory condition after a valid move finishes animating."""
        if session != self._session:
            return
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
