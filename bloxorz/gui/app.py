"""Creates the Ursina window, input() and update(). Owner: VT4 (task 4.2)."""
from __future__ import annotations

import sys
from typing import Any

from ursina import AmbientLight, DirectionalLight, Entity, Ursina, window

from bloxorz.gui.controller import GameController
from bloxorz.gui.scene.view import SceneView
from bloxorz.gui.ui import UI
from bloxorz.model import Direction

# Module-level references
_controller: GameController | None = None
_ui: UI | None = None

ARROW_KEYS: dict[str, Direction] = {
    # Ursina internal key names
    "up arrow": Direction.UP,
    "down arrow": Direction.DOWN,
    "left arrow": Direction.LEFT,
    "right arrow": Direction.RIGHT,
    # Common alternative names
    "arrow up": Direction.UP,
    "arrow down": Direction.DOWN,
    "arrow left": Direction.LEFT,
    "arrow right": Direction.RIGHT,
    "up": Direction.UP,
    "down": Direction.DOWN,
    "left": Direction.LEFT,
    "right": Direction.RIGHT,
    # WASD keys for convenience
    "w": Direction.UP,
    "s": Direction.DOWN,
    "a": Direction.LEFT,
    "d": Direction.RIGHT,
}


def handle_input(key: str) -> None:
    """Process key inputs."""
    global _controller, _ui
    if _controller is None or _ui is None:
        return

    # Debug print so terminal shows every key received
    if not key.endswith(" up") and not key.endswith(" hold"):
        print(f"[Key] received: {key!r}")

    # Arrow keys and WASD drive manual movement
    if key in ARROW_KEYS:
        print(f"[Key] -> Direction {ARROW_KEYS[key]}")
        _controller.on_direction(ARROW_KEYS[key])
        return

    # 'r' key triggers restart
    if key == "r":
        print("[Key] -> Restart")
        _controller.restart()
        return

    # 'n' key toggles the level selection menu
    if key == "n":
        print("[Key] -> Toggle Menu")
        _ui.toggle_menu()
        return

    # 'escape' closes the menu if open
    if key == "escape":
        print("[Key] -> Close Menu")
        _ui.close_menu()
        return


def handle_update() -> None:
    """Frame update hook to refresh UI texts."""
    global _ui
    if _ui is not None:
        _ui.update()


# Global functions for Ursina convention
def input(key: str) -> None:
    handle_input(key)


def update() -> None:
    handle_update()


class GameHandler(Entity):
    """Entity listener ensuring input and update hooks are always called by Ursina."""

    def input(self, key: str) -> None:
        handle_input(key)

    def update(self) -> None:
        handle_update()


def main() -> None:
    """Application entry point: sets up Ursina, scene, controller, UI, and runs."""
    global _controller, _ui

    app = Ursina()
    window.title = "Bloxorz Solver"
    window.borderless = False

    # Hook into __main__ if loaded from main.py
    if "__main__" in sys.modules:
        main_mod = sys.modules["__main__"]
        main_mod.input = input
        main_mod.update = update

    # Standard lighting consistent with scene demo
    AmbientLight(color=(0.65, 0.65, 0.65, 1))
    sun = DirectionalLight()
    sun.look_at((1, -2, -1))

    scene_view = SceneView()
    _controller = GameController(scene_view)
    _ui = UI(_controller)

    # Attach handler entity to scene
    GameHandler()

    # Load initial level (prefer basic_01 if available)
    if _ui.stages:
        initial_stage = next(
            (s for s in _ui.stages if s.id == "basic_01"),
            _ui.stages[0],
        )
        _controller.load(initial_stage)

    app.run()


if __name__ == "__main__":
    main()
