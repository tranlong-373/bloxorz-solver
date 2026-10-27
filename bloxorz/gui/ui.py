"""Buttons, level menu, text labels, solver panel. Owner: VT4 (tasks 4.2, 4.3, 4.5)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bloxorz.loader import list_stages
from bloxorz.search import ALGORITHMS
from bloxorz.stage import Stage
from bloxorz.gui.solver_runner import SolverRunner

try:
    from ursina import Button, Entity, Text, camera, color, curve, destroy, window
    from ursina.models.procedural.quad import Quad
except ImportError:
    Button = None
    Entity = None
    Text = None
    camera = None
    color = None
    curve = None
    destroy = None
    window = None
    Quad = None


# ---------------------------------------------------------------------------
# Text helpers (pure: no Ursina needed, covered by tests/app)
# ---------------------------------------------------------------------------

NOT_AVAILABLE = "chưa có"

# Group meaning, matching the mechanisms VT5 checks in tests/informed/test_bench_stages.py.
GROUP_INFO: dict[str, tuple[str, str]] = {
    "G1": ("Cơ bản", "Chỉ có sàn và đích, không ô dễ vỡ, cầu hay công tắc"),
    "G2": ("Ô dễ vỡ", "Có ô dễ vỡ F, khối đứng thẳng lên là rơi; không công tắc, không cầu"),
    "G3": ("Công tắc và cầu", "Công tắc mềm/nặng mở hoặc đóng cầu; không tách khối"),
    "G4": ("Tách khối", "Chỉ có công tắc tách: điều khiển 2 cube rồi ghép lại"),
    "G5": ("Tổng hợp", "Kết hợp từ 2 cơ chế trở lên: ô dễ vỡ, công tắc/cầu, tách khối"),
}
ALL_TAB_INFO = ("Tất cả", "Mọi màn: màn thử nghiệm, 32 màn gốc và bộ benchmark")
TAB_NAMES = {"G1": "Cơ bản", "G2": "Dễ vỡ", "G3": "Công tắc", "G4": "Tách khối",
             "G5": "Tổng hợp", "ALL": "Tất cả"}

STATUS_LABELS = {
    "solved": "Đã giải",
    "unsolvable": "Không có lời giải",
    "timeout": "Hết giờ",
    "cancelled": "Đã hủy",
    "error": "Lỗi",
}

FAIL_REASONS = {
    "fell": "Khối rơi khỏi bàn",
    "fragile_broke": "Ô dễ vỡ sụp dưới khối đứng",
    "bridge_closed": "Cầu đóng lại dưới khối",
}

ALGO_LABELS = {"bfs": "BFS", "dfs": "DFS", "ucs": "UCS", "astar": "A*"}

_ORIGINAL_ID = re.compile(r"stage_(\d+)")
_BENCH_ID = re.compile(r"g([1-5])_(\d+)")


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


def stage_source(stage_id: str) -> str:
    """'original', 'bench' or 'fixture', from the id scheme of each stage folder."""
    if _ORIGINAL_ID.fullmatch(stage_id):
        return "original"
    if _BENCH_ID.fullmatch(stage_id):
        return "bench"
    return "fixture"


def format_stage_title(stage_id: str, max_len: int = 16, menu: bool = False) -> str:
    """Friendly title for menu buttons and HUD; original stages keep source number."""
    original = _ORIGINAL_ID.fullmatch(stage_id)
    if original:
        if menu:
            return f"Màn gốc số {int(original.group(1))}"
        return f"Màn {int(original.group(1)):02d}"
    bench = _BENCH_ID.fullmatch(stage_id)
    if bench:
        return f"Bench G{bench.group(1)}-{bench.group(2)}"

    title = stage_id.replace("_", " ").title()
    if len(title) > max_len:
        return title[: max_len - 3].strip() + "..."
    return title


def group_caption(group: str) -> str:
    """One line describing a group (or the ALL tab) for the level menu."""
    name, detail = GROUP_INFO.get(group, ALL_TAB_INFO if group == "ALL" else (group, ""))
    prefix = "" if group == "ALL" else f"{group} · "
    return f"{prefix}{name}: {detail}" if detail else f"{prefix}{name}"


def _group_digits(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def solver_metric_rows(result: Any, cancelled: bool = False) -> list[tuple[str, str]]:
    """(label, value) rows for the solver table; unmeasured values read 'chưa có', never 0."""
    status = "cancelled" if cancelled else result.status
    solved = status == "solved"
    # Search ran (fully or partly): expanded/time are real measurements.
    searched = status != "error" or result.expanded > 0
    peak = result.peak_mem_bytes
    return [
        ("Trạng thái", f"{STATUS_LABELS.get(status, status)} ({status})"),
        ("Số nước", f"{result.length} nước" if solved else NOT_AVAILABLE),
        ("Chi phí", f"{result.cost:g}" if solved else NOT_AVAILABLE),
        ("Nút mở rộng", f"{_group_digits(result.expanded)} nút" if searched else NOT_AVAILABLE),
        ("Thời gian", f"{result.time_s * 1000:.1f} ms" if searched else NOT_AVAILABLE),
        ("Bộ nhớ đỉnh", NOT_AVAILABLE if peak is None else f"{peak / 1024:.1f} KiB"),
    ]


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


def end_screen_text(status: str, moves: int, fail_reason: str = "",
                    algorithm: str | None = None) -> tuple[str, str]:
    """(title, subtitle) of the centered win/lose screen."""
    if status == "won":
        if algorithm:
            label = ALGO_LABELS.get(algorithm, algorithm.upper())
            return "HOÀN THÀNH!", f"Lời giải {label} đưa khối về đích sau {moves} nước"
        return "HOÀN THÀNH!", f"Bạn đưa khối về đích sau {moves} bước"
    if status == "error":
        reason = FAIL_REASONS.get(fail_reason, fail_reason or "nước không hợp lệ")
        return "LỖI PHÁT LẠI", f"Lời giải dừng ở nước {moves + 1}: {reason}"
    reason = FAIL_REASONS.get(fail_reason, "Khối rơi khỏi bàn")
    return "THUA RỒI!", f"{reason} sau {moves} bước"


# ---------------------------------------------------------------------------
# Visual style
# ---------------------------------------------------------------------------

INK = "#e8f1ff"
MUTED = "#8ea3bd"
PANEL = "#0b1220"
EDGE = "#5ae6ff"
ACCENT = "#38d9f5"
SUCCESS = "#34d399"
DANGER = "#f2557a"
WARNING = "#fbbf24"
VIOLET = "#8b5cf6"
SLATE = "#1e293b"
SLATE_LIGHT = "#334155"
DISABLED = "#475569"

GROUP_COLORS = {
    "G1": "#38bdf8",
    "G2": "#f59e0b",
    "G3": "#34d399",
    "G4": "#a78bfa",
    "G5": "#f472b6",
    "ALL": "#94a3b8",
}
SOURCE_STYLE = {  # button fill, label in the menu footer
    "fixture": ("#1c2a3f", "Thử nghiệm"),
    "original": ("#243554", "Màn gốc"),
    "bench": ("#2d2550", "Benchmark"),
}

TOP_Y = 0.465  # first toolbar row
EDGE_GAP = 0.03


def _rgba(hex_code: str, alpha: int = 255):
    if color is None:
        return None
    code = hex_code.lstrip("#")
    return color.rgba32(int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16), alpha)


class UI:
    """2D HUD: status bar, key guide, legend, solver panel, end screen and level menu."""

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
        self._active_algorithm: str | None = None
        self._replay_algorithm: str | None = None
        self._end_status: str | None = None
        self._layout_aspect = None

        self._build_hud()
        self._build_toolbar()
        self._build_key_guide()
        self._build_legend()
        self._build_solver_panel()
        self._build_end_screen()
        self._build_menu()
        self._layout_ui()

    # -- small widget factories ------------------------------------------------

    def _panel(self, parent: Any, width: float, height: float, *, fill: str = PANEL,
               alpha: int = 215, edge: str = EDGE, edge_alpha: int = 60,
               radius: float = 0.12, position=(0, 0), z: float = 0.02) -> Any:
        """Rounded glass card (thin glowing rim + translucent fill), centered at position."""
        holder = Entity(parent=parent, position=(position[0], position[1], z))
        rim = 0.004
        Entity(
            parent=holder,
            model=Quad(radius=radius, aspect=(width + rim) / (height + rim)),
            scale=(width + rim, height + rim),
            color=_rgba(edge, edge_alpha),
            z=0.001,
        )
        holder.fill = Entity(
            parent=holder,
            model=Quad(radius=radius, aspect=width / height),
            scale=(width, height),
            color=_rgba(fill, alpha),
        )
        return holder

    def _text(self, parent: Any, text: str, position, *, scale: float = 1.0,
              tint: str = INK, origin=(-0.5, 0), **kwargs) -> Any:
        return Text(text=text, parent=parent, position=position, scale=scale,
                    origin=origin, color=_rgba(tint), **kwargs)

    def _button(self, parent: Any, text: str, position, size, fill: str, on_click,
                *, text_size: float = 0.85, radius: float = 0.3) -> Any:
        button = Button(
            text=text,
            parent=parent,
            position=position,
            scale=size,
            radius=radius,
            color=_rgba(fill),
            text_size=text_size,
            highlight_scale=1.04,
            pressed_scale=0.96,
            on_click=on_click,
        )
        self._paint(button, fill)
        return button

    @staticmethod
    def _paint(button: Any, fill: str) -> None:
        button.color = _rgba(fill)
        if hasattr(button.color, "tint"):
            button.highlight_color = button.color.tint(0.15)
            button.pressed_color = button.color.tint(-0.15)

    # -- top-left status card -------------------------------------------------

    def _build_hud(self) -> None:
        self.hud = Entity(parent=camera.ui)
        self._panel(self.hud, 0.62, 0.14, position=(0.31, -0.06))

        self.group_chip = Entity(
            parent=self.hud,
            model=Quad(radius=0.3, aspect=0.058 / 0.032),
            scale=(0.058, 0.032),
            position=(0.045, -0.022, -0.001),
            color=_rgba(GROUP_COLORS["G1"]),
        )
        self.group_chip_text = self._text(
            self.hud, "G1", (0.045, -0.022, -0.002), scale=0.8, tint=PANEL, origin=(0, 0)
        )
        self.title_text = self._text(self.hud, "--", (0.088, -0.020), scale=1.45)
        self.subtitle_text = self._text(self.hud, "", (0.018, -0.058), scale=0.8, tint=MUTED)
        # info_text / status_text keep their 4.2 names: moves counter and live status line.
        self.info_text = self._text(self.hud, "Bước 0", (0.018, -0.095), scale=1.0, tint=ACCENT)
        self.status_text = self._text(self.hud, "", (0.13, -0.095), scale=0.85, tint=MUTED)

    # -- top-right toolbar ------------------------------------------------------

    def _build_toolbar(self) -> None:
        self.toolbar = Entity(parent=camera.ui)
        size = (0.17, 0.05)
        self.btn_solver_panel = self._button(
            self.toolbar, "Solver", (0, 0), size, "#5b21b6", self.toggle_solver_panel
        )
        self.btn_new_game = self._button(
            self.toolbar, "New Game (N)", (0, 0), size, "#1e3a5f", self.toggle_menu
        )
        self.btn_restart = self._button(
            self.toolbar, "Restart (R)", (0, 0), size, "#0e7490", self.restart
        )

    # -- key guide (always visible, under the toolbar) -------------------------

    def _keycap(self, parent: Any, x: float, width: float, label: str = "",
                arrow_rotation: float | None = None) -> float:
        """Draw one key cap starting at x; return the x after it."""
        height = 0.032
        cx = x + width / 2
        Entity(parent=parent, model=Quad(radius=0.25, aspect=(width + 0.004) / (height + 0.004)),
               scale=(width + 0.004, height + 0.004), position=(cx, 0, 0.001),
               color=_rgba("#64748b"))
        Entity(parent=parent, model=Quad(radius=0.25, aspect=width / height),
               scale=(width, height), position=(cx, 0.001, 0), color=_rgba(SLATE))
        if arrow_rotation is not None:
            Entity(parent=parent, model="quad", texture="arrow_right", scale=0.016,
                   position=(cx, 0.001, -0.001), rotation_z=arrow_rotation, color=_rgba(INK))
        else:
            self._text(parent, label, (cx, 0.001, -0.001), scale=0.72, origin=(0, 0))
        return x + width

    def _build_key_guide(self) -> None:
        self.key_guide = Entity(parent=camera.ui)
        row = Entity(parent=self.key_guide)
        x = 0.0
        # Ursina's arrow_right texture points right; rotation_z turns it clockwise.
        for rotation in (-90, 90, 180, 0):
            x = self._keycap(row, x, 0.032, arrow_rotation=rotation) + 0.005
        items = ((None, "Lăn khối"), (("Space", 0.07), "Đổi cube"),
                 (("R", 0.032), "Chơi lại"), (("N", 0.032), "Chọn màn"))
        for cap, label in items:
            if cap is not None:
                x = self._keycap(row, x, cap[1], cap[0]) + 0.008
            else:
                x += 0.004
            text = self._text(row, label, (x, 0.0), scale=0.78, tint=MUTED)
            x += text.width + 0.025
        self._key_guide_width = x - 0.025
        pad = 0.018
        self._panel(self.key_guide, self._key_guide_width + 2 * pad, 0.05,
                    position=(self._key_guide_width / 2, 0), alpha=180, edge_alpha=40)

    # -- legend (bottom strip, outside the board frame) ------------------------

    def _build_legend(self) -> None:
        try:
            from bloxorz.gui.scene import theme
        except ImportError:  # scene unavailable: skip the legend, keep the game playable
            theme = None
        self.legend = Entity(parent=camera.ui)
        row = Entity(parent=self.legend)

        def tile(fill, rim=None):
            def draw(cx):
                if rim is not None:
                    Entity(parent=row, model=Quad(radius=0.2), scale=0.028,
                           position=(cx, 0, 0.001), color=rim)
                Entity(parent=row, model=Quad(radius=0.2), scale=0.022 if rim is not None else 0.026,
                       position=(cx, 0, 0), color=fill)
            return draw

        def soft(cx):
            Entity(parent=row, model="circle", scale=0.024, position=(cx, 0), color=link)

        def heavy(cx):
            for angle in (45, -45):
                Entity(parent=row, model="quad", scale=(0.028, 0.007), position=(cx, 0),
                       rotation_z=angle, color=link)

        def split(cx):
            for dx in (-0.006, 0.006):
                Entity(parent=row, model="quad", scale=(0.006, 0.026), position=(cx + dx, 0),
                       color=split_color)

        if theme is not None:
            floor = theme.TILE_COLORS["#"].tint(0.25)
            fragile = theme.TILE_COLORS["F"]
            goal = theme.TILE_COLORS["G"]
            portal = theme.PORTAL_COLOR
            link = theme.rgb(theme.LINK_PALETTE[0])
            split_color = theme.SWITCH_COLORS["split"]
        else:
            floor, fragile, goal, portal = (_rgba("#55607a"), _rgba("#f58c32"),
                                            _rgba("#040408"), _rgba("#3ce6ff"))
            link, split_color = _rgba("#46b9e6"), _rgba("#af73e1")

        items = (
            (tile(floor), "Sàn"),
            (tile(fragile), "Ô dễ vỡ (F)"),
            (tile(goal, portal), "Đích"),
            (tile(link), "Cầu"),
            (soft, "CT mềm: mọi tư thế"),
            (heavy, "CT nặng: khối đứng"),
            (split, "CT tách khối"),
        )
        x = 0.0
        for draw, label in items:
            draw(x + 0.014)
            text = self._text(row, label, (x + 0.034, 0), scale=0.72, tint=INK)
            x += 0.034 + text.width + 0.026
        note = self._text(row, "Cầu và công tắc cùng màu đi với nhau", (x, 0),
                          scale=0.68, tint=MUTED)
        self._legend_width = x + note.width
        row.x = -self._legend_width / 2
        self._panel(self.legend, self._legend_width + 0.04, 0.044, alpha=170, edge_alpha=35)

    # -- solver panel ---------------------------------------------------------------

    def _build_solver_panel(self) -> None:
        width, height = 0.44, 0.68
        self._solver_size = (width, height)
        # solver_panel and solver_controls keep their 4.3 names; both toggle together.
        self.solver_panel = Entity(parent=camera.ui, enabled=False)
        self.solver_controls = self.solver_panel
        self._panel(self.solver_panel, width, height, alpha=235, edge=VIOLET, edge_alpha=110)
        left = -width / 2 + 0.025
        right = width / 2 - 0.025
        y = height / 2 - 0.040

        self._text(self.solver_panel, "Giải tự động", (left, y), scale=1.2)
        self._text(self.solver_panel, "giới hạn 60 s", (right, y), scale=0.72,
                   tint=MUTED, origin=(0.5, 0))

        y -= 0.052
        self.solver_buttons: dict[str, Any] = {}
        labels = (("bfs", "BFS"), ("dfs", "DFS"), ("ucs", "UCS"), ("astar", "A*"))
        btn_w = 0.088
        step = (right - left - btn_w) / 3
        for index, (name, label) in enumerate(labels):
            button = self._button(
                self.solver_panel, label, (left + btn_w / 2 + step * index, y),
                (btn_w, 0.045), SLATE_LIGHT,
                lambda algorithm=name: self.start_solver(algorithm), text_size=0.9,
            )
            button.enabled = name in ALGORITHMS
            self.solver_buttons[name] = button

        y -= 0.052
        self.solver_status_text = self._text(self.solver_panel, "Sẵn sàng: chọn một thuật toán",
                                             (left, y), scale=0.88, tint=ACCENT)
        self.cancel_button = self._button(
            self.solver_panel, "Hủy", (right - 0.045, y), (0.09, 0.036), DANGER,
            self.cancel_solver, text_size=0.78,
        )
        self.cancel_button.enabled = False

        # Headless compatibility text entity (hidden visually to prevent overlapping)
        self.solver_text = Text(parent=self.solver_panel, enabled=False)

        y -= 0.046
        self.metric_label_texts: list[Any] = []
        self.metric_value_texts: list[Any] = []
        for index, (label, value) in enumerate(self._empty_metrics()):
            row_y = y - index * 0.038
            if index % 2 == 0:
                Entity(parent=self.solver_panel, model=Quad(radius=0.25, aspect=(width - 0.03) / 0.034),
                       scale=(width - 0.03, 0.034), position=(0, row_y, 0.005),
                       color=_rgba("#ffffff", 10))
            self.metric_label_texts.append(
                self._text(self.solver_panel, label, (left, row_y), scale=0.82, tint=MUTED)
            )
            self.metric_value_texts.append(
                self._text(self.solver_panel, value, (right, row_y), scale=0.88,
                           origin=(0.5, 0))
            )
        y -= 6 * 0.038 + 0.012
        self._text(self.solver_panel, "Chi phí: 1 mỗi nước, +4 khi đè ô F",
                   (left, y), scale=0.68, tint=MUTED)
        self._text(self.solver_panel, "Bộ nhớ: KiB Python (tracemalloc)",
                   (left, y - 0.024), scale=0.68, tint=MUTED)

        y -= 0.065
        self._text(self.solver_panel, "Phát lại", (left, y), scale=0.82, tint=MUTED)
        self.pause_button = self._button(self.solver_panel, "Pause", (left + 0.14, y),
                                         (0.08, 0.038), SLATE_LIGHT, self.controller.pause,
                                         text_size=0.78)
        self.step_button = self._button(self.solver_panel, "Step", (left + 0.23, y),
                                        (0.08, 0.038), SLATE_LIGHT, self.controller.step_once,
                                        text_size=0.78)
        self.resume_button = self._button(self.solver_panel, "Resume", (left + 0.32, y),
                                          (0.08, 0.038), SLATE_LIGHT, self.controller.resume,
                                          text_size=0.78)

        y -= 0.052
        self._text(self.solver_panel, "Tốc độ", (left, y), scale=0.82, tint=MUTED)
        self.speed_buttons: dict[int, Any] = {}
        for index, multiplier in enumerate((1, 2, 4)):
            self.speed_buttons[multiplier] = self._button(
                self.solver_panel, f"{multiplier}×", (left + 0.14 + index * 0.09, y),
                (0.08, 0.038), SLATE_LIGHT,
                lambda speed=multiplier: self.set_replay_speed(speed), text_size=0.82,
            )
        self.set_replay_speed(1)

    @staticmethod
    def _empty_metrics() -> list[tuple[str, str]]:
        labels = ("Trạng thái", "Số nước", "Chi phí", "Nút mở rộng", "Thời gian", "Bộ nhớ đỉnh")
        return [(label, NOT_AVAILABLE) for label in labels]

    def _show_metrics(self, rows: list[tuple[str, str]]) -> None:
        for text, (_, value) in zip(self.metric_value_texts, rows):
            text.text = value
            if color:
                text.color = _rgba(MUTED if value == NOT_AVAILABLE else INK)

    def set_replay_speed(self, multiplier: int) -> None:
        self.controller.set_speed(multiplier)
        for speed, button in self.speed_buttons.items():
            self._paint(button, VIOLET if speed == multiplier else SLATE_LIGHT)

    def toggle_solver_panel(self) -> None:
        visible = not self.solver_panel.enabled
        self.solver_panel.enabled = visible
        self.solver_controls.enabled = visible
        if visible:
            self.close_menu()

    def close_solver_panel(self) -> None:
        self.solver_panel.enabled = False
        self.solver_controls.enabled = False

    def start_solver(self, algorithm: str) -> None:
        if algorithm not in ALGORITHMS:
            return
        stage = self.controller.stage
        if stage is None or self.runner.running:
            return
        self.selected_algorithm = algorithm
        for name, button in self.solver_buttons.items():
            self._paint(button, VIOLET if name == algorithm else SLATE_LIGHT)
        self.runner.cancel()
        self.controller.restart()
        self._replay_algorithm = None
        self.controller.status = "solving"
        self.runner.start(algorithm, stage)
        self._cancel_requested = False
        self._active_algorithm = algorithm
        self._result_handled = False
        label = ALGO_LABELS.get(algorithm, algorithm.upper())
        if hasattr(self, "solver_status_text"):
            self.solver_status_text.text = f"Đang giải {label}..."
            if color:
                self.solver_status_text.color = _rgba(ACCENT)
        if hasattr(self, "solver_text"):
            self.solver_text.text = f"Solving {algorithm.upper()}..."
        self._show_metrics(self._empty_metrics())
        self.cancel_button.enabled = True
        for button in self.solver_buttons.values():
            button.disabled = True

    def cancel_solver(self) -> None:
        if self._result_handled or self._cancel_requested:
            return
        self.runner.cancel()
        self._cancel_requested = True
        if hasattr(self, "clear_solver_highlight"):
            self.clear_solver_highlight()
        if hasattr(self, "solver_status_text"):
            self.solver_status_text.text = "Đang hủy..."
            if color:
                self.solver_status_text.color = _rgba(WARNING)
        if hasattr(self, "solver_text"):
            self.solver_text.text = "Cancelling..."

    def reset_solver_action(self) -> None:
        self.cancel_button.enabled = False
        for name, button in self.solver_buttons.items():
            button.enabled = name in ALGORITHMS
            button.disabled = False

    def clear_solver_highlight(self) -> None:
        """Un-mark the last chosen algorithm button (back to the neutral colour)."""
        self.selected_algorithm = None
        for button in getattr(self, "solver_buttons", {}).values():
            self._paint(button, SLATE_LIGHT)

    def _abort_solver(self, message: str) -> None:
        """Drop a running search so its late result never touches the new game."""
        if not self._result_handled:
            if hasattr(self, "solver_status_text"):
                self.solver_status_text.text = message
            if hasattr(self, "solver_text"):
                self.solver_text.text = message
        self.runner.cancel()
        self._result_handled = True
        self._replay_algorithm = None

    def restart(self) -> None:
        self._abort_solver("Đã hủy vì chơi lại màn")
        self.controller.restart()
        self.reset_solver_action()
        if hasattr(self, "clear_solver_highlight"):
            self.clear_solver_highlight()

    # -- win / lose screen -----------------------------------------------------------

    def _build_end_screen(self) -> None:
        self.end_screen = Entity(parent=camera.ui, z=-0.5, enabled=False)
        self.end_dim = Entity(parent=self.end_screen, model="quad", scale=(4, 1),
                              color=_rgba("#000000", 120), z=0.05)
        self.end_card = self._panel(self.end_screen, 0.74, 0.34, alpha=235,
                                    edge=SUCCESS, edge_alpha=200, radius=0.1)
        self.end_card.z = 0
        self.end_title = self._text(self.end_card, "", (0, 0.085, -0.01), scale=3.2,
                                    origin=(0, 0))
        self.end_subtitle = self._text(self.end_card, "", (0, 0.005, -0.01), scale=1.0,
                                       tint=INK, origin=(0, 0))
        self.end_restart_button = self._button(
            self.end_card, "Chơi lại (R)", (-0.13, -0.09, -0.01), (0.23, 0.062),
            "#0e7490", self.restart, text_size=1.0,
        )
        self.end_menu_button = self._button(
            self.end_card, "Chọn màn khác (N)", (0.13, -0.09, -0.01), (0.23, 0.062),
            "#1e3a5f", self.open_menu, text_size=1.0,
        )

    def _show_end_screen(self, status: str) -> None:
        title, subtitle = end_screen_text(
            status, self.controller.moves, getattr(self.controller, "fail_reason", ""),
            self._replay_algorithm,
        )
        tint = SUCCESS if status == "won" else (WARNING if status == "error" else DANGER)
        self.end_title.text = title
        self.end_title.color = _rgba(tint)
        self.end_subtitle.text = subtitle
        rim = self.end_card.children[0]
        rim.color = _rgba(tint, 200)
        self.end_screen.enabled = True
        self.end_card.scale = 0.85
        self.end_card.animate_scale(1, duration=0.25, curve=curve.out_back)

    # -- level menu ------------------------------------------------------------

    def _build_menu(self) -> None:
        """Modal with group tabs, a one-line group description and a paged stage grid."""
        self.menu_panel = Entity(parent=camera.ui, z=-0.6, enabled=False)
        Entity(parent=self.menu_panel, model="quad", scale=(4, 1),
               color=_rgba("#000000", 140), z=0.06)
        self.menu_bg = self._panel(self.menu_panel, 1.24, 0.86, alpha=240,
                                   edge=EDGE, edge_alpha=90, radius=0.06)

        self._text(self.menu_panel, "CHỌN MÀN CHƠI", (0, 0.375), scale=1.7,
                   tint=ACCENT, origin=(0, 0))
        self._button(self.menu_panel, "Đóng (Esc)", (0.5, 0.375), (0.15, 0.042),
                     DANGER, self.close_menu, text_size=0.75)

        tabs = ("G1", "G2", "G3", "G4", "G5", "ALL")
        self.tab_buttons: dict[str, Any] = {}
        spacing = 0.19
        start_x = -((len(tabs) - 1) * spacing) / 2
        for index, key in enumerate(tabs):
            count = len(self._stages_for(key))
            name = TAB_NAMES[key] if key == "ALL" else f"{key} · {TAB_NAMES[key]}"
            self.tab_buttons[key] = self._button(
                self.menu_panel, f"{name} ({count})", (start_x + index * spacing, 0.3),
                (0.18, 0.046), SLATE, lambda k=key: self.switch_tab(k), text_size=0.72,
            )

        self.group_desc_text = self._text(self.menu_panel, "", (0, 0.245), scale=0.9,
                                          tint=INK, origin=(0, 0))
        self.grid_container = Entity(parent=self.menu_panel)

        self.previous_page_button = self._button(
            self.menu_panel, "Trước", (-0.16, -0.335), (0.12, 0.042), SLATE, self.previous_page
        )
        self.next_page_button = self._button(
            self.menu_panel, "Sau", (0.16, -0.335), (0.12, 0.042), SLATE, self.next_page
        )
        self.page_text = self._text(self.menu_panel, "", (0, -0.335), scale=0.85,
                                    tint=MUTED, origin=(0, 0))

        x = -0.56
        for source in ("fixture", "original", "bench"):
            fill, label = SOURCE_STYLE[source]
            Entity(parent=self.menu_panel, model=Quad(radius=0.25), scale=0.022,
                   position=(x, -0.39), color=_rgba(fill).tint(0.25))
            text = self._text(self.menu_panel, label, (x + 0.02, -0.39), scale=0.72, tint=MUTED)
            x += 0.05 + text.width
        self._text(self.menu_panel, "stage_30 không có trong danh sách (dữ liệu nguồn lỗi)",
                   (0.58, -0.39), scale=0.68, tint=MUTED, origin=(0.5, 0))
        self.render_stage_grid()

    def _stages_for(self, tab_key: str) -> list[Stage]:
        if tab_key == "ALL":
            return self.stages
        return [s for s in self.stages if s.group == tab_key]

    def switch_tab(self, tab_key: str) -> None:
        """Switch active group tab and rebuild grid."""
        if tab_key not in self.tab_buttons:
            return
        self.current_tab = tab_key
        self.current_page = 0
        for key, button in self.tab_buttons.items():
            self._paint(button, GROUP_COLORS[key] if key == tab_key else SLATE)
            if button.text_entity:
                text_tint = _rgba(PANEL if key == tab_key else INK)
                button.text_color = text_tint
                button.highlight_text_color = text_tint
        self.render_stage_grid()

    def render_stage_grid(self) -> None:
        """Render level buttons for current tab."""
        for button in self.grid_buttons:
            if destroy:
                destroy(button)
        self.grid_buttons.clear()

        active_stages = self._stages_for(self.current_tab)
        self.group_desc_text.text = f"{group_caption(self.current_tab)}  ·  {len(active_stages)} màn"
        self.group_desc_text.color = _rgba(GROUP_COLORS.get(self.current_tab, INK))

        page_count = max(1, (len(active_stages) + self.page_size - 1) // self.page_size)
        self.current_page = min(self.current_page, page_count - 1)
        start = self.current_page * self.page_size
        visible_stages = active_stages[start : start + self.page_size]

        cols = 5
        spacing_x, spacing_y = 0.225, 0.07
        start_x = -((cols - 1) * spacing_x) / 2
        start_y = 0.175
        current_id = self.controller.stage.id if self.controller.stage else None

        for index, stage in enumerate(visible_stages):
            x = start_x + (index % cols) * spacing_x
            y = start_y - (index // cols) * spacing_y
            fill = SOURCE_STYLE[stage_source(stage.id)][0]
            if stage.id == current_id:
                fill = "#0e7490"
            button = self._button(
                self.grid_container, format_stage_title(stage.id, menu=True), (x, y), (0.21, 0.056),
                fill, lambda s=stage: self.select_stage(s), text_size=0.82, radius=0.25,
            )
            self.grid_buttons.append(button)

        can_go_back = self.current_page > 0
        can_go_forward = self.current_page + 1 < page_count
        self._paint(self.previous_page_button, SLATE_LIGHT if can_go_back else DISABLED)
        self._paint(self.next_page_button, SLATE_LIGHT if can_go_forward else DISABLED)
        self.previous_page_button.disabled = not can_go_back
        self.next_page_button.disabled = not can_go_forward
        self.page_text.text = f"Trang {self.current_page + 1} / {page_count}"

    def previous_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.render_stage_grid()

    def next_page(self) -> None:
        active_count = len(self._stages_for(self.current_tab))
        page_count = max(1, (active_count + self.page_size - 1) // self.page_size)
        if self.current_page + 1 < page_count:
            self.current_page += 1
            self.render_stage_grid()

    def select_stage(self, stage: Stage) -> None:
        """Load chosen stage and dismiss the level select menu."""
        self._abort_solver("Sẵn sàng: chọn một thuật toán")
        if hasattr(self, "solver_status_text"):
            self.solver_status_text.text = "Sẵn sàng: chọn một thuật toán"
            if color:
                self.solver_status_text.color = _rgba(ACCENT)
        if hasattr(self, "solver_text"):
            self.solver_text.text = "Sẵn sàng: chọn một thuật toán"
        self._show_metrics(self._empty_metrics())
        self.controller.load(stage)
        self.reset_solver_action()
        if hasattr(self, "clear_solver_highlight"):
            self.clear_solver_highlight()
        self.close_menu()

    def toggle_menu(self) -> None:
        """Toggle level select modal visibility."""
        if self.menu_panel.enabled:
            self.close_menu()
        else:
            self.open_menu()

    def open_menu(self) -> None:
        self.menu_panel.enabled = True
        self.close_solver_panel()
        stage = self.controller.stage
        tab = stage.group if stage is not None and stage.group in self.tab_buttons else self.current_tab
        self.switch_tab(tab)
        page = next((i // self.page_size for i, s in enumerate(self._stages_for(tab))
                     if stage is not None and s.id == stage.id), 0)
        if page != self.current_page:
            self.current_page = page
            self.render_stage_grid()

    def close_menu(self) -> None:
        self.menu_panel.enabled = False

    # -- layout and per-frame refresh -----------------------------------------------

    def _layout_ui(self) -> None:
        if window is None:
            return
        half_width = window.aspect_ratio / 2
        left_x = -half_width + EDGE_GAP
        right_x = half_width - EDGE_GAP

        self.hud.position = (left_x, TOP_Y)

        width, gap = 0.17, 0.012
        self.btn_restart.position = (right_x - width / 2, TOP_Y)
        self.btn_new_game.position = (right_x - width * 1.5 - gap, TOP_Y)
        self.btn_solver_panel.position = (right_x - width * 2.5 - gap * 2, TOP_Y)

        self.key_guide.position = (right_x - 0.018 - self._key_guide_width, TOP_Y - 0.065)
        self.legend.position = (0, -0.5 + 0.03)

        solver_w, solver_h = self._solver_size
        self.solver_panel.position = (right_x - solver_w / 2, TOP_Y - 0.115 - solver_h / 2)
        self._layout_aspect = window.aspect_ratio

    def _live_status(self) -> tuple[str, str]:
        """Text and color of the status line next to the moves counter."""
        controller = self.controller
        if controller is None:
            return "", MUTED
        status = getattr(controller, "status", "playing")
        if status == "solving":
            label = ALGO_LABELS.get(self._active_algorithm, "")
            return f"Đang tìm lời giải {label}...", VIOLET
        if getattr(controller, "replaying", False):
            label = ALGO_LABELS.get(self._replay_algorithm, "")
            paused = " · tạm dừng" if getattr(controller, "paused", False) else ""
            speed = getattr(controller, "speed", 1)
            return f"Phát lại lời giải {label} · {speed}×{paused}", VIOLET
        state = getattr(controller, "state", None)
        if status == "playing" and state is not None and getattr(state, "pose", None) is None:
            selected_pos = getattr(controller, "selected_pos", None)
            index = 1 if selected_pos in (None, getattr(state, "pos", None)) else 2
            return f"Đang điều khiển cube {index}/2 · Space để đổi", WARNING
        if status == "won":
            return "Hoàn thành!", SUCCESS
        if status in ("lost", "error"):
            return "Bấm R để chơi lại", DANGER
        return "", MUTED

    def _refresh_hud(self) -> None:
        if not hasattr(self, "controller") or self.controller is None:
            return
        stage = getattr(self.controller, "stage", None)
        if stage is not None and hasattr(self, "title_text"):
            group = stage.group
            self.title_text.text = format_stage_title(stage.id, max_len=22, menu=True)
            if hasattr(self, "group_chip_text"):
                self.group_chip_text.text = group
            if hasattr(self, "group_chip") and self.group_chip:
                self.group_chip.color = _rgba(GROUP_COLORS.get(group, MUTED))
            name = GROUP_INFO.get(group, (group, ""))[0]
            if hasattr(self, "subtitle_text"):
                self.subtitle_text.text = f"Nhóm {name} · {stage.rows}×{stage.cols} ô · mã {stage.id}"
        if hasattr(self, "info_text"):
            moves = getattr(self.controller, "moves", 0)
            self.info_text.text = f"Bước {moves}"
        text, tint = self._live_status()
        if hasattr(self, "status_text"):
            self.status_text.text = text
            if color:
                self.status_text.color = _rgba(tint)

        status = getattr(self.controller, "status", "playing")
        menu_open = getattr(self, "menu_panel", None) is not None and getattr(self.menu_panel, "enabled", False)
        show_end = status in ("won", "lost", "error") and not menu_open
        end_screen = getattr(self, "end_screen", None)
        if show_end and getattr(self, "_end_status", None) != status:
            if hasattr(self, "_show_end_screen"):
                self._show_end_screen(status)
        elif not show_end and end_screen is not None and getattr(end_screen, "enabled", False):
            end_screen.enabled = False
        self._end_status = status if show_end else None

    def update(self) -> None:
        """Poll the solver, sync buttons and refresh the HUD every frame."""
        if window is not None and window.aspect_ratio != self._layout_aspect:
            self._layout_ui()

        result = self.runner.poll()
        if result is not None and not self._result_handled:
            self._result_handled = True
            cancelled = self._cancel_requested
            rows = solver_metric_rows(result, cancelled)
            if hasattr(self, "solver_text"):
                self.solver_text.text = format_solver_result(result, cancelled)
            if hasattr(self, "solver_status_text"):
                if cancelled:
                    self.solver_status_text.text = "Đã hủy tìm kiếm"
                    if color:
                        self.solver_status_text.color = _rgba(WARNING)
                elif result.status == "solved":
                    label = ALGO_LABELS.get(self._active_algorithm, "")
                    self.solver_status_text.text = f"Đã giải thành công ({label})!"
                    if color:
                        self.solver_status_text.color = _rgba(SUCCESS)
                elif result.status == "unsolvable":
                    self.solver_status_text.text = "Không tìm thấy lời giải"
                    if color:
                        self.solver_status_text.color = _rgba(WARNING)
                else:
                    self.solver_status_text.text = f"Kết thúc: {result.status}"
                    if color:
                        self.solver_status_text.color = _rgba(DANGER)
            if hasattr(self, "metric_value_texts"):
                self._show_metrics(rows)
            if result.status == "solved" and not cancelled:
                self._replay_algorithm = self._active_algorithm
                self.controller.start_replay(result.actions)
            else:
                self.controller.status = "playing"
            if hasattr(self, "reset_solver_action"):
                self.reset_solver_action()
            if not (result.status == "solved" and not cancelled):
                if hasattr(self, "clear_solver_highlight"):
                    self.clear_solver_highlight()
        elif not self._result_handled and self.runner.running:
            if hasattr(self, "solver_text"):
                self.solver_text.text = "Cancelling..." if self._cancel_requested else f"Solving {self._active_algorithm}..."
            if hasattr(self, "solver_status_text"):
                if self._cancel_requested:
                    self.solver_status_text.text = "Đang hủy tìm kiếm..."
                    if color:
                        self.solver_status_text.color = _rgba(WARNING)
                else:
                    label = ALGO_LABELS.get(self._active_algorithm, "")
                    self.solver_status_text.text = f"Đang giải {label}... {self.runner.elapsed_s:.1f} s"
                    if color:
                        self.solver_status_text.color = _rgba(ACCENT)

        if hasattr(self, "cancel_button"):
            self.cancel_button.enabled = not self._result_handled
        if hasattr(self, "pause_button"):
            self.pause_button.enabled = self.controller.replaying and not self.controller.paused
        if hasattr(self, "step_button"):
            self.step_button.enabled = self.controller.replaying and self.controller.paused
        if hasattr(self, "resume_button"):
            self.resume_button.enabled = self.controller.replaying and self.controller.paused
        self._refresh_hud()
