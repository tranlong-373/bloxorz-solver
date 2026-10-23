"""GameController: manual play, split control, replay. Must not import ursina. Owner: VT4 (tasks 4.2-4.4)."""
from __future__ import annotations

from typing import Any

from bloxorz.engine import Outcome, initial_state, is_goal, step
from bloxorz.model import Action, Direction, State
from bloxorz.stage import Stage


class GameController:
    """Coordinates gameplay logic, moves counter, and communicates with SceneView."""

    def __init__(self, scene: Any) -> None:
        self.scene = scene
        self.stage: Stage | None = None
        self.state: State | None = None
        self.moves: int = 0
        self.status: str = "playing"  # playing, falling, lost, winning, won

    def load(self, stage: Stage) -> None:
        """Load a stage, initialize state, reset moves and status."""
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
        if self.scene.is_busy() or self.status != "playing":
            return
        if self.stage is None or self.state is None:
            return

        action = Action(direction=d)
        res = step(self.stage, self.state, action)

        if res.outcome == Outcome.MOVED:
            before = self.state
            self.moves += 1
            self.state = res.state
            self.scene.show_state(self.state)
            self.scene.animate_step(before, action, res, on_done=self._after_move)
        elif res.outcome == Outcome.ILLEGAL:
            before = self.state
            self.status = "falling"
            self.scene.show_fall(before, action, on_done=lambda: self._set("lost"))

    def _after_move(self) -> None:
        """Check victory condition after a valid move finishes animating."""
        if self.stage is not None and self.state is not None and is_goal(self.stage, self.state):
            self.status = "winning"
            self.scene.show_win(on_done=lambda: self._set("won"))
        else:
            self.status = "playing"

    def _set(self, status: str) -> None:
        """Update game status."""
        self.status = status
