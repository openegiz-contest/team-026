import csv
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "telemetry.csv"

def save_data(truck, payload, fuel, speed):
    new_file = not DATA_FILE.exists() or DATA_FILE.stat().st_size == 0

    with open(DATA_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if new_file:
            writer.writerow(["timestamp", "truck", "payload", "fuel", "speed"])

        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            truck,
            payload,
            fuel,
            speed
        ])

print("=== MineGuard AI — сбор данных для ML ===", flush=True)
print("Для остановки нажми Ctrl + C", flush=True)

process = None

try:
    process = subprocess.Popen(
        [
            "docker", "exec", "-i", "openegiz-mosquitto-1",
            "mosquitto_sub",
            "-h", "localhost",
            "-t", "telemetry/truck-01",
            "-t", "telemetry/truck-02",
            "-v"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    collected = 0
    for line in process.stdout:
        try:
            topic, message = line.strip().split(" ", 1)
            data = json.loads(message)["value"]

            truck = topic.split("/")[-1]
            payload = float(data["payload"]["properties"]["value"])
            fuel = float(data["fuel"]["properties"]["value"])
            speed = float(data["speed"]["properties"]["value"])

            save_data(truck, payload, fuel, speed)
            collected += 1

            # Optional bounded training export; default 0 means continuous.
            limit = int(os.getenv("MINEGUARD_COLLECT_LIMIT", "0"))
            if limit > 0 and collected >= limit:
                print(f"Собрано {limit} записей. Сбор завершён.", flush=True)
                break

            print(
                f"Сохранено: {truck} | "
                f"груз={payload} т | "
                f"топливо={fuel}% | "
                f"скорость={speed} км/ч",
                flush=True
            )

        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            print(f"Ошибка данных: {error}", flush=True)

except KeyboardInterrupt:
    print("\nСбор данных остановлен.")

except OSError as error:
    print(f"Ошибка подключения: {error}")

finally:
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
