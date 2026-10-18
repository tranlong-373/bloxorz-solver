"""verify_solution(stage, actions): replay a solution and check it wins. Owner: VT1 (task 1.4)."""
from bloxorz.engine import Outcome, initial_state, is_goal, step


def verify_solution(stage, actions) -> tuple[bool, str]:
    """Replay `actions` from the initial state.

    Returns (True, "") if the block ends on the goal. Otherwise (False, msg):
    "bước i: reason" for an illegal move (i counts from 1), or "chưa tới đích".
    """
    state = initial_state(stage)
    for i, action in enumerate(actions, start=1):
        result = step(stage, state, action)
        if result.outcome is Outcome.ILLEGAL:
            return False, f"bước {i}: {result.reason}"
        state = result.state
    if not is_goal(stage, state):
        return False, "chưa tới đích"
    return True, ""
