
import json
import subprocess
import time

TRUCK_CAPACITY = 90
LOW_FUEL = 25


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

    if payload > TRUCK_CAPACITY:
        print("🚨 ОПАСНОСТЬ: перегрузка!")
    elif payload >= TRUCK_CAPACITY * 0.9:
        print("⚠️ ВНИМАНИЕ: почти полная загрузка!")
    else:
        print("✅ Загрузка в норме")

    if fuel < LOW_FUEL:
        print("⛽ ВНИМАНИЕ: низкий уровень топлива!")


print("=== MineGuard AI — непрерывный мониторинг ===")
print("Для остановки нажми Ctrl + C")

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

    try:
        for line in process.stdout:
            if not line.strip():
                continue

            try:
                topic, message = line.strip().split(" ", 1)
                truck_name = topic.split("/")[-1]

                check_truck(truck_name, message)

            except (ValueError, json.JSONDecodeError, KeyError, TypeError) as error:
                print(f"Ошибка обработки сообщения: {error}")

    except KeyboardInterrupt:
        print("\nМониторинг остановлен пользователем.")

    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

except OSError as error:
    print(f"Ошибка запуска MQTT: {error}")



