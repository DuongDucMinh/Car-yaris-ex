"""Regenerate the committed scenario JSON and readable numerical tables."""
import json
from pathlib import Path
from yaris_power import scenarios

ROOT = Path(__file__).resolve().parent


def main():
    data = scenarios()
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "results/scenarios.json").write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    lines = [
        "# Kết quả tính tự động",
        "",
        "Sinh bằng `python render_results.py`. Tất cả là kịch bản giả định; không phải số đo chiếc xe.",
        "",
        "Máy phát giả định 80 A, điện áp 14 V, hệ số nhiệt 0,85; hệ số tốc độ 1 khi chạy và 0,4 khi không tải.",
        "Tải xe ngoài âm thanh: 180 W ban ngày, 460 W ban đêm có quạt. Yêu cầu sạc 6 A; dự phòng thiết kế 15%.",
        "",
        "Dư điện trước sạc dương: có thể cấp điện sạc. Âm: ắc quy phải bù. Dự phòng không phải tải vật lý.",
        "",
        "| Trạng thái | Âm thanh | Điện âm thanh (W) | Tổng tải (W) | Máy phát khả dụng (W) | Dư trước sạc (W) | Đạt sạc + dự phòng? |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    names = {"driving_day": "Chạy ban ngày", "driving_night_ac": "Chạy ban đêm + quạt", "idle_night_ac": "Không tải ban đêm + quạt",
             "old_cd": "CD cũ", "android_normal": "Android vừa", "android_loud": "Android lớn", "external_amp_sub": "Ampli/sub lớn"}
    for r in data["scenarios"]:
        lines.append(f'| {names[r["state"]]} | {names[r["audio"]]} | {r["audio_input_w"]:.2f} | {r["total_service_load_w"]:.2f} | {r["available_alternator_w"]:.2f} | {r["margin_before_charge_w"]:.2f} | {"Có" if r["charge_target_and_reserve_met"] else "Không"} |')
    lines += ["", "## Năng lượng khi chạy ở tốc độ trung bình 20 km/h", "",
              "Hiệu suất máy phát 55%, hiệu suất gia tăng động cơ 22%, xăng 8,9 kWh/lít.",
              "Mức nền 9,2 lít/100 km tương đương 818,8 Wh năng lượng hóa học/km.",
              "Cột tăng so CD chỉ tính phần chênh lệch; không cộng toàn bộ đầu mới vào đầu cũ.", "",
              "| Âm thanh | Điện (Wh/km) | Xăng quy cho âm thanh (lít/100 km) | Tăng so CD (lít/100 km) |",
              "|---|---:|---:|---:|"]
    for r in data["scenarios"][:4]:
        f = r["fuel_for_audio"]
        lines.append(f'| {names[r["audio"]]} | {f["electrical_wh_per_km"]:.3f} | {f["extra_l_per_100km"]:.3f} | {r["replacement_vs_cd"]["extra_l_per_100km"]:.3f} |')
    lines += ["", "## Độ nhạy máy phát", "", "Tải 460 W + Android vừa, nhiệt 0,85. Không thể dùng số A danh định làm số A tại không tải.", "",
              "| Danh định (A) | Hệ số tốc độ | Khả dụng (W) | Dư trước sạc (W) |", "|---:|---:|---:|---:|"]
    for r in data["sensitivity"]:
        lines.append(f'| {r["rated_a"]} | {r["speed_factor"]:.1f} | {r["available_alternator_w"]:.2f} | {r["margin_before_charge_w"]:.2f} |')
    lines += ["", "## Độ nhạy xăng tăng do đổi CD sang Android ở cùng công suất loa", "",
              "| Tốc độ (km/h) | Hiệu suất gia tăng động cơ | Tăng (lít/100 km) |", "|---:|---:|---:|"]
    for r in data["fuel_sensitivity"]:
        lines.append(f'| {r["speed_kmh"]} | {r["engine_efficiency"]:.2f} | {r["extra_l_per_100km"]:.3f} |')
    off = data["engine_off"]
    lines += ["", "## Khi động cơ tắt", "",
              "Ắc quy giả định 45 Ah, dung lượng còn 70%, SOC từ 85% đến mốc dự phòng 60%: 99,225 Wh.",
              f'Chỉ Android vừa: {off["audio_only_hours_to_reserve"]:.2f} giờ tới mốc; thêm tải phụ 100 W: {off["audio_plus_100w_accessories_hours"]:.2f} giờ.',
              "Đây không phải thời gian nghe nhạc được bảo đảm hoặc thời điểm hết điện/không đề được.", "",
              "| Dòng rò tăng thêm (A) | Điện mất sau 72 giờ (Ah) | Giờ tới mốc dự phòng giả định |", "|---:|---:|---:|"]
    for r in data["parked_leak"]:
        lines.append(f'| {r["additional_sleep_current_a"]:.3f} | {r["additional_ah_over_72h"]:.2f} | {r["hours_to_assumed_reserve"]:.2f} |')
    lines += ["", "Không tải: kết quả trên mỗi km là null, vì xe không đi được km nào. Lít/giờ vẫn có nghĩa.",
              "Xăng cho âm thanh là ước lượng năng lượng dài hạn, không phải xăng tức thời khi ắc quy đang bù điện.", ""]
    (ROOT / "docs/KET_QUA.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
