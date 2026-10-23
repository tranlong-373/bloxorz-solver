"""Benchmark orchestration tests, using the real shared model and engine."""
import csv
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from benchmark import run as bench
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.search import Limits, SearchResult
from bloxorz.search.base import ALGORITHMS
from bloxorz.stage import Stage

ROOT = Path(__file__).resolve().parents[2]
STAGE = Stage('one', 'G1', ('###G',), (0, 0), (0, 3))
ACTIONS = (Action(Direction.RIGHT),) * 2
META = dict(commit='abc', python='test', machine='test')


def solved(**changes):
    return replace(SearchResult('bfs', 'one', 'solved', ACTIONS, 2, 2., 3, .01), **changes)


def write_stage(folder, name='one'):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f'{name}.json').write_text(json.dumps(dict(id=name, group='G1', grid=['S##G'])), encoding='utf-8')


def read_output(out):
    with out.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        assert tuple(reader.fieldnames) == bench.FIELDS
        rows = list(reader)
    records = [json.loads(line) for line in out.with_suffix('.csv.runs.jsonl').read_text(encoding='utf-8').splitlines()]
    return rows, records


def test_real_cli_csv_and_no_gui(tmp_path):
    stages = tmp_path / 'stages'
    write_stage(stages)
    write_stage(stages, 'two')
    out = tmp_path / 'nested' / 'run.csv'
    code = ('import sys; from benchmark.run import main; '
            'result = main(sys.argv[1:]); '
            'assert not any(m == "ursina" or m.startswith("bloxorz.gui") for m in sys.modules); '
            'raise SystemExit(result)')
    process = subprocess.run([sys.executable, '-c', code, '--stages', str(stages),
                              '--algos', 'bfs', 'dfs', 'ucs', '--repeat', '2', '--out', str(out)],
                             cwd=ROOT, capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    rows, raw = read_output(out)
    assert len(rows) == 6 and len(raw) == 18
    assert all(r['verified'] == 'True' and r['status'] == 'solved' for r in rows)
    assert all(len(r['time_ms_all'].split(';')) == 2 for r in rows)
    assert all(len(r['actions']) == 2 for r in raw)
    assert State(Pose.STANDING, STAGE.start).pos == (0, 0)


def test_call_counts_median_and_verifies_memory_result(tmp_path, monkeypatch):
    stages = tmp_path / 'stages'
    write_stage(stages)
    times = iter([.005, .001, .003, .002, .099, 80.])
    calls, verified = [], []
    def fake_run(algorithm, stage, limits, measure_memory=False):
        calls.append((measure_memory, stage, limits))
        return solved(time_s=next(times), peak_mem_bytes=2048 if measure_memory else None)
    real_verify = bench.verify_solution
    def verify(stage, actions):
        verified.append(actions)
        return real_verify(stage, actions)
    monkeypatch.setattr(bench, 'run', fake_run)
    monkeypatch.setattr(bench, 'verify_solution', verify)
    out = tmp_path / 'run.csv'
    assert bench.main(['--stages', str(stages), '--algos', 'bfs', '--out', str(out)]) == 0
    rows, records = read_output(out)
    assert [c[0] for c in calls] == [False] * 5 + [True]
    assert len({id(c[1]) for c in calls}) == 6
    assert len(verified) == 6
    assert rows[0]['time_ms_median'] == '3.0'
    assert rows[0]['time_ms_all'] == '5.0;1.0;3.0;2.0;99.0'
    assert rows[0]['peak_mem_kb'] == '2.0'
    assert records[-1]['phase'] == 'memory'


def test_real_memory_api_performs_two_searches(monkeypatch):
    calls = []
    def solver(stage, ctx):
        calls.append(stage)
        return ACTIONS
    monkeypatch.setitem(ALGORITHMS, '_bench', solver)
    records = [bench.measure(STAGE, '_bench', Limits(), False) for _ in range(5)]
    records.append(bench.measure(STAGE, '_bench', Limits(), True))
    assert len(calls) == 7
    assert all(r['verified'] is True for r in records)
    assert records[-1]['peak_mem_bytes'] is not None


@pytest.mark.parametrize('status', ['timeout', 'cancelled', 'error', 'unsolvable'])
def test_failure_states_retained(status, tmp_path, monkeypatch):
    write_stage(tmp_path / 'stages')
    monkeypatch.setattr(bench, 'run', lambda *a, **kw: SearchResult('bfs', 'one', status, message='reason'))
    out = tmp_path / 'run.csv'
    bench.main(['--stages', str(tmp_path / 'stages'), '--algos', 'bfs', '--repeat', '1', '--out', str(out)])
    rows, records = read_output(out)
    assert rows[0]['status'] == status
    assert rows[0]['peak_mem_kb'] == rows[0]['verified'] == ''
    assert all(r['message'] == 'reason' for r in records)


def test_invalid_solution_and_mixed_status(monkeypatch):
    results = iter([solved(), solved(status='timeout'), solved(actions=())])
    monkeypatch.setattr(bench, 'run', lambda *a, **kw: next(results))
    records = [bench.measure(STAGE, 'bfs', Limits(), m) for m in (False, False, True)]
    row = bench.summarize(STAGE, 'bfs', records, META)
    assert row['status'] == 'mixed' and row['verified'] is False
    assert records[-1]['effective_status'] == 'verification_failed'
    assert records[-1]['verification_message'] == 'chưa tới đích'
    assert row['time_ms_all'] == '10.0;10.0'


def test_all_invalid_solutions_fail(monkeypatch):
    monkeypatch.setattr(bench, 'run', lambda *a, **kw: solved(actions=()))
    records = [bench.measure(STAGE, 'bfs', Limits(), m) for m in (False, True)]
    assert bench.summarize(STAGE, 'bfs', records, META)['status'] == 'verification_failed'


@pytest.mark.parametrize('field', ['length', 'cost', 'expanded'])
def test_differing_metrics_blank_and_preserved(field, monkeypatch):
    results = iter([solved(), solved(**{field: 99}), solved()])
    monkeypatch.setattr(bench, 'run', lambda *a, **kw: next(results))
    records = [bench.measure(STAGE, 'bfs', Limits(), m) for m in (False, False, True)]
    row = bench.summarize(STAGE, 'bfs', records, META)
    assert row[field] is None and records[1][field] == 99


def test_original_excludes_only_stage_30(tmp_path, monkeypatch, capsys):
    # Isolate dataset filtering from which algorithms are currently implemented.
    for algorithm in bench.DEFAULT_ALGOS:
        monkeypatch.setitem(bench.ALGORITHMS, algorithm, lambda stage, ctx: None)
    calls = []
    def fake(algorithm, stage, limits, measure_memory=False):
        calls.append(stage.id)
        return SearchResult(algorithm, stage.id, 'unsolvable')
    monkeypatch.setattr(bench, 'run', fake)
    out = tmp_path / 'run.csv'
    assert bench.main(['--stages', str(ROOT / 'stages/original'), '--algos',
                       *bench.DEFAULT_ALGOS, '--repeat', '1', '--out', str(out)]) == 0
    rows, _ = read_output(out)
    assert len(rows) == 160
    expected_ids = {f'stage_{i:02}' for i in range(1, 34)} - {'stage_30'}
    assert set(calls) == expected_ids
    assert {row['stage_id'] for row in rows} == expected_ids
    assert all(row['status'] == 'unsolvable' for row in rows)
    assert 'Excluded stage_30: dataset decision' in capsys.readouterr().out


def test_same_id_outside_original_is_kept(tmp_path, monkeypatch):
    write_stage(tmp_path / 'stages', 'stage_30')
    out = tmp_path / 'run.csv'
    assert bench.main(['--stages', str(tmp_path / 'stages'), '--algos', 'bfs', '--repeat', '1', '--out', str(out)]) == 0
    assert read_output(out)[0][0]['stage_id'] == 'stage_30'


def test_unknown_algorithm_has_error_rows(tmp_path, capsys):
    write_stage(tmp_path / 'stages')
    out = tmp_path / 'run.csv'
    assert bench.main(['--stages', str(tmp_path / 'stages'), '--algos', 'absent', '--repeat', '1', '--out', str(out)]) == 1
    rows, records = read_output(out)
    assert rows[0]['status'] == 'error' and rows[0]['algorithm'] == 'absent'
    assert 'unknown algorithm' in records[0]['message']
    assert 'Unavailable algorithms' in capsys.readouterr().out


@pytest.mark.parametrize('args', [ ['--repeat', '0'], ['--repeat', '-1'], ['--repeat', 'x'],
    ['--timeout', '0'], ['--timeout', '-1'], ['--timeout', 'nan'], ['--timeout', 'inf'],
    ['--algos', 'bfs', 'bfs'] ])
def test_invalid_arguments(args):
    with pytest.raises(SystemExit) as exc:
        bench.main(args)
    assert exc.value.code == 2


def test_missing_and_empty_directory(tmp_path):
    for folder in (tmp_path, tmp_path / 'absent'):
        with pytest.raises(SystemExit) as exc:
            bench.main(['--stages', str(folder)])
        assert exc.value.code == 2


def test_metadata_fallback(monkeypatch):
    def missing(*a, **kw):
        raise FileNotFoundError('git')
    monkeypatch.setattr(bench.subprocess, 'run', missing)
    monkeypatch.setattr(bench.platform, 'processor', lambda: '')
    assert 'outside repository' in bench.metadata()['commit']
    assert 'processor unavailable' in bench.metadata()['machine']


@pytest.mark.parametrize('failure', ['error', 'timeout', 'cancelled', 'invalid', 'unsolvable', 'different'])
def test_real_memory_failure_retains_message_and_blank_csv_peak(tmp_path, monkeypatch, capsys, failure):
    from bloxorz.search.base import SearchAborted

    write_stage(tmp_path / 'stages')
    calls = []
    def solver(stage, ctx):
        calls.append(stage)
        # repeat=1: timing search, memory API first search, then traced search.
        if len(calls) == 3:
            if failure == 'error':
                raise RuntimeError('traced search bug')
            if failure in ('timeout', 'cancelled'):
                raise SearchAborted(failure)
            if failure == 'invalid':
                return (ACTIONS[0],)
            if failure == 'unsolvable':
                return None
            if failure == 'different':
                return (ACTIONS[0], Action(Direction.LEFT), *ACTIONS)
        return ACTIONS
    monkeypatch.setitem(ALGORITHMS, '_memory_integration', solver)
    out = tmp_path / 'run.csv'
    assert bench.main(['--stages', str(tmp_path / 'stages'), '--algos', '_memory_integration',
                       '--repeat', '1', '--out', str(out)]) == 0
    rows, records = read_output(out)
    assert len(calls) == 3 and len(records) == 2
    assert rows[0]['status'] == 'solved' and rows[0]['verified'] == 'True'
    assert rows[0]['peak_mem_kb'] == ''
    assert records[0]['message'] == ''
    assert records[-1]['phase'] == 'memory' and records[-1]['peak_mem_bytes'] is None
    assert records[-1]['message'].startswith('memory pass:')
    reasons = {'error': 'traced search bug', 'timeout': 'timeout', 'cancelled': 'cancelled',
               'invalid': 'invalid solution', 'unsolvable': 'status solved -> unsolvable',
               'different': 'differs from first pass'}
    assert reasons[failure] in records[-1]['message']
    assert records[-1]['message'] in capsys.readouterr().out
