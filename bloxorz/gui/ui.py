"""Buttons, level menu, text labels, solver panel. Owner: VT4 (tasks 4.2, 4.3, 4.5)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from bloxorz.loader import list_stages
from bloxorz.stage import Stage

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
        num = stage_id.split("_")[1]
        return f"Màn {int(num):02d}"

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
        self.grid_buttons: list[Any] = []

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
            scale=(0.15, 0.048),
            radius=0.18,
            position=(0.74, 0.445),
            parent=camera.ui if camera else None,
            on_click=self.controller.restart,
        )

        self.btn_new_game = Button(
            text="New Game (N)",
            color=color.hex("#d35400") if color else None,
            highlight_color=color.hex("#e67e22") if color else None,
            scale=(0.17, 0.048),
            radius=0.18,
            position=(0.56, 0.445),
            parent=camera.ui if camera else None,
            on_click=self.toggle_menu,
        )

        # Level Selection Modal
        self._build_menu()

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
            color=color.rgba(18, 24, 34, 250) if color else None,
            position=(0, 0, 0.05),
        )

        # Modal Header Title
        Text(
            text="CHỌN MÀN CHƠI",
            parent=self.menu_panel,
            position=(-0.16, 0.34),
            scale=1.45,
            color=color.hex("#f39c12") if color else None,
        )

        # Close button
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

        # Elegant segmented tab bar frame (Khung bao quanh thanh chọn nhóm)
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
            ("ALL", "Tất cả"),
        ]

        self.tab_buttons: dict[str, Any] = {}
        tab_w = 0.188
        spacing_t = 0.198
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
        self.render_stage_grid()

    def switch_tab(self, tab_key: str) -> None:
        """Switch active group tab and rebuild grid."""
        self.current_tab = tab_key
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

        cols = 5
        btn_w = 0.188
        btn_h = 0.052
        spacing_x = 0.205
        spacing_y = 0.064
        start_x = -((cols - 1) * spacing_x) / 2
        start_y = 0.155

        for i, stg in enumerate(active_stages):
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

    def select_stage(self, stage: Stage) -> None:
        """Load chosen stage and dismiss the level select menu."""
        self.controller.load(stage)
        self.close_menu()

    def toggle_menu(self) -> None:
        """Toggle level select modal visibility."""
        self.menu_panel.enabled = not self.menu_panel.enabled
        if self.menu_panel.enabled:
            self.switch_tab(self.current_tab)

    def open_menu(self) -> None:
        self.menu_panel.enabled = True
        self.switch_tab(self.current_tab)

    def close_menu(self) -> None:
        self.menu_panel.enabled = False

    def update(self) -> None:
        """Refresh HUD text every frame."""
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
