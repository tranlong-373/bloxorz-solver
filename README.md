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

## Nguồn tham khảo và bộ màn gốc
Bộ 33 màn gốc trong `stages/original/` được chuyển đổi từ dự án [quick_bloxorz](https://github.com/jgordon510/quick_bloxorz) của Jeffrey Gordon (giấy phép Creative Commons Attribution - CC BY).

### Quyết định bộ màn và loại trừ stage_30
- **Phạm vi sử dụng**: Nhóm giữ đầy đủ 33 file chuyển đổi (`stage_01.json` đến `stage_33.json`) trong thư mục `stages/original/` để phục vụ đối chiếu nguyên trạng với dữ liệu nguồn. Tuy nhiên, chỉ **32 màn** được đưa vào danh sách chơi thực tế và bộ benchmark đánh giá thuật toán; `stage_30` được loại trừ rõ ràng trước khi chạy.
- **Bằng chứng đối chiếu cho stage_30**:
  - File bản đồ nguồn `bloxorz30.json` của `quick_bloxorz` bị lỗi thiếu các ô sàn hợp lệ so với bản game Bloxorz gốc (DX Interactive 2007).
  - Vị trí xuất phát nằm tại `(4, 2)` bị bao quanh bởi các ô void và ô dễ vỡ (`F`). Do thiếu các ô sàn chuyển tiếp cần thiết để vượt qua bẫy ô dễ vỡ và kích hoạt công tắc, khối không thể tìm được bất kỳ chuỗi di chuyển hợp lệ nào để tiếp cận đích Goal tại `(1, 4)`. Thuật toán BFS duyệt cạn toàn bộ không gian trạng thái đạt được và xác nhận màn chơi không thể giải được (`unsolvable`).
  - Theo thống nhất của nhóm, dự án không tự ý sửa đổi dữ liệu nguồn để tạo ra lời giải nhân tạo, mà giữ nguyên dữ liệu chuyển đổi để đối chiếu và thực hiện loại trừ `stage_30` ở tầng ứng dụng và kiểm thử.

