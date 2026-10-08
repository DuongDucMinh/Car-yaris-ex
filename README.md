# Toyota Yaris: màn hình nghe nhạc có làm yếu điện không?

**Chưa đủ dữ liệu để kết luận màn hình 16 triệu đồng gây chết máy hoặc cần nâng máy phát.** Giá tiền không cho biết công suất. Dự án này giúp tính tải điện và nhiên liệu, xem điều kiện nào thiếu điện, rồi thay giả định bằng số đo thực tế.

- [Báo cáo dễ hiểu, kiến trúc xe và thông tin thị trường](docs/BAO_CAO.md)
- [Bảng kết quả được sinh từ code](docs/KET_QUA.md)
- [Kết quả đầy đủ dạng JSON](results/scenarios.json)
- [Mẫu nhập thông số](examples/assumptions.json) — hiện chứa giả định, chưa phải số đo.

## Chạy trên Windows hoặc Linux

Cần Python 3.10 trở lên; không cần cài thư viện ngoài.

```powershell
python yaris_power.py
python yaris_power.py --config examples/assumptions.json
python yaris_power.py --output results/custom.json
python render_results.py
python -m unittest discover -s tests -v
```

Xem mức tín hiệu trung bình của một bản nhạc WAV PCM 16-bit:

```powershell
python yaris_power.py --wav bai-nhac.wav
```

WAV cho biết RMS và tỷ số tín hiệu tương đối, không tự cho biết màn hình tiêu thụ bao nhiêu W. Không có bản nhạc hay số đo thiết bị thật trong dự án.

## Đọc kết quả

- `battery_discharge_w > 0`: ắc quy phải bù điện trong điều kiện đang mô phỏng.
- `possible_charge_w`: phần điện có thể dành cho mục tiêu sạc; chưa tính giới hạn nhận sạc của bình.
- `charge_target_and_reserve_met = false` có thể chỉ là thiếu dự phòng hoặc sạc chậm, chưa chắc đang xả bình.
- `required_rated_a_for_assumed_conditions`: phép tính yêu cầu dưới giả định hiện tại, **không phải chỉ định mua máy phát**.
- `replacement_vs_old` / `replacement_vs_cd`: chỉ phần tăng/giảm so với đầu cũ.
- Khi tốc độ bằng 0, đại lượng trên mỗi km là `null`; lít/giờ vẫn tính được.
- Thời gian đến SOC dự phòng là phép ước lượng năng lượng, không bảo đảm đề máy được.

## Thay bằng số đo

Sao chép `examples/assumptions.json`, thay các giá trị đã đo rồi chạy với `--config`. Trường chưa nhập sẽ dùng mặc định; CLI xuất lại toàn bộ thông số đã dùng để kiểm tra. Trường sai tên, số âm không hợp lệ, NaN/Infinity và hiệu suất ngoài (0, 1] bị từ chối.

Nếu đã đo trực tiếp dòng toàn bộ cụm màn hình: đặt `electronics_w = điện áp × dòng đo`, `speaker_average_w = 0` và các tải ampli ngoài bằng 0 nếu chúng đã nằm trong phép đo. Đây là cách nhập tải tổng, tránh cộng trùng ampli. `other_loads_w` phải loại trừ đầu nghe nhạc.

Nếu đã đo dòng máy phát khả dụng trong đúng điều kiện nhiệt/vòng tua: có thể đặt `alternator_rated_a` bằng dòng khả dụng đo được và `speed_factor = thermal_factor = 1`. Lúc đó trường có tên rated chỉ là đầu vào quy đổi; không được dùng nó để suy ra thông số danh định trên tem máy phát.

## Kiểm chứng

26 kiểm thử gồm tính tay, cân bằng năng lượng với 300 tổ hợp ngẫu nhiên có seed, các trường hợp thiếu điện/sạc chậm, đơn vị nhiên liệu, đầu vào sai, CLI, WAV stereo/im lặng/cắt cụt và tỷ lệ công suất khi gấp đôi biên độ. CI chạy trên Python 3.11–3.13 và kiểm tra bảng/JSON có tái sinh đúng từ code.

Các kiểm thử xác nhận phép tính và hành vi code; chúng không xác nhận giá trị giả định là thông số của chiếc xe.
