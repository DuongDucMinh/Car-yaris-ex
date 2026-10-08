import json
import math
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

from yaris_power import Audio, Battery, Vehicle, electrical_budget, fuel_effect, replacement_effect, scenarios, wav_statistics

ROOT = Path(__file__).resolve().parents[1]


class ModelTests(unittest.TestCase):
    def test_audio_energy_balance(self):
        self.assertAlmostEqual(Audio().input_w, 25 + 10 / .55)
        self.assertAlmostEqual(Audio(external_speaker_average_w=400, external_idle_w=10).input_w, 25 + 10 / .55 + 400 / .85 + 10)

    def test_voltage_current_power(self):
        r = electrical_budget(Vehicle(), Audio())
        self.assertAlmostEqual(r["audio_input_a"] * 14, r["audio_input_w"])
        self.assertAlmostEqual(r["available_alternator_w"], 952)

    def test_idle_service_deficit(self):
        r = electrical_budget(Vehicle(speed_factor=.4, other_loads_w=460), Audio())
        self.assertAlmostEqual(r["available_alternator_w"], 380.8)
        self.assertAlmostEqual(r["battery_discharge_w"], 122.38181818181818)
        self.assertEqual(r["possible_charge_w"], 0)
        self.assertTrue(r["service_deficit"])

    def test_charge_shortfall_is_not_discharge(self):
        # 14 * 10 A supply, 130 W service load: 10 W charging, NOT 74 W draining.
        r = electrical_budget(Vehicle(alternator_rated_a=10, thermal_factor=1, other_loads_w=130),
                              Audio(electronics_w=0, speaker_average_w=0))
        self.assertEqual(r["battery_discharge_w"], 0)
        self.assertEqual(r["possible_charge_w"], 10)
        self.assertEqual(r["requested_charge_shortfall_w"], 74)

    def test_reserve_is_not_physical_load(self):
        r = electrical_budget(Vehicle(alternator_rated_a=10, thermal_factor=1, other_loads_w=130,
                                      requested_charge_a=0), Audio(electronics_w=0, speaker_average_w=0))
        self.assertFalse(r["charge_target_and_reserve_met"])
        self.assertFalse(r["service_deficit"])

    def test_boundary_load_matches_supply(self):
        r = electrical_budget(Vehicle(alternator_rated_a=10, thermal_factor=1, other_loads_w=140),
                              Audio(electronics_w=0, speaker_average_w=0))
        self.assertEqual(r["margin_before_charge_w"], 0)
        self.assertFalse(r["service_deficit"])

    def test_required_rating_satisfies_design(self):
        v = Vehicle(speed_factor=.4, other_loads_w=460)
        rating = electrical_budget(v, Audio())["required_rated_a_for_assumed_conditions"]
        updated = Vehicle(**{**v.__dict__, "alternator_rated_a": rating + .000001})
        self.assertTrue(electrical_budget(updated, Audio())["charge_target_and_reserve_met"])

    def test_fuel_units_hand_calculation(self):
        # 100 W electric / .5 / .2 = 1000 W chemical; 10 kWh/L => .1 L/h.
        r = fuel_effect(Vehicle(alternator_efficiency=.5, engine_incremental_efficiency=.2,
                                gasoline_kwh_per_l=10, speed_kmh=25, baseline_l_per_100km=8), 100)
        self.assertAlmostEqual(r["extra_l_per_hour"], .1)
        self.assertAlmostEqual(r["extra_l_per_100km"], .4)
        self.assertEqual(r["electrical_wh_per_km"], 4)
        self.assertEqual(r["baseline_chemical_wh_per_km"], 800)

    def test_stopped_vehicle_no_per_km(self):
        r = fuel_effect(Vehicle(speed_kmh=0), 100)
        self.assertIsNone(r["extra_l_per_100km"])
        self.assertIsNone(r["electrical_wh_per_km"])
        self.assertGreater(r["extra_l_per_hour"], 0)

    def test_replacement_counts_only_delta(self):
        old, new = Audio(electronics_w=8), Audio()
        r = replacement_effect(Vehicle(), old, new)
        self.assertEqual(r["electrical_w"], 17)
        self.assertAlmostEqual(r["extra_l_per_100km"], .0789302632556412)
        self.assertEqual(replacement_effect(Vehicle(), new, new)["extra_l_per_hour"], 0)

    def test_lower_power_replacement_saves_fuel(self):
        r = replacement_effect(Vehicle(), Audio(), Audio(electronics_w=8))
        self.assertEqual(r["electrical_w"], -17)
        self.assertLess(r["extra_l_per_hour"], 0)

    def test_battery_budget_and_zero(self):
        b = Battery()
        self.assertAlmostEqual(b.budget_wh, 99.225)
        self.assertAlmostEqual(b.hours_to_reserve(100), .99225)
        self.assertIsNone(b.hours_to_reserve(0))

    def test_invalid_inputs(self):
        invalid = [
            (Audio, {"speaker_average_w": -1}), (Audio, {"amplifier_efficiency": 0}),
            (Audio, {"external_amplifier_efficiency": 1.01}), (Audio, {"electronics_w": float("nan")}),
            (Vehicle, {"bus_voltage_v": 0}), (Vehicle, {"speed_factor": 0}),
            (Vehicle, {"thermal_factor": 1.01}), (Vehicle, {"design_reserve_fraction": 1}),
            (Vehicle, {"speed_kmh": -1}), (Vehicle, {"alternator_rated_a": float("inf")}),
            (Battery, {"initial_soc": .3, "reserve_soc": .6}), (Battery, {"capacity_ah": True}),
            (Battery, {"capacity_health_fraction": 0}), (Vehicle, {"speed_kmh": "20"}),
        ]
        for cls, args in invalid:
            with self.subTest(cls=cls, args=args), self.assertRaises(ValueError):
                cls(**args)

    def test_negative_budget_arguments(self):
        with self.assertRaises(ValueError):
            fuel_effect(Vehicle(), -1)
        with self.assertRaises(ValueError):
            Battery().hours_to_reserve(-1)

    def test_randomized_conservation(self):
        rng = random.Random(2008)
        for _ in range(300):
            v = Vehicle(alternator_rated_a=rng.uniform(30, 160), speed_factor=rng.uniform(.2, 1),
                        other_loads_w=rng.uniform(0, 1000), requested_charge_a=rng.uniform(0, 20))
            a = Audio(speaker_average_w=rng.uniform(0, 100))
            r = electrical_budget(v, a)
            used_supply = min(r["available_alternator_w"], r["total_service_load_w"])
            self.assertAlmostEqual(used_supply + r["battery_discharge_w"], r["total_service_load_w"])
            self.assertGreaterEqual(r["possible_charge_w"], 0)
            self.assertLessEqual(r["possible_charge_w"], v.requested_charge_a * v.bus_voltage_v + 1e-9)
            self.assertFalse(r["battery_discharge_w"] > 0 and r["possible_charge_w"] > 0)

    def test_scenarios_are_strict_json(self):
        r = scenarios()
        self.assertEqual(len(r["scenarios"]), 12)
        self.assertEqual(len(r["sensitivity"]), 12)
        self.assertEqual(len(r["fuel_sensitivity"]), 9)
        json.dumps(r, allow_nan=False)


class WavTests(unittest.TestCase):
    def make_wav(self, folder, samples, channels=1, width=2, declared_extra=False):
        filename = Path(folder) / "audio.wav"
        with wave.open(str(filename), "wb") as out:
            out.setnchannels(channels)
            out.setsampwidth(width)
            out.setframerate(8000)
            out.writeframes(b"".join(struct.pack("<h", n) for n in samples) if width == 2 else bytes(samples))
        if declared_extra:
            raw = filename.read_bytes()
            filename.write_bytes(raw[:-2])
        return filename

    def test_rms_and_crest_known_samples(self):
        with tempfile.TemporaryDirectory() as folder:
            r = wav_statistics(self.make_wav(folder, [16384, -16384, 0, 0]))
        self.assertAlmostEqual(r["mean_square_full_scale"], .125)
        self.assertAlmostEqual(r["crest_db"], 10 * math.log10(2))
        self.assertAlmostEqual(r["duration_s"], 4 / 8000)

    def test_stereo_silence_channel_is_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            r = wav_statistics(self.make_wav(folder, [16384, 0, -16384, 0], channels=2))
        self.assertEqual(r["channels"], 2)
        self.assertAlmostEqual(r["mean_square_full_scale"], .125)
        self.assertAlmostEqual(r["duration_s"], 2 / 8000)

    def test_silence_finite_json(self):
        with tempfile.TemporaryDirectory() as folder:
            r = wav_statistics(self.make_wav(folder, [0, 0]))
        self.assertEqual(r["rms_full_scale"], 0)
        self.assertIsNone(r["rms_dbfs"])
        self.assertIsNone(r["crest_db"])
        json.dumps(r, allow_nan=False)

    def test_double_amplitude_quadruples_relative_power(self):
        with tempfile.TemporaryDirectory() as folder:
            low = wav_statistics(self.make_wav(folder, [1000, -1000]))
            high = wav_statistics(self.make_wav(folder, [2000, -2000]))
        self.assertAlmostEqual(high["mean_square_full_scale"] / low["mean_square_full_scale"], 4)

    def test_negative_fullscale_sample(self):
        with tempfile.TemporaryDirectory() as folder:
            r = wav_statistics(self.make_wav(folder, [-32768]))
        self.assertEqual(r["sample_peak_full_scale"], 1)

    def test_reject_empty_unsupported_and_truncated(self):
        with tempfile.TemporaryDirectory() as folder:
            for args in ({"samples": []}, {"samples": [128, 129], "width": 1},
                         {"samples": [1000, 2000], "declared_extra": True}):
                with self.subTest(args=args), self.assertRaises(ValueError):
                    wav_statistics(self.make_wav(folder, **args))


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "yaris_power.py"), *map(str, args)],
                              cwd=ROOT, text=True, capture_output=True)

    def test_default_and_config(self):
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(json.loads(r.stdout)["scenarios"]), 12)
        r = self.run_cli("--config", ROOT / "examples/assumptions.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout)["budget"]["service_deficit"])

    def test_output_file(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "output.json"
            r = self.run_cli("--output", output)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "")
            self.assertIn("scenarios", json.loads(output.read_text(encoding="utf-8")))

    def test_bad_config_unknown_field_and_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "bad.json"
            for content in ('{"vehicle":{"speed_kmh":-1}}', '{"vehicle":{"mystery":1}}', '{"mystery":1}', "[]", "{broken"):
                filename.write_text(content, encoding="utf-8")
                r = self.run_cli("--config", filename)
                self.assertEqual(r.returncode, 2)
                self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.run_cli("--config", "missing-file.json").returncode, 2)

    def test_conflicting_options(self):
        self.assertEqual(self.run_cli("--config", "x.json", "--wav", "x.wav").returncode, 2)


if __name__ == "__main__":
    unittest.main()
