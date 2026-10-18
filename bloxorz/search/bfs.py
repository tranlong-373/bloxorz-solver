"""Breadth-first search. Owner: VT1 (task 1.4)."""
from collections import deque

from bloxorz.engine import initial_state, is_goal, successors
from bloxorz.search.base import reconstruct, register


@register("bfs")
def bfs(stage, ctx):
    start = initial_state(stage)
    if is_goal(stage, start):
        return ()
    parents = {start: None}  # doubles as the visited set; keyed by the whole State
    queue = deque([start])
    while queue:
        s = queue.popleft()
        ctx.tick()
        for a, nxt in successors(stage, s):
            if nxt in parents:
                continue
            parents[nxt] = (s, a)
            if is_goal(stage, nxt):  # goal test on generation: first hit is shallowest
                return reconstruct(parents, nxt)
            queue.append(nxt)
    return None
