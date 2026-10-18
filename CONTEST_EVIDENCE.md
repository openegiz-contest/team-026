# MineGuard AI 2.1 · Evidence and validation

## Scope

The original contest additions are in `mineguard/`: deterministic haulage model, ML risk monitor, native MQTT → Ditto scenario publishing, nine connected Ditto twins, a **spatial 2D SVG mine view read from Ditto**, safety and production comparisons, automatic Docker Compose setup and persistent CSV storage. The Example Mine is a data source only.

## Reproducible local validation

From repository root in a Python environment with the pinned dependencies:

```bash
python -m unittest discover -s mineguard/tests -v
```

The tests verify known risk thresholds and anomaly classifications, deterministic haul-cycle outputs, queues, fuel, repairs, payload capacity clipping, connected twin topology, MQTT Ditto-protocol JSON structure, and complete 7-object scenario payload propagation. They **do not assert successful MQTT-to-Ditto network transmission** without a running OpenEgiz stack.

To test directly in the container:

```bash
docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml -f examples/mine/compose.yml -f mineguard/compose.yml run --rm --no-deps --entrypoint python mineguard-ai -m unittest discover -s /app/tests -v
```

## Demonstration contracts

- Reference live `org.openegiz.mine:*` telemetry flows through Mosquitto into Ditto.
- Team 026's **`org.mineguard.team026:live-truck-*`** twins are updated by the monitor after ML assessment via MQTT → Ditto.
- Nine original twin schemas, seven scenario writes and two live mirror twins are defined in `ditto_bridge.py`. Each scenario update carries related values for equipment, logistics and mine production.
- The Streamlit map obtains features from Ditto **server-side using credentials from `.env`**, not the local web session. The HTML contains only rendered equipment values and no credentials.
- Explicit Apply/Reset changes only the separate scenario twin namespace; the underlying Example Mine is not modified.

## Results and caveats

**Prior local environment (team terminal/screenshots):** 16 test cases passed; Docker images built; the Decision Lab container reported Healthy; `mineguard-ai` ran with MQTT / InfluxDB success; persistent Docker volume mounted and retained CSV history. These observations are from the version before the new Ditto bridge and spatial view.

**Current package:** local unit-test results and static YAML/Python validation can be repeated. **Full clean-room startup, live MQTT propagation, and exact runtime map behaviour require confirmation in an environment with a Docker Engine and running Ditto.** Do not infer this from passing unit tests.

**Sample counterfactual:** baseline 70 t / 60% fuel / 25 km/h scores 0/100; requested 95 t / 12% fuel / 35 km/h scores 80/100 under shipped rules (both can be non-anomalous). Maximum **actual** payload in simulated haulage is 90 t. 8 h model baseline is 3,920 t; user-altered scenarios may differ. All amounts are modelled, not real tonnage or certified forecasts.

**Safe usage:** `.env`, personal CSV and runtime caches are excluded from the Git deliverable. `make clean` and `docker compose down -v` are destructive for persistent data and should not be used during normal operation.

## Network round-trip smoke test (optional; after boot)

```bash
make mineguard-check
```

The command sends a wet-road scenario into **seven Team 026 sandbox twins** via Mosquitto, polls Ditto's HTTP API until all seven changed values are present, then restores the baseline and confirms the restored states. It fails with a non-zero exit code if end-to-end propagation is not observed. **Not executed in this artifact-building environment because Docker Engine is unavailable.**
