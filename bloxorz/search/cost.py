"""move_cost: 1 per move, +4 when the moved piece lands on a fragile tile. Owner: VT5 (task 5.1)."""
from bloxorz.engine.rules import footprint
from bloxorz.model import Action, State
from bloxorz.stage import Stage

FRAGILE_PENALTY = 4


def move_cost(stage: Stage, s: State, a: Action, s2: State) -> float:
    if s.pose is None:  # đi 1 cube (kể cả nước ghép): chỉ lấy ô mới của cube vừa đi
        landed = [p for p in footprint(s2) if p not in (s.pos, s.cube2)]
    elif s2.pose is None:  # vừa tách: khối vừa đứng lên công tắc tách (ô '#')
        landed = ()
    else:  # lăn khối nguyên
        landed = footprint(s2)
    hit = any(stage.cell(p) == "F" for p in landed)
    return float(1 + (FRAGILE_PENALTY if hit else 0))
