"""move_cost: 1 per move, +4 when the moved piece lands on a fragile tile. Owner: VT5 (task 5.1)."""
from bloxorz.engine.rules import footprint
from bloxorz.model import Action, State
from bloxorz.stage import Stage

FRAGILE_PENALTY = 4


def move_cost(
    stage: Stage, before: State, action: Action, after: State
) -> float:
    cost = 1.0
    if before.pose is not None:
        moved_cells = footprint(after)
    else:
        still = before.cube2 if action.cube == 0 else before.pos
        moved_cells = [p for p in footprint(after) if p != still]
    for p in moved_cells:
        if stage.cell(p) == "F":
            cost += FRAGILE_PENALTY
            break
    return cost
