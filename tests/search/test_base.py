import threading
import time

import pytest

from bloxorz.model import Action, Direction, Pose, State
from bloxorz.search.base import ALGORITHMS, Limits, reconstruct, register, run
from bloxorz.stage import Stage

A = Action(Direction.RIGHT)


@pytest.fixture(autouse=True)
def clean_registry():
    before = set(ALGORITHMS)
    yield
    for k in set(ALGORITHMS) - before:
        del ALGORITHMS[k]


@pytest.fixture
def stage():
    return Stage("t", "G1", ("###", "##G"), (0, 0), (1, 2))


def test_solved(stage):
    register("_t3")(lambda st, ctx: (A, A, A))
    r = run("_t3", stage)
    assert r.status == "solved" and r.length == 3 and r.cost == 3.0
    assert r.algorithm == "_t3" and r.stage_id == "t"


def test_unsolvable(stage):
    register("_tn")(lambda st, ctx: None)
    assert run("_tn", stage).status == "unsolvable"


def test_timeout(stage):
    @register("_tt")
    def spin(st, ctx):
        while True:
            ctx.tick()

    t0 = time.perf_counter()
    r = run("_tt", stage, Limits(timeout_s=0.2))
    assert r.status == "timeout" and time.perf_counter() - t0 < 1


def test_cancelled(stage):
    @register("_tc")
    def spin(st, ctx):
        while True:
            ctx.tick()

    cancel = threading.Event()
    cancel.set()
    assert run("_tc", stage, Limits(cancel=cancel)).status == "cancelled"


def test_solver_exception(stage):
    @register("_te")
    def boom(st, ctx):
        raise ValueError("boom")

    r = run("_te", stage)
    assert r.status == "error" and "boom" in r.message


def test_peak_memory(stage):
    @register("_tm")
    def alloc(st, ctx):
        data = list(range(10_000))
        return (A,) if data else None

    assert run("_tm", stage, measure_memory=True).peak_mem_bytes > 0


def test_reconstruct():
    s0, s1, s2 = (State(Pose.STANDING, (0, i)) for i in range(3))
    b = Action(Direction.DOWN)
    parents = {s0: None, s1: (s0, A), s2: (s1, b)}
    assert reconstruct(parents, s2) == (A, b)
    assert reconstruct(parents, s0) == ()


def test_unknown_algorithm(stage):
    assert run("nope", stage).status == "error"
