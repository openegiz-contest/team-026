from pathlib import Path

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

ENV_FILE = Path(__file__).resolve().parent.parent / "deploy/compose/.env"


def read_token():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if line.startswith("INFLUXDB_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")

    raise RuntimeError("INFLUXDB_TOKEN не найден")


def send_ml_result(truck, is_anomaly, score):
    point = (
        Point("mineguard_ml")
        .tag("truck", truck)
        .field("anomaly", int(is_anomaly))
        .field("score", float(score))
        .time(None, WritePrecision.NS)
    )

    with InfluxDBClient(
        url="http://localhost:8086",
        token=read_token(),
        org="opentwins",
    ) as client:
        client.write_api(write_options=SYNCHRONOUS).write(
            bucket="default",
            org="opentwins",
            record=point,
        )