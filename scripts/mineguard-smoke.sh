#!/usr/bin/env bash
# End-to-end check after `make mineguard`; never removes containers or volumes.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
COMPOSE=(docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml -f examples/mine/compose.yml -f mineguard/compose.yml)

check_running() {
  local service="$1" id
  id=$("${COMPOSE[@]}" ps -q "$service")
  [[ -n "$id" && "$(docker inspect -f '{{.State.Running}}' "$id")" == true ]]
}
logs_have_mqtt() {
  local out
  out=$("${COMPOSE[@]}" logs --no-color mineguard-ai 2>/dev/null) || return 1
  grep -qF "MQTT подключён" <<<"$out"
}
pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

[[ -f deploy/compose/.env ]] || fail 'Missing .env — run make mineguard first'
for service in mineguard-ai mineguard-web mosquitto influxdb grafana; do
  check_running "$service" || fail "$service is not running"
done
pass 'Docker services running'

"${COMPOSE[@]}" exec -T mineguard-web python -c \
 'import urllib.request; assert urllib.request.urlopen("http://127.0.0.1:8501/_stcore/health",timeout=5).status==200' \
 || fail 'Streamlit health'
pass 'Streamlit healthy'

logs_have_mqtt || fail 'MQTT connection marker absent from monitor logs'
pass 'Monitor connected to MQTT'

"${COMPOSE[@]}" exec -T mineguard-ai python - <<'PY' || fail 'No recent mineguard_ml measurement in InfluxDB'
import os
from influxdb_client import InfluxDBClient
query = '''from(bucket:"default") |> range(start:-30m) |> filter(fn:(r)=>r._measurement=="mineguard_ml") |> limit(n:1)'''
with InfluxDBClient(url=os.environ['INFLUXDB_URL'],token=os.environ['INFLUXDB_TOKEN'],org='opentwins') as client:
    tables=client.query_api().query(query)
    assert any(t.records for t in tables), 'No measurements in the last 30 minutes'
PY
pass 'InfluxDB has recent ML/risk measurements'

"${COMPOSE[@]}" exec -T mineguard-web python -c \
 'import urllib.request; assert urllib.request.urlopen("http://grafana:3000/api/health",timeout=5).status==200' \
 || fail 'Grafana health'
pass 'Grafana API responding (dashboard content not verified here)'

"${COMPOSE[@]}" exec -T mineguard-web python -u /app/smoke_ditto.py || fail 'Ditto scenario round trip'
pass 'Ditto round-trip and baseline reset'

if [[ "${RUN_TESTS:-0}" == 1 ]]; then
  "${COMPOSE[@]}" exec -T mineguard-web python -m unittest discover -s /app/tests -v || fail 'Container regression tests'
  pass 'Container regression tests'
fi
printf 'MineGuard smoke: PASS\n'
