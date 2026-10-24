"""Creates the Ursina window, input() and update(). Owner: VT4 (task 4.2)."""
from __future__ import annotations

import sys
from typing import Any

from ursina import AmbientLight, DirectionalLight, Ursina, window

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


def input(key: str) -> None:
    """Handle global keyboard inputs."""
    global _controller, _ui
    if _controller is None or _ui is None:
        return

    # Arrow keys and WASD drive manual movement
    if key in ARROW_KEYS:
        if _ui.menu_panel.enabled:
            return
        _controller.on_direction(ARROW_KEYS[key])
        return

    # 'r' key triggers restart
    if key == "r":
        _controller.restart()
        return

    # 'n' key toggles the level selection menu
    if key == "n":
        _ui.toggle_menu()
        return

    # 'escape' closes the menu if open
    if key == "escape":
        _ui.close_menu()
        return


def update() -> None:
    """Frame update hook to refresh UI texts."""
    global _ui
    if _ui is not None:
        _ui.update()


def main() -> None:
    """Application entry point: sets up Ursina, scene, controller, UI, and runs."""
    global _controller, _ui

    app = Ursina()
    window.title = "Bloxorz Solver"
    window.borderless = False

    # Hook input and update into __main__ so Ursina dispatches directly without duplicate entities
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

    # Load initial level (prefer basic_01 if available)
    if _ui.stages:
        initial_stage = next(
            (s for s in _ui.stages if s.id == "basic_01"),
            _ui.stages[0],
        )
        _controller.load(initial_stage)

    app.run(info=False)


if __name__ == "__main__":
    main()
