"""Headless benchmark CLI (task 1.6).

CSV times are medians of *all* untraced search times returned by run(), excluding
loading, replay and cost calculation. A separate run(measure_memory=True) invokes
one untraced search and, on solved/unsolvable, one traced search. Its time is never
included in the median. Base validates both solved paths outside search timing
and tracing; the runner also verifies every returned solved result. The API does
not expose the traced pass's individual result, so JSONL is not its raw evidence.
A peak is retained only when both searches match in status/actions/cost/expanded;
a different valid path is a pairing mismatch, not proof of an invalid solution.

Each API call receives a fresh Stage. Within the memory call the traced search
reuses bridge_at/switch_at data caches warmed by the untraced search/replay.
Peak therefore excludes rebuilding these caches and excludes validation/replay;
it is not cold Stage setup or total process memory. Heuristic table caches are
separate: none exist in the current placeholder implementation.

The adjacent <output>.runs.jsonl preserves every returned result, actions,
verification messages, configuration and metadata. Mixed outcomes get status
'mixed'; differing length/cost/expanded fields are blank instead of selecting one
run. Invalid returned solutions get 'verification_failed'. No shared result type
is changed. Memory units: peak_mem_kb = traced Python bytes / 1024 (KiB, not RSS).
A* must build its heuristic inside the solver on every invocation; the current
A* and heuristic modules are placeholders, so that requirement is unverified.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import statistics
import subprocess
from dataclasses import asdict
from pathlib import Path

from bloxorz.loader import LevelError, list_stages
from bloxorz.search import ALGORITHMS, Limits, SearchResult, run
from bloxorz.stage import Stage
from bloxorz.verify import verify_solution

FIELDS = (
    'stage_id', 'group', 'algorithm', 'status', 'length', 'cost', 'expanded',
    'time_ms_median', 'time_ms_all', 'peak_mem_kb', 'verified', 'commit',
    'python', 'machine',
)
DEFAULT_ALGOS = ('bfs', 'dfs', 'ucs', 'astar', 'astar_manhattan')


def metadata() -> dict:
    """Resolve revision from the caller's cwd; explicitly label non-Git runs."""
    try:
        commit = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'], check=True,
            capture_output=True, text=True, timeout=5,
        ).stdout.strip() or 'unknown (empty git revision)'
    except (OSError, subprocess.SubprocessError):
        commit = 'unknown (git unavailable or outside repository)'
    return dict(commit=commit, python=platform.python_version(),
                machine=platform.processor() or f'{platform.machine() or "unknown"} (processor unavailable)')


def measure(stage: Stage, algorithm: str, limits: Limits, memory: bool) -> dict:
    # Rebuild Stage to avoid warming cached_property maps across independent runs.
    fresh = Stage(stage.id, stage.group, stage.grid, stage.start, stage.goal,
                  stage.bridges, stage.switches)
    try:
        result = run(algorithm, fresh, limits, measure_memory=memory)
    except Exception as exc:
        result = SearchResult(algorithm, stage.id, 'error',
                              message=f'{type(exc).__name__}: {exc}')
    verified, verification_message = None, ''
    if result.status == 'solved':
        try:
            verified, verification_message = verify_solution(fresh, result.actions)
        except Exception as exc:
            verified, verification_message = False, f'{type(exc).__name__}: {exc}'
    record = asdict(result)
    record['actions'] = [dict(direction=a.direction.value, cube=a.cube)
                         for a in result.actions]
    record.update(phase='memory' if memory else 'time', verified=verified,
                  verification_message=verification_message,
                  effective_status='verification_failed' if verified is False else result.status)
    return record


def summarize(stage: Stage, algorithm: str, records: list[dict], meta: dict) -> dict:
    timed = [r for r in records if r['phase'] == 'time']
    memory = records[-1]
    statuses = {r['effective_status'] for r in records}
    times = [r['time_s'] * 1000 for r in timed]
    solved = [r for r in records if r['status'] == 'solved']
    row = dict(stage_id=stage.id, group=stage.group, algorithm=algorithm,
               status=next(iter(statuses)) if len(statuses) == 1 else 'mixed',
               time_ms_median=statistics.median(times),
               time_ms_all=';'.join(str(t) for t in times),
               peak_mem_kb=None if memory['peak_mem_bytes'] is None else memory['peak_mem_bytes'] / 1024,
               verified=all(r['verified'] for r in solved) if solved else None,
               **meta)
    for field in ('length', 'cost', 'expanded'):
        values = {r[field] for r in records}
        row[field] = next(iter(values)) if len(values) == 1 else None
    return row


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return number


def positive_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('must be finite and positive')
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--stages', type=Path, default=Path('stages/bench'))
    parser.add_argument('--algos', nargs='+', default=list(DEFAULT_ALGOS))
    parser.add_argument('--repeat', type=positive_int, default=5)
    parser.add_argument('--timeout', type=positive_float, default=60.0)
    parser.add_argument('--out', type=Path, default=Path('results/run.csv'))
    args = parser.parse_args(argv)
    if len(set(args.algos)) != len(args.algos):
        parser.error('--algos contains duplicates')
    if not args.stages.is_dir():
        parser.error(f'stage directory does not exist: {args.stages}')
    try:
        stages = list_stages(args.stages)
    except (LevelError, OSError) as exc:
        parser.error(str(exc))
    original = Path(__file__).resolve().parents[1] / 'stages' / 'original'
    if args.stages.resolve() == original.resolve():
        if any(s.id == 'stage_30' for s in stages):
            print('Excluded stage_30: dataset decision 2026-10-21; retain the other original stages.')
        stages = [s for s in stages if s.id != 'stage_30']
    if not stages:
        parser.error(f'no stages in {args.stages}; the planned bench set has 17 stages')
    unavailable = [a for a in args.algos if a not in ALGORITHMS]
    if unavailable:
        print(f'Unavailable algorithms (recorded as error, no substitution): {", ".join(unavailable)}')
    print(f'{len(stages)} stages x {len(args.algos)} configurations; '
          f'{args.repeat} timing calls + 1 memory API call per pair.')
    print('Base validates both solved paths; JSONL stores returned API results only. '
          'Memory requires deterministic pairing; peak_mem_kb uses bytes / 1024 (KiB), '
          'with Stage data caches warm and validation/replay outside tracing.')
    meta = metadata()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    raw_path = args.out.with_suffix(args.out.suffix + '.runs.jsonl')
    limits = Limits(timeout_s=args.timeout)
    failed = bool(unavailable)
    with args.out.open('w', newline='', encoding='utf-8') as csv_file, raw_path.open('w', encoding='utf-8') as raw:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
        writer.writeheader()
        total = len(stages) * len(args.algos)
        index = 0
        for stage in stages:
            for algorithm in args.algos:
                records = []
                for i in range(args.repeat + 1):
                    record = measure(stage, algorithm, limits, i == args.repeat)
                    records.append(record)
                    raw.write(json.dumps(dict(record, group=stage.group,
                                              iteration=i + 1 if i < args.repeat else 1,
                                              timeout_s=args.timeout, repeat=args.repeat, **meta),
                                         ensure_ascii=False) + '\n')
                    raw.flush()
                row = summarize(stage, algorithm, records, meta)
                writer.writerow(row)
                csv_file.flush()
                if records[-1]['message']:
                    print(f'{stage.id} {algorithm} memory API: {records[-1]["message"]} (see JSONL)')
                index += 1
                differences = [key for key in ('status', 'length', 'cost', 'expanded')
                               if len({r['effective_status'] if key == 'status' else r[key] for r in records}) > 1]
                print(f'[{index}/{total}] {stage.id} {algorithm} {row["status"]} '
                      f'{row["time_ms_median"]:.3f} ms'
                      + (f' differing: {", ".join(differences)} (see JSONL)' if differences else ''))
                failed |= row['status'] in ('mixed', 'error', 'verification_failed')
    print(f'CSV: {args.out}; raw returned results: {raw_path}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
