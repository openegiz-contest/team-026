# MineGuard AI 2.1 · Team 026

**Digital Mine on OpenEgiz — Haulage safety, connected digital twins and an interactive dispatch decision lab**

MineGuard creates an **original linked haulage cell in Eclipse Ditto**: mine, loader, two trucks, road, crusher and fuel station, plus two live AI-monitor twins. It receives live truck data from the OpenEgiz Example Mine pipeline; the Python AI publishes its risk assessments **back into MineGuard's own Ditto twins via MQTT**. The Streamlit interface **reads the twins through Ditto HTTP API** and renders a 2D schematic of the mine. Interactive What-if scenarios update **seven related scenario twins** in Ditto when the operator explicitly clicks Apply. No commands are sent to real machinery.

> The reference Example Mine supplies synthetic real-time events; the added Team 026 twins, spatial view, ML integration and scenario propagation are original work. These are distinct from the unchanged upstream example dashboard.

## Start — clean Ubuntu 24.04 / Judge Environment

**Run the following commands from the repository root.** Docker Engine with the Compose v2 plugin must be running and your user must have Docker access. The judge image has these installed but **does not have GNU Make**.

```bash
sudo apt-get update
sudo apt-get install -y make
make mineguard
```

`make mineguard` automatically creates local secrets (once), starts OpenEgiz, seeds Example Mine twins, starts its telemetry simulator, seeds **nine MineGuard twins** in Ditto, then builds and starts the AI monitor and What-if web UI. It waits for service readiness. First launch downloads Docker images and Python wheels; no manual training, external private account, data download or human interaction is required. **Do not run `make clean`**: it removes data volumes and credentials.

To obtain your own local checkout outside the Judge Environment:

```bash
git clone https://github.com/openegiz-contest/team-026.git
cd team-026
```

### Open these URLs after startup

| App | URL | Jury-facing purpose |
|---|---|---|
| **MineGuard Decision Lab — start here** | **http://localhost:8501** | Original 2D spatial map, Ditto live twins, scenario publishing, ML and haul-cycle comparison |
| Grafana · MineGuard AI | http://localhost:3000/d/team026-mineguard | Live AI Risk Score and anomalous telemetry |
| Example Mine | Grafana → OpenEgiz Examples → Example Mine | Reference simulator telemetry (not counted as original contribution) |

Grafana credentials are generated into the **ignored** `deploy/compose/.env` by `scripts/compose-env.sh`; `make up` prints the access details. Do not commit that file.

## Demonstration — 4 minutes

1. Open **http://localhost:8501** → **🗺️ Карта цифрового рудника**. Show both the **LIVE** map (observed data from Eclipse Ditto) and the separate **WHAT-IF** map. The labels and values on these maps are fetched server-side from Ditto (they are not hardcoded into the browser).
2. Choose **«Перегрузка + мало топлива»**; the safety comparison shows **0 → 80/100** for default inputs. Switch to the map tab and click **«Применить AFTER в Ditto»**. The simulator publishes seven linked twin updates through `telemetry/#` MQTT → Eclipse Ditto. Click **«Считать текущие двойники»** to re-read the resulting states. Observe payload, risk, road, crusher, loader and mine tonnes on the map/table.
3. Choose **«Скользкая дорога»** and click **Apply** again. The road twin's slowdown, crusher throughput and mine's modelled tonnage change together. Compare **🏭 Работа шахты** throughput and the line chart. Try **«Очередь на дробилке»** or **«Ремонт одного самосвала»** for additional operational constraints.
4. Click **«Вернуть базовый режим»** to restore the scenario twins to the BEFORE settings. The *live* Example Mine twins are never altered by What-if experiments. Use **📋 Доказательства и допущения** → JSON export for reproducible model inputs and outputs.
5. Open Grafana to inspect running telemetry and risk trends. **A counterfactual model is not a live prediction.**

**When to refresh:** MQTT → Ditto is asynchronous. The Apply action waits briefly; click the Refresh button if a newly published state has not yet appeared. This is a separate *simulation namespace*, not a command to actual trucks.

## OpenEgiz connection and model architecture

```text
OpenEgiz Example Mine simulator (synthetic)
         │ MQTT telemetry/truck-01, telemetry/truck-02
         ▼
  Mosquitto ──▶ Eclipse Ditto (original Example Mine reference twins)
         │
         ▼
MineGuard AI monitor.py ─▶ IsolationForest + transparent Risk Score
         │                             │
         │                             └──▶ InfluxDB → Grafana
         └─ MQTT Ditto protocol ──▶ org.mineguard.team026:live-truck-01/02
                                                      │
                                                      ▼
                                        Streamlit server reads Ditto HTTP API
                                                      │
                                                      ▼
                                        LIVE 2D mine spatial schematic

Streamlit sliders → what_if.py + operations_sim.py (counterfactual calculation)
         │ Operator clicks Apply / Reset (no industrial control)
         ▼
  MQTT telemetry/mg026-* → Ditto bridge → 7 scenario twins
         │ mine, loader, 2 trucks, haul-road, crusher, fuel station
         ▼
  Ditto GET → WHAT-IF map and linked twin state table
```

Twin namespace: `org.mineguard.team026`. **Nine linked twins** are created automatically by `mineguard-setup`; the seeding operation is idempotent and does not wipe earlier scenarios. Seven are modified by each What-if transaction, two are independently updated by observed AI telemetry. Their `attributes.connected_to` expose physical/process relationships. REST is used for seeding and trusted server-side reading; actual scenario/live updates are delivered **through OpenEgiz MQTT → Ditto**.

### Process layout (schematic, not GPS)

```text
      [LOADER] ───── truck-01 / truck-02 ── 3.2 km haul ─── [CRUSHER]
         │                      │                             │
         └──── [FUEL BAY] ──────┴───── [ROAD] ───────────────┘
                           │
                       [MINE CELL]
```

The browser visualization is **self-contained inline SVG**, with no external tile server, API key or CDN. Truck positions in the LIVE view are sourced from Ditto `route_km`; the What-if view shows representative positions for a selected hypothetical state rather than a realtime route animation.

## What-if assumptions and safety limitations

- **Haulage:** two 90 t trucks, one 22 t-bucket excavator, one crusher, 3.2 km one-way route; 35 s per bucket and 60 s nominal dump. At most one truck loads/dumps at a time. 10 s simulated time steps, 8-hour default shift. Delay, repair and refuelling parameters are adjustable. The model counts **completed dumps only**.
- **Manufacturer plausibility:** the 90 t classroom payload is in the class of **Komatsu HD785-7 (rated 91 t)** and **Caterpillar 777 (target payload 91.7 t)**. This does **not** assert our virtual site uses either exact machine. The remaining times/distances/fuel-rate assumptions are adapted from `examples/mine/simulator.py` and are **not manufacturer specifications**. Sources: [Komatsu HD785-7](https://www.komatsu.eu/en/Product-Archive/Rigid-Dump-Trucks/HD785-7), [CAT 777](https://www.cat.com/en_US/products/new/equipment/off-highway-trucks/off-highway-trucks/115560.html).
- **Risk Score:** payload 81–90 t +25, >90 t +50, fuel <25% +15, fuel <15% +30, ML outlier +35; capped at 100. LOW 0–34, MEDIUM 35–69, HIGH 70–100. The **requested** payload can exceed capacity to test safety warnings, while operations enforce 90 t **actual** capacity.
- **ML:** `mineguard/risk_model.joblib` (IsolationForest trained on synthetic payload/fuel/speed); sklearn pinned to 1.9.1, not trained on accident labels. Speed only influences the ML model, not a direct rule penalty.
- **Interpretation:** Risk Score is an **ordinal demo heuristic, not probability of an accident**. Production, queues and tonnage are illustrative deterministic outputs, not field-validated productivity forecasts or monetary savings.
- **Safety:** hypothetical changes modify *only MineGuard sandbox twins* in Ditto. They never instruct machines, write into Example Mine twins, or contaminate live Grafana measurements.

## Verification

```bash
python3 -m unittest discover -s mineguard/tests -v
```

On the judge image, local Python dependencies are not required. After `make mineguard` the container has the dependencies:

```bash
docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml -f examples/mine/compose.yml -f mineguard/compose.yml run --rm --no-deps --entrypoint python mineguard-ai -m unittest discover -s /app/tests -v
curl -fsS http://localhost:8501/_stcore/health
```

To verify **actual MQTT → Ditto propagation** of all seven scenario twins, and automatically restore the baseline, run this optional command **after the stack starts**:

```bash
make mineguard-check
```

To inspect live twin state use the web app's **Ditto twin state** table. The automated tests verify risk/operations and build native Ditto protocol messages; **the full clean Docker+Ditto chain must still be validated in a judge-equivalent environment**.

## Structure

| Path | Purpose |
|---|---|
| `mineguard/ditto_bridge.py` | Original twin definitions, Ditto HTTP reads, MQTT publish and linked state updates |
| `mineguard/mine_map.py` | Self-contained spatial SVG from actual Ditto JSON values |
| `mineguard/monitor.py`, `risk_score.py` | Live MQTT monitor, ML rule engine, writes monitored twin values and InfluxDB |
| `mineguard/what_if_app.py`, `what_if.py`, `operations_sim.py` | Streamlit Decision Lab + deterministic hauling and queues |
| `mineguard/tests/` | Regression, Ditto protocol and scenario propagation unit tests |
| `mineguard/compose.yml` | Three service overlay (Ditto seed job, AI, web) and persistent local data volume |
| `SUBMISSION.md` | Intent, modules, scenarios, assumptions and limits |
| `CONTEST_EVIDENCE.md` | Verification evidence and remaining risks |
| `presentation.pdf` | Contest presentation |

**Stop preserving data:**

```bash
docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml -f examples/mine/compose.yml -f mineguard/compose.yml down
```

Do **not** use `down -v` / `make clean` for ordinary stopping. `alerts.csv` and `telemetry.csv` are retained in Docker volume `openegiz_mineguard-data`.

**Team 026 · MIT licence (see LICENSE).** The evaluated submission is the last commit of the repository's `main` branch at the freeze deadline, not a ZIP uploaded to ChatGPT.
