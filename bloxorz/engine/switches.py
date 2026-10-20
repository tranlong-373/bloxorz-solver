"""Soft/heavy switch activation and bridge state updates (task 2.3)."""

from __future__ import annotations

from bloxorz.model import Pos
from bloxorz.stage import Stage


def apply_switches(
    stage: Stage,
    landed_cells: tuple[Pos, ...],
    piece: str,
    bridges_open: frozenset[str],
) -> tuple[frozenset[str], tuple[str, ...]]:
    """Apply switches under a landed piece and report actual state changes.

    ``piece`` is ``"standing"`` (intact upright block), ``"lying"``
    (intact horizontal/vertical block), or ``"cube"`` (one split cube).
    Split switches are handled separately in task 2.4.

    Switches activate in ascending ID order. Each switch's bridge IDs are
    processed in their declared order; a bridge event is recorded only if
    its open/closed state actually changes.
    """
    # The shared Stage can map a cell to one Switch or a tuple of Switches.
    # Flatten the values first, so multiple switches at one cell all fire.
    switches = []
    for p in landed_cells:
        found = stage.switch_at.get(p)
        if found is None:
            continue
        if isinstance(found, tuple):
            switches.extend(found)
        else:
            switches.append(found)
    switches.sort(key=lambda switch: switch.id)

    opened = set(bridges_open)
    events: list[str] = []

    for switch in switches:
        if switch.kind == "split":
            continue
        if switch.kind == "heavy" and piece != "standing":
            continue
        if switch.kind != "soft" and switch.kind != "heavy":
            continue

        events.append(f"switch:{switch.id}")

        for bridge_id in switch.bridges:
            was_open = bridge_id in opened
            if switch.mode == "toggle":
                should_open = not was_open
            elif switch.mode == "permanent":
                should_open = switch.set_to == "open"
            else:
                raise ValueError(f"Invalid mode for switch {switch.id}: {switch.mode!r}")

            if should_open == was_open:
                continue

            if should_open:
                opened.add(bridge_id)
                events.append(f"bridge:{bridge_id}:open")
            else:
                opened.remove(bridge_id)
                events.append(f"bridge:{bridge_id}:close")

    return frozenset(opened), tuple(events)
