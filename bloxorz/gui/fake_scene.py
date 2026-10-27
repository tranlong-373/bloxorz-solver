"""FakeScene: SceneView stand-in that prints, for tests. Must not import ursina. Owner: VT4 (task 4.2)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bloxorz.model import Action, State
from bloxorz.stage import Stage


class FakeScene:
    """Mock SceneView for testing GameController without Ursina or 3D engine."""

    def __init__(self) -> None:
        self.stage: Stage | None = None
        self.state: State | None = None
        self.selected_cube: int | None = None
        self.busy: bool = False
        self.events: list[tuple[str, Any]] = []

    def load_stage(self, stage: Stage, state: State) -> None:
        self.stage = stage
        self.state = state
        self.selected_cube = None
        self.events.append(("load_stage", stage.id, state))
        print(f"[FakeScene] load_stage: stage={stage.id}, state={state}")

    def show_state(self, state: State) -> None:
        self.state = state
        self.events.append(("show_state", state))
        print(f"[FakeScene] show_state: state={state}")

    def is_busy(self) -> bool:
        return self.busy

    def animate_step(
        self,
        before: State,
        action: Action,
        result: Any,
        on_done: Callable[[], None],
    ) -> None:
        self.state = result.state
        self.events.append(("animate_step", before, action, result.outcome))
        print(f"[FakeScene] animate_step: action={action}, outcome={result.outcome}")
        on_done()

    def show_fall(
        self,
        before: State,
        action: Action,
        on_done: Callable[[], None],
    ) -> None:
        self.events.append(("show_fall", before, action))
        print(f"[FakeScene] show_fall: before={before}, action={action}")
        on_done()

    def show_illegal_step(
        self,
        before: State,
        action: Action,
        result: Any,
        on_done: Callable[[], None],
    ) -> None:
        """Mirror SceneView.show_illegal_step: 'fell' is a plain fall."""
        if result.reason not in ("fell", "fragile_broke", "bridge_closed"):
            raise ValueError(f"Not an illegal-move result: {result!r}")
        if result.reason == "fell":
            self.show_fall(before, action, on_done)
            return
        self.events.append(("show_illegal_step", before, action, result.reason))
        print(f"[FakeScene] show_illegal_step: reason={result.reason}, action={action}")
        on_done()

    def show_win(self, on_done: Callable[[], None]) -> None:
        self.events.append(("show_win",))
        print("[FakeScene] show_win")
        on_done()

    def set_selected(self, cube: int | None) -> None:
        self.selected_cube = cube
        self.events.append(("set_selected", cube))
        print(f"[FakeScene] set_selected: cube={cube}")
