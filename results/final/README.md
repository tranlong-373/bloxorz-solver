# Benchmark chính thức — task 1.7

Đo ngày 25/10/2026 trên Windows bằng Python 3.12.10. Mã chạy đo: commit `56176ac` trên `main`; tag bộ màn cố định: `stages-v1` (`df6b563`).

## Máy đo

| Thành phần | Cấu hình thực tế |
| --- | --- |
| CPU | 13th Gen Intel Core i7-13620H |
| RAM vật lý | 33.965.985.792 byte (khoảng 31,63 GiB) |
| Hệ điều hành | Microsoft Windows 11 Home Single Language, phiên bản 10.0.26300 |
| Python | 3.12.10 |
| Thư viện đã cài | Ursina 8.3.0; pytest 9.1.1; matplotlib 3.11.2; pandas 3.0.6 |

## Dữ liệu và kiểm tra

Hai lệnh benchmark dùng năm lượt đo thời gian và giới hạn 60 giây cho mỗi lượt; các file `.runs.jsonl` chứa kết quả từng lượt, kể cả lượt đo bộ nhớ riêng.

| File | Bộ màn | Số dòng CSV | Kết quả |
| --- | --- | ---: | --- |
| `results.csv` | 17 màn G1–G5 × 5 cấu hình | 85 | 85 solved, 85 verified=True |
| `original.csv` | 32 màn gốc sử dụng × 5 cấu hình | 160 | 160 solved, 160 verified=True |

Không có dòng timeout, mixed, error hay verification_failed. Cả 1.470 bản ghi trong hai file JSONL đều solved và verified=True. `stage_30` không có trong `original.csv`: nhóm đã loại màn này trước khi chạy vì bản đồ nguồn thiếu ô sàn hợp lệ, khiến màn không có đường đi tới đích. File `stages/original/stage_30.json` vẫn được giữ để đối chiếu dữ liệu nguồn; không tính màn này vào mẫu số 32 màn.

Thời gian CSV là trung vị của năm lượt tìm kiếm không bật `tracemalloc`. Lượt đo bộ nhớ tách riêng; `peak_mem_kb` là KiB cấp phát Python do `tracemalloc` ghi nhận, không phải RAM toàn tiến trình.
