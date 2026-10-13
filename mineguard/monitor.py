
import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd
from joblib import load

from influx_writer import send_ml_result
from risk_score import calculate_risk, risk_level


TRUCK_CAPACITY = 90
LOW_FUEL = 25

ALERTS_FILE = Path(__file__).parent / "alerts.csv"
ML_MODEL_FILE = Path(__file__).parent / "risk_model.joblib"

ml_model = load(ML_MODEL_FILE)


def save_alert(truck_name, alert_type, payload, fuel, speed):
    file_exists = ALERTS_FILE.exists()

    with open(ALERTS_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not file_exists or ALERTS_FILE.stat().st_size == 0:
            writer.writerow([
                "timestamp",
                "truck",
                "alert_type",
                "payload",
                "fuel",
                "speed"
            ])

        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            truck_name,
            alert_type,
            payload,
            fuel,
            speed
        ])


def check_truck(truck_name, message):
    data = json.loads(message)
    features = data["value"]

    payload = features["payload"]["properties"]["value"]
    fuel = features["fuel"]["properties"]["value"]
    speed = features["speed"]["properties"]["value"]

    print(f"\n🚛 Самосвал: {truck_name}")
    print(f"Груз: {payload} тонн")
    print(f"Топливо: {fuel}%")
    print(f"Скорость: {speed} км/ч")

    # ML: обнаружение необычного поведения
    sample = pd.DataFrame(
        [[payload, fuel, speed]],
        columns=["payload", "fuel", "speed"]
    )

    prediction = ml_model.predict(sample)[0]
    score = ml_model.decision_function(sample)[0]

    is_anomaly = prediction == -1

    # Расчёт Risk Score
    risk = calculate_risk(
        payload=payload,
        fuel=fuel,
        is_anomaly=is_anomaly
    )

    level = risk_level(risk)

    print(f"🛡️ Risk Score: {risk}/100")
    print(f"🚦 Risk Level: {level}")

    if level == "HIGH":
        print("🚨🚨 CRITICAL ALERT — HIGH RISK! 🚨🚨")
        print(f"🚛 Самосвал: {truck_name}")
        print(f"🔴 Risk Score: {risk}/100")
        print("⚠️ Требуется проверка состояния самосвала!")
        save_alert(truck_name, "HIGH_RISK", payload, fuel, speed)

    # Отправка ML-результата и Risk Score в InfluxDB
    try:
        send_ml_result(
            truck=truck_name,
            is_anomaly=is_anomaly,
            score=score,
            risk=risk
        )
        print("📊 ML и Risk Score отправлены в InfluxDB")
    except Exception as error:
        print(f"⚠️ Ошибка отправки в InfluxDB: {error}")

    # Проверка ML-аномалии
    if is_anomaly:
        print(f"🤖 ML: обнаружена аномалия (оценка {score:.4f})")
        save_alert(truck_name, "ML_ANOMALY", payload, fuel, speed)
    else:
        print(f"🤖 ML: обычное поведение (оценка {score:.4f})")

    # Проверка загрузки
    if payload > TRUCK_CAPACITY:
        print("🚨 ОПАСНОСТЬ: перегрузка!")
        save_alert(truck_name, "OVERLOAD", payload, fuel, speed)

    elif payload >= TRUCK_CAPACITY * 0.9:
        print("⚠️ ВНИМАНИЕ: почти полная загрузка!")
        save_alert(truck_name, "HIGH_LOAD", payload, fuel, speed)

    else:
        print("✅ Загрузка в норме")

    # Проверка топлива
    if fuel < LOW_FUEL:
        print("⛽ ВНИМАНИЕ: низкий уровень топлива!")
        save_alert(truck_name, "LOW_FUEL", payload, fuel, speed)


print("=== MineGuard AI — непрерывный мониторинг ===")
print("Для остановки нажми Ctrl + C")

process = None

try:
    process = subprocess.Popen(
        [
            "docker", "exec", "-i", "openegiz-mosquitto-1",
            "mosquitto_sub",
            "-h", "localhost",
            "-t", "telemetry/truck-01",
            "-t", "telemetry/truck-02",
            "-v",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    for line in process.stdout:
        if not line.strip():
            continue

        try:
            topic, message = line.strip().split(" ", 1)
            truck_name = topic.split("/")[-1]

            check_truck(truck_name, message)

        except (
            ValueError,
            json.JSONDecodeError,
            KeyError,
            TypeError
        ) as error:
            print(f"Ошибка обработки сообщения: {error}")

except KeyboardInterrupt:
    print("\nМониторинг остановлен пользователем.")

except OSError as error:
    print(f"Ошибка запуска MQTT: {error}")

finally:
    if process is not None and process.poll() is None:
        process.terminate()

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
