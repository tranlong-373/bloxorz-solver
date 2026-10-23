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

_CHECK_EVERY = 1


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

    def check_limits(self) -> None:
        """Cooperative check; does not count an expanded node.

        Cancellation takes precedence when both limits are reached. This cannot
        interrupt a solver that neither ticks nor returns control to run().
        """
        if self.limits.cancel is not None and self.limits.cancel.is_set():
            raise SearchAborted("cancelled")
        if time.perf_counter() >= self.deadline:
            raise SearchAborted("timeout")

    def tick(self) -> None:
        """Check before each expansion; aborted checks do not increment expanded."""
        if self.expanded % _CHECK_EVERY == 0:
            self.check_limits()
        self.expanded += 1


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
    from .cost import move_cost
    from ..engine import initial_state, step
    s = initial_state(stage)
    total = 0.0
    for i, a in enumerate(actions):
        r = step(stage, s, a)
        if r.state is None:
            raise ValueError(f"action {i}: {r.reason}")
        total += move_cost(stage, s, a, r.state)
        s = r.state
    return total


def run(algorithm: str, stage: Stage, limits: Limits = Limits(),
        measure_memory: bool = False) -> SearchResult:
    """Run a solver cooperatively; validate solved paths outside search timing.

    Memory is paired only for deterministic results (same actions, cost and
    expanded count). A different valid solution is a pairing mismatch, not an
    invalid solution: keep the first result, omit peak, and explain in message.
    The traced search reuses Stage data caches warmed by the untraced search;
    validation/cost replay is outside tracing. No cold-cache/RSS claim is made.
    """
    fn = ALGORITHMS.get(algorithm)
    if fn is None:
        return SearchResult(algorithm, stage.id, "error",
                            message=f"unknown algorithm: {algorithm}")

    # Timing includes limit checks and the solver, including heuristic building
    # done inside it. Loading, replay/cost and memory validation are excluded.
    ctx = SearchContext(limits)
    actions: tuple[Action, ...] | None = None
    message = ""
    t0 = time.perf_counter()
    try:
        ctx.check_limits()
        actions = fn(stage, ctx)
        ctx.check_limits()  # also covers solvers returning without any tick
        status = "solved" if actions is not None else "unsolvable"
    except SearchAborted as e:
        status = e.status
    except Exception as e:  # solver bug must not crash the caller
        status = "error"
        message = f"{type(e).__name__}: {e}"
    time_s = time.perf_counter() - t0
    expanded = ctx.expanded

    cost = 0.0
    if status == "solved":
        try:
            cost = _path_cost(stage, actions)
            from ..verify import verify_solution
            valid, reason = verify_solution(stage, actions)
            if not valid:
                raise ValueError(f"invalid solution: {reason}")
        except Exception as e:
            return SearchResult(algorithm, stage.id, "error", expanded=expanded,
                                time_s=time_s, message=f"{type(e).__name__}: {e}")

    peak = None
    if measure_memory and status in ("solved", "unsolvable"):
        # Keep the same Stage: its bridge_at/switch_at caches may already be warm.
        # This measures additional traced allocations, not total process memory
        # or cold Stage setup. No heuristic cache exists in the current stubs.
        try:
            try:
                tracemalloc.start()
                memory_ctx = SearchContext(limits)
                memory_ctx.check_limits()
                memory_actions = fn(stage, memory_ctx)
                memory_ctx.check_limits()
                candidate_peak = tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()

            # Validation and cost replay are OUTSIDE the traced allocation scope.
            # verify imports only the engine; neither imports search/base, so this
            # local dependency reuses the existing replay without an import cycle.
            memory_status = "solved" if memory_actions is not None else "unsolvable"
            memory_cost = 0.0
            if memory_status == "solved":
                from ..verify import verify_solution
                valid, reason = verify_solution(stage, memory_actions)
                if not valid:
                    raise ValueError(f"invalid solution: {reason}")
                memory_cost = _path_cost(stage, memory_actions)
            differences = []
            if memory_status != status:
                differences.append(f"status {status} -> {memory_status}")
            if memory_actions != actions:
                differences.append("actions")
            if memory_cost != cost:
                differences.append("cost")
            if memory_ctx.expanded != expanded:
                differences.append(f"expanded {expanded} -> {memory_ctx.expanded}")
            if differences:
                raise ValueError("differs from first pass: " + ", ".join(differences))
            peak = candidate_peak
        except SearchAborted as e:
            message = f"memory pass: {e.status}; peak unavailable"
        except Exception as e:
            message = f"memory pass: {type(e).__name__}: {e}; peak unavailable"

    if status != "solved":
        return SearchResult(algorithm, stage.id, status, expanded=expanded,
                            time_s=time_s, peak_mem_bytes=peak, message=message)
    return SearchResult(algorithm, stage.id, status, actions, len(actions),
                        cost, expanded, time_s, peak, message)
