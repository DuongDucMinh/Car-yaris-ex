# Kết quả tính tự động

Sinh bằng `python render_results.py`. Tất cả là kịch bản giả định; không phải số đo chiếc xe.

Máy phát giả định 80 A, điện áp 14 V, hệ số nhiệt 0,85; hệ số tốc độ 1 khi chạy và 0,4 khi không tải.
Tải xe ngoài âm thanh: 180 W ban ngày, 460 W ban đêm có quạt. Yêu cầu sạc 6 A; dự phòng thiết kế 15%.

Dư điện trước sạc dương: có thể cấp điện sạc. Âm: ắc quy phải bù. Dự phòng không phải tải vật lý.

| Trạng thái | Âm thanh | Điện âm thanh (W) | Tổng tải (W) | Máy phát khả dụng (W) | Dư trước sạc (W) | Đạt sạc + dự phòng? |
|---|---|---:|---:|---:|---:|---|
| Chạy ban ngày | CD cũ | 26.18 | 206.18 | 952.00 | 745.82 | Có |
| Chạy ban ngày | Android vừa | 43.18 | 223.18 | 952.00 | 728.82 | Có |
| Chạy ban ngày | Android lớn | 97.73 | 277.73 | 952.00 | 674.27 | Có |
| Chạy ban ngày | Ampli/sub lớn | 578.32 | 758.32 | 952.00 | 193.68 | Không |
| Chạy ban đêm + quạt | CD cũ | 26.18 | 486.18 | 952.00 | 465.82 | Có |
| Chạy ban đêm + quạt | Android vừa | 43.18 | 503.18 | 952.00 | 448.82 | Có |
| Chạy ban đêm + quạt | Android lớn | 97.73 | 557.73 | 952.00 | 394.27 | Có |
| Chạy ban đêm + quạt | Ampli/sub lớn | 578.32 | 1038.32 | 952.00 | -86.32 | Không |
| Không tải ban đêm + quạt | CD cũ | 26.18 | 486.18 | 380.80 | -105.38 | Không |
| Không tải ban đêm + quạt | Android vừa | 43.18 | 503.18 | 380.80 | -122.38 | Không |
| Không tải ban đêm + quạt | Android lớn | 97.73 | 557.73 | 380.80 | -176.93 | Không |
| Không tải ban đêm + quạt | Ampli/sub lớn | 578.32 | 1038.32 | 380.80 | -657.52 | Không |

## Năng lượng khi chạy ở tốc độ trung bình 20 km/h

Hiệu suất máy phát 55%, hiệu suất gia tăng động cơ 22%, xăng 8,9 kWh/lít.
Mức nền 9,2 lít/100 km tương đương 818,8 Wh năng lượng hóa học/km.
Cột tăng so CD chỉ tính phần chênh lệch; không cộng toàn bộ đầu mới vào đầu cũ.

| Âm thanh | Điện (Wh/km) | Xăng quy cho âm thanh (lít/100 km) | Tăng so CD (lít/100 km) |
|---|---:|---:|---:|
| CD cũ | 1.309 | 0.122 | 0.000 |
| Android vừa | 2.159 | 0.200 | 0.079 |
| Android lớn | 4.886 | 0.454 | 0.332 |
| Ampli/sub lớn | 28.916 | 2.685 | 2.564 |

## Độ nhạy máy phát

Tải 460 W + Android vừa, nhiệt 0,85. Không thể dùng số A danh định làm số A tại không tải.

| Danh định (A) | Hệ số tốc độ | Khả dụng (W) | Dư trước sạc (W) |
|---:|---:|---:|---:|
| 60 | 0.3 | 214.20 | -288.98 |
| 60 | 0.4 | 285.60 | -217.58 |
| 60 | 0.6 | 428.40 | -74.78 |
| 60 | 1.0 | 714.00 | 210.82 |
| 80 | 0.3 | 285.60 | -217.58 |
| 80 | 0.4 | 380.80 | -122.38 |
| 80 | 0.6 | 571.20 | 68.02 |
| 80 | 1.0 | 952.00 | 448.82 |
| 100 | 0.3 | 357.00 | -146.18 |
| 100 | 0.4 | 476.00 | -27.18 |
| 100 | 0.6 | 714.00 | 210.82 |
| 100 | 1.0 | 1190.00 | 686.82 |

## Độ nhạy xăng tăng do đổi CD sang Android ở cùng công suất loa

| Tốc độ (km/h) | Hiệu suất gia tăng động cơ | Tăng (lít/100 km) |
|---:|---:|---:|
| 10 | 0.15 | 0.232 |
| 10 | 0.22 | 0.158 |
| 10 | 0.30 | 0.116 |
| 20 | 0.15 | 0.116 |
| 20 | 0.22 | 0.079 |
| 20 | 0.30 | 0.058 |
| 40 | 0.15 | 0.058 |
| 40 | 0.22 | 0.039 |
| 40 | 0.30 | 0.029 |

## Khi động cơ tắt

Ắc quy giả định 45 Ah, dung lượng còn 70%, SOC từ 85% đến mốc dự phòng 60%: 99,225 Wh.
Chỉ Android vừa: 2.30 giờ tới mốc; thêm tải phụ 100 W: 0.69 giờ.
Đây không phải thời gian nghe nhạc được bảo đảm hoặc thời điểm hết điện/không đề được.

| Dòng rò tăng thêm (A) | Điện mất sau 72 giờ (Ah) | Giờ tới mốc dự phòng giả định |
|---:|---:|---:|
| 0.005 | 0.36 | 1575.00 |
| 0.050 | 3.60 | 157.50 |
| 0.300 | 21.60 | 26.25 |

Không tải: kết quả trên mỗi km là null, vì xe không đi được km nào. Lít/giờ vẫn có nghĩa.
Xăng cho âm thanh là ước lượng năng lượng dài hạn, không phải xăng tức thời khi ắc quy đang bù điện.
