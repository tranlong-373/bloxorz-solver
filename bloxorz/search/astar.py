"""A* với hai hàm ước lượng relaxed và Manhattan. VT5, task 5.2."""
from bloxorz.search.base import register
from bloxorz.search.heuristics import make_heuristic
from bloxorz.search.ucs import best_first


# Dùng chung vòng tìm kiếm với UCS; A* ưu tiên g + h thay vì chỉ g.
# Heuristic được dựng trong mỗi lượt gọi, nên thời gian đo tính cả bước này.
# Hai heuristic nhất quán nên không cần mở lại trạng thái đã đóng.
@register("astar")
def astar(stage, ctx):
    """Chạy A* với heuristic khoảng cách trên bàn thư giãn."""
    return best_first(stage, ctx, make_heuristic(stage, "relaxed"))


@register("astar_manhattan")
def astar_manhattan(stage, ctx):
    """Chạy A* với heuristic khoảng cách Manhattan."""
    return best_first(stage, ctx, make_heuristic(stage, "manhattan"))
