"""Buttons, level menu, text labels, solver panel. Owner: VT4 (tasks 4.2, 4.3, 4.5)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from bloxorz.loader import list_stages
from bloxorz.search import ALGORITHMS
from bloxorz.stage import Stage
from bloxorz.gui.solver_runner import SolverRunner

try:
    from ursina import (
        Button,
        Entity,
        Text,
        camera,
        color,
        destroy,
        window,
    )
except ImportError:
    Button = None
    Entity = None
    Text = None
    camera = None
    color = None
    destroy = None
    window = None


def get_menu_stages(repo_root: Path | str | None = None) -> list[Stage]:
    """Collect stages from fixtures, original, and bench folders, excluding stage_30."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    else:
        repo_root = Path(repo_root)

    fixtures = list_stages(repo_root / "stages" / "fixtures")
    original = list_stages(repo_root / "stages" / "original")
    bench = list_stages(repo_root / "stages" / "bench")

    combined = fixtures + original + bench
    # Keep 32 original stages and exclude stage_30
    return [s for s in combined if s.id != "stage_30"]


def format_stage_title(stage_id: str, max_len: int = 12) -> str:
    """Friendly title display for menu buttons with truncation for long names."""
    if stage_id.startswith("stage_"):
        suffix = stage_id.removeprefix("stage_")
        if suffix.isdecimal():
            return f"Màn {int(suffix):02d}"

    title = stage_id.replace("_", " ").title()
    if len(title) > max_len:
        return title[: max_len - 3].strip() + "..."
    return title


def format_solver_result(result: Any, cancelled: bool = False) -> str:
    """Format solver metrics, leaving solution-only values blank when unavailable."""
    status = "cancelled" if cancelled else result.status
    solved = result.status == "solved" and not cancelled
    moves = str(result.length) if solved else "—"
    cost = f"{result.cost:g}" if solved else "—"
    peak = "—" if result.peak_mem_bytes is None else f"{result.peak_mem_bytes / 1024:.1f} KiB"
    return (
        f"{status} | moves {moves} | cost {cost}\n"
        f"expanded {result.expanded} | time {result.time_s * 1000:.1f} ms\n"
        f"peak memory {peak}"
        + (f"\n{result.message}" if result.message else "")
    )


class UI:
    """Manages 2D HUD labels, action buttons, and a categorized level menu."""

    def __init__(self, controller: Any) -> None:
        self.controller = controller
        self.stages = get_menu_stages()
        self.current_tab = "G1"
        self.current_page = 0
        self.page_size = 25
        self.grid_buttons: list[Any] = []
        self.runner = SolverRunner()
        self._result_handled = True
        self._cancel_requested = False
        self.selected_algorithm: str | None = None

        # Top-Left HUD Info Text
        self.info_text = Text(
            text="Màn: -- · Bước: 0",
            position=(-0.84, 0.45),
            scale=1.25,
            origin=(-0.5, 0),
            color=color.hex("#f8f9fa") if color else None,
            parent=camera.ui if camera else None,
        )

        # Status text (displayed below info)
        self.status_text = Text(
            text="",
            position=(-0.84, 0.38),
            scale=1.25,
            origin=(-0.5, 0),
            color=color.hex("#2ecc71") if color else None,
            parent=camera.ui if camera else None,
        )

        # Top-Right Action Buttons
        self.btn_restart = Button(
            text="Restart (R)",
            color=color.hex("#2980b9") if color else None,
            highlight_color=color.hex("#3498db") if color else None,
            scale=(0.19, 0.054),
            radius=0.18,
            position=(0.72, 0.445),
            parent=camera.ui if camera else None,
            on_click=self.restart,
        )

        self.btn_new_game = Button(
            text="New Game (N)",
            color=color.hex("#d35400") if color else None,
            highlight_color=color.hex("#e67e22") if color else None,
            scale=(0.19, 0.054),
            radius=0.18,
            position=(0.52, 0.445),
            parent=camera.ui if camera else None,
            on_click=self.toggle_menu,
        )

        self.btn_solver_panel = Button(
            text="Solver",
            color=color.hex("#2980b9") if color else None,
            highlight_color=color.hex("#3498db") if color else None,
            scale=(0.19, 0.054),
            radius=0.18,
            position=(0.31, 0.445),
            parent=camera.ui if camera else None,
            on_click=self.toggle_solver_panel,
        )

        self._build_solver_panel()

        # Level Selection Modal
        self._build_menu()
        self._layout_aspect = None
        self._layout_ui()

    def _layout_ui(self) -> None:
        if window is None:
            return

        half_width = window.aspect_ratio / 2
        edge_gap = 0.035
        button_width = 0.19
        button_gap = 0.015
        toolbar_shift = 0.05
        restart_x = half_width - edge_gap - button_width / 2 - toolbar_shift
        new_game_x = restart_x - button_width - button_gap
        solver_x = new_game_x - button_width - button_gap

        self.btn_restart.position = (restart_x, 0.445)
        self.btn_new_game.position = (new_game_x, 0.445)
        self.btn_solver_panel.position = (solver_x, 0.445)

        left_x = -half_width + edge_gap
        self.info_text.x = left_x
        self.status_text.x = left_x

        panel_x = half_width - edge_gap - 0.42 / 2
        panel_y = -0.5 + edge_gap + 0.42 / 2
        self.solver_panel.position = (panel_x, panel_y, 0.1)
        self.solver_controls.x = panel_x - 0.70
        self.solver_controls.y = panel_y - 0.19
        self._layout_aspect = window.aspect_ratio

    def _build_solver_panel(self) -> None:
        panel_x, panel_y = 0.70, 0.19
        self.solver_panel = Entity(
            parent=camera.ui if camera else None,
            model="quad",
            scale=(0.42, 0.42),
            position=(panel_x, panel_y, 0.1),
            color=color.hex("#121822") if color else None,
            enabled=False,
        )
        self.solver_controls = Entity(
            parent=camera.ui if camera else None,
            enabled=False,
        )
        Text(
            text="Solver",
            parent=self.solver_controls,
            position=(panel_x - 0.18, panel_y + 0.12),
            scale=1.1,
            origin=(-0.5, 0),
            color=color.hex("#f8f9fa") if color else None,
        )
        self.solver_buttons: dict[str, Any] = {}
        labels = (("bfs", "BFS"), ("dfs", "DFS"), ("ucs", "UCS"), ("astar", "A*"))
        button_x = (panel_x - 0.15, panel_x - 0.075, panel_x, panel_x + 0.075)
        for index, (name, label) in enumerate(labels):
            button = Button(
                text=label,
                parent=self.solver_controls,
                scale=(0.065, 0.04),
                position=(button_x[index], panel_y + 0.055),
                on_click=lambda algorithm=name: self.start_solver(algorithm),
            )
            button.enabled = name in ALGORITHMS
            self.solver_buttons[name] = button

        self.cancel_button = Button(
            text="Cancel",
            parent=self.solver_controls,
            scale=(0.34, 0.04),
            position=(panel_x, panel_y + 0.02),
            on_click=self.cancel_solver,
            color=color.hex("#6b7280") if color else None,
            enabled=False,
        )
        self.solver_text = Text(
            text="Ready",
            parent=self.solver_controls,
            position=(panel_x - 0.19, panel_y - 0.045),
            scale=0.62,
            origin=(-0.5, 0),
            color=color.hex("#cbd5e1") if color else None,
        )
        self.pause_button = Button(
            text="Pause",
            parent=self.solver_controls,
            scale=(0.075, 0.04),
            position=(panel_x - 0.09, panel_y - 0.12),
            on_click=self.controller.pause,
        )
        self.step_button = Button(
            text="Step",
            parent=self.solver_controls,
            scale=(0.065, 0.04),
            position=(panel_x, panel_y - 0.12),
            on_click=self.controller.step_once,
        )
        self.resume_button = Button(
            text="Resume",
            parent=self.solver_controls,
            scale=(0.065, 0.04),
            position=(panel_x + 0.09, panel_y - 0.12),
            on_click=self.controller.resume,
        )
        self.speed_buttons: dict[int, Any] = {}
        for index, multiplier in enumerate((1, 2, 4)):
            speed_button = Button(
                text=f"{multiplier}×",
                parent=self.solver_controls,
                scale=(0.055, 0.04),
                position=(panel_x - 0.045 + index * 0.065, panel_y - 0.17),
                on_click=lambda speed=multiplier: self.set_replay_speed(speed),
            )
            speed_button.color = color.hex("#7c3aed") if multiplier == 1 else color.hex("#334155")
            self.speed_buttons[multiplier] = speed_button
        self.controller.set_speed(1)
        Text(
            text="Speed",
            parent=self.solver_controls,
            position=(panel_x - 0.18, panel_y - 0.17),
            scale=0.65,
            origin=(-0.5, 0),
            color=color.hex("#cbd5e1") if color else None,
        )

    def set_replay_speed(self, multiplier: int) -> None:
        self.controller.set_speed(multiplier)
        for speed, button in self.speed_buttons.items():
            button.color = color.hex("#7c3aed") if speed == multiplier else color.hex("#334155")

    def toggle_solver_panel(self) -> None:
        visible = not self.solver_panel.enabled
        self.solver_panel.enabled = visible
        self.solver_controls.enabled = visible

    def close_solver_panel(self) -> None:
        self.solver_panel.enabled = False
        self.solver_controls.enabled = False

    def start_solver(self, algorithm: str) -> None:
        if algorithm not in ALGORITHMS:
            return
        self.selected_algorithm = algorithm
        for name, button in self.solver_buttons.items():
            button.color = color.hex("#7c3aed") if name == algorithm else color.hex("#334155")
        stage = self.controller.stage
        if stage is None or self.runner.running:
            return
        self.runner.cancel()
        self.controller.restart()
        self.controller.status = "solving"
        self.runner.start(algorithm, stage)
        self._cancel_requested = False
        self._active_algorithm = algorithm
        self._result_handled = False
        self.solver_text.text = f"Solving {algorithm.upper()}..."
        self.cancel_button.text = "Cancel"
        self.cancel_button.enabled = True
        self.cancel_button.color = color.hex("#c0392b") if color else None
        for button in self.solver_buttons.values():
            button.enabled = False

    def cancel_solver(self) -> None:
        if self._result_handled or self._cancel_requested:
            return
        self.runner.cancel()
        self._cancel_requested = True
        self.solver_text.text = "Cancelling..."

    def reset_solver_action(self) -> None:
        self.cancel_button.text = "Cancel"
        self.cancel_button.enabled = False
        self.cancel_button.color = color.hex("#6b7280") if color else None
        for name, button in self.solver_buttons.items():
            button.enabled = name in ALGORITHMS

    def restart(self) -> None:
        self.runner.cancel()
        self._result_handled = True
        self.controller.restart()
        self.reset_solver_action()

    def _build_menu(self) -> None:
        """Construct a polished modal with tab bar frame and level grid."""
        self.menu_panel = Entity(
            parent=camera.ui if camera else None,
            enabled=False,
        )

        # Main modal backdrop
        self.menu_bg = Entity(
            parent=self.menu_panel,
            model="quad",
            scale=(1.12, 0.78),
            color=color.hex("#121822") if color else None,
            position=(0, 0, 0.05),
        )

        Text(
            text="CHỌN MÀN CHƠI",
            parent=self.menu_panel,
            position=(-0.16, 0.34),
            scale=1.45,
            color=color.hex("#f39c12") if color else None,
        )

        Button(
            text="Đóng",
            parent=self.menu_panel,
            color=color.hex("#c0392b") if color else None,
            highlight_color=color.hex("#e74c3c") if color else None,
            scale=(0.11, 0.042),
            radius=0.15,
            position=(0.47, 0.34),
            on_click=self.close_menu,
        )

        self.tab_frame_border = Entity(
            parent=self.menu_panel,
            model="quad",
            scale=(1.02, 0.068),
            color=color.hex("#2c3e50") if color else None,
            position=(0, 0.25, 0.025),
        )
        self.tab_frame_inner = Entity(
            parent=self.menu_panel,
            model="quad",
            scale=(1.012, 0.060),
            color=color.hex("#0f172a") if color else None,
            position=(0, 0.25, 0.02),
        )

        # Category Tabs
        tabs = [
            ("G1", "Nhóm G1"),
            ("G2", "Nhóm G2"),
            ("G3", "Nhóm G3"),
            ("G4", "Nhóm G4"),
            ("G5", "Nhóm G5"),
            ("ALL", "Tất cả"),
        ]

        self.tab_buttons: dict[str, Any] = {}
        tab_w = 0.155
        spacing_t = 0.163
        start_tx = -((len(tabs) - 1) * spacing_t) / 2

        for i, (tab_key, tab_label) in enumerate(tabs):
            tx = start_tx + i * spacing_t

            def make_tab_handler(k: str):
                return lambda: self.switch_tab(k)

            btn = Button(
                text=tab_label,
                parent=self.menu_panel,
                color=color.hex("#1e293b") if color else None,
                highlight_color=color.hex("#334155") if color else None,
                scale=(tab_w, 0.048),
                radius=0.14,
                position=(tx, 0.25),
                on_click=make_tab_handler(tab_key),
            )
            self.tab_buttons[tab_key] = btn

        # Container for stage grid buttons
        self.grid_container = Entity(parent=self.menu_panel)
        self.previous_page_button = Button(
            text="Trước",
            parent=self.menu_panel,
            scale=(0.13, 0.042),
            position=(-0.18, -0.30),
            on_click=self.previous_page,
        )
        self.next_page_button = Button(
            text="Sau",
            parent=self.menu_panel,
            scale=(0.13, 0.042),
            position=(0.18, -0.30),
            on_click=self.next_page,
        )
        self.page_text = Text(
            text="",
            parent=self.menu_panel,
            position=(-0.03, -0.31),
            scale=0.8,
        )
        self.render_stage_grid()

    def switch_tab(self, tab_key: str) -> None:
        """Switch active group tab and rebuild grid."""
        if tab_key not in self.tab_buttons:
            return
        self.current_tab = tab_key
        self.current_page = 0
        # Highlight active tab button, dim inactive ones
        for k, btn in self.tab_buttons.items():
            if k == tab_key:
                btn.color = color.hex("#2980b9") if color else None
            else:
                btn.color = color.hex("#1e293b") if color else None
        self.render_stage_grid()

    def render_stage_grid(self) -> None:
        """Render level buttons for current tab."""
        # Clear existing buttons
        for btn in self.grid_buttons:
            if destroy:
                destroy(btn)
        self.grid_buttons.clear()

        # Filter stages by active tab
        if self.current_tab == "ALL":
            active_stages = self.stages
        else:
            active_stages = [s for s in self.stages if s.group == self.current_tab]

        page_count = max(1, (len(active_stages) + self.page_size - 1) // self.page_size)
        self.current_page = min(self.current_page, page_count - 1)
        start = self.current_page * self.page_size
        visible_stages = active_stages[start : start + self.page_size]

        cols = 5
        btn_w = 0.188
        btn_h = 0.052
        spacing_x = 0.205
        spacing_y = 0.064
        start_x = -((cols - 1) * spacing_x) / 2
        start_y = 0.155

        for i, stg in enumerate(visible_stages):
            col_idx = i % cols
            row_idx = i // cols
            x = start_x + col_idx * spacing_x
            y = start_y - row_idx * spacing_y

            display_name = format_stage_title(stg.id)

            def make_click_handler(s: Stage):
                return lambda: self.select_stage(s)

            btn = Button(
                text=display_name,
                parent=self.grid_container,
                color=color.hex("#1e293b") if color else None,
                highlight_color=color.hex("#3b82f6") if color else None,
                scale=(btn_w, btn_h),
                radius=0.16,
                position=(x, y),
                on_click=make_click_handler(stg),
            )
            self.grid_buttons.append(btn)

        can_go_back = self.current_page > 0
        can_go_forward = self.current_page + 1 < page_count
        self.previous_page_button.enabled = True
        self.next_page_button.enabled = True
        self.previous_page_button.color = color.hex(
            "#1e293b" if can_go_back else "#6b7280"
        ) if color else None
        self.next_page_button.color = color.hex(
            "#1e293b" if can_go_forward else "#6b7280"
        ) if color else None
        self.page_text.text = f"{self.current_page + 1} / {page_count}"

    def previous_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.render_stage_grid()

    def next_page(self) -> None:
        if self.current_tab == "ALL":
            active_count = len(self.stages)
        else:
            active_count = sum(stage.group == self.current_tab for stage in self.stages)
        page_count = max(1, (active_count + self.page_size - 1) // self.page_size)
        if self.current_page + 1 < page_count:
            self.current_page += 1
            self.render_stage_grid()

    def select_stage(self, stage: Stage) -> None:
        """Load chosen stage and dismiss the level select menu."""
        self.runner.cancel()
        self._result_handled = True
        self.controller.load(stage)
        self.reset_solver_action()
        self.close_menu()

    def toggle_menu(self) -> None:
        """Toggle level select modal visibility."""
        self.menu_panel.enabled = not self.menu_panel.enabled
        if self.menu_panel.enabled:
            self.close_solver_panel()
            self.switch_tab(self.current_tab)

    def open_menu(self) -> None:
        self.menu_panel.enabled = True
        self.close_solver_panel()
        self.switch_tab(self.current_tab)

    def close_menu(self) -> None:
        self.menu_panel.enabled = False

    def update(self) -> None:
        """Refresh HUD text every frame."""
        if window is not None and window.aspect_ratio != self._layout_aspect:
            self._layout_ui()

        result = self.runner.poll()
        if result is not None and not self._result_handled:
            self._result_handled = True
            self.solver_text.text = format_solver_result(result, self._cancel_requested)
            if result.status == "solved" and not self._cancel_requested:
                self.controller.start_replay(result.actions)
            else:
                self.controller.status = "playing"
            self.reset_solver_action()
        elif not self._result_handled and self.runner.running:
            if self._cancel_requested:
                self.solver_text.text = "Cancelling..."
            else:
                self.solver_text.text = (
                    f"Solving {self._active_algorithm.upper()}... "
                    f"{self.runner.elapsed_s:.1f} s"
                )

        self.cancel_button.enabled = not self._result_handled
        self.pause_button.enabled = self.controller.replaying and not self.controller.paused
        self.step_button.enabled = self.controller.replaying and self.controller.paused
        self.resume_button.enabled = self.controller.replaying and self.controller.paused

        stage_id = self.controller.stage.id if self.controller.stage else "--"
        moves = self.controller.moves
        self.info_text.text = f"Màn: {stage_id} · Bước: {moves}"

        status = self.controller.status
        if status == "won":
            self.status_text.text = f"Thắng sau {moves} bước!"
            if color:
                self.status_text.color = color.hex("#2ecc71")
        elif status == "lost":
            self.status_text.text = "Thua – bấm Restart để chơi lại"
            if color:
                self.status_text.color = color.hex("#e74c3c")
        else:
            self.status_text.text = ""
