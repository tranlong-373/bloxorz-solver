"""Tìm kiếm theo chiều sâu (DFS) có đánh dấu trạng thái. VT1, task 1.5."""
from bloxorz.engine import initial_state, is_goal, successors
from bloxorz.search.base import reconstruct, register


@register("dfs")
def dfs(stage, ctx):
    """Duyệt sâu theo thứ tự hướng cố định và trả lời giải nếu tìm thấy."""
    start = initial_state(stage)
    stack = [(start, None, None)]  # giữ cha và hành động để dựng lại lời giải
    parents = {}  # đánh dấu khi lấy khỏi stack, không phải khi thêm vào
    while stack:
        s, parent, action = stack.pop()
        if s in parents:
            continue
        parents[s] = None if parent is None else (parent, action)
        if is_goal(stage, s):
            return reconstruct(parents, s)
        ctx.tick()
        # Đảo thứ tự thêm vào để hướng UP được lấy ra trước.
        for a, nxt in reversed(successors(stage, s)):
            if nxt not in parents:
                stack.append((nxt, s, a))
    return None
