"""Depth-first search (graph search with visited set). Owner: VT1 (task 1.5)."""
from bloxorz.engine import initial_state, is_goal, successors
from bloxorz.search.base import reconstruct, register


@register("dfs")
def dfs(stage, ctx):
    start = initial_state(stage)
    stack = [(start, None, None)]  # (state, parent state, action that led here)
    parents = {}  # doubles as the visited set; keyed by the whole State
    while stack:
        s, parent, action = stack.pop()
        if s in parents:
            continue  # already expanded via another path
        parents[s] = None if parent is None else (parent, action)
        if is_goal(stage, s):  # goal test on pop, not on generation
            return reconstruct(parents, s)
        ctx.tick()
        # push reversed so the first successor (UP) is popped first
        for a, nxt in reversed(successors(stage, s)):
            if nxt not in parents:
                stack.append((nxt, s, a))
    return None
