import json
from pathlib import Path

source = Path("examples/mine/dashboard.json")
output = Path("deploy/compose/grafana/dashboards/mineguard.json")

dashboard = json.loads(source.read_text(encoding="utf-8"))

dashboard["uid"] = "team026-mineguard"
dashboard["title"] = "MineGuard AI | Team 026"
dashboard["tags"] = ["mineguard", "team-026", "digital-mine"]
dashboard["description"] = "Мониторинг загрузки и топлива самосвалов цифровой шахты."
dashboard["version"] = 1
dashboard["panels"] = []

fields = [
    ("truck-01", "payload", "Truck-01 | Груз", "t"),
    ("truck-02", "payload", "Truck-02 | Груз", "t"),
    ("truck-01", "fuel", "Truck-01 | Топливо", "percent"),
    ("truck-02", "fuel", "Truck-02 | Топливо", "percent"),
]

for index, (truck, field, title, unit) in enumerate(fields):
    query = (
        'from(bucket: "default")\n'
        '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
        f'  |> filter(fn: (r) => r.thingId == "org.openegiz.mine:{truck}" '
        f'and r._field == "value_{field}_properties_value")\n'
        '  |> last()\n'
        '  |> keep(columns: ["_time", "_value"])'
    )

    thresholds = (
        [
            {"color": "green", "value": None},
            {"color": "yellow", "value": 81},
            {"color": "red", "value": 90.01},
        ]
        if field == "payload"
        else [
            {"color": "red", "value": None},
            {"color": "yellow", "value": 15},
            {"color": "green", "value": 25},
        ]
    )

    dashboard["panels"].append({
        "id": index + 1,
        "type": "stat",
        "title": title,
        "datasource": {"type": "influxdb", "uid": "opentwins-influxdb"},
        "gridPos": {
            "x": (index % 2) * 12,
            "y": (index // 2) * 7,
            "w": 12,
            "h": 7,
        },
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "decimals": 1,
                "min": 0,
                "max": 90 if field == "payload" else 100,
                "thresholds": {"mode": "absolute", "steps": thresholds},
                "color": {"mode": "thresholds"},
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {
                "calcs": ["lastNotNull"],
                "fields": "",
                "values": False,
            },
            "colorMode": "value",
            "graphMode": "area",
            "textMode": "value",
        },
        "targets": [{
            "refId": "A",
            "datasource": {"type": "influxdb", "uid": "opentwins-influxdb"},
            "query": query,
        }],
    })

output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(
    json.dumps(dashboard, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"Панель создана: {output}")
print(f"Количество показателей: {len(dashboard['panels'])}")
