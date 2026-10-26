# Bloxorz Solver

Dự án mô phỏng trò chơi Bloxorz kinh điển với giao diện 3D trực quan bằng Ursina Engine, hỗ trợ người chơi tương tác trực tiếp và tích hợp bốn thuật toán tìm kiếm tự động: BFS, DFS, UCS và A*.
Đồ án thuộc môn học CSC14003 – Nhập môn Trí tuệ Nhân tạo do nhóm 5 thành viên thực hiện.

## Yêu cầu

- Python **3.12 trở lên** (phiên bản chuẩn nhóm dùng để thử nghiệm: Python 3.12; CI kiểm thử tự động trên cả Python 3.12 và 3.13).
- Hệ điều hành: Windows, macOS hoặc Linux.
- Các thư viện phụ thuộc quy định tại `requirements.txt`: `ursina==8.3.0`, `pytest==9.1.1`, `matplotlib==3.11.2`, `pandas==3.0.6`.

## Cài đặt

Khởi tạo môi trường ảo `.venv` và cài đặt các thư viện cần thiết từ thư mục gốc của repository:

**Windows (PowerShell / Command Prompt):**
```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Chạy game

```bash
python main.py
```

Lệnh trên sẽ mở cửa sổ trò chơi với đồ họa 3D. Bạn có thể tự mình điều khiển khối lăn trên sàn để về đích, hoặc mở bảng **Solver** để hệ thống tự động tìm kiếm lời giải và phát lại từng bước di chuyển.

## Điều khiển

Bảng hướng dẫn phím luôn được hiển thị ở góc màn hình:

| Phím / Thao tác | Chức năng |
| --- | --- |
| `↑` `↓` `←` `→` hoặc `W` `S` `A` `D` | Lăn khối bê tông theo 4 hướng |
| `Space` | Chuyển đổi điều khiển giữa 2 cube 1×1 khi khối đang bị tách (`split`) |
| `R` | Chơi lại màn hiện tại (`Restart`) |
| `N` | Mở danh sách chọn màn chơi (`New Game`) |
| `Esc` | Đóng menu chọn màn chơi / cửa sổ modal |

Các thành phần hỗ trợ trên giao diện:
- **Nút Solver**: Mở bảng chọn thuật toán giải tự động (**BFS**, **DFS**, **UCS**, **A***), theo dõi bảng thông số chi tiết (trạng thái, số nước, chi phí đường đi, số nút mở rộng, thời gian thực thi, bộ nhớ đỉnh) và thanh điều khiển phát lại lời giải (**Pause**, **Step**, **Resume**, tốc độ **1×**, **2×**, **4×**).
- **Màn hình kết thúc**: Khi khối về đích hoặc rơi khỏi bàn, màn hình thông báo nổi bật ở giữa với nguyên nhân cụ thể và nút bấm nhanh **Restart (R)** hoặc **Chọn màn khác (N)**.
- **Menu chọn màn (N)**: Phân loại theo nhóm cơ chế **G1–G5** và tab **Tất cả**, mỗi nhóm kèm dòng giải thích cơ chế, hỗ trợ phân trang và đánh số rõ ràng (màn gốc hiển thị định dạng *Màn gốc số N*).
- **Bảng chú giải (Legend)**: Hiển thị ở cạnh dưới màn hình giúp phân biệt nhanh các loại ô sàn (sàn thường, ô dễ vỡ `F`, ô đích `G`, ô cầu) và các loại công tắc (mềm, nặng, tách khối).

## Chạy test

Kiểm tra toàn bộ engine luật chơi, các thuật toán tìm kiếm và logic điều khiển giao diện:

```bash
pytest -q
```

*Lưu ý:* Toàn bộ bài test đều được thiết kế chạy headless, không yêu cầu khởi tạo đồ họa Ursina (đảm bảo tính tương thích trên máy chủ CI GitHub Actions).

## Chạy benchmark và vẽ biểu đồ

Dự án cung cấp bộ công cụ đo lường hiệu năng tìm kiếm độc lập không cần giao diện:

### 1. Chạy đo thời gian và bộ nhớ (VT1 - `benchmark/run.py`)

Chạy 5 thuật toán tìm kiếm (`bfs`, `dfs`, `ucs`, `astar`, `astar_manhattan`) với giới hạn 60 giây và 5 lượt đo thời gian cho mỗi màn:

- **Đo trên 17 màn benchmark chuẩn G1–G5:**
  ```bash
  python -m benchmark.run --stages stages/bench --out results/results.csv
  ```
- **Đo trên 32 màn gốc (tự động loại trừ stage_30):**
  ```bash
  python -m benchmark.run --stages stages/original --out results/original.csv
  ```

### 2. Xuất bảng số liệu và vẽ đồ thị so sánh (VT5 - `benchmark/plots.py`)

Đọc file CSV kết quả đo để tự động tạo các bảng Markdown (lưu tại `results/tables/`) và biểu đồ trực quan (lưu tại `results/figures/`):

```bash
python -m benchmark.plots results/final/results.csv --out results
```
*(Muốn kết xuất dữ liệu cho đợt đo mới, thay đường dẫn bằng `results/results.csv`).*

## Định dạng file màn

Mỗi màn chơi được lưu trữ dưới dạng một file JSON độc lập mô tả cấu hình hình học và cơ chế tương tác:

- **`id`**: Chuỗi định danh duy nhất của màn chơi (ví dụ: `"basic_01"`, `"stage_01"`).
- **`group`**: Nhóm phân loại cơ chế từ `"G1"` đến `"G5"`.
- **`grid`**: Mảng các chuỗi ký tự thể hiện ma trận bản đồ (tối đa 12 hàng × 20 cột):
  - `#`: Sàn đá bình thường, chịu lực tốt.
  - `.`: Khoảng trống hư vô (khối lăn vào sẽ rơi).
  - `S`: Vị trí xuất phát của khối (bộ tải `loader` tự động đổi thành `#` và ghi nhận tọa độ `start`).
  - `G`: Ô đích (Goal) – khối đứng thẳng tại đây là chiến thắng.
  - `F`: Ô dễ vỡ (Fragile) – khối nguyên đứng thẳng lên ô này sẽ làm sập sàn và rơi xuống.
  - `B`: Ô cầu (Bridge) – chỉ đi qua an toàn khi cầu tương ứng đang mở.
- **`bridges`**: Danh sách các cầu điều khiển gồm `id`, danh sách tọa độ các ô `cells`, và cờ `initially_open`.
- **`switches`**: Danh sách công tắc kích hoạt gồm:
  - `kind`: `"soft"` (công tắc mềm – mọi tư thế đều kích hoạt được), `"heavy"` (công tắc nặng – chỉ khối đứng thẳng kích hoạt được), `"split"` (công tắc tách khối thành hai cube 1×1).
  - `pos`: Tọa độ `[hàng, cột]` của công tắc (luôn nằm trên ô sàn `#`).
  - `mode`: `"toggle"` (đảo trạng thái đóng/mở) hoặc `"permanent"` (giữ cố định một trạng thái).
  - `set_to`: Trạng thái đặt cầu khi dùng permanent (`"open"` hoặc `"close"`).
  - `bridges`: Danh sách mã `id` của các cầu chịu sự điều khiển.
  - `targets`: Cặp tọa độ dịch chuyển hai khối cube khi kích hoạt công tắc `"split"`.

Màn chơi mẫu tích hợp toàn bộ các cơ chế trên: [stages/fixtures/full_01.json](stages/fixtures/full_01.json).

## Nguồn tham khảo và bộ màn gốc

Bộ 33 màn gốc trong thư mục `stages/original/` được chuyển đổi từ dự án mã nguồn mở [quick_bloxorz](https://github.com/jgordon510/quick_bloxorz) của tác giả Jeffrey Gordon (phát hành theo giấy phép Creative Commons Attribution – CC BY).

### Quyết định sử dụng và loại trừ stage_30

- **Dữ liệu đối chiếu**: Nhóm lưu trữ toàn bộ 33 file chuyển đổi (`stage_01.json` đến `stage_33.json`) trong thư mục `stages/original/` nhằm phục vụ việc đối chiếu nguyên trạng với dữ liệu nguồn.
- **32 màn chơi thực tế**: Nhóm sử dụng 32 màn cho ứng dụng chơi game, danh sách menu chọn màn và toàn bộ các bộ đo benchmark.
- **Loại trừ stage_30**: Màn `stage_30` được loại trừ theo quyết định thống nhất của nhóm sau phản hồi lỗi dữ liệu nguồn từ thành viên VT4. File bản đồ `bloxorz30.json` từ nguồn `quick_bloxorz` thiếu các ô sàn kết nối cần thiết quanh điểm xuất phát `(4, 2)`, khiến khối không thể tìm được chuỗi di chuyển hợp lệ nào để đến được ô đích (thuật toán BFS duyệt cạn toàn bộ không gian trạng thái đạt được và xác nhận không có lời giải `unsolvable`). Nhóm giữ dữ liệu chuyển đổi để đối chiếu và thực hiện loại trừ ở tầng ứng dụng, không tự ý tạo thêm sàn giả lập và không đưa ra tuyên bố chưa kiểm chứng độc lập về bản đồ gốc Bloxorz (DX Interactive 2007).
