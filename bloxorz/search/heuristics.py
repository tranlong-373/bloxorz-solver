"""make_heuristic(stage, name): "relaxed" and "manhattan". Owner: VT5 (task 5.2)."""
from collections import deque

from bloxorz.engine.rules import ROLL, footprint
from bloxorz.model import Direction, Pose, State

INF = float("inf")


def manhattan(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def split_switch_positions(stage):
    return [sw.pos for sw in stage.switches if sw.kind == "split"]


# BFS trên "bàn trống" (cả hình chữ nhật là sàn, chỉ giữ biên bàn), trạng thái (tư thế, pos),
# bắt đầu từ khối đứng ở các ô trong sources. Lăn ngược lại được nên cũng là số nước ít nhất để tới sources
def relaxed_distances(stage, sources):
    dist = {}
    queue = deque()
    for p in sources:
        key = (Pose.STANDING, p)
        if key not in dist:
            dist[key] = 0
            queue.append(key)
    while queue:
        pose, (r, c) = key = queue.popleft()
        for d in Direction:
            new_pose, dr, dc = ROLL[(pose, d)]
            nxt = (new_pose, (r + dr, c + dc))
            if nxt in dist:
                continue
            if all(stage.in_bounds(p) for p in footprint(State(*nxt))):
                dist[nxt] = dist[key] + 1
                queue.append(nxt)
    return dist


def make_heuristic(stage, name="relaxed"):
    splits = split_switch_positions(stage)
    if name == "relaxed":
        d_goal = relaxed_distances(stage, [stage.goal])
        d_split = relaxed_distances(stage, splits)

        def h(s):
            if s.pose is None:
                return 2  # còn ít nhất 1 nước ghép + 1 nước đứng dậy
            key = (s.pose, s.pos)
            # Có thể tới đích trực tiếp hoặc qua công tắc tách khối.
            return min(d_goal.get(key, INF), d_split.get(key, INF) + 2)
        return h
    if name == "manhattan":
        def h(s):
            if s.pose is None:
                return 2
            # Một lần lăn đi tối đa 2 ô, nên chia đôi khoảng cách Manhattan.
            best = manhattan(s.pos, stage.goal) / 2
            for p in splits:
                best = min(best, manhattan(s.pos, p) / 2 + 2)
            # Khối nằm cần ít nhất 1 nước nữa: lấy max, không cộng thêm 1
            return max(best, 1) if s.pose in (Pose.HORIZONTAL, Pose.VERTICAL) else best
        return h
    raise ValueError(f"unknown heuristic: {name}")
