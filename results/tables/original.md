# Phụ lục: kết quả trên các màn gốc

Nguồn quick_bloxorz có 33 màn. Nhóm dùng 32 màn, `stage_30` bị loại trước khi chạy (quyết định nhóm 21/10/2026, map nguồn bị lỗi) nên không có số liệu, không tính vào mẫu số.

## Theo nhóm

Bảng theo nhóm: cột "Giải được" đếm số màn solved trên tổng số màn. Các cột thời gian, bộ nhớ, nút mở rộng, số nước, chi phí chỉ tính trên các màn giải được, nhóm không có màn nào giải được thì ghi "–". Thời gian là trung vị các lần chạy (ms). Bộ nhớ đỉnh đo bằng tracemalloc, đơn vị KiB (1 KiB = 1024 byte), không phải RSS.

| Thuật toán | Nhóm | Giải được | Thời gian trung vị (ms) | Bộ nhớ đỉnh trung vị (KiB) | Nút mở rộng trung vị | Số nước trung bình | Chi phí trung bình |
|---|---|---|---:|---:|---:|---:|---:|
| BFS | G1 | 3/3 | 1.10 | 35.9 | 81 | 20.3 | 20.3 |
| BFS | G2 | 2/2 | 1.35 | 39.2 | 100.5 | 37.5 | 89.5 |
| BFS | G3 | 17/17 | 7.74 | 118.9 | 325 | 69.5 | 74.5 |
| BFS | G4 | 10/10 | 107.22 | 1259.4 | 2800 | 56.8 | 68 |
| BFS | Tất cả | 32/32 | 8.52 | 170.6 | 435 | 58.9 | 68.3 |
| DFS | G1 | 3/3 | 1.01 | 32.0 | 68 | 55 | 55 |
| DFS | G2 | 2/2 | 1.31 | 41.4 | 93 | 63 | 111 |
| DFS | G3 | 17/17 | 5.00 | 120.9 | 263 | 132.3 | 139.8 |
| DFS | G4 | 10/10 | 36.18 | 712.6 | 929.5 | 467.5 | 501.1 |
| DFS | Tất cả | 32/32 | 4.91 | 117.3 | 260.5 | 225.5 | 243.0 |
| UCS | G1 | 3/3 | 1.74 | 50.4 | 87 | 20.3 | 20.3 |
| UCS | G2 | 2/2 | 1.88 | 48.4 | 102 | 39 | 83 |
| UCS | G3 | 17/17 | 8.02 | 194.2 | 333 | 69.5 | 74.5 |
| UCS | G4 | 10/10 | 122.83 | 1621.4 | 2926.5 | 57.6 | 66.8 |
| UCS | Tất cả | 32/32 | 9.99 | 230.5 | 466.5 | 59.3 | 67.5 |
| A\* relaxed | G1 | 3/3 | 2.19 | 43.7 | 74 | 20.3 | 20.3 |
| A\* relaxed | G2 | 2/2 | 3.20 | 65.8 | 99 | 39 | 83 |
| A\* relaxed | G3 | 17/17 | 10.30 | 183.5 | 333 | 69.5 | 74.5 |
| A\* relaxed | G4 | 10/10 | 136.13 | 1652.3 | 2673 | 57.6 | 66.8 |
| A\* relaxed | Tất cả | 32/32 | 12.13 | 243.1 | 382.5 | 59.3 | 67.5 |
| A\* manhattan | G1 | 3/3 | 1.55 | 49.3 | 82 | 20.3 | 20.3 |
| A\* manhattan | G2 | 2/2 | 1.94 | 47.7 | 100 | 39 | 83 |
| A\* manhattan | G3 | 17/17 | 7.68 | 168.1 | 333 | 69.5 | 74.5 |
| A\* manhattan | G4 | 10/10 | 119.23 | 1528.0 | 2699 | 57.6 | 66.8 |
| A\* manhattan | Tất cả | 32/32 | 10.57 | 228.8 | 402 | 59.3 | 67.5 |

## Từng màn

Bảng từng màn: mỗi dòng là 1 lần chạy, kể cả lần không giải được. Lần không giải được vẫn ghi nút mở rộng, thời gian, bộ nhớ của chính lần chạy đó (nếu có), còn số nước và chi phí ghi "–". Cột Trạng thái: OK = giải được, NOSOL = không có lời giải, TLE = quá thời gian, trạng thái khác ghi nguyên. Thời gian là trung vị các lần chạy (ms). Bộ nhớ đỉnh đo bằng tracemalloc, đơn vị KiB (1 KiB = 1024 byte), không phải RSS.

| Màn | Nhóm | Thuật toán | Trạng thái | Số nước | Chi phí | Nút mở rộng | Thời gian (ms) | Bộ nhớ đỉnh (KiB) |
|---|---|---|---|---:|---:|---:|---:|---:|
| stage_01 | G1 | BFS | OK | 7 | 7 | 48 | 0.70 | 25.5 |
| stage_01 | G1 | DFS | OK | 45 | 45 | 56 | 0.87 | 32.0 |
| stage_01 | G1 | UCS | OK | 7 | 7 | 64 | 1.19 | 33.5 |
| stage_01 | G1 | A\* relaxed | OK | 7 | 7 | 16 | 0.91 | 18.6 |
| stage_01 | G1 | A\* manhattan | OK | 7 | 7 | 25 | 0.64 | 22.3 |
| stage_03 | G1 | BFS | OK | 19 | 19 | 81 | 1.10 | 35.9 |
| stage_03 | G1 | DFS | OK | 66 | 66 | 111 | 1.60 | 50.8 |
| stage_03 | G1 | UCS | OK | 19 | 19 | 87 | 2.12 | 50.4 |
| stage_03 | G1 | A\* relaxed | OK | 19 | 19 | 74 | 2.19 | 43.7 |
| stage_03 | G1 | A\* manhattan | OK | 19 | 19 | 82 | 1.55 | 49.3 |
| stage_06 | G1 | BFS | OK | 35 | 35 | 102 | 1.34 | 41.2 |
| stage_06 | G1 | DFS | OK | 54 | 54 | 68 | 1.01 | 31.6 |
| stage_06 | G1 | UCS | OK | 35 | 35 | 106 | 1.74 | 55.1 |
| stage_06 | G1 | A\* relaxed | OK | 35 | 35 | 88 | 2.95 | 67.4 |
| stage_06 | G1 | A\* manhattan | OK | 35 | 35 | 104 | 1.86 | 54.9 |
| stage_04 | G2 | BFS | OK | 29 | 89 | 69 | 0.98 | 27.5 |
| stage_04 | G2 | DFS | OK | 56 | 116 | 92 | 1.36 | 40.3 |
| stage_04 | G2 | UCS | OK | 29 | 89 | 70 | 1.28 | 31.6 |
| stage_04 | G2 | A\* relaxed | OK | 29 | 89 | 68 | 2.63 | 49.5 |
| stage_04 | G2 | A\* manhattan | OK | 29 | 89 | 69 | 1.47 | 31.1 |
| stage_13 | G2 | BFS | OK | 46 | 90 | 132 | 1.72 | 50.9 |
| stage_13 | G2 | DFS | OK | 70 | 106 | 94 | 1.26 | 42.5 |
| stage_13 | G2 | UCS | OK | 49 | 77 | 134 | 2.49 | 65.3 |
| stage_13 | G2 | A\* relaxed | OK | 49 | 77 | 130 | 3.77 | 82 |
| stage_13 | G2 | A\* manhattan | OK | 49 | 77 | 131 | 2.41 | 64.3 |
| stage_02 | G3 | BFS | OK | 17 | 17 | 257 | 3.71 | 99.8 |
| stage_02 | G3 | DFS | OK | 145 | 145 | 248 | 4.10 | 120.9 |
| stage_02 | G3 | UCS | OK | 17 | 17 | 274 | 5.25 | 130.3 |
| stage_02 | G3 | A\* relaxed | OK | 17 | 17 | 156 | 4.12 | 104.1 |
| stage_02 | G3 | A\* manhattan | OK | 17 | 17 | 208 | 4.23 | 112.6 |
| stage_05 | G3 | BFS | OK | 33 | 33 | 308 | 4.46 | 113.9 |
| stage_05 | G3 | DFS | OK | 134 | 134 | 240 | 3.44 | 107.7 |
| stage_05 | G3 | UCS | OK | 33 | 33 | 319 | 5.42 | 166.2 |
| stage_05 | G3 | A\* relaxed | OK | 33 | 33 | 208 | 5.49 | 123.9 |
| stage_05 | G3 | A\* manhattan | OK | 33 | 33 | 263 | 4.94 | 124.2 |
| stage_07 | G3 | BFS | OK | 44 | 44 | 172 | 2.32 | 70.0 |
| stage_07 | G3 | DFS | OK | 68 | 68 | 174 | 2.70 | 74.6 |
| stage_07 | G3 | UCS | OK | 44 | 44 | 176 | 2.96 | 88.5 |
| stage_07 | G3 | A\* relaxed | OK | 44 | 44 | 164 | 5.08 | 84.2 |
| stage_07 | G3 | A\* manhattan | OK | 44 | 44 | 175 | 3.07 | 88.4 |
| stage_11 | G3 | BFS | OK | 47 | 47 | 186 | 2.63 | 71.5 |
| stage_11 | G3 | DFS | OK | 51 | 51 | 169 | 2.42 | 62.9 |
| stage_11 | G3 | UCS | OK | 47 | 47 | 186 | 3.55 | 89.6 |
| stage_11 | G3 | A\* relaxed | OK | 47 | 47 | 181 | 4.69 | 98.1 |
| stage_11 | G3 | A\* manhattan | OK | 47 | 47 | 186 | 3.24 | 89.7 |
| stage_12 | G3 | BFS | OK | 65 | 65 | 305 | 4.33 | 114.8 |
| stage_12 | G3 | DFS | OK | 187 | 187 | 371 | 5.97 | 165.7 |
| stage_12 | G3 | UCS | OK | 65 | 65 | 320 | 5.69 | 167.8 |
| stage_12 | G3 | A\* relaxed | OK | 65 | 65 | 273 | 6.43 | 143.4 |
| stage_12 | G3 | A\* manhattan | OK | 65 | 65 | 294 | 5.40 | 134.3 |
| stage_14 | G3 | BFS | OK | 67 | 67 | 458 | 6.49 | 168.3 |
| stage_14 | G3 | DFS | OK | 113 | 113 | 326 | 5.00 | 128.3 |
| stage_14 | G3 | UCS | OK | 67 | 67 | 459 | 8.02 | 226.4 |
| stage_14 | G3 | A\* relaxed | OK | 67 | 67 | 458 | 9.91 | 246.5 |
| stage_14 | G3 | A\* manhattan | OK | 67 | 67 | 459 | 8.48 | 228.3 |
| stage_17 | G3 | BFS | OK | 106 | 106 | 705 | 10.73 | 274.5 |
| stage_17 | G3 | DFS | OK | 220 | 220 | 469 | 7.04 | 207.8 |
| stage_17 | G3 | UCS | OK | 106 | 106 | 711 | 14.10 | 356.4 |
| stage_17 | G3 | A\* relaxed | OK | 106 | 106 | 522 | 12.44 | 276.8 |
| stage_17 | G3 | A\* manhattan | OK | 106 | 106 | 635 | 12.65 | 307.6 |
| stage_18 | G3 | BFS | OK | 85 | 85 | 596 | 8.72 | 212.4 |
| stage_18 | G3 | DFS | OK | 204 | 204 | 440 | 6.61 | 196.4 |
| stage_18 | G3 | UCS | OK | 85 | 85 | 596 | 16.62 | 273.0 |
| stage_18 | G3 | A\* relaxed | OK | 85 | 85 | 594 | 25.49 | 295.2 |
| stage_18 | G3 | A\* manhattan | OK | 85 | 85 | 596 | 23.46 | 276.9 |
| stage_19 | G3 | BFS | OK | 67 | 67 | 222 | 5.58 | 84.0 |
| stage_19 | G3 | DFS | OK | 79 | 79 | 111 | 2.87 | 45.5 |
| stage_19 | G3 | UCS | OK | 67 | 67 | 223 | 5.52 | 103.2 |
| stage_19 | G3 | A\* relaxed | OK | 67 | 67 | 187 | 5.55 | 110.1 |
| stage_19 | G3 | A\* manhattan | OK | 67 | 67 | 211 | 6.27 | 100.3 |
| stage_21 | G3 | BFS | OK | 71 | 71 | 232 | 8.31 | 87.2 |
| stage_21 | G3 | DFS | OK | 71 | 71 | 108 | 3.23 | 47.0 |
| stage_21 | G3 | UCS | OK | 71 | 71 | 234 | 6.70 | 107.0 |
| stage_21 | G3 | A\* relaxed | OK | 71 | 71 | 211 | 6.95 | 118.0 |
| stage_21 | G3 | A\* manhattan | OK | 71 | 71 | 221 | 6.80 | 103.0 |
| stage_22 | G3 | BFS | OK | 65 | 65 | 325 | 7.74 | 118.9 |
| stage_22 | G3 | DFS | OK | 149 | 149 | 258 | 5.43 | 113.8 |
| stage_22 | G3 | UCS | OK | 65 | 65 | 333 | 9.41 | 194.2 |
| stage_22 | G3 | A\* relaxed | OK | 65 | 65 | 287 | 11.82 | 153.1 |
| stage_22 | G3 | A\* manhattan | OK | 65 | 65 | 307 | 6.88 | 168.1 |
| stage_25 | G3 | BFS | OK | 55 | 55 | 464 | 9.12 | 172.9 |
| stage_25 | G3 | DFS | OK | 76 | 76 | 177 | 3.97 | 74.6 |
| stage_25 | G3 | UCS | OK | 55 | 55 | 474 | 10.58 | 234.6 |
| stage_25 | G3 | A\* relaxed | OK | 55 | 55 | 432 | 14.81 | 239.7 |
| stage_25 | G3 | A\* manhattan | OK | 55 | 55 | 456 | 16.64 | 229.3 |
| stage_27 | G3 | BFS | OK | 71 | 135 | 312 | 6.40 | 112.9 |
| stage_27 | G3 | DFS | OK | 71 | 135 | 263 | 4.81 | 99.9 |
| stage_27 | G3 | UCS | OK | 71 | 135 | 333 | 6.61 | 164.6 |
| stage_27 | G3 | A\* relaxed | OK | 71 | 135 | 333 | 10.30 | 183.5 |
| stage_27 | G3 | A\* manhattan | OK | 71 | 135 | 333 | 7.68 | 165.2 |
| stage_29 | G3 | BFS | OK | 104 | 104 | 1809 | 33.13 | 848.8 |
| stage_29 | G3 | DFS | OK | 126 | 126 | 1108 | 20.56 | 468.9 |
| stage_29 | G3 | UCS | OK | 104 | 104 | 1811 | 42.33 | 1090.6 |
| stage_29 | G3 | A\* relaxed | OK | 104 | 104 | 1794 | 52.71 | 1162.2 |
| stage_29 | G3 | A\* manhattan | OK | 104 | 104 | 1808 | 44.53 | 1101.7 |
| stage_31 | G3 | BFS | OK | 91 | 111 | 854 | 23.29 | 391.4 |
| stage_31 | G3 | DFS | OK | 210 | 274 | 752 | 14.58 | 356.0 |
| stage_31 | G3 | UCS | OK | 91 | 111 | 880 | 28.15 | 484.6 |
| stage_31 | G3 | A\* relaxed | OK | 91 | 111 | 764 | 25.58 | 493.6 |
| stage_31 | G3 | A\* manhattan | OK | 91 | 111 | 809 | 26.84 | 468.3 |
| stage_32 | G3 | BFS | OK | 129 | 129 | 626 | 17.38 | 224.1 |
| stage_32 | G3 | DFS | OK | 269 | 269 | 624 | 17.02 | 241.7 |
| stage_32 | G3 | UCS | OK | 129 | 129 | 630 | 16.53 | 287.8 |
| stage_32 | G3 | A\* relaxed | OK | 129 | 129 | 595 | 18.27 | 294.0 |
| stage_32 | G3 | A\* manhattan | OK | 129 | 129 | 609 | 13.78 | 281.5 |
| stage_33 | G3 | BFS | OK | 65 | 65 | 732 | 25.58 | 275.6 |
| stage_33 | G3 | DFS | OK | 76 | 76 | 567 | 18.77 | 226.1 |
| stage_33 | G3 | UCS | OK | 65 | 65 | 737 | 24.48 | 360.5 |
| stage_33 | G3 | A\* relaxed | OK | 65 | 65 | 683 | 25.95 | 400.6 |
| stage_33 | G3 | A\* manhattan | OK | 65 | 65 | 703 | 25.38 | 368.1 |
| stage_08 | G4 | BFS | OK | 10 | 10 | 412 | 12.67 | 193.4 |
| stage_08 | G4 | DFS | OK | 66 | 66 | 138 | 2.62 | 78.1 |
| stage_08 | G4 | UCS | OK | 10 | 10 | 532 | 29.13 | 286.7 |
| stage_08 | G4 | A\* relaxed | OK | 10 | 10 | 314 | 20.33 | 287.9 |
| stage_08 | G4 | A\* manhattan | OK | 10 | 10 | 348 | 14.63 | 241.7 |
| stage_09 | G4 | BFS | OK | 24 | 24 | 690 | 27.81 | 283.7 |
| stage_09 | G4 | DFS | OK | 221 | 221 | 418 | 12.34 | 338.6 |
| stage_09 | G4 | UCS | OK | 24 | 24 | 741 | 29.70 | 371.0 |
| stage_09 | G4 | A\* relaxed | OK | 24 | 24 | 670 | 42.37 | 388.6 |
| stage_09 | G4 | A\* manhattan | OK | 24 | 24 | 670 | 32.70 | 359.8 |
| stage_10 | G4 | BFS | OK | 57 | 57 | 3182 | 112.90 | 1455.9 |
| stage_10 | G4 | DFS | OK | 737 | 737 | 975 | 32.30 | 918.9 |
| stage_10 | G4 | UCS | OK | 57 | 57 | 3301 | 141.81 | 1854.8 |
| stage_10 | G4 | A\* relaxed | OK | 57 | 57 | 3077 | 129.69 | 1914.2 |
| stage_10 | G4 | A\* manhattan | OK | 57 | 57 | 3112 | 136.60 | 1788.7 |
| stage_15 | G4 | BFS | OK | 57 | 57 | 2418 | 101.54 | 1062.8 |
| stage_15 | G4 | DFS | OK | 1030 | 1030 | 1559 | 60.73 | 1453.7 |
| stage_15 | G4 | UCS | OK | 57 | 57 | 2552 | 103.85 | 1388.1 |
| stage_15 | G4 | A\* relaxed | OK | 57 | 57 | 2269 | 142.58 | 1390.4 |
| stage_15 | G4 | A\* manhattan | OK | 57 | 57 | 2286 | 101.86 | 1267.4 |
| stage_16 | G4 | BFS | OK | 28 | 28 | 140 | 2.85 | 55.5 |
| stage_16 | G4 | DFS | OK | 78 | 78 | 87 | 1.77 | 56.6 |
| stage_16 | G4 | UCS | OK | 28 | 28 | 151 | 4.58 | 74.6 |
| stage_16 | G4 | A\* relaxed | OK | 28 | 28 | 125 | 5.85 | 83.8 |
| stage_16 | G4 | A\* manhattan | OK | 28 | 28 | 136 | 3.67 | 68.2 |
| stage_20 | G4 | BFS | OK | 56 | 56 | 3983 | 160.42 | 1871 |
| stage_20 | G4 | DFS | OK | 725 | 725 | 1466 | 46.88 | 1119.4 |
| stage_20 | G4 | UCS | OK | 56 | 56 | 4264 | 210.72 | 2393.1 |
| stage_20 | G4 | A\* relaxed | OK | 56 | 56 | 3676 | 202.17 | 2251.4 |
| stage_20 | G4 | A\* manhattan | OK | 56 | 56 | 3713 | 199.17 | 2159.4 |
| stage_23 | G4 | BFS | OK | 75 | 167 | 3692 | 127.47 | 1675.7 |
| stage_23 | G4 | DFS | OK | 890 | 1054 | 1540 | 49.24 | 1394.8 |
| stage_23 | G4 | UCS | OK | 83 | 155 | 4040 | 195.07 | 2306.7 |
| stage_23 | G4 | A\* relaxed | OK | 83 | 155 | 3913 | 176.08 | 2361.9 |
| stage_23 | G4 | A\* manhattan | OK | 83 | 155 | 3964 | 209.74 | 2262.4 |
| stage_24 | G4 | BFS | OK | 57 | 57 | 515 | 14.34 | 187.7 |
| stage_24 | G4 | DFS | OK | 80 | 80 | 176 | 3.00 | 77.6 |
| stage_24 | G4 | UCS | OK | 57 | 57 | 520 | 20.13 | 248.4 |
| stage_24 | G4 | A\* relaxed | OK | 57 | 57 | 482 | 16.52 | 273.0 |
| stage_24 | G4 | A\* manhattan | OK | 57 | 57 | 507 | 17.51 | 244.1 |
| stage_26 | G4 | BFS | OK | 104 | 104 | 5022 | 171.28 | 2244.1 |
| stage_26 | G4 | DFS | OK | 608 | 608 | 2051 | 83.52 | 1268.3 |
| stage_26 | G4 | UCS | OK | 104 | 104 | 5132 | 262.63 | 3115.5 |
| stage_26 | G4 | A\* relaxed | OK | 104 | 104 | 4908 | 234.38 | 2710.0 |
| stage_26 | G4 | A\* manhattan | OK | 104 | 104 | 4908 | 239.62 | 2592.6 |
| stage_28 | G4 | BFS | OK | 100 | 120 | 3476 | 129.76 | 1572.4 |
| stage_28 | G4 | DFS | OK | 240 | 412 | 884 | 40.06 | 506.4 |
| stage_28 | G4 | UCS | OK | 100 | 120 | 3316 | 158.49 | 1924.1 |
| stage_28 | G4 | A\* relaxed | OK | 100 | 120 | 3175 | 182.39 | 1999.0 |
| stage_28 | G4 | A\* manhattan | OK | 100 | 120 | 3175 | 179.97 | 1869.0 |
