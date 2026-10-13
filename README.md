# Bloxorz Solver

CSC14003 – Introduction to Artificial Intelligence – Project 1.
Bloxorz game with a 3D GUI (Ursina) and four hand-written solvers: BFS, DFS, UCS, A*.

> Bản tối thiểu (task 1.1). VT4 viết bản đầy đủ ở task 4.5.

## Yêu cầu
Python **3.12 trở lên** (nhóm thử chính trên 3.12).

## Cài đặt
Windows:
```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Chạy test
```bash
pytest -q
```

## Cấu trúc thư mục
```
bloxorz/          mã nguồn chính
  engine/         luật chơi (VT2)
  search/         BFS, DFS (VT1) · UCS, A*, heuristic (VT5)
  gui/            ứng dụng (VT4) · gui/scene/ cảnh 3D (VT3)
stages/           file màn: fixtures/, original/, bench/
tools/            script đổi 33 màn gốc
benchmark/        đo hiệu năng và vẽ biểu đồ
results/          kết quả đo
tests/            test
sandbox/          code nháp (không nộp)
```
