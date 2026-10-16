"""Stage, Bridge, Switch: an immutable loaded level. Owner: VT1 (task 1.2)."""
from dataclasses import dataclass
from functools import cached_property
from typing import Literal

from bloxorz.model import Pos

SwitchKind = Literal["soft", "heavy", "split"]
SwitchMode = Literal["toggle", "permanent"]


@dataclass(frozen=True)
class Bridge:
    id: str
    cells: tuple[Pos, ...]
    initially_open: bool = False


@dataclass(frozen=True)
class Switch:
    id: str
    kind: SwitchKind
    pos: Pos
    mode: SwitchMode | None = None  # soft/heavy only; None for split
    set_to: Literal["open", "close"] = "open"  # used when mode="permanent"
    bridges: tuple[str, ...] = ()  # soft/heavy: ids of controlled bridges
    targets: tuple[Pos, Pos] | None = None  # split: where the 2 cubes appear


@dataclass(frozen=True)
class Stage:
    id: str
    group: str  # "G1".."G5"
    grid: tuple[str, ...]  # one string per row; 'S' already replaced by '#'
    start: Pos
    goal: Pos
    bridges: tuple[Bridge, ...] = ()
    switches: tuple[Switch, ...] = ()

    @property
    def rows(self) -> int:
        return len(self.grid)

    @property
    def cols(self) -> int:
        return len(self.grid[0])  # loader guarantees a rectangle

    def in_bounds(self, p: Pos) -> bool:
        return 0 <= p[0] < self.rows and 0 <= p[1] < self.cols

    def cell(self, p: Pos) -> str:
        return self.grid[p[0]][p[1]] if self.in_bounds(p) else "."

    @cached_property
    def switch_at(self) -> dict[Pos, Switch]:
        return {s.pos: s for s in self.switches}

    @cached_property
    def bridge_at(self) -> dict[Pos, str]:
        return {c: b.id for b in self.bridges for c in b.cells}

    def initial_bridges_open(self) -> frozenset[str]:
        return frozenset(b.id for b in self.bridges if b.initially_open)
