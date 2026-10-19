"""Seeded uncertainty study around the contest's deterministic haul simulation.

Inputs are assumptions, NOT calibrated reliability or a real probability model.
"""
from dataclasses import dataclass, replace
import math
import random
from statistics import mean

from operations_sim import Scenario, Stochastic, run_haul_shift


@dataclass(frozen=True)
class MonteCarloAssumptions:
    speed_variation: float = 0.10
    duration_variation: float = 0.15
    mean_time_between_failures_hours: float = 24.0
    repair_min_minutes: int = 30
    repair_max_minutes: int = 90


def _percentile(values, percentile):
    if not values:
        raise ValueError("Empty values")
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100
    lo = math.floor(position)
    hi = math.ceil(position)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def run_monte_carlo(scenario: Scenario, *, n=200, seed=42, plan_tonnes=None,
                    assumptions=None):
    if not 1 <= n <= 5000:
        raise ValueError("n must be 1–5000")
    if plan_tonnes is not None and (not math.isfinite(plan_tonnes) or plan_tonnes < 0):
        raise ValueError("Plan must be nonnegative and finite")
    assumptions = assumptions or MonteCarloAssumptions()
    rng = random.Random(seed)
    deliveries = []
    failure_count = 0
    for _ in range(n):
        # One independently sampled speed and two task durations per model run.
        speed_factor = rng.uniform(1-assumptions.speed_variation, 1+assumptions.speed_variation)
        speed = max(1.0, min(80.0, scenario.loaded_speed_kmh * speed_factor))
        config = replace(scenario, loaded_speed_kmh=speed)
        hourly_rate = 1 / assumptions.mean_time_between_failures_hours
        # Probability of >=1 failure within the shift, for each of two trucks.
        fail_probability = 1 - math.exp(-config.shift_hours * hourly_rate)
        repairs = [rng.randint(assumptions.repair_min_minutes, assumptions.repair_max_minutes)
                   if rng.random() < fail_probability else 0 for _ in range(2)]
        failure_count += sum(bool(x) for x in repairs)
        stochastic = Stochastic(
            loading_multiplier=rng.uniform(1-assumptions.duration_variation, 1+assumptions.duration_variation),
            dump_multiplier=rng.uniform(1-assumptions.duration_variation, 1+assumptions.duration_variation),
            repair_truck_01_minutes=repairs[0], repair_truck_02_minutes=repairs[1],
        )
        deliveries.append(run_haul_shift(config, stochastic)["tonnes"])
    reference = run_haul_shift(scenario)["tonnes"]
    return {
        "seed": seed, "runs": n, "deterministic_tonnes": reference,
        "p10_tonnes": round(_percentile(deliveries,10), 1),
        "p50_tonnes": round(_percentile(deliveries,50), 1),
        "p90_tonnes": round(_percentile(deliveries,90), 1),
        "mean_tonnes": round(mean(deliveries), 1),
        "plan_tonnes": plan_tonnes,
        "plan_met_pct": round(sum(v >= plan_tonnes for v in deliveries) / n * 100, 1) if plan_tonnes is not None else None,
        "failure_events_sampled": failure_count,
        "samples_tonnes": deliveries,
        "assumptions": vars(assumptions),
        "note": "Synthetic uncertainty experiment; not an empirical mining forecast or calibrated probabilities.",
    }
