"""best_first (shared by UCS and A*) and uniform-cost search. Owner: VT5 (task 5.1)."""
import heapq
import itertools

from bloxorz.engine import initial_state, is_goal, successors
from bloxorz.search.base import reconstruct, register
from bloxorz.search.cost import move_cost


def best_first(stage, ctx, h):
    start = initial_state(stage)
    g = {start: 0.0}  # chi phí tốt nhất đã biết để tới mỗi trạng thái
    parents = {start: None}
    tie = itertools.count()  # số thứ tự để không phải so sánh State
    heap = [(h(start), next(tie), start)]
    closed = set()

    while heap:
        _, _, s = heapq.heappop(heap)
        if s in closed:
            continue
        if is_goal(stage, s):
            return reconstruct(parents, s)
        closed.add(s)
        ctx.tick()
        for a, s2 in successors(stage, s):
            new_g = g[s] + move_cost(stage, s, a, s2)
            # Chỉ thay cha khi tìm được đường đi rẻ hơn.
            if s2 not in g or new_g < g[s2]:
                g[s2] = new_g
                parents[s2] = (s, a)
                heapq.heappush(heap, (new_g + h(s2), next(tie), s2))
    return None


@register("ucs")
def ucs(stage, ctx):
    # h = 0 nên hàng đợi ưu tiên đúng chi phí đã đi.
    return best_first(stage, ctx, lambda s: 0)
