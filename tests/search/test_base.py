import builtins
import threading
import tracemalloc

import pytest

import bloxorz.search.base as base
import bloxorz.search.cost as cost_module
import bloxorz.verify as verify_module
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.search.base import (
    ALGORITHMS, Limits, SearchAborted, SearchContext, reconstruct, register, run,
)
from bloxorz.stage import Stage

A = Action(Direction.RIGHT)
PLAN = (A, A)


@pytest.fixture(autouse=True)
def clean_registry():
    before = dict(ALGORITHMS)
    yield
    ALGORITHMS.clear()
    ALGORITHMS.update(before)


@pytest.fixture
def stage():
    return Stage('t', 'G1', ('###G',), (0, 0), (0, 3))


@pytest.fixture
def clock(monkeypatch):
    # Manual monotonic clock: no sleep, scheduling assumptions or long loops.
    now = [0.0]
    monkeypatch.setattr(base.time, 'perf_counter', lambda: now[0])
    return now


def test_solved(stage):
    register('_t3')(lambda st, ctx: PLAN)
    r = run('_t3', stage)
    assert r.status == 'solved' and r.length == 2 and r.cost == 2.0
    assert r.algorithm == '_t3' and r.stage_id == 't'


def test_unsolvable(stage):
    register('_tn')(lambda st, ctx: None)
    assert run('_tn', stage).status == 'unsolvable'


@pytest.mark.parametrize('cancelled', [False, True])
def test_preflight_does_not_call_solver(stage, clock, cancelled):
    calls = []
    register('_pre')(lambda st, ctx: calls.append(1))
    cancel = threading.Event()
    if cancelled:
        cancel.set()
    r = run('_pre', stage, Limits(timeout_s=0 if not cancelled else 60, cancel=cancel))
    assert r.status == ('cancelled' if cancelled else 'timeout')
    assert r.expanded == 0 and calls == []


def test_limit_check_is_independent_of_expansion(clock):
    ctx = SearchContext(Limits(timeout_s=1))
    ctx.check_limits()
    ctx.check_limits()
    assert ctx.expanded == 0
    ctx.tick()
    assert ctx.expanded == 1
    clock[0] = 1  # equality reaches the deadline
    with pytest.raises(SearchAborted, match='timeout'):
        ctx.check_limits()
    with pytest.raises(SearchAborted, match='timeout'):
        ctx.tick()
    assert ctx.expanded == 1


@pytest.mark.parametrize('cancelled', [False, True])
def test_limits_with_fewer_than_1000_nodes(stage, clock, cancelled):
    cancel = threading.Event()
    def solver(st, ctx):
        ctx.tick()
        if cancelled:
            cancel.set()
        else:
            clock[0] = 2
        ctx.tick()
        pytest.fail('must abort on second tick')
    register('_small')(solver)
    r = run('_small', stage, Limits(timeout_s=1, cancel=cancel))
    assert r.status == ('cancelled' if cancelled else 'timeout')
    assert r.expanded == 1


@pytest.mark.parametrize('actions', [PLAN, None])
@pytest.mark.parametrize('cancelled', [False, True])
def test_check_after_solver_returns_without_tick(stage, clock, actions, cancelled):
    cancel = threading.Event()
    def solver(st, ctx):
        if cancelled:
            cancel.set()
        else:
            clock[0] = 2
        return actions
    register('_return')(solver)
    r = run('_return', stage, Limits(timeout_s=1, cancel=cancel))
    assert r.status == ('cancelled' if cancelled else 'timeout')
    assert r.expanded == 0 and r.actions == ()


def test_cancellation_precedes_expired_deadline(clock):
    cancel = threading.Event()
    cancel.set()
    ctx = SearchContext(Limits(timeout_s=0, cancel=cancel))
    with pytest.raises(SearchAborted, match='cancelled'):
        ctx.check_limits()


def test_solver_exception(stage):
    def boom(st, ctx):
        raise ValueError('boom')
    register('_te')(boom)
    r = run('_te', stage)
    assert r.status == 'error' and 'boom' in r.message


def test_peak_memory(stage):
    def alloc(st, ctx):
        data = list(range(10_000))
        return PLAN if data else None
    register('_tm')(alloc)
    r = run('_tm', stage, measure_memory=True)
    assert r.status == 'solved' and r.peak_mem_bytes > 0 and r.message == ''
    assert not tracemalloc.is_tracing()


def test_reconstruct():
    s0, s1, s2 = (State(Pose.STANDING, (0, i)) for i in range(3))
    b = Action(Direction.DOWN)
    parents = {s0: None, s1: (s0, A), s2: (s1, b)}
    assert reconstruct(parents, s2) == (A, b)
    assert reconstruct(parents, s0) == ()


def test_unknown_algorithm(stage):
    assert run('nope', stage).status == 'error'


@pytest.mark.parametrize('failure', ['error', 'cancelled', 'timeout', 'illegal', 'not_goal', 'unsolvable', 'expanded'])
def test_memory_failure_keeps_first_result(stage, clock, failure):
    cancel = threading.Event()
    calls = []
    def solver(st, ctx):
        calls.append(st)
        if len(calls) == 2:
            if failure == 'error':
                raise RuntimeError('memory boom')
            if failure == 'cancelled':
                cancel.set()  # post-return check must catch this, without tick
            elif failure == 'timeout':
                clock[0] = 2
            elif failure == 'illegal':
                return (Action(Direction.UP),)
            elif failure == 'not_goal':
                return (A,)
            elif failure == 'unsolvable':
                return None
            elif failure == 'expanded':
                ctx.tick()
        return PLAN
    register('_memory')(solver)
    r = run('_memory', stage, Limits(timeout_s=1, cancel=cancel), measure_memory=True)
    assert (r.status, r.actions, r.length, r.cost, r.expanded, r.time_s) == ('solved', PLAN, 2, 2., 0, 0.)
    assert r.peak_mem_bytes is None and r.message.startswith('memory pass:')
    reason = {'error': 'memory boom', 'cancelled': 'cancelled', 'timeout': 'timeout',
              'illegal': 'fell', 'not_goal': 'chưa tới đích', 'unsolvable': 'status solved -> unsolvable',
              'expanded': 'expanded 0 -> 1'}[failure]
    assert reason in r.message
    assert len(calls) == 2 and calls[0] is stage and calls[1] is stage
    assert not tracemalloc.is_tracing()


@pytest.mark.parametrize('second_solved', [False, True])
def test_unsolvable_memory_pass(stage, second_solved):
    calls = []
    def solver(st, ctx):
        calls.append(1)
        return PLAN if len(calls) == 2 and second_solved else None
    register('_uns_mem')(solver)
    r = run('_uns_mem', stage, measure_memory=True)
    assert r.status == 'unsolvable'
    if second_solved:
        assert r.peak_mem_bytes is None and 'status unsolvable -> solved' in r.message
    else:
        assert r.peak_mem_bytes is not None and r.message == ''
    assert not tracemalloc.is_tracing()


def test_different_valid_memory_solution_is_reported():
    stage = Stage('cycle', 'G1', ('###G',), (0, 0), (0, 3))
    left = Action(Direction.LEFT)
    calls = []
    def solver(st, ctx):
        calls.append(1)
        return PLAN if len(calls) == 1 else (A, left, A, A)
    register('_different')(solver)
    r = run('_different', stage, measure_memory=True)
    assert r.status == 'solved' and r.actions == PLAN and r.cost == 2
    assert r.peak_mem_bytes is None and 'actions' in r.message and 'cost' in r.message


def test_memory_validation_outside_trace_and_timing(stage, clock, monkeypatch):
    phases = []
    calls = []
    def solver(st, ctx):
        calls.append(tracemalloc.is_tracing())
        clock[0] += 1
        return PLAN
    register('_scope')(solver)
    real_verify = verify_module.verify_solution
    def verify(st, actions):
        phases.append(tracemalloc.is_tracing())
        clock[0] += 100  # validation does not affect time_s or solver deadline
        return real_verify(st, actions)
    monkeypatch.setattr(verify_module, 'verify_solution', verify)
    r = run('_scope', stage, measure_memory=True)
    assert r.status == 'solved' and r.time_s == 1 and r.peak_mem_bytes is not None
    assert calls == [False, True] and phases == [False, False]


def test_stage_caches_are_reused_not_cleared(stage):
    calls = []
    def solver(st, ctx):
        calls.append((st, st.__dict__.get('bridge_at'), st.__dict__.get('switch_at')))
        return base.ALGORITHMS['bfs'](st, ctx)
    register('_cache')(solver)
    assert 'bridge_at' not in stage.__dict__ and 'switch_at' not in stage.__dict__
    r = run('_cache', stage, measure_memory=True)
    assert r.peak_mem_bytes is not None
    assert calls[0][1:] == (None, None)
    assert calls[1][0] is stage
    assert calls[1][1] is stage.bridge_at and calls[1][2] is stage.switch_at


@pytest.mark.parametrize('exception', [ImportError('missing dependency'), ValueError('cost bug')])
def test_cost_failure_is_error_not_step_count(stage, monkeypatch, exception):
    def fail(*args):
        raise exception
    monkeypatch.setattr(cost_module, 'move_cost', fail)
    register('_cost')(lambda st, ctx: PLAN)
    r = run('_cost', stage)
    assert r.status == 'error' and type(exception).__name__ in r.message
    assert str(exception) in r.message and r.cost == 0


def test_cost_import_failure_is_not_hidden(stage, monkeypatch):
    original = builtins.__import__
    def import_module(name, *args, **kwargs):
        if name == 'cost':
            raise ImportError('cost unavailable')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', import_module)
    register('_import')(lambda st, ctx: PLAN)
    r = run('_import', stage)
    assert r.status == 'error' and 'ImportError: cost unavailable' in r.message


def test_cost_replay_illegal_action_is_error(stage):
    register('_illegal')(lambda st, ctx: (Action(Direction.UP),))
    r = run('_illegal', stage)
    assert r.status == 'error' and 'action 0: fell' in r.message


def test_cost_replay_sums_real_move_cost():
    stage = Stage('fragile', 'G2', ('#F#G',), (0, 0), (0, 3))
    register('_fragile')(lambda st, ctx: PLAN)
    r = run('_fragile', stage)
    assert r.status == 'solved' and r.cost == 6.0


def test_memory_cost_failure_keeps_first_cost(stage, monkeypatch):
    real_cost = cost_module.move_cost
    calls = []
    def move_cost(*args):
        calls.append(1)
        if len(calls) > 2:
            raise ValueError('memory replay cost')
        return real_cost(*args)
    monkeypatch.setattr(cost_module, 'move_cost', move_cost)
    register('_mem_cost')(lambda st, ctx: PLAN)
    r = run('_mem_cost', stage, measure_memory=True)
    assert r.status == 'solved' and r.cost == 2.0 and r.peak_mem_bytes is None
    assert 'memory replay cost' in r.message and not tracemalloc.is_tracing()


def test_memory_preflight_does_not_call_solver_after_cancel(stage, monkeypatch):
    cancel = threading.Event()
    calls = []
    real_cost = base._path_cost
    def path_cost(st, actions):
        value = real_cost(st, actions)
        cancel.set()  # request arrives between the first search and memory pass
        return value
    monkeypatch.setattr(base, '_path_cost', path_cost)
    def solver(st, ctx):
        calls.append(1)
        return PLAN
    register('_mem_pre')(solver)
    r = run('_mem_pre', stage, Limits(cancel=cancel), measure_memory=True)
    assert calls == [1] and r.status == 'solved' and r.cost == 2
    assert r.peak_mem_bytes is None and 'memory pass: cancelled' in r.message
    assert not tracemalloc.is_tracing()


def test_memory_verification_exception_keeps_first_result(stage, monkeypatch):
    real_verify = verify_module.verify_solution
    calls = []
    def fail(st, actions):
        assert not tracemalloc.is_tracing()
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError('verification bug')
        return real_verify(st, actions)
    monkeypatch.setattr(verify_module, 'verify_solution', fail)
    register('_verify_error')(lambda st, ctx: PLAN)
    r = run('_verify_error', stage, measure_memory=True)
    assert r.status == 'solved' and r.actions == PLAN and r.cost == 2
    assert r.peak_mem_bytes is None and 'verification bug' in r.message
    assert not tracemalloc.is_tracing()


def test_memory_pass_is_not_run_for_first_pass_error(stage):
    calls = []
    def solver(st, ctx):
        calls.append(1)
        raise RuntimeError('first pass error')
    register('_first_error')(solver)
    r = run('_first_error', stage, measure_memory=True)
    assert calls == [1] and r.status == 'error' and r.peak_mem_bytes is None
    assert r.message == 'RuntimeError: first pass error'


@pytest.mark.parametrize('memory', [False, True])
@pytest.mark.parametrize('actions', [(), (A,)])
def test_first_pass_legal_but_not_goal_is_error(stage, memory, actions):
    calls = []
    def solver(st, ctx):
        calls.append(1)
        return actions
    register('_not_goal')(solver)
    r = run('_not_goal', stage, measure_memory=memory)
    assert r.status == 'error' and 'invalid solution: chưa tới đích' in r.message
    assert r.peak_mem_bytes is None and calls == [1]


def test_equal_cost_valid_memory_path_is_pairing_mismatch():
    stage = Stage('two_routes', 'G1', ('#######', '#######', '######G',
                                      '#######', '#######'), (2, 0), (2, 6))
    up, down = Action(Direction.UP), Action(Direction.DOWN)
    first, second = (up,) + (A,) * 6 + (down,), (down,) + (A,) * 6 + (up,)
    assert verify_module.verify_solution(stage, first)[0]
    assert verify_module.verify_solution(stage, second)[0]
    calls = []
    def solver(st, ctx):
        calls.append(1)
        return first if len(calls) == 1 else second
    register('_equal_routes')(solver)
    r = run('_equal_routes', stage, measure_memory=True)
    assert r.status == 'solved' and r.cost == 8 and r.actions == first
    assert r.peak_mem_bytes is None and 'differs from first pass: actions' in r.message
    assert 'invalid solution' not in r.message
