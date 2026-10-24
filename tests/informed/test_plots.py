"""Tests for benchmark/plots.py (tables and charts). Owner: VT5 (task 5.5)."""
import csv

import pytest

from benchmark import plots

FIELDS = ["stage_id", "group", "algorithm", "status", "length", "cost", "expanded",
          "time_ms_median", "time_ms_all", "peak_mem_kb", "verified", "commit", "python", "machine"]


def row(stage_id, group, algorithm, status="solved", length="10", cost="10.0", expanded="50",
        time_ms="1.5", mem="20.0"):
    return {"stage_id": stage_id, "group": group, "algorithm": algorithm, "status": status,
            "length": length, "cost": cost, "expanded": expanded, "time_ms_median": time_ms,
            "time_ms_all": time_ms, "peak_mem_kb": mem, "verified": "True" if status == "solved" else "",
            "commit": "abc1234", "python": "3.12", "machine": "test"}


def sample_rows():
    return [
        row("g1_01", "G1", "bfs", length="7", cost="7.0", expanded="48", time_ms="0.4"),
        row("g1_01", "G1", "ucs", length="7", cost="7.0", expanded="64", time_ms="0.8"),
        row("g1_02", "G1", "bfs", length="19", cost="19.0", expanded="80", time_ms="0.6"),
        # unsolvable rows from the runner have length 0 and cost 0.0
        row("g1_02", "G1", "ucs", status="unsolvable", length="0", cost="0.0", expanded="99", time_ms="0.9"),
        row("g2_01", "G2", "bfs", length="8", cost="12.0", expanded="15"),
        row("g2_01", "G2", "ucs", length="10", cost="10.0", expanded="16"),
        row("g2_01", "G2", "astar", status="timeout", length="", cost="", expanded="", time_ms="", mem=""),
    ]


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _summary(rows, algorithm, group):
    return next(s for s in plots.summary(rows) if s["algorithm"] == algorithm and s["group"] == group)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def test_summary_counts_solved_and_uses_only_solved_rows():
    s = _summary(sample_rows(), "ucs", "G1")
    assert (s["solved"], s["total"]) == (1, 2)
    # the unsolvable row (length 0, 99 nodes) must not pull the numbers down or up
    assert s["length_mean"] == 7 and s["cost_mean"] == 7
    assert s["expanded_median"] == 64 and s["time_ms_median"] == 0.8


def test_summary_has_a_row_for_all_groups():
    s = _summary(sample_rows(), "bfs", plots.ALL)
    assert (s["solved"], s["total"]) == (3, 3)
    assert s["expanded_median"] == 48
    assert s["cost_mean"] == pytest.approx((7 + 19 + 12) / 3)


def test_summary_algorithm_order_follows_algos():
    algos = []
    for s in plots.summary(sample_rows()):
        if s["algorithm"] not in algos:
            algos.append(s["algorithm"])
    assert algos == ["bfs", "ucs", "astar"]


def test_summary_with_no_solved_row_gives_none():
    s = _summary(sample_rows(), "astar", "G2")
    assert (s["solved"], s["total"]) == (0, 1)
    assert s["time_ms_median"] is None and s["cost_mean"] is None


def test_detail_never_writes_zero_for_a_failure():
    d = {(x["stage_id"], x["algorithm"]): x for x in plots.detail(sample_rows())}
    assert d[("g1_02", "ucs")]["length"] is None and d[("g1_02", "ucs")]["cost"] is None
    assert d[("g1_02", "ucs")]["expanded"] == 99  # real count of the search, kept
    assert d[("g2_01", "astar")]["status"] == "timeout"
    assert "| g1_02 | G1 | UCS | unsolvable | – | – | 99 |" in plots.detail_md(sample_rows())


def test_detail_rows_sorted_by_group_then_stage():
    rows = sample_rows()[::-1]
    stages = [d["stage_id"] for d in plots.detail(rows)]
    assert stages == sorted(stages, key=lambda s: (s[:2], s))


def test_md_table_escapes_star_and_aligns_numbers():
    text = plots.md_table(["Thuật toán", "Nút"], [["A* relaxed", 5]], left=1)
    lines = text.splitlines()
    assert lines[1] == "|---|---:|"
    assert lines[2] == "| A\\* relaxed | 5 |"


@pytest.mark.parametrize("value, digits, text", [
    (None, 1, "–"), (7.0, 1, "7"), (12.25, 2, "12.25"), (0.4181, 2, "0.42"), (20.55, 1, "20.6"),
])
def test_fmt(value, digits, text):
    assert plots.fmt(value, digits) == text


def test_make_tables_writes_files_and_drops_stage_30(tmp_path, capsys):
    original = [row("stage_01", "G1", "bfs"), row("stage_23", "G4", "bfs", status="unsolvable", length="0"),
                row("stage_30", "G3", "bfs")]
    paths = plots.make_tables(sample_rows(), tmp_path, original)
    assert sorted(p.name for p in paths) == ["detail.csv", "detail.md", "original.md", "summary.csv", "summary.md"]
    text = (tmp_path / "original.md").read_text(encoding="utf-8")
    assert "33 màn" in text and "dùng 2 màn" in text
    assert "| stage_30 |" not in text
    assert "| stage_23 | G4 | BFS | unsolvable | – | – |" in text  # used stage that fails is kept
    assert "Giải được" in text and "| BFS | G4 | 0/1 |" in text
    assert "stage_30" in capsys.readouterr().out


def test_summary_csv_has_numbers_and_blank_for_missing(tmp_path):
    plots.make_tables(sample_rows(), tmp_path)
    with open(tmp_path / "summary.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    astar = next(r for r in rows if r["algorithm"] == "astar" and r["group"] == "G2")
    assert (astar["solved"], astar["total"], astar["cost_mean"]) == ("0", "1", "")
    assert not (tmp_path / "original.md").exists()


def test_notes_separate_summary_and_detail_tables(tmp_path):
    original = [row("stage_01", "G1", "bfs")]
    plots.make_tables(sample_rows(), tmp_path, original)
    summary_md = (tmp_path / "summary.md").read_text(encoding="utf-8")
    detail_md = (tmp_path / "detail.md").read_text(encoding="utf-8")
    assert "chỉ tính trên các màn giải được" in summary_md and "kể cả lần không giải được" not in summary_md
    assert "kể cả lần không giải được" in detail_md and "chỉ tính trên các màn giải được" not in detail_md
    original_md = (tmp_path / "original.md").read_text(encoding="utf-8")
    assert "chỉ tính trên các màn giải được" in original_md and "kể cả lần không giải được" in original_md


def test_memory_unit_is_kib_everywhere(tmp_path):
    plots.make_tables(sample_rows(), tmp_path)
    for name in ("summary.md", "detail.md"):
        text = (tmp_path / name).read_text(encoding="utf-8")
        assert "(KiB)" in text and "KB" not in text


def test_empty_csv_gives_clear_error(tmp_path, capsys):
    with pytest.raises(ValueError, match="không có dòng"):
        plots.make_tables([], tmp_path / "a")
    with pytest.raises(ValueError, match="không có dòng"):
        plots.make_tables(sample_rows(), tmp_path / "b", [])
    with pytest.raises(ValueError, match="không có dòng"):
        plots.write_csv(tmp_path / "x.csv", [])
    # original CSV with only stage_30: error before the main tables are written
    with pytest.raises(ValueError, match="stage_30"):
        plots.make_tables(sample_rows(), tmp_path / "c", [row("stage_30", "G3", "bfs")])
    assert not (tmp_path / "a").exists() and not (tmp_path / "b").exists() and not (tmp_path / "c").exists()

    data = write(tmp_path / "results.csv", [])
    assert plots.main([str(data), "--out", str(tmp_path / "out")]) == 1
    assert "Lỗi" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


# ---------------------------------------------------------------------------
# Charts (matplotlib is not installed on CI)
# ---------------------------------------------------------------------------

def test_main_writes_tables_and_five_charts(tmp_path):
    pytest.importorskip("matplotlib")
    Image = pytest.importorskip("PIL.Image")
    data = write(tmp_path / "results.csv", sample_rows())
    write(tmp_path / "original.csv", [row("stage_01", "G1", "bfs"), row("stage_30", "G3", "bfs")])
    assert plots.main([str(data), "--out", str(tmp_path / "out")]) == 0

    tables = sorted(p.name for p in (tmp_path / "out" / "tables").iterdir())
    assert tables == ["detail.csv", "detail.md", "original.md", "summary.csv", "summary.md"]
    figures = sorted(p.name for p in (tmp_path / "out" / "figures").iterdir())
    assert figures == ["expanded.png", "heuristics.png", "length_cost.png", "memory.png", "time.png"]
    for name in figures:
        with Image.open(tmp_path / "out" / "figures" / name) as img:
            assert min(img.info["dpi"]) >= 150


def test_charts_when_ucs_fails_but_astar_solves(tmp_path):
    # Heuristic chart has no % for that stage, it must not crash or mark A* as failed.
    # A* may also expand a bit more than UCS (ties at f = C*), the bar must stay inside the chart
    pytest.importorskip("matplotlib")
    rows = [row("g1_01", "G1", "ucs", status="timeout", length="", cost="", expanded="5000", time_ms="60000"),
            row("g1_01", "G1", "astar", expanded="300"), row("g1_01", "G1", "astar_manhattan", expanded="900"),
            row("g1_02", "G1", "ucs", expanded="100"), row("g1_02", "G1", "astar", expanded="104"),
            row("g1_02", "G1", "astar_manhattan", expanded="100")]
    paths = plots.make_figures(rows, tmp_path)
    assert len(paths) == 5 and all(p.stat().st_size > 0 for p in paths)


def test_two_path_stage_found_for_the_chart():
    assert plots._two_path_stages(sample_rows()) == ["g2_01"]
    # a solved row with a missing number is skipped, not compared with None
    rows = sample_rows() + [row("g3_01", "G3", "bfs", length=""), row("g3_01", "G3", "ucs")]
    assert plots._two_path_stages(rows) == ["g2_01"]


def test_charts_skip_when_csv_has_only_bfs_ucs_dfs(tmp_path, capsys):
    # vd chạy benchmark.run --algos bfs ucs dfs: không có A* thì không có hình so sánh heuristic
    pytest.importorskip("matplotlib")
    rows = [r for r in sample_rows() if r["algorithm"] != "astar"]
    rows += [row("g1_01", "G1", "dfs", length="45", cost="45.0")]
    paths = plots.make_figures(rows, tmp_path)
    assert sorted(p.name for p in paths) == ["expanded.png", "length_cost.png", "memory.png", "time.png"]
    assert not (tmp_path / "heuristics.png").exists()
    assert "Bỏ qua heuristics.png" in capsys.readouterr().out


def test_charts_skip_when_nothing_to_compare(tmp_path, capsys):
    pytest.importorskip("matplotlib")
    paths = plots.make_figures([row("g1_01", "G1", "dfs")], tmp_path)
    assert sorted(p.name for p in paths) == ["expanded.png", "memory.png", "time.png"]
    out = capsys.readouterr().out
    assert "Bỏ qua length_cost.png" in out and "Bỏ qua heuristics.png" in out
    # A* có mà thiếu UCS thì cũng không có gì để chia
    paths = plots.make_figures([row("g1_01", "G1", "astar")], tmp_path / "b")
    assert "heuristics.png" not in [p.name for p in paths]
    # thuật toán lạ thì bỏ qua hết, không lỗi chia 0
    assert plots.make_figures([row("g1_01", "G1", "greedy")], tmp_path / "c") == []
