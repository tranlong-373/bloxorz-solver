"""Task 2.2: fragile ('F') tiles only break under an intact standing block.

Tests use the project's shared State/Action/Stage classes, not test doubles.
"""

import pytest

from bloxorz.engine import Outcome, StepResult, step, successors
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Stage


def open_stage(*, fragile=(), void=()):
    """Make a 7x7 floor stage with selected fragile and void cells."""
    assert not set(fragile) & set(void)
    rows = [list("#######") for _ in range(7)]
    rows[6][6] = "G"
    for r, c in fragile:
        rows[r][c] = "F"
    for r, c in void:
        rows[r][c] = "."
    return Stage(
        id="fragile7",
        group="G2",
        grid=tuple("".join(row) for row in rows),
        start=(3, 3),
        goal=(6, 6),
    )


@pytest.mark.parametrize(
    "pose, direction, fragile_pos",
    [
        (Pose.HORIZONTAL, Direction.LEFT, (3, 2)),
        (Pose.HORIZONTAL, Direction.RIGHT, (3, 5)),
        (Pose.VERTICAL, Direction.UP, (2, 3)),
        (Pose.VERTICAL, Direction.DOWN, (5, 3)),
    ],
)
def test_landing_upright_on_fragile_breaks(pose, direction, fragile_pos):
    """All four lying-to-standing rolls break when landing on F."""
    stage = open_stage(fragile=(fragile_pos,))
    before = State(pose, (3, 3))

    result = step(stage, before, Action(direction))

    assert result == StepResult(Outcome.ILLEGAL, None, "fragile_broke")
    assert result.reason == "fragile_broke"
    assert result.events == ()
    assert before == State(pose, (3, 3))


@pytest.mark.parametrize(
    "direction, fragile_pos, expected_pose, expected_pos",
    [
        (Direction.UP, (1, 3), Pose.VERTICAL, (1, 3)),
        (Direction.UP, (2, 3), Pose.VERTICAL, (1, 3)),
        (Direction.DOWN, (4, 3), Pose.VERTICAL, (4, 3)),
        (Direction.DOWN, (5, 3), Pose.VERTICAL, (4, 3)),
        (Direction.LEFT, (3, 1), Pose.HORIZONTAL, (3, 1)),
        (Direction.LEFT, (3, 2), Pose.HORIZONTAL, (3, 1)),
        (Direction.RIGHT, (3, 4), Pose.HORIZONTAL, (3, 4)),
        (Direction.RIGHT, (3, 5), Pose.HORIZONTAL, (3, 4)),
    ],
)
def test_standing_roll_onto_one_fragile_is_safe(
    direction, fragile_pos, expected_pose, expected_pos
):
    """A lying block may rest on one F tile and one regular floor tile."""
    stage = open_stage(fragile=(fragile_pos,))

    result = step(stage, State(Pose.STANDING, (3, 3)), Action(direction))

    assert result == StepResult(Outcome.MOVED, State(expected_pose, expected_pos))
    assert result.reason == ""
    assert result.events == ()


@pytest.mark.parametrize(
    "direction, fragile_cells, expected_pose, expected_pos",
    [
        (
            Direction.RIGHT,
            ((3, 4), (3, 5)),
            Pose.HORIZONTAL,
            (3, 4),
        ),
        (
            Direction.UP,
            ((1, 3), (2, 3)),
            Pose.VERTICAL,
            (1, 3),
        ),
    ],
)
def test_lying_across_two_fragile_tiles_is_safe(
    direction, fragile_cells, expected_pose, expected_pos
):
    """Both occupied cells may be F while the whole block is lying."""
    stage = open_stage(fragile=fragile_cells)

    result = step(stage, State(Pose.STANDING, (3, 3)), Action(direction))

    assert result == StepResult(Outcome.MOVED, State(expected_pose, expected_pos))


@pytest.mark.parametrize("direction", list(Direction))
def test_leaving_fragile_tiles_while_lying_is_safe(direction):
    """Only the destination is evaluated; leaving F does not break it."""
    stage = open_stage(fragile=((3, 4), (3, 5)))
    before = State(Pose.HORIZONTAL, (3, 4))

    result = step(stage, before, Action(direction))

    assert result.outcome is Outcome.MOVED
    assert result.state is not None
    assert result.reason == ""
    assert result.events == ()
    assert before == State(Pose.HORIZONTAL, (3, 4))


@pytest.mark.parametrize(
    "pose, direction, fragile_cells, expected",
    [
        (
            Pose.HORIZONTAL,
            Direction.UP,
            ((2, 3), (2, 4)),
            State(Pose.HORIZONTAL, (2, 3)),
        ),
        (
            Pose.VERTICAL,
            Direction.RIGHT,
            ((3, 4), (4, 4)),
            State(Pose.VERTICAL, (3, 4)),
        ),
    ],
)
def test_sideways_roll_across_fragile_is_safe(
    pose, direction, fragile_cells, expected
):
    """Lying-to-lying moves may land entirely on fragile tiles."""
    stage = open_stage(fragile=fragile_cells)

    result = step(stage, State(pose, (3, 3)), Action(direction))

    assert result == StepResult(Outcome.MOVED, expected)


def test_void_in_destination_still_causes_fall_next_to_fragile():
    """F supports a lying block, but the other cell must be supported too."""
    stage = open_stage(fragile=((3, 4),), void=((3, 5),))

    result = step(stage, State(Pose.STANDING, (3, 3)), Action(Direction.RIGHT))

    assert result == StepResult(Outcome.ILLEGAL, None, "fell")
    assert result.events == ()


@pytest.mark.parametrize(
    "pose, fragile_cells, expected_directions, expected_states",
    [
        (
            Pose.HORIZONTAL,
            ((3, 2), (3, 5)),
            (Direction.UP, Direction.DOWN),
            (State(Pose.HORIZONTAL, (2, 3)), State(Pose.HORIZONTAL, (4, 3))),
        ),
        (
            Pose.VERTICAL,
            ((2, 3), (5, 3)),
            (Direction.LEFT, Direction.RIGHT),
            (State(Pose.VERTICAL, (3, 2)), State(Pose.VERTICAL, (3, 4))),
        ),
    ],
)
def test_successors_exclude_fragile_breaks_and_keep_order(
    pose, fragile_cells, expected_directions, expected_states
):
    """Only legal moves remain, in UP/DOWN/LEFT/RIGHT order."""
    stage = open_stage(fragile=fragile_cells)

    moves = successors(stage, State(pose, (3, 3)))

    assert [action.direction for action, _ in moves] == list(expected_directions)
    assert [state for _, state in moves] == list(expected_states)
