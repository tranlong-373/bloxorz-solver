"""Convert the 33 original stages from quick_bloxorz (CC BY) to the team format. Owner: VT4 (task 4.7)."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


def convert_map(map_data: dict[str, Any], stage_num: int) -> dict[str, Any]:
    # collect all objects and filter playable tiles
    playable_tiles: list[tuple[int, int, str, dict[str, Any]]] = []
    objects_by_id: dict[int, tuple[str, dict[str, Any]]] = {}

    for layer in map_data.get("layers", []):
        if layer.get("type") != "objectgroup":
            continue
        layer_name = layer.get("name", "")
        for obj in layer.get("objects", []):
            objects_by_id[obj["id"]] = (layer_name, obj)
            if layer_name != "border":
                row = obj["y"] // 50
                col = obj["x"] // 50
                playable_tiles.append((row, col, layer_name, obj))

    # compute bounding box for the playable board
    min_row = min(r for r, c, _, _ in playable_tiles)
    max_row = max(r for r, c, _, _ in playable_tiles)
    min_col = min(c for r, c, _, _ in playable_tiles)
    max_col = max(c for r, c, _, _ in playable_tiles)

    total_rows = max_row - min_row + 1
    total_cols = max_col - min_col + 1
    grid_matrix = [["." for _ in range(total_cols)] for _ in range(total_rows)]

    # determine stage group based on mechanics
    has_split = any(name == "splitter" for _, _, name, _ in playable_tiles)
    has_switch_or_bridge = any(name in ("button", "bridge") for _, _, name, _ in playable_tiles)
    has_fragile = any(name == "weak" for _, _, name, _ in playable_tiles)

    if has_split:
        group = "G4"
    elif has_switch_or_bridge:
        group = "G3"
    elif has_fragile:
        group = "G2"
    else:
        group = "G1"

    # fill grid characters from object layers
    for row, col, name, _ in playable_tiles:
        grid_row = row - min_row
        grid_col = col - min_col
        if name in ("normal", "button", "splitter"):
            grid_matrix[grid_row][grid_col] = "#"
        elif name == "weak":
            grid_matrix[grid_row][grid_col] = "F"
        elif name == "goal":
            grid_matrix[grid_row][grid_col] = "G"
        elif name == "bridge":
            grid_matrix[grid_row][grid_col] = "B"

    # starting tile is always at pixel 0 0
    start_grid_row = -min_row
    start_grid_col = -min_col
    grid_matrix[start_grid_row][start_grid_col] = "S"

    grid_strings = ["".join(row_chars) for row_chars in grid_matrix]

    # group bridge tiles by bridge id
    bridges_map: dict[str, dict[str, Any]] = {}
    for row, col, name, obj in playable_tiles:
        if name == "bridge":
            props = obj.get("properties", {})
            bridge_id = props.get("id", "")
            init_open = props.get("startActivated", False)
            grid_row = row - min_row
            grid_col = col - min_col
            if bridge_id not in bridges_map:
                bridges_map[bridge_id] = {
                    "id": bridge_id,
                    "cells": [],
                    "initially_open": bool(init_open),
                }
            elif init_open:
                bridges_map[bridge_id]["initially_open"] = True
            bridges_map[bridge_id]["cells"].append([grid_row, grid_col])

    bridges_list = list(bridges_map.values())
    bridges_list.sort(key=lambda b: b["id"])
    for bridge_entry in bridges_list:
        bridge_entry["cells"].sort()

    # parse switches including buttons and splitters
    switches_list: list[dict[str, Any]] = []
    switch_counter = 1

    for row, col, name, obj in playable_tiles:
        grid_row = row - min_row
        grid_col = col - min_col
        props = obj.get("properties", {})

        if name == "button":
            is_heavy = props.get("hard", False)
            button_type = props.get("type", "toggle")
            activating_str = props.get("activating", "")
            bridge_targets = [b.strip() for b in activating_str.split(",") if b.strip()]
            kind = "heavy" if is_heavy else "soft"

            switch_data: dict[str, Any] = {
                "id": f"sw_{switch_counter}",
                "kind": kind,
                "pos": [grid_row, grid_col],
                "bridges": bridge_targets,
            }

            if button_type == "toggle":
                switch_data["mode"] = "toggle"
            elif button_type == "on":
                switch_data["mode"] = "permanent"
                switch_data["set_to"] = "open"
            elif button_type == "off":
                switch_data["mode"] = "permanent"
                switch_data["set_to"] = "close"

            switches_list.append(switch_data)
            switch_counter += 1

        elif name == "splitter":
            split1_id = props.get("split1")
            split2_id = props.get("split2")
            target_obj1 = objects_by_id[split1_id][1]
            target_obj2 = objects_by_id[split2_id][1]

            target1_pos = [target_obj1["y"] // 50 - min_row, target_obj1["x"] // 50 - min_col]
            target2_pos = [target_obj2["y"] // 50 - min_row, target_obj2["x"] // 50 - min_col]

            switch_data = {
                "id": f"sw_{switch_counter}",
                "kind": "split",
                "pos": [grid_row, grid_col],
                "targets": [target1_pos, target2_pos],
            }
            switches_list.append(switch_data)
            switch_counter += 1

    stage_id = f"stage_{stage_num:02d}"
    stage_data: dict[str, Any] = {
        "id": stage_id,
        "group": group,
        "grid": grid_strings,
        "bridges": bridges_list,
        "switches": switches_list,
    }
    if stage_num == 30:
        stage_data["note"] = (
            "Excluded from active stages and benchmarks: quick_bloxorz source map is missing floor tiles, making the level unsolvable."
        )
    return stage_data


def convert_all(input_dir: Path, output_dir: Path) -> None:
    # make sure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    for stage_num in range(1, 34):
        input_path = input_dir / f"bloxorz{stage_num}.json"
        if not input_path.exists():
            raise FileNotFoundError(f"Missing map file: {input_path}")

        raw_content = json.loads(input_path.read_text(encoding="utf-8"))
        stage_dict = convert_map(raw_content, stage_num)

        output_path = output_dir / f"stage_{stage_num:02d}.json"
        output_path.write_text(json.dumps(stage_dict, indent=2), encoding="utf-8")
        print(f"Converted {input_path.name} -> {output_path.name} ({stage_dict['group']})")


def main() -> None:
    # handle optional command line arguments
    in_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../maps")
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("stages/original")
    convert_all(in_dir, out_dir)


if __name__ == "__main__":
    main()
