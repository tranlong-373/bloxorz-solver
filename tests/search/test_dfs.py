from bloxorz.engine import initial_state, is_goal, step
from bloxorz.search import run
from bloxorz.stage import Stage

# 3x4 open floor, goal at the top-right. Shortest plan is 2 moves (R, R).
OPEN = Stage("open", "G1", ("###G", "####", "####"), (0, 0), (0, 3))
# Floor ends in a 2-wide gap before the goal: the goal can never be reached,
# but the 2x2 floor still has cycles, so DFS needs `visited` to stop.
UNREACHABLE = Stage("gap", "G1", ("##..G", "##..#"), (0, 0), (0, 4))


def replay_reaches_goal(stage, actions):
    s = initial_state(stage)
    for a in actions:
        s = step(stage, s, a).state
        assert s is not None
    return is_goal(stage, s)


def test_dfs_solves_and_plan_replays():
    r = run("dfs", OPEN)
    assert r.status == "solved" and r.length == len(r.actions) > 0
    assert replay_reaches_goal(OPEN, r.actions)


def test_dfs_terminates_on_unsolvable_stage_with_cycles():
    r = run("dfs", UNREACHABLE)
    assert r.status == "unsolvable" and r.expanded > 0


def test_dfs_is_deterministic():
    assert run("dfs", OPEN).actions == run("dfs", OPEN).actions


def test_dfs_not_shortest():
    # Optimal is 2 moves (checked by hand: R, R). DFS tries UP, DOWN, LEFT, RIGHT
    # in that order and dives deep first, so it returns a longer plan.
    r = run("dfs", OPEN)
    assert r.status == "solved" and r.length > 2
