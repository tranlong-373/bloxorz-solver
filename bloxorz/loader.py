"""Read a stage JSON file, validate it, return a Stage. Owner: VT4 (task 4.1)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bloxorz.model import Pos
from bloxorz.stage import Bridge, Stage, Switch

VALID_GROUPS = {"G1", "G2", "G3", "G4", "G5"}
VALID_CELLS = {"#", ".", "F", "G", "S", "B"}
VALID_KINDS = {"soft", "heavy", "split"}
VALID_MODES = {"toggle", "permanent"}
VALID_SET_TO = {"open", "close"}
MAX_ROWS = 12
MAX_COLS = 20

ALLOWED_STAGE_FIELDS = {"id", "group", "grid", "bridges", "switches", "source", "note"}
ALLOWED_BRIDGE_FIELDS = {"id", "cells", "initially_open"}
ALLOWED_SWITCH_FIELDS = {"id", "kind", "pos", "mode", "set_to", "bridges", "targets"}


class LevelError(ValueError):
    """Raised when a stage JSON file fails syntax or validation checks."""

    def __init__(self, errors: list[str] | str):
        if isinstance(errors, str):
            errors = [errors]
        self.errors = errors
        super().__init__("\n".join(errors))


def _fmt_err(path: str | Path, msg: str, pos: Pos | None = None) -> str:
    p_str = Path(path).as_posix()
    # Errors that are not tied to one cell use (0, 0) so every message has the same format
    if pos is None:
        pos = (0, 0)
    return f"{p_str}: hàng {pos[0]}, cột {pos[1]}: {msg}"


def _is_valid_pos(p: Any) -> bool:
    return (
        isinstance(p, (list, tuple))
        and len(p) == 2
        and isinstance(p[0], int)
        and not isinstance(p[0], bool)
        and isinstance(p[1], int)
        and not isinstance(p[1], bool)
    )


def validate(raw: Any, path: str | Path = "<stage>") -> list[str]:
    """Validate parsed JSON data of a stage and return a list of error strings."""
    errors: list[str] = []
    if not isinstance(raw, dict):
        errors.append(_fmt_err(path, "Dữ liệu JSON gốc phải là một object (dict)"))
        return errors

    for k in sorted(raw.keys()):
        if k not in ALLOWED_STAGE_FIELDS:
            errors.append(_fmt_err(path, f"Trường lạ không hợp lệ ở cấp màn: {k!r}"))

    # Check id and group
    stage_id = raw.get("id")
    if not isinstance(stage_id, str) or not stage_id.strip():
        errors.append(_fmt_err(path, "Thiếu hoặc sai kiểu trường 'id'"))
    else:
        stem = Path(path).stem
        if stem not in ("<stage>", "") and stage_id != stem:
            errors.append(_fmt_err(path, f"id '{stage_id}' không trùng tên file '{stem}'"))

    group = raw.get("group")
    if not isinstance(group, str) or group not in VALID_GROUPS:
        errors.append(_fmt_err(path, f"Trường 'group' ({group!r}) phải thuộc {sorted(VALID_GROUPS)}"))

    # Check grid format
    grid = raw.get("grid")
    if (
        not isinstance(grid, list)
        or not grid
        or not all(isinstance(r, str) and len(r) > 0 for r in grid)
    ):
        errors.append(_fmt_err(path, "Trường 'grid' phải là danh sách các chuỗi không rỗng"))
        return errors

    rows = len(grid)
    cols = len(grid[0])

    # Check that all rows have the same length
    for r, row_str in enumerate(grid):
        if len(row_str) != cols:
            errors.append(
                _fmt_err(
                    path,
                    f"Các hàng trong grid dài khác nhau (hàng 0 dài {cols}, hàng {r} dài {len(row_str)})",
                    (r, 0),
                )
            )

    # Check grid dimension limits
    if rows > MAX_ROWS or cols > MAX_COLS:
        errors.append(
            _fmt_err(
                path,
                f"Kích thước lưới {rows}x{cols} vượt quá giới hạn {MAX_ROWS} hàng x {MAX_COLS} cột",
                (0, 0),
            )
        )

    # Scan grid tiles and find start, goal, bridge positions
    s_positions: list[Pos] = []
    g_positions: list[Pos] = []
    grid_b_cells: set[Pos] = set()

    for r, row_str in enumerate(grid):
        for c, ch in enumerate(row_str):
            if ch not in VALID_CELLS:
                errors.append(_fmt_err(path, f"Ký tự lạ trong grid: '{ch}'", (r, c)))
            elif ch == "S":
                s_positions.append((r, c))
            elif ch == "G":
                g_positions.append((r, c))
            elif ch == "B":
                grid_b_cells.add((r, c))

    # Check goal tile
    if len(g_positions) == 0:
        errors.append(_fmt_err(path, "Không có ô đích G trong grid", (0, 0)))
    elif len(g_positions) >= 2:
        errors.append(_fmt_err(path, f"Có từ 2 G trở lên ({len(g_positions)} ô G)", g_positions[1]))

    # Check start tile
    if len(s_positions) == 0:
        errors.append(_fmt_err(path, "Không có ô xuất phát S trong grid", (0, 0)))
    elif len(s_positions) >= 2:
        errors.append(_fmt_err(path, f"Có từ 2 S trở lên ({len(s_positions)} ô S)", s_positions[1]))

    def in_bounds(p: Pos) -> bool:
        return 0 <= p[0] < rows and len(grid[p[0]]) > p[1] >= 0

    def cell_at(p: Pos) -> str:
        return grid[p[0]][p[1]]

    seen_ids: set[str] = set()
    bridge_ids: set[str] = set()
    declared_b_cells: set[Pos] = set()

    # Validate bridges
    bridges_raw = raw.get("bridges", [])
    if not isinstance(bridges_raw, list):
        errors.append(_fmt_err(path, "Trường 'bridges' phải là một list"))
        bridges_raw = []

    for b in bridges_raw:
        if not isinstance(b, dict):
            errors.append(_fmt_err(path, "Phần tử trong 'bridges' phải là object"))
            continue

        b_id = b.get("id")
        cells = b.get("cells")
        first_pos: Pos = (
            (int(cells[0][0]), int(cells[0][1]))
            if isinstance(cells, list) and cells and _is_valid_pos(cells[0])
            else (0, 0)
        )

        for k in sorted(b.keys()):
            if k not in ALLOWED_BRIDGE_FIELDS:
                errors.append(_fmt_err(path, f"Cầu '{b_id}' có trường lạ không hợp lệ: {k!r}", first_pos))

        if not isinstance(b_id, str) or not b_id.strip():
            errors.append(_fmt_err(path, "Cầu thiếu trường 'id' hợp lệ", first_pos))
        else:
            if b_id in seen_ids:
                errors.append(_fmt_err(path, f"id '{b_id}' bị trùng", first_pos))
            seen_ids.add(b_id)
            bridge_ids.add(b_id)

        if "initially_open" in b and not isinstance(b["initially_open"], bool):
            errors.append(_fmt_err(path, f"Cầu '{b_id}' có 'initially_open' không phải boolean", first_pos))

        if not isinstance(cells, list) or not cells:
            errors.append(_fmt_err(path, f"Cầu '{b_id}' thiếu danh sách 'cells'", first_pos))
            continue

        for cell in cells:
            if not _is_valid_pos(cell):
                errors.append(_fmt_err(path, f"Cầu '{b_id}' có tọa độ ô không hợp lệ: {cell!r}", first_pos))
                continue
            pos: Pos = (cell[0], cell[1])
            if not in_bounds(pos):
                errors.append(_fmt_err(path, f"Ô trong cầu '{b_id}' nằm ngoài bàn", pos))
            else:
                if cell_at(pos) != "B":
                    errors.append(
                        _fmt_err(
                            path,
                            f"Ô trong bridges ('{b_id}') không phải B trên grid (đang là '{cell_at(pos)}')",
                            pos,
                        )
                    )
                if pos in declared_b_cells:
                    errors.append(_fmt_err(path, f"Ô cầu {pos} bị khai báo nhiều lần trong bridges", pos))
                declared_b_cells.add(pos)

    # Check unreferenced B cells on the grid
    for b_pos in sorted(grid_b_cells - declared_b_cells):
        errors.append(_fmt_err(path, "Ô B trên grid không thuộc cầu nào trong bridges", b_pos))

    # Validate switches
    switches_raw = raw.get("switches", [])
    if not isinstance(switches_raw, list):
        errors.append(_fmt_err(path, "Trường 'switches' phải là một list"))
        switches_raw = []

    seen_switch_pos: set[Pos] = set()

    for sw in switches_raw:
        if not isinstance(sw, dict):
            errors.append(_fmt_err(path, "Phần tử trong 'switches' phải là object"))
            continue

        sw_id = sw.get("id")
        raw_pos = sw.get("pos")
        sw_pos: Pos = (raw_pos[0], raw_pos[1]) if _is_valid_pos(raw_pos) else (0, 0)

        for k in sorted(sw.keys()):
            if k not in ALLOWED_SWITCH_FIELDS:
                errors.append(_fmt_err(path, f"Công tắc '{sw_id}' có trường lạ không hợp lệ: {k!r}", sw_pos))

        if not isinstance(sw_id, str) or not sw_id.strip():
            errors.append(_fmt_err(path, "Công tắc thiếu trường 'id' hợp lệ", sw_pos))
        else:
            if sw_id in seen_ids:
                errors.append(_fmt_err(path, f"id '{sw_id}' bị trùng", sw_pos))
            seen_ids.add(sw_id)

        if not _is_valid_pos(raw_pos):
            errors.append(_fmt_err(path, f"Công tắc '{sw_id}' có 'pos' không hợp lệ", (0, 0)))
        else:
            if not in_bounds(sw_pos):
                errors.append(_fmt_err(path, f"Công tắc '{sw_id}' nằm ngoài bàn (không nằm trên ô #)", sw_pos))
            elif cell_at(sw_pos) != "#":
                errors.append(
                    _fmt_err(
                        path,
                        f"Công tắc '{sw_id}' không nằm trên ô # (đang đặt trên '{cell_at(sw_pos)}')",
                        sw_pos,
                    )
                )
            if sw_pos in seen_switch_pos:
                errors.append(_fmt_err(path, f"Có nhiều công tắc đặt cùng vị trí {sw_pos}", sw_pos))
            seen_switch_pos.add(sw_pos)

        # Validate switch fields by kind
        kind = sw.get("kind")
        if not isinstance(kind, str) or kind not in VALID_KINDS:
            errors.append(
                _fmt_err(
                    path,
                    f"Công tắc '{sw_id}' có kind={kind!r} không hợp lệ (phải thuộc {sorted(VALID_KINDS)})",
                    sw_pos,
                )
            )
            continue

        # set_to is only allowed when mode is "permanent" (missing means "open")
        if "set_to" in sw:
            set_to = sw["set_to"]
            if sw.get("mode") != "permanent":
                errors.append(
                    _fmt_err(path, f"Công tắc '{sw_id}' chỉ được ghi 'set_to' khi mode là 'permanent'", sw_pos)
                )
            elif not isinstance(set_to, str) or set_to not in VALID_SET_TO:
                errors.append(
                    _fmt_err(
                        path,
                        f"Công tắc '{sw_id}' có set_to={set_to!r} không thuộc {sorted(VALID_SET_TO)}",
                        sw_pos,
                    )
                )

        if kind in ("soft", "heavy"):
            if "targets" in sw:
                errors.append(
                    _fmt_err(path, f"Công tắc {kind} '{sw_id}' không được khai báo 'targets'", sw_pos)
                )

            mode = sw.get("mode")
            if mode is None:
                errors.append(_fmt_err(path, f"Công tắc {kind} '{sw_id}' thiếu trường 'mode'", sw_pos))
            elif not isinstance(mode, str) or mode not in VALID_MODES:
                errors.append(
                    _fmt_err(
                        path,
                        f"Công tắc '{sw_id}' có mode={mode!r} không thuộc {sorted(VALID_MODES)}",
                        sw_pos,
                    )
                )

            sw_bridges = sw.get("bridges")
            if (
                not isinstance(sw_bridges, list)
                or len(sw_bridges) == 0
                or not all(isinstance(x, str) for x in sw_bridges)
            ):
                errors.append(_fmt_err(path, f"Công tắc {kind} '{sw_id}' thiếu trường 'bridges' hợp lệ", sw_pos))
            else:
                for ref_b in sw_bridges:
                    if ref_b not in bridge_ids:
                        errors.append(
                            _fmt_err(
                                path,
                                f"Công tắc '{sw_id}' trỏ tới id cầu không tồn tại: '{ref_b}'",
                                sw_pos,
                            )
                        )

        elif kind == "split":
            # split must not declare mode or bridges at all, even as null or []
            if "mode" in sw or "bridges" in sw:
                errors.append(
                    _fmt_err(path, f"Công tắc split '{sw_id}' không được khai báo 'mode' hoặc 'bridges'", sw_pos)
                )

            targets = sw.get("targets")
            if not isinstance(targets, list) or len(targets) != 2:
                errors.append(_fmt_err(path, f"Công tắc split '{sw_id}' thiếu trường 'targets' gồm đúng 2 vị trí", sw_pos))
                continue

            if not (_is_valid_pos(targets[0]) and _is_valid_pos(targets[1])):
                errors.append(_fmt_err(path, f"Công tắc split '{sw_id}' có tọa độ targets sai định dạng", sw_pos))
                continue

            t1: Pos = (targets[0][0], targets[0][1])
            t2: Pos = (targets[1][0], targets[1][1])

            # Check split targets are valid tiles and not adjacent
            for idx, t in enumerate((t1, t2), start=1):
                if not in_bounds(t):
                    errors.append(_fmt_err(path, f"Công tắc split '{sw_id}' có target {idx} nằm ngoài bàn", t))
                elif cell_at(t) != "#":
                    errors.append(
                        _fmt_err(
                            path,
                            f"Công tắc split '{sw_id}' có target {idx} không phải ô # (đang là '{cell_at(t)}')",
                            t,
                        )
                    )

            if t1 == t2:
                errors.append(_fmt_err(path, f"Công tắc split '{sw_id}' có 2 targets trùng nhau", t1))
            elif abs(t1[0] - t2[0]) + abs(t1[1] - t2[1]) == 1:
                errors.append(_fmt_err(path, f"Công tắc split '{sw_id}' có 2 targets kề nhau ({t1} và {t2})", t1))

    return errors


def load_stage(path: str | Path) -> Stage:
    """Read a stage JSON file, validate it, and return an immutable Stage."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise LevelError(_fmt_err(file_path, f"Không thể đọc file: {exc}")) from exc

    # Parse JSON and catch syntax errors
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LevelError(
            _fmt_err(file_path, f"JSON sai cú pháp tại dòng {exc.lineno}: {exc.msg}", (exc.lineno, exc.colno))
        ) from exc

    errors = validate(raw, file_path)
    if errors:
        raise LevelError(errors)

    start_pos: Pos = (0, 0)
    goal_pos: Pos = (0, 0)
    clean_grid: list[str] = []

    for r, row_str in enumerate(raw["grid"]):
        if "S" in row_str:
            start_pos = (r, row_str.index("S"))
        if "G" in row_str:
            goal_pos = (r, row_str.index("G"))
        clean_grid.append(row_str.replace("S", "#"))

    bridges = tuple(
        Bridge(
            id=b["id"],
            cells=tuple(( int(c[0]), int(c[1]) ) for c in b["cells"]),
            initially_open=bool(b.get("initially_open", False)),
        )
        for b in raw.get("bridges", [])
    )

    switches_list: list[Switch] = []
    for sw in raw.get("switches", []):
        kind = sw["kind"]
        pos: Pos = (int(sw["pos"][0]), int(sw["pos"][1]))
        if kind in ("soft", "heavy"):
            switches_list.append(
                Switch(
                    id=sw["id"],
                    kind=kind,
                    pos=pos,
                    mode=sw["mode"],
                    set_to=sw.get("set_to", "open"),
                    bridges=tuple(sw["bridges"]),
                    targets=None,
                )
            )
        else:
            t1, t2 = sw["targets"]
            switches_list.append(
                Switch(
                    id=sw["id"],
                    kind="split",
                    pos=pos,
                    mode=None,
                    set_to="open",
                    bridges=(),
                    targets=((int(t1[0]), int(t1[1])), (int(t2[0]), int(t2[1]))),
                )
            )

    return Stage(
        id=raw["id"],
        group=raw["group"],
        grid=tuple(clean_grid),
        start=start_pos,
        goal=goal_pos,
        bridges=bridges,
        switches=tuple(switches_list),
    )


def list_stages(folder: str | Path) -> list[Stage]:
    """Load all .json stages in a folder, sorted by (group, id)."""
    folder_path = Path(folder)
    stages = [load_stage(p) for p in sorted(folder_path.glob("*.json"))]
    stages.sort(key=lambda s: (s.group, s.id))
    return stages