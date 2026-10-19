"""ML gating unit tests; no Docker or network required."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml_gate import evaluate_ml


class MLGateTests(unittest.TestCase):
    def setUp(self):
        self.model = Mock()
        self.model.predict.return_value = [-1]
        self.model.decision_function.return_value = [-0.25]

    def test_unscored_for_normal_nonhaul_states(self):
        states = ('loading', 'queued_at_excavator', 'waiting_loader', 'dumping',
                  'returning', 'refueling', 'maintenance', 'repair', 'idle', 'unknown')
        for state in states:
            with self.subTest(state=state):
                result = evaluate_ml(self.model, 85, 60, 0, state)
                self.assertFalse(result.scored)
                self.assertFalse(result.anomaly)
                self.assertIsNone(result.score)
        self.model.predict.assert_not_called()

    def test_many_off_domain_samples_do_not_invoke_model(self):
        for i in range(2700):
            state = ('loading', 'dumping', 'returning')[i % 3]
            result = evaluate_ml(self.model, 84 + i % 5, 60, 0, state)
            self.assertFalse(result.anomaly)
        self.model.predict.assert_not_called()

    def test_moving_loaded_haul_is_scored(self):
        result = evaluate_ml(self.model, 85, 55, 27, 'hauling')
        self.assertTrue(result.scored)
        self.assertTrue(result.anomaly)
        self.assertEqual(result.score, -0.25)
        self.model.predict.assert_called_once()

    def test_stopped_or_empty_haul_not_scored(self):
        self.assertFalse(evaluate_ml(self.model, 80, 55, 0, 'hauling').scored)
        self.assertFalse(evaluate_ml(self.model, 0, 55, 20, 'hauling').scored)
        self.model.predict.assert_not_called()

    def test_state_not_case_sensitive(self):
        self.assertTrue(evaluate_ml(self.model, 65, 70, 20, ' Hauling ').scored)

    def test_skipped_ml_keeps_separate_heuristic_risk(self):
        from risk_score import calculate_risk
        decision = evaluate_ml(self.model, 95, 12, 0, 'loading')
        self.assertFalse(decision.scored)
        self.assertEqual(calculate_risk(95, 12, decision.anomaly), 80)

    def test_shipped_model_detects_known_haul_outlier(self):
        from joblib import load
        real = load(Path(__file__).resolve().parents[1] / 'risk_model.joblib')
        result = evaluate_ml(real, 10, 50, 25, 'hauling')
        self.assertTrue(result.scored)
        self.assertTrue(result.anomaly)


if __name__ == '__main__':
    unittest.main()
