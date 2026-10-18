"""Standard-library regression tests for the submission's independent scenarios."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from operations_sim import Scenario, run_haul_shift
from risk_score import calculate_risk, risk_level
from what_if import simulate


class RiskRegressionTests(unittest.TestCase):
    def test_known_baseline(self):
        result = simulate(70, 60, 25)
        self.assertEqual(result["risk"], 0)
        self.assertEqual(result["level"], "LOW")

    def test_overload_low_fuel(self):
        result = simulate(95, 12, 35)
        self.assertGreaterEqual(result["risk"], 80)
        self.assertEqual(result["level"], "HIGH")
        self.assertEqual(result["risk"], min(sum(result["factors"].values()),100))

    def test_shipped_model_detects_known_outlier(self):
        # Actual model classification, not a hardcoded UI flag.
        result = simulate(10, 50, 25)
        self.assertTrue(result["anomaly"])
        self.assertLess(result["ml_decision_score"], 0)
        self.assertEqual(result["risk"], 35)
        self.assertEqual(result["level"], "MEDIUM")

    def test_exact_thresholds(self):
        self.assertEqual(calculate_risk(90, 25, False), 25)
        self.assertEqual(calculate_risk(91, 24, False), 65)
        self.assertEqual(calculate_risk(91, 14, True), 100)
        self.assertEqual(risk_level(34), "LOW")
        self.assertEqual(risk_level(35), "MEDIUM")
        self.assertEqual(risk_level(70), "HIGH")

    def test_invalid_or_nonfinite_values(self):
        for args in ((-1,60,20),(50,101,20),(50,60,-1),(float("nan"),60,20)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                simulate(*args)


class HaulCycleTests(unittest.TestCase):
    def setUp(self):
        self.base = run_haul_shift(Scenario())

    def test_produces_ore_and_monotonic_timeline(self):
        self.assertGreater(self.base["tonnes"], 0)
        self.assertEqual(len(self.base["timeline"]), 16)
        readings = [r["tonnes"] for r in self.base["timeline"]]
        self.assertEqual(readings, sorted(readings))
        self.assertEqual(readings[-1],self.base["tonnes"])
        self.assertAlmostEqual(self.base["tonnes"],self.base["trips"]*70)

    def test_road_slowdown_reduces_throughput(self):
        wet = run_haul_shift(Scenario(road_slowdown_pct=45))
        self.assertLess(wet["tonnes"],self.base["tonnes"])

    def test_crusher_congestion_reduces_throughput(self):
        slow = run_haul_shift(Scenario(crusher_delay_seconds=240))
        self.assertLess(slow["tonnes"],self.base["tonnes"])

    def test_truck_repair_reduces_throughput(self):
        repair = run_haul_shift(Scenario(maintenance_minutes=120))
        self.assertLess(repair["tonnes"],self.base["tonnes"])
        self.assertGreater(repair["maintenance_minutes"],0)

    def test_refuelling_is_accounted_for(self):
        low = run_haul_shift(Scenario(fuel_pct=10))
        self.assertGreater(low["refuel_minutes"], self.base["refuel_minutes"])
        self.assertLessEqual(low["tonnes"], self.base["tonnes"])

    def test_reduced_loaded_speed_changes_delivery(self):
        slow = run_haul_shift(Scenario(loaded_speed_kmh=15))
        self.assertLess(slow["tonnes"], self.base["tonnes"])

    def test_maintenance_zero_is_equivalent_to_base(self):
        same = run_haul_shift(Scenario(maintenance_minutes=0))
        self.assertEqual(same, self.base)

    def test_payload_capped_at_capacity(self):
        overload = run_haul_shift(Scenario(payload_t=110))
        self.assertEqual(overload["effective_payload_t"],90)
        self.assertAlmostEqual(overload["tonnes"], overload["trips"]*90)

    def test_zero_payload(self):
        empty = run_haul_shift(Scenario(payload_t=0))
        self.assertEqual(empty["tonnes"],0)
        self.assertEqual(empty["trips"],0)

    def test_repeatable(self):
        self.assertEqual(self.base,run_haul_shift(Scenario()))

    def test_reject_invalid(self):
        for scenario in (Scenario(fuel_pct=-1),Scenario(loaded_speed_kmh=0),Scenario(road_slowdown_pct=90), Scenario(payload_t=float('inf'))):
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                run_haul_shift(scenario)


if __name__ == "__main__":
    unittest.main()
