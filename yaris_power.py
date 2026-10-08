"""Illustrative car electrical budget: assumptions, not a diagnosis. Python 3.10+."""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import struct
import wave


def check(name, value, *, positive=False, fraction=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name}: must be a finite number")
    if value < 0 or (positive and value == 0) or (fraction and value > 1):
        raise ValueError(f"{name}: outside allowed range")


@dataclass(frozen=True)
class Audio:
    electronics_w: float = 25
    speaker_average_w: float = 10  # TOTAL electrical output to all speakers.
    amplifier_efficiency: float = 0.55
    external_speaker_average_w: float = 0
    external_amplifier_efficiency: float = 0.85
    external_idle_w: float = 0

    def __post_init__(self):
        for name in ("electronics_w", "speaker_average_w", "external_speaker_average_w", "external_idle_w"):
            check(name, getattr(self, name))
        for name in ("amplifier_efficiency", "external_amplifier_efficiency"):
            check(name, getattr(self, name), positive=True, fraction=True)

    @property
    def input_w(self):
        return (self.electronics_w + self.speaker_average_w / self.amplifier_efficiency
                + self.external_idle_w
                + self.external_speaker_average_w / self.external_amplifier_efficiency)


@dataclass(frozen=True)
class Vehicle:
    bus_voltage_v: float = 14
    alternator_rated_a: float = 80  # NOT a verified specification for this Yaris.
    speed_factor: float = 1
    thermal_factor: float = 0.85
    other_loads_w: float = 180  # Excludes old AND new head unit.
    requested_charge_a: float = 6
    design_reserve_fraction: float = 0.15
    alternator_efficiency: float = 0.55
    engine_incremental_efficiency: float = 0.22
    gasoline_kwh_per_l: float = 8.9
    speed_kmh: float = 20
    baseline_l_per_100km: float = 9.2

    def __post_init__(self):
        for name in ("bus_voltage_v", "alternator_rated_a", "gasoline_kwh_per_l"):
            check(name, getattr(self, name), positive=True)
        for name in ("speed_factor", "thermal_factor", "alternator_efficiency", "engine_incremental_efficiency"):
            check(name, getattr(self, name), positive=True, fraction=True)
        for name in ("other_loads_w", "requested_charge_a", "speed_kmh", "baseline_l_per_100km"):
            check(name, getattr(self, name))
        check("design_reserve_fraction", self.design_reserve_fraction, fraction=True)
        if self.design_reserve_fraction == 1:
            raise ValueError("reserve must be less than 1")


@dataclass(frozen=True)
class Battery:
    capacity_ah: float = 45
    capacity_health_fraction: float = 0.7
    initial_soc: float = 0.85
    reserve_soc: float = 0.60
    nominal_voltage_v: float = 12.6

    def __post_init__(self):
        for name in ("capacity_ah", "nominal_voltage_v"):
            check(name, getattr(self, name), positive=True)
        check("capacity_health_fraction", self.capacity_health_fraction, positive=True, fraction=True)
        for name in ("initial_soc", "reserve_soc"):
            check(name, getattr(self, name), fraction=True)
        if self.initial_soc < self.reserve_soc:
            raise ValueError("initial SOC must not be below reserve")

    @property
    def budget_wh(self):
        return self.capacity_ah * self.capacity_health_fraction * self.nominal_voltage_v * (self.initial_soc - self.reserve_soc)

    def hours_to_reserve(self, load_w):
        check("load_w", load_w)
        return self.budget_wh / load_w if load_w else None


def electrical_budget(v: Vehicle, a: Audio):
    """Charge is requested, not guaranteed battery acceptance. Reserve is planning only."""
    available_a = v.alternator_rated_a * v.speed_factor * v.thermal_factor
    available_w = available_a * v.bus_voltage_v
    load_w = v.other_loads_w + a.input_w
    margin_w = available_w - load_w
    charge_w = v.requested_charge_a * v.bus_voltage_v
    planning_w = available_w * (1 - v.design_reserve_fraction)
    return {
        "audio_input_w": a.input_w,
        "audio_input_a": a.input_w / v.bus_voltage_v,
        "available_alternator_a": available_a,
        "available_alternator_w": available_w,
        "total_service_load_w": load_w,
        "margin_before_charge_w": margin_w,
        "battery_discharge_w": max(0, -margin_w),
        "possible_charge_w": max(0, min(margin_w, charge_w)),
        "requested_charge_shortfall_w": max(0, charge_w - max(0, margin_w)),
        "planning_margin_after_charge_w": planning_w - load_w - charge_w,
        "service_deficit": margin_w < 0,
        "charge_target_and_reserve_met": planning_w >= load_w + charge_w,
        "required_rated_a_for_assumed_conditions": (load_w + charge_w) / (
            v.bus_voltage_v * v.speed_factor * v.thermal_factor * (1 - v.design_reserve_fraction)),
    }


def fuel_effect(v: Vehicle, electrical_w):
    """Constant incremental efficiency estimate; assumes eventual alternator energy supply."""
    check("electrical_w", electrical_w)
    mechanical_w = electrical_w / v.alternator_efficiency
    chemical_w = mechanical_w / v.engine_incremental_efficiency
    l_per_hour = chemical_w / (v.gasoline_kwh_per_l * 1000)
    moving = v.speed_kmh > 0
    return {
        "electrical_w": electrical_w,
        "mechanical_w": mechanical_w,
        "chemical_w": chemical_w,
        "extra_l_per_hour": l_per_hour,
        "electrical_wh_per_km": electrical_w / v.speed_kmh if moving else None,
        "extra_l_per_100km": l_per_hour / v.speed_kmh * 100 if moving else None,
        "baseline_chemical_wh_per_km": v.baseline_l_per_100km / 100 * v.gasoline_kwh_per_l * 1000 if moving else None,
    }


def replacement_effect(v, old, new):
    delta = new.input_w - old.input_w
    result = fuel_effect(v, abs(delta))
    for key in ("electrical_w", "mechanical_w", "chemical_w", "extra_l_per_hour", "electrical_wh_per_km", "extra_l_per_100km"):
        if result[key] is not None:
            result[key] *= -1 if delta < 0 else 1
    return result


def wav_statistics(filename):
    """Stream 16-bit PCM WAV. Digital RMS is NOT an absolute car power measurement."""
    with wave.open(str(filename), "rb") as wav:
        if wav.getsampwidth() != 2 or wav.getcomptype() != "NONE":
            raise ValueError("Only uncompressed 16-bit PCM WAV is supported")
        channels, rate = wav.getnchannels(), wav.getframerate()
        count, square_sum, peak = 0, 0, 0
        while raw := wav.readframes(8192):
            if len(raw) % (2 * channels):
                raise ValueError("Truncated PCM frame")
            for (sample,) in struct.iter_unpack("<h", raw):
                count += 1
                square_sum += sample * sample
                peak = max(peak, abs(sample))
        if count == 0 or count != wav.getnframes() * channels:
            raise ValueError("Empty or truncated WAV")
        mean_square = square_sum / count / 32768**2
        rms, peak_norm = math.sqrt(mean_square), peak / 32768
        return {
            "channels": channels, "duration_s": count / channels / rate,
            "rms_full_scale": rms, "mean_square_full_scale": mean_square,
            "sample_peak_full_scale": peak_norm,
            "rms_dbfs": 20 * math.log10(rms) if rms else None,
            "crest_db": 20 * math.log10(peak_norm / rms) if rms else None,
            "note": "Compare at same gain, EQ, speakers and processing; no absolute watt calibration.",
        }


def scenarios():
    old, normal = Audio(electronics_w=8), Audio()
    loud = Audio(speaker_average_w=40)
    external = Audio(speaker_average_w=40, external_speaker_average_w=400, external_idle_w=10)
    battery, rows = Battery(), []
    for state, factor, base in (("driving_day", 1, 180), ("driving_night_ac", 1, 460), ("idle_night_ac", 0.4, 460)):
        v = Vehicle(speed_factor=factor, other_loads_w=base, speed_kmh=0 if state.startswith("idle") else 20)
        for label, audio in (("old_cd", old), ("android_normal", normal), ("android_loud", loud), ("external_amp_sub", external)):
            budget = electrical_budget(v, audio)
            rows.append({"state": state, "audio": label, "vehicle": asdict(v), "audio_assumptions": asdict(audio),
                         **budget, "battery_hours_to_reserve_if_deficit": battery.hours_to_reserve(budget["battery_discharge_w"]),
                         "fuel_for_audio": fuel_effect(v, audio.input_w), "replacement_vs_cd": replacement_effect(v, old, audio)})
    sensitivity = []
    for rating in (60, 80, 100):
        for factor in (0.3, 0.4, 0.6, 1):
            v = Vehicle(alternator_rated_a=rating, speed_factor=factor, other_loads_w=460)
            sensitivity.append({"rated_a": rating, "speed_factor": factor, **electrical_budget(v, normal)})
    return {
        "warning": "Scenario values are assumptions, not measured specifications or a diagnosis.",
        "battery_assumptions": asdict(battery), "scenarios": rows, "sensitivity": sensitivity,
        "engine_off": {"audio_only_hours_to_reserve": battery.hours_to_reserve(normal.input_w),
                       "audio_plus_100w_accessories_hours": battery.hours_to_reserve(normal.input_w + 100)},
        "parked_leak": [{"additional_sleep_current_a": current, "additional_ah_over_72h": current * 72,
                        "hours_to_assumed_reserve": battery.hours_to_reserve(current * battery.nominal_voltage_v)}
                       for current in (0.005, 0.05, 0.3)],
        "fuel_sensitivity": [{"speed_kmh": speed, "engine_efficiency": eta,
                             **replacement_effect(Vehicle(speed_kmh=speed, engine_incremental_efficiency=eta), old, normal)}
                            for speed in (10, 20, 40) for eta in (0.15, 0.22, 0.30)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="JSON: vehicle, audio, optional battery/old_audio")
    parser.add_argument("--wav", type=Path, help="Analyze 16-bit PCM WAV")
    parser.add_argument("--output", type=Path, help="Save strict JSON; default stdout")
    args = parser.parse_args()
    if args.wav and args.config:
        parser.error("Use either --wav or --config")
    try:
        if args.wav:
            result = wav_statistics(args.wav)
        elif args.config:
            config = json.loads(args.config.read_text(encoding="utf-8"))
            if not isinstance(config, dict) or set(config) - {"vehicle", "audio", "battery", "old_audio"}:
                raise ValueError("Invalid configuration keys")
            v, a, b = Vehicle(**config.get("vehicle", {})), Audio(**config.get("audio", {})), Battery(**config.get("battery", {}))
            budget = electrical_budget(v, a)
            result = {"inputs": {"vehicle": asdict(v), "audio": asdict(a), "battery": asdict(b)},
                      "budget": budget, "fuel_for_audio": fuel_effect(v, a.input_w),
                      "battery_hours_to_reserve_if_deficit": b.hours_to_reserve(budget["battery_discharge_w"])}
            if "old_audio" in config:
                result["replacement_vs_old"] = replacement_effect(v, Audio(**config["old_audio"]), a)
        else:
            result = scenarios()
        output = json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
    except (ValueError, TypeError, OSError, wave.Error, EOFError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
