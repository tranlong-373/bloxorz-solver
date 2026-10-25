"""Khung chạy thuật toán: giới hạn, kết quả, bảng đăng ký và đo tìm kiếm. VT1 (1.3)."""
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
    """Tạo decorator đăng ký thuật toán theo tên cho run()."""
    def deco(fn):
        """Lưu hàm giải vào bảng đăng ký rồi trả lại chính hàm đó."""
        ALGORITHMS[name] = fn
        return fn

    return deco


class SearchAborted(Exception):
    def __init__(self, status: str):  # "timeout" | "cancelled"
        """Ghi lý do dừng sớm: hết giờ hoặc bị hủy."""
        super().__init__(status)
        self.status = status


class SearchContext:
    def __init__(self, limits: Limits):
        """Tạo bộ đếm và thời điểm hết hạn cho một lượt tìm kiếm."""
        self.limits = limits
        self.expanded = 0
        self.deadline = time.perf_counter() + limits.timeout_s

    def check_limits(self) -> None:
        """Kiểm tra hủy trước hết giờ, không tăng số nút mở rộng.

        Chỉ dừng tại nơi gọi hàm này; không ngắt ngang một bước solver đang chạy.
        """
        if self.limits.cancel is not None and self.limits.cancel.is_set():
            raise SearchAborted("cancelled")
        if time.perf_counter() >= self.deadline:
            raise SearchAborted("timeout")

    def tick(self) -> None:
        """Kiểm tra giới hạn rồi tăng số nút chuẩn bị mở rộng."""
        if self.expanded % _CHECK_EVERY == 0:
            self.check_limits()
        self.expanded += 1


def reconstruct(parents: dict, goal: State) -> tuple[Action, ...]:
    """Lần theo cha từ đích về đầu rồi đảo lại chuỗi hành động."""
    actions = []
    entry = parents[goal]
    while entry is not None:
        parent, action = entry
        actions.append(action)
        entry = parents[parent]
    return tuple(reversed(actions))


def _path_cost(stage: Stage, actions: tuple[Action, ...]) -> float:
    """Phát lại lời giải theo luật chơi để tính tổng chi phí thực tế."""
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
    """Chạy solver, đo thời gian và kiểm tra lời giải ngoài khoảng đo.

    Chỉ giữ số đo bộ nhớ khi hai lượt cho cùng trạng thái, hành động, chi phí
    và số nút mở rộng. Nếu lời giải vẫn hợp lệ nhưng khác, giữ kết quả đầu và
    để trống số đo bộ nhớ. Lượt đo bộ nhớ dùng lại cache của Stage đã làm nóng;
    phát lại và xác minh nằm ngoài vùng theo dõi cấp phát, không đo RSS.
    """
    fn = ALGORITHMS.get(algorithm)
    if fn is None:
        return SearchResult(algorithm, stage.id, "error",
                            message=f"unknown algorithm: {algorithm}")

    # Thời gian gồm solver và bước dựng heuristic, không gồm tải màn hay phát lại.
    ctx = SearchContext(limits)
    actions: tuple[Action, ...] | None = None
    message = ""
    t0 = time.perf_counter()
    try:
        ctx.check_limits()
        actions = fn(stage, ctx)
        ctx.check_limits()  # bắt cả solver trả về mà chưa gọi tick
        status = "solved" if actions is not None else "unsolvable"
    except SearchAborted as e:
        status = e.status
    except Exception as e:  # lỗi solver được trả về thay vì làm hỏng chương trình gọi
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
        # Dùng lại Stage đã làm nóng cache cầu/công tắc; chỉ đo cấp phát Python,
        # không đo RAM toàn tiến trình. Heuristic được dựng lại ở mỗi lượt gọi.
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

            # Phát lại, tính chi phí và xác minh đều nằm ngoài vùng đo bộ nhớ.
            # Import tại đây để tránh vòng import giữa search và verify.
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
