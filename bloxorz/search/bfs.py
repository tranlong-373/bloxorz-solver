"""Tìm kiếm theo chiều rộng (BFS)."""
from collections import deque

from bloxorz.engine import initial_state, is_goal, successors
from bloxorz.search.base import reconstruct, register


@register("bfs")
def bfs(stage, ctx):
    """Duyệt theo lớp để tìm lời giải ít bước nhất, hoặc None nếu không có."""
    start = initial_state(stage)
    if is_goal(stage, start):
        return ()
    parents = {start: None}  # vừa lưu đường đi, vừa đánh dấu trạng thái đã gặp
    # Hàng đợi FIFO giúp duyệt hết mức hiện tại trước khi sang mức sâu hơn.
    queue = deque([start])
    while queue:
        s = queue.popleft()
        ctx.tick()
        for a, nxt in successors(stage, s):
            if nxt in parents:
                continue
            parents[nxt] = (s, a)
            # BFS xét đích khi sinh: lần gặp đầu có ít bước nhất.
            if is_goal(stage, nxt):
                return reconstruct(parents, nxt)
            queue.append(nxt)
    return None
