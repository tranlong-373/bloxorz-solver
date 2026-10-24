"""SolverRunner: run a solver on a background thread with cancel. Must not import ursina. Owner: VT4 (task 4.3)."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from bloxorz.search import Limits, SearchResult, run
from bloxorz.stage import Stage


class SolverRunner:
    """Run a solver in a worker and expose its result through poll()."""

    def __init__(self, timeout_s: float = 60.0) -> None:
        self.timeout_s = timeout_s
        self._cancel = threading.Event()
        self._result: SearchResult | None = None
        self._thread: threading.Thread | None = None
        self._started_at = 0.0
        self._lock = threading.Lock()

    def start(self, algorithm: str, stage: Stage) -> None:
        self.cancel()
        self._cancel = threading.Event()
        self._result = None
        self._started_at = time.perf_counter()
        cancel_event = self._cancel

        def work() -> None:
            result = run(
                algorithm,
                stage,
                Limits(timeout_s=self.timeout_s, cancel=cancel_event),
                measure_memory=True,
            )
            with self._lock:
                if self._cancel is cancel_event:
                    self._result = result

        self._thread = threading.Thread(target=work, daemon=True)
        self._thread.start()

    def poll(self) -> SearchResult | None:
        with self._lock:
            return self._result

    def cancel(self) -> None:
        self._cancel.set()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def elapsed_s(self) -> float:
        if self._started_at == 0.0:
            return 0.0
        return time.perf_counter() - self._started_at
