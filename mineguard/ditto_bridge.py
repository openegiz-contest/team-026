"""OpenEgiz Eclipse Ditto integration for MineGuard's *own* connected twins.

All scenario writes use the existing OpenEgiz Mosquitto -> Ditto connection.
HTTP Basic is used only on the trusted server to seed/read the twins; credentials
are never serialized into HTML, JSON reports, or browser-side code.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


NAMESPACE = "org.mineguard.team026"
EXAMPLE_NAMESPACE = "org.openegiz.mine"
ROUTE_KM = 3.2

# Diagram positions are symbolic process-layout coordinates, not GPS positions.
ASSETS = {
    "pit-01": ("mine", "MineGuard haulage cell", 70, 145, ["loader-01", "haul-road-01", "crusher-01"]),
    "loader-01": ("loader", "Loader / EX-01", 175, 215, ["truck-01", "truck-02", "haul-road-01"]),
    "truck-01": ("haul-truck", "Haul truck / HT-01", 370, 170, ["loader-01", "haul-road-01", "crusher-01"]),
    "truck-02": ("haul-truck", "Haul truck / HT-02", 370, 255, ["loader-01", "haul-road-01", "crusher-01"]),
    "haul-road-01": ("road", "3.2 km haul road", 495, 320, ["loader-01", "crusher-01"]),
    "crusher-01": ("crusher", "Primary crusher / CR-01", 810, 215, ["truck-01", "truck-02", "haul-road-01"]),
    "fuel-bay-01": ("fuel-station", "Fuel bay / FS-01", 165, 350, ["truck-01", "truck-02"]),
    "live-truck-01": ("monitor", "HT-01 live AI monitor", 355, 115, ["truck-01"]),
    "live-truck-02": ("monitor", "HT-02 live AI monitor", 355, 290, ["truck-02"]),
}


def prop(value, unit=None):
    properties = {"value": value}
    if unit is not None:
        properties["unit"] = unit
    return {"properties": properties}


def _features(values):
    return {name: prop(*value) if isinstance(value, tuple) else prop(value)
            for name, value in values.items()}


def _default_features(name):
    if name.startswith("truck-") or name.startswith("live-truck-"):
        return _features({"payload_t": (0, "t"), "fuel_pct": (80, "%"),
                          "speed_kmh": (0, "km/h"), "route_km": (0, "km"),
                          "risk_score": 0, "risk_level": "LOW", "state": "idle", "anomaly": False,
                          "ml_scored": False})
    if name == "pit-01":
        return _features({"shift_tonnes": (0, "t"), "shift_hours": (8, "h"),
                          "risk_level": "LOW", "mode": "baseline"})
    if name == "loader-01":
        return _features({"state": "loading", "queue_minutes": (0, "min")})
    if name == "crusher-01":
        return _features({"state": "crushing", "throughput_tph": (0, "t/h"),
                          "queue_minutes": (0, "min")})
    if name == "haul-road-01":
        return _features({"state": "open", "slowdown_pct": (0, "%"), "effective_speed_kmh": (25, "km/h")})
    return _features({"state": "available", "refuel_minutes": (0, "min")})


def twin_document(name):
    kind, label, x, y, connections = ASSETS[name]
    return {
        "policyId": "default:basic_policy",
        "attributes": {"name": label, "kind": kind, "team": "026", "x": x, "y": y,
                       "connected_to": [f"{NAMESPACE}:{other}" for other in connections],
                       "diagram_only": True},
        "features": _default_features(name),
    }


def _auth_header():
    password = os.environ.get("DITTO_PASSWORD", "")
    if not password:
        raise RuntimeError("DITTO_PASSWORD is required for Ditto API operations")
    user = os.environ.get("DITTO_USER", "ditto")
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def _request(method, namespace, name, body=None, timeout=6):
    url = os.environ.get("DITTO_URL", "http://ditto-nginx:80").rstrip("/")
    thing_id = urllib.parse.quote(f"{namespace}:{name}", safe=":")
    headers = {"Authorization": _auth_header(), "Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(f"{url}/api/2/things/{thing_id}",
                                     method=method, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
        return json.loads(content) if content else None


def fetch_twin(name, namespace=NAMESPACE):
    return _request("GET", namespace, name)


def read_twin_values(name, namespace=NAMESPACE):
    twin = fetch_twin(name, namespace)
    return {key: item.get("properties", {}).get("value")
            for key, item in twin.get("features", {}).items()}


def seed_twins(retries=20, delay_seconds=3):
    """Create only *missing* twins; never wipe persisted scenarios on restart."""
    for name in ASSETS:
        for attempt in range(retries):
            try:
                try:
                    fetch_twin(name)
                    status = "kept"
                except urllib.error.HTTPError as error:
                    if error.code != 404:
                        raise
                    _request("PUT", NAMESPACE, name, twin_document(name))
                    status = "created"
                print(f"{status}: {NAMESPACE}:{name}", flush=True)
                break
            except (urllib.error.URLError, TimeoutError, RuntimeError) as error:
                if attempt + 1 == retries:
                    raise RuntimeError(f"Ditto initialization failed for {name}: {error}") from error
                time.sleep(delay_seconds)
    print(f"MineGuard: {len(ASSETS)} Ditto twins ready", flush=True)


def build_scenario_updates(before, after, before_ops, after_ops, scenario):
    """Publish a consistent set of related mine states for ONE hypothetical scenario.

    This is not a command to industrial equipment. Simulated metrics are
    written only to the org.mineguard.team026 namespace.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    mode = scenario.name
    risk_level = after["level"]
    slowdown = scenario.road_slowdown_pct
    return {
        "pit-01": {"shift_tonnes": (after_ops["tonnes"], "t"),
                   "shift_hours": (scenario.shift_hours, "h"),
                   "base_tonnes": (before_ops["tonnes"], "t"),
                   "delta_tonnes": (round(after_ops["tonnes"] - before_ops["tonnes"], 1), "t"),
                   "risk_level": risk_level, "mode": mode, "updated_utc": timestamp},
        "truck-01": {"payload_t": (min(after["payload"], 90), "t"),
                     "requested_payload_t": (after["payload"], "t"), "fuel_pct": (after["fuel"], "%"),
                     "speed_kmh": (after["speed"], "km/h"), "route_km": (1.25, "km"),
                     "risk_score": after["risk"], "risk_level": risk_level,
                     "anomaly": after["anomaly"],
                     "state": "maintenance" if scenario.maintenance_minutes else "hauling"},
        "truck-02": {"payload_t": (min(after["payload"], 90), "t"),
                     "requested_payload_t": (after["payload"], "t"), "fuel_pct": (after["fuel"], "%"),
                     "speed_kmh": (after["speed"], "km/h"), "route_km": (2.5, "km"),
                     "risk_score": after["risk"], "risk_level": risk_level,
                     "anomaly": after["anomaly"], "state": "hauling"},
        "loader-01": {"state": "loading", "queue_minutes": (after_ops["loader_queue_minutes"], "min"),
                       "shift_trips": after_ops["trips"]},
        "crusher-01": {"state": "congested" if scenario.crusher_delay_seconds else "crushing",
                        "throughput_tph": (after_ops["tonnes_per_hour"], "t/h"),
                        "queue_minutes": (after_ops["crusher_queue_minutes"], "min"),
                        "dump_delay_seconds": (scenario.crusher_delay_seconds, "s")},
        "haul-road-01": {"state": "slippery" if slowdown else "open",
                         "slowdown_pct": (slowdown, "%"),
                         "effective_speed_kmh": (after_ops["effective_loaded_speed_kmh"], "km/h")},
        "fuel-bay-01": {"state": "active" if after_ops["refuel_minutes"] else "available",
                        "refuel_minutes": (after_ops["refuel_minutes"], "min")},
    }


def make_ditto_command(name, values):
    return {"topic": f"{NAMESPACE}/{name}/things/twin/commands/modify",
            "path": "/features", "value": _features(values)}


def publish_messages(messages, mqtt_host=None, mqtt_port=None):
    host = mqtt_host or os.getenv("MQTT_HOST", "mosquitto")
    port = int(mqtt_port or os.getenv("MQTT_PORT", "1883"))
    import paho.mqtt.client as mqtt
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(host, port, keepalive=30)
        client.loop_start()
        for name, values in messages.items():
            # The connection in deploy/compose/init/mosquitto-source-connection.json
            # subscribes to telemetry/#; the payload is native Ditto protocol.
            message = make_ditto_command(name, values)
            info = client.publish(f"telemetry/mg026-{name}", json.dumps(message), qos=1)
            info.wait_for_publish(timeout=8)
            if not info.is_published():
                raise RuntimeError(f"MQTT did not confirm publish for {name}")
    finally:
        try:
            client.disconnect()
        finally:
            client.loop_stop()


def live_monitor_values(payload, fuel, speed, route_km, risk, level, anomaly, state, *, ml_scored=False, ml_score=None):
    return {"payload_t": (payload, "t"), "fuel_pct": (fuel, "%"),
            "speed_kmh": (speed, "km/h"), "route_km": (route_km, "km"),
            "risk_score": risk, "risk_level": level, "anomaly": bool(anomaly),
            "ml_scored": bool(ml_scored), "ml_score": ml_score,
            "state": state, "updated_utc": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    seed_twins()
