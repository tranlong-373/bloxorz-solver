"""Solver framework: Limits, SearchResult, ALGORITHMS registry, SearchContext, run(). Owner: VT1 (task 1.3)."""
import threading
import time
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass

from bloxorz.model import Action, State
from bloxorz.stage import Stage


@dataclass(frozen=True)
class Limits:
    timeout_s: float = 60.0
    cancel: threading.Event | None = None


@dataclass(frozen=True)
class SearchResult:
    algorithm: str  # "bfs" | "dfs" | "ucs" | "astar" | "astar_manhattan"
    stage_id: str
    status: str  # "solved" | "unsolvable" | "timeout" | "cancelled" | "error"
    actions: tuple[Action, ...] = ()
    length: int = 0
    cost: float = 0.0
    expanded: int = 0
    time_s: float = 0.0
    peak_mem_bytes: int | None = None
    message: str = ""


SolverFn = Callable[[Stage, "SearchContext"], tuple[Action, ...] | None]
ALGORITHMS: dict[str, SolverFn] = {}

_CHECK_EVERY = 1000


def register(name: str):
    def deco(fn):
        ALGORITHMS[name] = fn
        return fn

    return deco


class SearchAborted(Exception):
    def __init__(self, status: str):  # "timeout" | "cancelled"
        super().__init__(status)
        self.status = status


class SearchContext:
    def __init__(self, limits: Limits):
        self.limits = limits
        self.expanded = 0
        self.deadline = time.perf_counter() + limits.timeout_s

    def tick(self) -> None:
        """Call once per expanded node."""
        self.expanded += 1
        if self.expanded % _CHECK_EVERY:
            return
        if time.perf_counter() > self.deadline:
            raise SearchAborted("timeout")
        if self.limits.cancel is not None and self.limits.cancel.is_set():
            raise SearchAborted("cancelled")


def reconstruct(parents: dict, goal: State) -> tuple[Action, ...]:
    """parents[state] = (parent_state, action); parents[start] = None."""
    actions = []
    entry = parents[goal]
    while entry is not None:
        parent, action = entry
        actions.append(action)
        entry = parents[parent]
    return tuple(reversed(actions))


def _path_cost(stage: Stage, actions: tuple[Action, ...]) -> float:
    try:
        from .cost import move_cost
        from ..engine import initial_state, step
    except ImportError:  # task 2.1 / 5.1 not merged yet
        return float(len(actions))
    s = initial_state(stage)
    total = 0.0
    for a in actions:
        s2 = step(stage, s, a).state
        total += move_cost(stage, s, a, s2)
        s = s2
    return total


def run(algorithm: str, stage: Stage, limits: Limits = Limits(),
        measure_memory: bool = False) -> SearchResult:
    fn = ALGORITHMS.get(algorithm)
    if fn is None:
        return SearchResult(algorithm, stage.id, "error",
                            message=f"unknown algorithm: {algorithm}")

    ctx = SearchContext(limits)
    actions: tuple[Action, ...] | None = None
    message = ""
    t0 = time.perf_counter()
    try:
        actions = fn(stage, ctx)
        status = "solved" if actions is not None else "unsolvable"
    except SearchAborted as e:
        status = e.status
    except Exception as e:  # solver bug must not crash the caller
        status = "error"
        message = f"{type(e).__name__}: {e}"
    time_s = time.perf_counter() - t0
    expanded = ctx.expanded

    peak = None
    if measure_memory and status in ("solved", "unsolvable"):
        tracemalloc.start()
        try:
            fn(stage, SearchContext(limits))
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()

    if status != "solved":
        return SearchResult(algorithm, stage.id, status, expanded=expanded,
                            time_s=time_s, peak_mem_bytes=peak, message=message)
    return SearchResult(algorithm, stage.id, status, actions, len(actions),
                        _path_cost(stage, actions), expanded, time_s, peak)
