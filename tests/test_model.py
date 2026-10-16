from dataclasses import FrozenInstanceError

import pytest

from bloxorz.model import Pose, State
from bloxorz.stage import Bridge, Stage, Switch


def make_stage() -> Stage:
    return Stage(
        id="t",
        group="G1",
        grid=("#####", "#.B.#", "####G"),
        start=(0, 0),
        goal=(2, 4),
        bridges=(Bridge("b1", ((1, 2),)),),
        switches=(Switch("sw1", "soft", (0, 3), mode="toggle", bridges=("b1",)),),
    )


def test_state_is_frozen():
    s = State(Pose.STANDING, (1, 1))
    with pytest.raises(FrozenInstanceError):
        s.pos = (0, 0)


def test_state_hashable():
    s = State(Pose.STANDING, (1, 1))
    assert {s: 1}[State(Pose.STANDING, (1, 1))] == 1
    assert len({s, State(Pose.STANDING, (1, 1))}) == 1


def test_split_cubes_are_ordered():
    a = State(None, (5, 5), (1, 1))
    b = State(None, (1, 1), (5, 5))
    assert a == b and hash(a) == hash(b)
    assert a.pos == (1, 1) and a.cube2 == (5, 5)


def test_cell_out_of_bounds_is_empty():
    assert make_stage().cell((-1, 0)) == "."


def test_switch_at():
    st = make_stage()
    assert st.switch_at[(0, 3)].id == "sw1"
    assert (0, 0) not in st.switch_at
