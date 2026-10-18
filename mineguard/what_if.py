"""Counterfactual safety assessment using the same model as monitor.py.

Computations do not mutate any twins. The UI can explicitly publish selected
results to Team 026 sandbox twins; live Example Mine twins are never changed.
"""
import math
from pathlib import Path

import pandas as pd
from joblib import load

from risk_score import calculate_risk, risk_level

MODEL_PATH = Path(__file__).parent / "risk_model.joblib"
model = load(MODEL_PATH)


def risk_factors(payload, fuel, is_anomaly):
    """Explain the exact heuristic already used by the live monitoring service."""
    return {
        "Overload / high payload": 50 if payload > 90 else 25 if payload >= 81 else 0,
        "Low fuel": 30 if fuel < 15 else 15 if fuel < 25 else 0,
        "ML outlier": 35 if is_anomaly else 0,
    }


def simulate(payload, fuel, speed):
    values = (payload, fuel, speed)
    if any(not math.isfinite(float(v)) for v in values):
        raise ValueError("All inputs must be finite numeric values")
    if not (0 <= payload <= 120 and 0 <= fuel <= 100 and 0 <= speed <= 80):
        raise ValueError("Expected payload 0–120 t, fuel 0–100%, speed 0–80 km/h")

    sample = pd.DataFrame([[payload, fuel, speed]], columns=["payload", "fuel", "speed"])
    is_anomaly = bool(model.predict(sample)[0] == -1)
    decision_score = float(model.decision_function(sample)[0])
    factors = risk_factors(payload, fuel, is_anomaly)
    risk = int(calculate_risk(payload=payload, fuel=fuel, is_anomaly=is_anomaly))
    assert risk == min(sum(factors.values()), 100)

    return {
        "payload": float(payload),
        "fuel": float(fuel),
        "speed": float(speed),
        "anomaly": is_anomaly,
        "ml_decision_score": round(decision_score, 5),
        "risk": risk,
        "level": risk_level(risk),
        "factors": factors,
    }


def show_result(name, result):
    print(f"\n--- {name} ---")
    for title, key, unit in (("Груз", "payload", "т"), ("Топливо", "fuel", "%"), ("Скорость", "speed", "км/ч")):
        print(f"{title}: {result[key]} {unit}")
    print(f"ML anomaly: {result['anomaly']} (decision={result['ml_decision_score']:.4f})")
    print(f"Risk Score: {result['risk']}/100 ({result['level']})")


if __name__ == "__main__":
    before = simulate(70, 60, 25)
    after = simulate(95, 12, 35)
    show_result("BEFORE", before)
    show_result("AFTER", after)
    print(f"\nRisk delta: {after['risk'] - before['risk']:+d} points")
