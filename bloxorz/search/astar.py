"""A* search: astar (relaxed heuristic) and astar_manhattan. Owner: VT5 (task 5.2)."""
from bloxorz.search.base import register
from bloxorz.search.heuristics import make_heuristic
from bloxorz.search.ucs import best_first


# Bảng heuristic được xây trong mỗi lần gọi solver, nên thời gian đo đã gồm cả bước này.
# best_first không mở lại trạng thái đã đóng: chỉ đúng vì cả 2 heuristic đều consistent.
@register("astar")
def astar(stage, ctx):
    return best_first(stage, ctx, make_heuristic(stage, "relaxed"))


@register("astar_manhattan")
def astar_manhattan(stage, ctx):
    return best_first(stage, ctx, make_heuristic(stage, "manhattan"))
