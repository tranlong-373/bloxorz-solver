# Quy trình đóng góp

Chi tiết đầy đủ nằm trên Notion của nhóm (trang chủ và từng thẻ task). Tóm tắt:

## Mỗi task
```bash
git switch main
git pull
git switch -c feat/2.3-switch-bridge     # loại/mã-task-mô-tả-ngắn
.venv\Scripts\activate                    # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pytest -q                                 # phải xanh trước khi sửa gì
```
- Nhắn Zalo khi bắt đầu: `[BẮT ĐẦU] mã tên-task – nhánh – dự kiến xong ngày`.
- Chỉ sửa file của mình. Chỉ `git add` đúng file của task.
- Commit: `loại(phần): việc đã làm`, ví dụ `feat(switch): toggle bridges on soft switch`.
  Loại: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`.

## Mở Pull Request
```bash
git fetch origin
git merge origin/main
pytest -q
git push -u origin feat/2.3-switch-bridge
```
- Tiêu đề PR: `loại(module): mô tả (mã task)`, ví dụ `feat(switch): add soft/heavy switches and bridges (2.3)`.
- Điền mẫu PR, ghi `Closes #số-issue`.
- Reviewer theo bảng: VT1→VT5, VT2→VT1 (vắng: VT5), VT3→VT4, VT4→VT3 (loader: VT2), VT5→VT1.
- Lead bấm **Squash and merge** khi đã được approve và CI xanh.

## Review (trả lời trong 24 giờ)
1. Kéo nhánh về, chạy `pytest -q` thấy xanh.
2. PR chỉ sửa file của tác giả.
3. Có test với kết quả cụ thể.
4. Mình đọc hiểu đủ để trả lời khi thầy hỏi.

## Quy tắc code
- Thuật toán tìm kiếm tự cài, không dùng thư viện tìm kiếm có sẵn.
- Chỉ code trong `bloxorz/gui/` được import `ursina`. Test không bao giờ import `ursina` (CI không cài).
- `bloxorz/gui/controller.py`, `solver_runner.py`, `fake_scene.py` không import `ursina`.
- Không sửa khung chung (kiểu dữ liệu, tên hàm, định dạng file màn) khi chưa thống nhất trên Zalo.
- `successors()` luôn trả theo thứ tự U, D, L, R; khi tách: cube 0 rồi cube 1.
- Không sửa test chỉ để test xanh. Test đỏ thì tìm nguyên nhân trước.
- Chỉ VT1 sửa `requirements.txt`.
