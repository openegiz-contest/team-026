import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from operations_sim import Scenario, Stochastic, run_haul_shift
from monte_carlo import run_monte_carlo
from quarry_view import render_cycle

class MonteCarloTests(unittest.TestCase):
    def test_same_seed_same_results(self):
        a=run_monte_carlo(Scenario(), n=30, seed=17, plan_tonnes=3000)
        b=run_monte_carlo(Scenario(), n=30, seed=17, plan_tonnes=3000)
        self.assertEqual(a,b)

    def test_percentiles_ordered(self):
        result=run_monte_carlo(Scenario(), n=40, plan_tonnes=3000)
        self.assertLessEqual(result['p10_tonnes'],result['p50_tonnes'])
        self.assertLessEqual(result['p50_tonnes'],result['p90_tonnes'])
        self.assertGreaterEqual(result['plan_met_pct'],0)
        self.assertLessEqual(result['plan_met_pct'],100)

    def test_deterministic_unchanged(self):
        self.assertEqual(run_haul_shift(Scenario()),run_haul_shift(Scenario(),Stochastic()))
        result=run_monte_carlo(Scenario(),n=10)
        self.assertEqual(result['deterministic_tonnes'],run_haul_shift(Scenario())['tonnes'])

    def test_stochastic_parameters_change_production(self):
        baseline=run_haul_shift(Scenario())
        slower=run_haul_shift(Scenario(),Stochastic(loading_multiplier=1.5,dump_multiplier=1.5))
        self.assertLess(slower['tonnes'],baseline['tonnes'])

    def test_invalid_sample_count(self):
        for n in (0,5001):
            with self.assertRaises(ValueError):run_monte_carlo(Scenario(),n=n)

    def test_quarry_render_is_escaped(self):
        rendered=render_cycle(run_haul_shift(Scenario()),'<unsafe>')
        self.assertIn('&lt;unsafe&gt;',rendered)
        self.assertIn('Дробилка',rendered)

if __name__ == '__main__':unittest.main()
