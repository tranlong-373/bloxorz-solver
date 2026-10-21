"""best_first (shared by UCS and A*) and uniform-cost search. Owner: VT5 (task 5.1)."""
import heapq

from bloxorz.engine import initial_state, is_goal, successors
from bloxorz.search.base import reconstruct, register
from bloxorz.search.cost import move_cost


def best_first(stage, ctx, heuristic=None):
    start = initial_state(stage)
    if is_goal(stage, start):
        return ()

    counter = 0
    h_start = heuristic(start) if heuristic is not None else 0.0
    heap = [(0.0 + h_start, counter, 0.0, start)]

    cost_so_far = {start: 0.0}
    parents = {start: None}

    while heap:
        priority, _, g, s = heapq.heappop(heap)

        if g > cost_so_far[s]:
            continue

        if is_goal(stage, s):
            return reconstruct(parents, s)

        ctx.tick()

        for a, nxt in successors(stage, s):
            step_cost = move_cost(stage, s, a, nxt)
            new_g = g + step_cost

            if nxt not in cost_so_far or new_g < cost_so_far[nxt]:
                cost_so_far[nxt] = new_g
                parents[nxt] = (s, a)
                h_val = heuristic(nxt) if heuristic is not None else 0.0
                counter += 1
                heapq.heappush(heap, (new_g + h_val, counter, new_g, nxt))

    return None


@register("ucs")
def ucs(stage, ctx):
    return best_first(stage, ctx, heuristic=None)
