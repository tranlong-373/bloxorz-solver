"""Tests for all Bloxorz pose transitions and two edge falls.

Expected engine public API (module ``src.engine``):
    Stage, State, Pose, Direction, Action, Outcome, step

The engine is imported inside each test rather than at module import time so
pytest collects all 14 tests before the engine implementation exists.
"""

import importlib

import pytest



ENGINE_MODULE = "bloxorz.engine"


def load_engine():
    """Load the engine lazily so missing code fails tests, not collection."""
    try:
        return importlib.import_module(ENGINE_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name not in ("bloxorz", ENGINE_MODULE):
            raise
        pytest.fail(
            f"Engine is not implemented (expected {ENGINE_MODULE!r}): {exc}",
            pytrace=False,
        )


def open_stage():
    """Build an open 7x7 stage with the goal in its bottom-right corner."""
    Stage = importlib.import_module(ENGINE_MODULE).Stage

    rows = ["#######"] * 6 + ["######G"]
    return Stage(id="open7", group="G1", grid=tuple(rows), start=(3, 3), goal=(6, 6))


# (pose before, direction, pose after, position after)
# Names are resolved to Pose/Direction members at test time so the suite
CASES = [
    ("STANDING", "UP", "VERTICAL", (1, 3)),
    ("STANDING", "DOWN", "VERTICAL", (4, 3)),
    ("STANDING", "LEFT", "HORIZONTAL", (3, 1)),
    ("STANDING", "RIGHT", "HORIZONTAL", (3, 4)),
    ("HORIZONTAL", "UP", "HORIZONTAL", (2, 3)),
    ("HORIZONTAL", "DOWN", "HORIZONTAL", (4, 3)),
    ("HORIZONTAL", "LEFT", "STANDING", (3, 2)),
    ("HORIZONTAL", "RIGHT", "STANDING", (3, 5)),
    ("VERTICAL", "UP", "STANDING", (2, 3)),
    ("VERTICAL", "DOWN", "STANDING", (5, 3)),
    ("VERTICAL", "LEFT", "VERTICAL", (3, 2)),
    ("VERTICAL", "RIGHT", "VERTICAL", (3, 4)),
]


@pytest.mark.parametrize("before, d, after, pos_after", CASES)
def test_roll(before, d, after, pos_after):
    engine = load_engine()
    before_pose = engine.Pose[before]
    direction = engine.Direction[d]
    after_pose = engine.Pose[after]

    res = engine.step(
        open_stage(),
        engine.State(before_pose, (3, 3)),
        engine.Action(direction),
    )

    assert res.outcome is engine.Outcome.MOVED
    assert res.state == engine.State(after_pose, pos_after)


def test_standing_falls_off_top_edge():
    engine = load_engine()
    res = engine.step(
        open_stage(),
        engine.State(engine.Pose.STANDING, (0, 0)),
        engine.Action(engine.Direction.UP),
    )

    assert res.outcome is engine.Outcome.ILLEGAL
    assert res.reason == "fell"


def test_horizontal_falls_off_right_edge():
    engine = load_engine()
    # A horizontal block at (0, 5) occupies (0, 5) and (0, 6).
    res = engine.step(
        open_stage(),
        engine.State(engine.Pose.HORIZONTAL, (0, 5)),
        engine.Action(engine.Direction.RIGHT),
    )

    assert res.outcome is engine.Outcome.ILLEGAL
    assert res.reason == "fell"
