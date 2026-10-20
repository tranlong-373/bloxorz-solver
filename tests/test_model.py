from dataclasses import FrozenInstanceError, replace

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
    assert st.switch_at[(0, 3)] == (st.switches[0],)
    assert st.switch_at[(0, 3)][0].id == "sw1"
    assert (0, 0) not in st.switch_at
    assert st.switch_at.get((0, 0), ()) == ()


@pytest.mark.parametrize("reverse", [False, True])
def test_switch_at_preserves_shared_position_switches(reverse):
    open_a = Switch(
        "sw1", "soft", (0, 3), mode="permanent", set_to="open", bridges=("A",)
    )
    close_b = Switch(
        "sw2", "heavy", (0, 3), mode="permanent", set_to="close", bridges=("B",)
    )
    switches = (close_b, open_a) if reverse else (open_a, close_b)
    st = replace(make_stage(), switches=switches)

    lookup = st.switch_at

    assert lookup == {(0, 3): (open_a, close_b)}
    assert lookup[(0, 3)][0] is open_a
    assert lookup[(0, 3)][1] is close_b
    assert [
        (s.id, s.kind, s.mode, s.set_to, s.bridges) for s in lookup[(0, 3)]
    ] == [
        ("sw1", "soft", "permanent", "open", ("A",)),
        ("sw2", "heavy", "permanent", "close", ("B",)),
    ]
    assert st.switches is switches
    assert st.switches == ((close_b, open_a) if reverse else (open_a, close_b))


def test_switch_at_groups_distinct_positions():
    first = make_stage().switches[0]
    second = Switch("sw2", "heavy", first.pos, mode="toggle", bridges=("b1",))
    split = Switch("sw3", "split", (2, 2), targets=((0, 0), (2, 3)))
    st = replace(make_stage(), switches=(second, split, first))

    assert st.switch_at == {first.pos: (first, second), split.pos: (split,)}
    assert st.switch_at[split.pos][0] is split
    assert st.switch_at[split.pos][0].targets == ((0, 0), (2, 3))


def test_switch_at_without_switches():
    st = replace(make_stage(), switches=())
    assert st.switch_at == {}
    assert st.switch_at.get((0, 3), ()) == ()


def test_switch_at_is_cached():
    st = make_stage()
    assert st.switch_at is st.switch_at
