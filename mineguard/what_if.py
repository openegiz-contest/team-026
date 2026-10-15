from pathlib import Path

import pandas as pd
from joblib import load

from risk_score import calculate_risk, risk_level


# Загружаем обученную ML-модель
MODEL_PATH = Path(__file__).parent / "risk_model.joblib"
model = load(MODEL_PATH)


def simulate(payload, fuel, speed):
    # Проверяем допустимость исходных значений
    if payload < 0 or not 0 <= fuel <= 100 or speed < 0:
        raise ValueError("Некорректные параметры самосвала")

    # Подготавливаем данные для ML
    data = pd.DataFrame(
        [[payload, fuel, speed]],
        columns=["payload", "fuel", "speed"]
    )

    # Проверяем аномалию
    prediction = model.predict(data)[0]
    is_anomaly = prediction == -1

    # Рассчитываем риск
    risk = calculate_risk(
        payload=payload,
        fuel=fuel,
        is_anomaly=is_anomaly
    )

    return {
        "payload": payload,
        "fuel": fuel,
        "speed": speed,
        "anomaly": is_anomaly,
        "risk": risk,
        "level": risk_level(risk)
    }


def show_result(name, result):
    print(f"\n--- {name} ---")
    print(f"Груз: {result['payload']} тонн")
    print(f"Топливо: {result['fuel']}%")
    print(f"Скорость: {result['speed']} км/ч")
    print(f"ML-аномалия: {result['anomaly']}")
    print(f"Risk Score: {result['risk']}/100")
    print(f"Уровень риска: {result['level']}")


if __name__ == "__main__":
    print("=== MineGuard AI | What-if Simulator ===")

    # Сценарий 1: нормальная работа
    before = simulate(
        payload=70,
        fuel=60,
        speed=25
    )

    # Сценарий 2: перегрузка и мало топлива
    after = simulate(
        payload=95,
        fuel=12,
        speed=35
    )

    show_result("BEFORE", before)
    show_result("AFTER", after)

    difference = after["risk"] - before["risk"]

    print("\n=== COMPARISON ===")
    print(f"Изменение Risk Score: {difference:+d} баллов")
    print(f"До: {before['level']}")
    print(f"После: {after['level']}")