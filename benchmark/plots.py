"""python -m benchmark.plots: tables and charts from the CSV. Owner: VT5 (task 5.5)."""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

ALGOS = ["bfs", "dfs", "ucs", "astar", "astar_manhattan"]
LABELS = {"bfs": "BFS", "dfs": "DFS", "ucs": "UCS", "astar": "A* relaxed", "astar_manhattan": "A* manhattan"}
# Mỗi thuật toán 1 màu cố định ở mọi biểu đồ
COLORS = {"bfs": "#2a78d6", "dfs": "#eb6834", "ucs": "#1baf7a", "astar": "#eda100", "astar_manhattan": "#e87ba4"}
GROUPS = ["G1", "G2", "G3", "G4", "G5"]
ALL = "Tất cả"
DASH = "–"
# Mã trạng thái theo mẫu báo cáo, chỉ dùng trong bảng .md (CSV giữ nguyên status gốc)
STATUS_CODE = {"solved": "OK", "unsolvable": "NOSOL", "timeout": "TLE"}
DROPPED = "stage_30"  # nhóm loại màn 30 từ 21/10, không đưa vào bảng, mẫu số hay biểu đồ

INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(row, key):
    value = (row.get(key) or "").strip() if row else ""
    return float(value) if value else None


def solved(row):
    return row is not None and row["status"] == "solved"


def fmt(value, digits=1):
    if value is None:
        return DASH
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.{digits}f}"


def ordered(values, order):
    return [v for v in order if v in values] + sorted(set(values) - set(order))


def stage_order(rows):
    return sorted({(r["group"], r["stage_id"]) for r in rows})


def _median(rows, key):
    values = [v for v in (num(r, key) for r in rows) if v is not None]
    return statistics.median(values) if values else None


def _mean(rows, key):
    values = [v for v in (num(r, key) for r in rows) if v is not None]
    return statistics.mean(values) if values else None


def summary(rows):
    """One row per algorithm x group, numbers only from solved stages."""
    out = []
    groups = ordered({r["group"] for r in rows}, GROUPS)
    for algo in ordered({r["algorithm"] for r in rows}, ALGOS):
        for group in groups + [ALL]:
            part = [r for r in rows if r["algorithm"] == algo and group in (ALL, r["group"])]
            if not part:
                continue
            ok = [r for r in part if solved(r)]
            out.append({
                "algorithm": algo, "group": group, "solved": len(ok), "total": len(part),
                "time_ms_median": _median(ok, "time_ms_median"),
                "peak_mem_kb_median": _median(ok, "peak_mem_kb"),
                "expanded_median": _median(ok, "expanded"),
                "length_mean": _mean(ok, "length"),
                "cost_mean": _mean(ok, "cost"),
            })
    return out


def detail(rows):
    """One row per stage x algorithm; length/cost only when solved (never 0 for a failure)."""
    by = {(r["stage_id"], r["algorithm"]): r for r in rows}
    out = []
    for group, stage_id in stage_order(rows):
        for algo in ordered({r["algorithm"] for r in rows}, ALGOS):
            r = by.get((stage_id, algo))
            if r is None:
                continue
            ok = solved(r)
            out.append({
                "stage_id": stage_id, "group": group, "algorithm": algo, "status": r["status"],
                "length": num(r, "length") if ok else None,
                "cost": num(r, "cost") if ok else None,
                "expanded": num(r, "expanded"),
                "time_ms_median": num(r, "time_ms_median"),
                "peak_mem_kb": num(r, "peak_mem_kb"),
            })
    return out


def md_table(header, rows, left=1):
    # left: số cột chữ canh trái, các cột số canh phải
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join("---" if i < left else "---:" for i in range(len(header))) + "|"]
    lines += ["| " + " | ".join(str(c).replace("*", "\\*") for c in row) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def summary_md(rows):
    header = ["Thuật toán", "Nhóm", "Giải được", "Thời gian trung vị (ms)", "Bộ nhớ đỉnh trung vị (KiB)",
              "Nút mở rộng trung vị", "Số nước trung bình", "Chi phí trung bình"]
    body = [[LABELS.get(s["algorithm"], s["algorithm"]), s["group"], f"{s['solved']}/{s['total']}",
             fmt(s["time_ms_median"], 2), fmt(s["peak_mem_kb_median"]), fmt(s["expanded_median"]),
             fmt(s["length_mean"]), fmt(s["cost_mean"])] for s in summary(rows)]
    return md_table(header, body, left=3)


def detail_md(rows):
    header = ["Màn", "Nhóm", "Thuật toán", "Trạng thái", "Số nước", "Chi phí", "Nút mở rộng",
              "Thời gian (ms)", "Bộ nhớ đỉnh (KiB)"]
    body = [[d["stage_id"], d["group"], LABELS.get(d["algorithm"], d["algorithm"]),
             STATUS_CODE.get(d["status"], d["status"]), fmt(d["length"]), fmt(d["cost"]), fmt(d["expanded"]), fmt(d["time_ms_median"], 2),
             fmt(d["peak_mem_kb"])] for d in detail(rows)]
    return md_table(header, body, left=4)


def write_csv(path, dicts):
    if not dicts:
        raise ValueError(f"không có dòng nào để ghi vào {path}")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(dicts[0]))
        writer.writeheader()
        for d in dicts:
            writer.writerow({k: "" if v is None else v for k, v in d.items()})


UNITS = ("Thời gian là trung vị các lần chạy (ms). Bộ nhớ đỉnh đo bằng tracemalloc, đơn vị KiB (1 KiB = 1024 byte), "
         "không phải RSS.")
NOTE_SUMMARY = ("Bảng theo nhóm: cột \"Giải được\" đếm số màn solved trên tổng số màn. Các cột thời gian, bộ nhớ, "
                "nút mở rộng, số nước, chi phí chỉ tính trên các màn giải được, nhóm không có màn nào giải được "
                "thì ghi \"–\". " + UNITS + "\n")
NOTE_DETAIL = ("Bảng từng màn: mỗi dòng là 1 lần chạy, kể cả lần không giải được. Lần không giải được vẫn ghi "
               "nút mở rộng, thời gian, bộ nhớ của chính lần chạy đó (nếu có), còn số nước và chi phí ghi \"–\". "
               "Cột Trạng thái: OK = giải được, NOSOL = không có lời giải, TLE = quá thời gian, "
               "trạng thái khác ghi nguyên. " + UNITS + "\n")


def make_tables(rows, out, original_rows=None):
    if not rows:
        raise ValueError("CSV kết quả không có dòng dữ liệu nào")
    if original_rows is not None and not original_rows:
        raise ValueError("CSV màn gốc không có dòng dữ liệu nào")
    # kiểm hết dữ liệu trước khi ghi file nào, tránh để lại bảng dở dang
    used = None
    if original_rows is not None:
        used = [r for r in original_rows if r["stage_id"] != DROPPED]
        if not used:
            raise ValueError(f"CSV màn gốc chỉ có {DROPPED}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.md").write_text("# Kết quả theo nhóm\n\n" + NOTE_SUMMARY + "\n" + summary_md(rows),
                                    encoding="utf-8")
    write_csv(out / "summary.csv", summary(rows))
    (out / "detail.md").write_text("# Kết quả từng màn\n\n" + NOTE_DETAIL + "\n" + detail_md(rows), encoding="utf-8")
    write_csv(out / "detail.csv", detail(rows))
    written = ["summary.md", "summary.csv", "detail.md", "detail.csv"]
    if used is not None:
        if len(used) != len(original_rows):
            print(f"Bỏ {len(original_rows) - len(used)} dòng của {DROPPED} trong CSV màn gốc")
        n = len({r["stage_id"] for r in used})
        text = ("# Phụ lục: kết quả trên các màn gốc\n\n"
                f"Nguồn quick_bloxorz có 33 màn. Nhóm dùng {n} màn, `{DROPPED}` bị loại trước khi chạy "
                "(quyết định nhóm 21/10/2026, map nguồn bị lỗi) nên không có số liệu, không tính vào mẫu số.\n\n"
                "## Theo nhóm\n\n" + NOTE_SUMMARY + "\n" + summary_md(used)
                + "\n## Từng màn\n\n" + NOTE_DETAIL + "\n" + detail_md(used))
        (out / "original.md").write_text(text, encoding="utf-8")
        written.append("original.md")
    return [out / name for name in written]


# ---------------------------------------------------------------------------
# Biểu đồ (matplotlib chỉ import ở đây, phần bảng không cần)
# ---------------------------------------------------------------------------

def _pyplot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 9, "axes.titlesize": 11, "axes.titlelocation": "left", "axes.titlecolor": INK,
        "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
        "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False,
    })
    return plt


def _stage_axis(ax, stages, labels=True):
    # tên màn ở trục x, tên nhóm bên dưới, vạch mảnh ngăn giữa các nhóm
    ax.set_xticks(range(len(stages)), [s for _, s in stages])
    ax.set_xlim(-0.6, len(stages) - 0.4)
    ax.tick_params(axis="x", length=0)
    groups = ordered({g for g, _ in stages}, GROUPS)
    for g in groups:
        xs = [i for i, (gg, _) in enumerate(stages) if gg == g]
        if labels:
            ax.text((xs[0] + xs[-1]) / 2, -0.1, g, transform=ax.get_xaxis_transform(),
                    ha="center", va="top", color=INK, fontweight="bold")
        if xs[0] > 0:
            ax.axvline(xs[0] - 0.5, color=GRID, linewidth=0.8)


def _slot(algos):
    return min(0.84 / len(algos), 0.3)  # ít thuật toán thì cột không quá to


def _x(j, i, algos):
    return j + (i - (len(algos) - 1) / 2) * _slot(algos)


def _grouped_bars(ax, rows, stages, algos, value, log=False):
    """Cột nhóm theo thuật toán; lần chạy không solved thì gạch chéo + dấu x, không vẽ như số 0."""
    by = {(r["stage_id"], r["algorithm"]): r for r in rows}
    slot = _slot(algos)
    failed = False
    for i, algo in enumerate(algos):
        for j, (_, stage_id) in enumerate(stages):
            r = by.get((stage_id, algo))
            x = _x(j, i, algos)
            v = value(r) if r else None
            ok = solved(r)
            if v is not None and (v > 0 or not log):
                ax.bar(x, v, slot * 0.86, color=COLORS[algo], alpha=1 if ok else 0.35,
                       hatch=None if ok else "////", edgecolor=COLORS[algo] if not ok else "none", linewidth=0)
            if r is not None and not ok:
                failed = True
                y = v if v is not None and (v > 0 or not log) else None
                ax.plot(x, y if y is not None else 0, marker="x", color=INK, markersize=5,
                        transform=ax.transData if y is not None else ax.get_xaxis_transform())
    if log:
        ax.set_yscale("log")
    return failed


def _legend(ax, algos, failed):
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles = [Patch(color=COLORS[a], label=LABELS[a]) for a in algos]
    if failed:
        handles.append(Line2D([], [], marker="x", color=INK, linestyle="none", label="không giải được (gạch chéo)"))
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=len(handles),
              handlelength=1.2, columnspacing=1.2)


def _save(fig, path):
    fig.savefig(path, dpi=200, bbox_inches="tight")
    return path


def make_figures(rows, out):
    plt = _pyplot()
    out.mkdir(parents=True, exist_ok=True)
    stages = stage_order(rows)
    algos = ordered({r["algorithm"] for r in rows} & set(ALGOS), ALGOS)
    paths = []

    charts = [
        ("expanded.png", "Số nút mở rộng theo từng màn", "Số nút mở rộng (thang log)", "expanded"),
        ("time.png", "Thời gian tìm theo từng màn (trung vị, có tính xây heuristic)", "Thời gian (ms, thang log)",
         "time_ms_median"),
        ("memory.png", "Bộ nhớ đỉnh theo từng màn (tracemalloc)", "Bộ nhớ đỉnh (KiB, thang log)", "peak_mem_kb"),
    ]
    for name, title, ylabel, key in charts:
        if not algos:
            print(f"Bỏ qua {name}: CSV không có thuật toán nào trong {', '.join(ALGOS)}")
            continue
        fig, ax = plt.subplots(figsize=(10, 4.2))
        failed = _grouped_bars(ax, rows, stages, algos, lambda r, key=key: num(r, key), log=True)
        _stage_axis(ax, stages)
        ax.set_ylabel(ylabel)
        ax.set_title(title, pad=24)
        _legend(ax, algos, failed)
        paths.append(_save(fig, out / name))
        plt.close(fig)

    for chart in (_length_cost, _heuristics):
        path = chart(plt, rows, stages, out)
        if path is not None:
            paths.append(path)
    return paths


def _two_path_stages(rows):
    # màn mà BFS ít nước hơn UCS nhưng UCS rẻ hơn
    by = {(r["stage_id"], r["algorithm"]): r for r in rows}
    found = []
    for _, s in stage_order(rows):
        b, u = by.get((s, "bfs")), by.get((s, "ucs"))
        if not (solved(b) and solved(u)):
            continue
        lb, cb, lu, cu = num(b, "length"), num(b, "cost"), num(u, "length"), num(u, "cost")
        if None not in (lb, cb, lu, cu) and lb < lu and cu < cb:
            found.append(s)
    return found


def _length_cost(plt, rows, stages, out):
    algos = [a for a in ("bfs", "ucs", "astar", "astar_manhattan") if any(r["algorithm"] == a for r in rows)]
    if not algos:
        print("Bỏ qua length_cost.png: CSV không có bfs, ucs, astar, astar_manhattan")
        return None
    two_path = _two_path_stages(rows)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True)
    failed = False
    for ax, key, ylabel in ((ax1, "length", "Số nước"), (ax2, "cost", "Chi phí")):
        failed |= _grouped_bars(ax, rows, stages, algos, lambda r, key=key: num(r, key) if solved(r) else None)
        ax.set_ylabel(ylabel)
    _stage_axis(ax1, stages, labels=False)
    _stage_axis(ax2, stages)
    ax1.set_title("Số nước và chi phí lời giải: BFS so với UCS và A*", pad=24)
    _legend(ax1, algos, failed)
    # chỉ ghi số ở các màn 2 lối, đánh dấu tên màn
    by = {(r["stage_id"], r["algorithm"]): r for r in rows}
    index = {s: j for j, (_, s) in enumerate(stages)}
    for s in two_path:
        for ax, key in ((ax1, "length"), (ax2, "cost")):
            for i, a in enumerate(algos):
                if a in ("bfs", "ucs") and solved(by.get((s, a))):
                    v = num(by[(s, a)], key)
                    ax.text(_x(index[s], i, algos), v, fmt(v), ha="center", va="bottom", fontsize=7, color=INK2)
        ax2.text(index[s], 1.0, "2 lối", transform=ax2.get_xaxis_transform(), ha="center", va="bottom",
                 fontsize=8, color=INK, fontweight="bold")
    path = _save(fig, out / "length_cost.png")
    plt.close(fig)
    return path


def _heuristics(plt, rows, stages, out):
    """Số nút A* mở rộng tính theo % của UCS (UCS = 100%)."""
    by = {(r["stage_id"], r["algorithm"]): r for r in rows}
    algos = [a for a in ("astar_manhattan", "astar") if any(r["algorithm"] == a for r in rows)]

    def percent(r):
        u = by.get((r["stage_id"], "ucs"))
        e, eu = num(r, "expanded"), num(u, "expanded")
        return 100 * e / eu if solved(u) and e is not None and eu else None

    # CSV chạy riêng vài thuật toán (vd --algos bfs ucs dfs) thì không có gì để so
    if not algos or not any(r["algorithm"] == "ucs" for r in rows):
        print("Bỏ qua heuristics.png: cần có ucs và ít nhất 1 trong astar, astar_manhattan")
        return None
    fig, ax = plt.subplots(figsize=(10, 4.2))
    failed = _grouped_bars(ax, rows, stages, algos, percent)
    ax.axhline(100, color=INK2, linewidth=1)
    ax.text(len(stages) - 0.45, 101, "UCS = 100%", ha="right", va="bottom", fontsize=8, color=INK2)
    # màn UCS không giải được thì không có % để so, ghi chú thay vì để trống
    for j, (_, s) in enumerate(stages):
        if (s, "ucs") in by and not solved(by[(s, "ucs")]):
            ax.text(j, 2, "UCS ×", ha="center", va="bottom", fontsize=7, color=INK2)
    _stage_axis(ax, stages)
    values = [percent(r) for r in rows if r["algorithm"] in algos]
    ax.set_ylim(0, max([112] + [1.08 * v for v in values if v is not None]))
    ax.set_ylabel("Nút mở rộng (% so với UCS)")
    ax.set_title("So sánh 2 heuristic: số nút A* mở rộng so với UCS", pad=24)
    _legend(ax, algos, failed)
    path = _save(fig, out / "heuristics.png")
    plt.close(fig)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bảng và biểu đồ từ CSV benchmark")
    parser.add_argument("csv", type=Path, help="CSV của bộ màn chính, vd results/final/results.csv")
    parser.add_argument("--out", type=Path, default=Path("results"), help="thư mục ra (tables/, figures/)")
    parser.add_argument("--original", type=Path, default=None,
                        help="CSV của 32 màn gốc, mặc định original.csv cạnh file CSV chính")
    args = parser.parse_args(argv)

    rows = read_rows(args.csv)
    original = args.original or args.csv.with_name("original.csv")
    original_rows = read_rows(original) if original.exists() else None
    if original_rows is None:
        print(f"Không thấy {original}, bỏ qua bảng phụ lục màn gốc")

    try:
        paths = make_tables(rows, args.out / "tables", original_rows)
    except ValueError as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        return 1
    paths += make_figures(rows, args.out / "figures")
    for p in paths:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
