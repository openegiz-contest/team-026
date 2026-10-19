"""Decide when the *haul-trained* IsolationForest may be evaluated.

An unscored observation is **not** proof of normal/safe operation. Heuristic
payload/fuel rules continue to apply regardless of the model gate.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class MLDecision:
    scored: bool
    anomaly: bool
    score: float | None
    reason: str


def evaluate_ml(model, payload: float, fuel: float, speed: float, state: str) -> MLDecision:
    """Score only moving, loaded, hauling trucks (training domain)."""
    normalized = str(state or "unknown").strip().lower()
    if normalized != "hauling":
        return MLDecision(False, False, None, f"state={normalized}")
    if speed <= 1 or payload <= 0:
        return MLDecision(False, False, None, "not_moving_loaded")

    import pandas as pd
    sample = pd.DataFrame([[payload, fuel, speed]], columns=["payload", "fuel", "speed"])
    anomaly = bool(model.predict(sample)[0] == -1)
    score = float(model.decision_function(sample)[0])
    return MLDecision(True, anomaly, score, "scored")
