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
        Slider,
        camera,
        color,
        destroy,
        window,
    )
except ImportError:
    Button = None
    Entity = None
    Text = None
    Slider = None
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
            color=color.hex("#f8f9fa") if color else None,
            parent=camera.ui if camera else None,
        )

        # Status text (displayed below info)
        self.status_text = Text(
            text="",
            position=(-0.84, 0.38),
            scale=1.25,
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

    def _build_solver_panel(self) -> None:
        panel_x, panel_y = 0.70, 0.19
        self.solver_panel = Entity(
            parent=camera.ui if camera else None,
            model="quad",
            scale=(0.42, 0.34),
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
                on_click=lambda algorithm=name: self.select_algorithm(algorithm),
            )
            button.enabled = name in ALGORITHMS
            self.solver_buttons[name] = button

        self.solver_action_button = Button(
            text="Play",
            parent=self.solver_controls,
            scale=(0.065, 0.04),
            position=(panel_x + 0.15, panel_y - 0.14),
            on_click=self.start_selected_solver,
            color=color.hex("#6b7280") if color else None,
        )
        self.solver_action_button.enabled = True
        self.solver_text = Text(
            text="Ready",
            parent=self.solver_controls,
            position=(panel_x - 0.19, panel_y + 0.012),
            scale=0.62,
            color=color.hex("#cbd5e1") if color else None,
        )
        self.pause_button = Button(
            text="Pause",
            parent=self.solver_controls,
            scale=(0.075, 0.04),
            position=(panel_x - 0.09, panel_y - 0.09),
            on_click=self.controller.pause,
        )
        self.step_button = Button(
            text="Step",
            parent=self.solver_controls,
            scale=(0.065, 0.04),
            position=(panel_x, panel_y - 0.09),
            on_click=self.controller.step_once,
        )
        self.resume_button = Button(
            text="Resume",
            parent=self.solver_controls,
            scale=(0.065, 0.04),
            position=(panel_x + 0.09, panel_y - 0.09),
            on_click=self.controller.resume,
        )
        self.speed_slider = Slider(
            min=0,
            max=1,
            default=0.83,
            step=0.01,
            parent=self.solver_controls,
            position=(panel_x - 0.10, panel_y - 0.14),
            scale=(0.30, 0.35, 1),
            on_value_changed=self._set_speed,
        )
        self.speed_slider.knob.scale = (2.4, 2.4, 1)
        self._set_speed()
        Text(
            text="Speed",
            parent=self.solver_controls,
            position=(panel_x - 0.18, panel_y - 0.14),
            scale=0.65,
            color=color.hex("#cbd5e1") if color else None,
        )

    def _set_speed(self) -> None:
        slider = getattr(self, "speed_slider", None)
        value = float(slider.value) if slider is not None else 0.83
        self.controller.set_delay(1.0 - value * 0.9)

    def toggle_solver_panel(self) -> None:
        visible = not self.solver_panel.enabled
        self.solver_panel.enabled = visible
        self.solver_controls.enabled = visible

    def close_solver_panel(self) -> None:
        self.solver_panel.enabled = False
        self.solver_controls.enabled = False

    def select_algorithm(self, algorithm: str) -> None:
        if algorithm not in ALGORITHMS:
            return
        self.selected_algorithm = algorithm
        for name, button in self.solver_buttons.items():
            button.color = color.hex("#7c3aed") if name == algorithm else color.hex("#334155")
        self.solver_action_button.enabled = True
        self.solver_action_button.color = (
            color.hex("#7c3aed")
            if self.controller.stage is not None and color
            else color.hex("#6b7280") if color else None
        )

    def start_selected_solver(self) -> None:
        stage = self.controller.stage
        algorithm = self.selected_algorithm
        if stage is None or algorithm not in ALGORITHMS:
            return
        self.runner.cancel()
        self.controller.restart()
        self.controller.status = "solving"
        self.runner.start(algorithm, stage)
        self._cancel_requested = False
        self._active_algorithm = algorithm
        self._result_handled = False
        self.solver_text.text = f"Solving {algorithm.upper()}..."
        self.solver_action_button.text = "Cancel"
        self.solver_action_button.on_click = self.cancel_solver
        self.solver_action_button.color = color.hex("#c0392b") if color else None
        self.solver_action_button.enabled = True

    def cancel_solver(self) -> None:
        self.runner.cancel()
        self._cancel_requested = True
        self.solver_text.text = "Cancelling..."
        self.solver_action_button.text = "Cancelling"
        self.solver_action_button.enabled = True
        self.solver_action_button.color = color.hex("#6b7280") if color else None

    def reset_solver_action(self) -> None:
        self.solver_action_button.text = "Play"
        self.solver_action_button.on_click = self.start_selected_solver
        self.solver_action_button.enabled = True
        self.solver_action_button.color = (
            color.hex("#7c3aed")
            if self.selected_algorithm is not None and color
            else color.hex("#6b7280") if color else None
        )

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
        result = self.runner.poll()
        if result is not None and not self._result_handled:
            self._result_handled = True
            display_status = "cancelled" if self._cancel_requested else result.status
            peak = "n/a" if result.peak_mem_bytes is None else f"{result.peak_mem_bytes / 1024:.1f} KB"
            self.solver_text.text = (
                f"{display_status} | moves {result.length} | cost {result.cost:g}\n"
                f"expanded {result.expanded} | time {result.time_s * 1000:.1f} ms\n"
                f"peak memory {peak}"
            )
            if result.message:
                self.solver_text.text += f"\n{result.message}"
            if result.status == "solved" and not self._cancel_requested:
                self.controller.start_replay(result.actions)
            else:
                self.controller.status = "playing"
            self.reset_solver_action()
        elif not self._result_handled and self.runner.running:
            self.solver_text.text = (
                f"Solving {self._active_algorithm.upper()}... "
                f"{self.runner.elapsed_s:.1f} s"
            )

        if not self._result_handled and not self._cancel_requested:
            self.solver_action_button.enabled = True
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
