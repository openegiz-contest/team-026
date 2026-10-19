def calculate_risk(payload, fuel, is_anomaly):
    risk = 0

    # Риск из-за высокой загрузки
    if payload > 90:
        risk += 50
    elif payload >= 81:
        risk += 25

    # Риск из-за низкого топлива
    if fuel < 15:
        risk += 30
    elif fuel < 25:
        risk += 15

    # Дополнительный риск при ML-аномалии
    if is_anomaly:
        risk += 35

    return min(risk, 100)


def risk_level(score):
    if score >= 70:
        return "HIGH"
    elif score >= 35:
        return "MEDIUM"
    return "LOW"