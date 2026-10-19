
import csv
import json
from datetime import datetime
from pathlib import Path

import os
import paho.mqtt.client as mqtt
from joblib import load

from influx_writer import send_ml_result
from risk_score import calculate_risk, risk_level
from ml_gate import evaluate_ml
from ditto_bridge import NAMESPACE, live_monitor_values, make_ditto_command


TRUCK_CAPACITY = 90
LOW_FUEL = 25

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ALERTS_FILE = DATA_DIR / "alerts.csv"
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


def check_truck(truck_name, message, publisher=None):
    data = json.loads(message)
    features = data["value"]

    payload = features["payload"]["properties"]["value"]
    fuel = features["fuel"]["properties"]["value"]
    speed = features["speed"]["properties"]["value"]

    print(f"\n🚛 Самосвал: {truck_name}")
    print(f"Груз: {payload} тонн")
    print(f"Топливо: {fuel}%")
    print(f"Скорость: {speed} км/ч")

    # Only loaded travel is within the IsolationForest training domain.
    # Unscored != safe: payload/fuel rules still contribute to Risk Score.
    truck_state = features.get("state", {}).get("properties", {}).get("value", "unknown")
    decision = evaluate_ml(ml_model, payload, fuel, speed, truck_state)
    is_anomaly = decision.anomaly
    score = decision.score

    # Расчёт Risk Score
    risk = calculate_risk(
        payload=payload,
        fuel=fuel,
        is_anomaly=is_anomaly
    )

    level = risk_level(risk)

    # Original Team 026 twins, updated via the OpenEgiz MQTT -> Ditto bridge.
    # This publishes an observed risk assessment, NEVER equipment commands.
    if publisher is not None:
        route_km = features.get("route_position", {}).get("properties", {}).get("value", 0)
        live_name = "live-" + truck_name
        live_values = live_monitor_values(payload, fuel, speed, route_km,
                                          risk, level, is_anomaly, truck_state,
                                          ml_scored=decision.scored, ml_score=score)
        packet = make_ditto_command(live_name, live_values)
        info = publisher.publish("telemetry/mg026-" + live_name, json.dumps(packet), qos=1)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            print(f"⚠️ Ditto MQTT publication failed for {live_name}: {info.rc}", flush=True)

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
            risk=risk,
            ml_scored=decision.scored,
        )
        print("📊 ML и Risk Score отправлены в InfluxDB")
    except Exception as error:
        print(f"⚠️ Ошибка отправки в InfluxDB: {error}")

    # Проверка ML-аномалии
    if not decision.scored:
        print(f"🤖 ML: не применяется ({decision.reason}); это не означает отсутствие риска")
    elif is_anomaly:
        print(f"🤖 ML: обнаружена аномалия (оценка {score:.4f})")
        save_alert(truck_name, "ML_ANOMALY", payload, fuel, speed)
    else:
        print(f"🤖 ML: обычное поведение при движении (оценка {score:.4f})")

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


print("=== MineGuard AI — непрерывный мониторинг ===", flush=True)
print("Для остановки нажми Ctrl + C", flush=True)

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("✅ MQTT подключён", flush=True)
        client.subscribe("telemetry/+")
    else:
        print(f"❌ Ошибка MQTT: {reason_code}", flush=True)

def on_message(client, userdata, msg):
    truck_name = msg.topic.split("/")[-1]
    if truck_name not in ("truck-01", "truck-02"):
        return
    try:
        check_truck(truck_name, msg.payload.decode("utf-8"), publisher=client)
    except (ValueError, json.JSONDecodeError, KeyError, TypeError) as error:
        print(f"Ошибка обработки сообщения: {error}", flush=True)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\\nМониторинг остановлен пользователем.")
except OSError as error:
    print(f"Ошибка подключения MQTT: {error}")
finally:
    client.disconnect()
