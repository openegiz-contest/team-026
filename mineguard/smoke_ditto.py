"""Real, optional OpenEgiz end-to-end smoke test (requires running Docker stack).

Publishes into Team 026 sandbox twins via MQTT, reads them back from Ditto,
and restores the baseline. Does not touch Example Mine or operational equipment.
"""
from __future__ import annotations
import sys
import time

from ditto_bridge import (build_scenario_updates, publish_messages,
                          read_twin_values)
from operations_sim import Scenario, run_haul_shift
from what_if import simulate


def expected_value(entry):
    return entry[0] if isinstance(entry, tuple) else entry


def wait_ditto(updates, timeout=25):
    deadline = time.monotonic() + timeout
    missing = []
    while time.monotonic() < deadline:
        missing = []
        for name, fields in updates.items():
            try:
                observed = read_twin_values(name)
            except Exception as error:
                missing.append(f"{name}: {error}")
                continue
            for key, entry in fields.items():
                expected = expected_value(entry)
                if observed.get(key) != expected:
                    missing.append(f"{name}.{key}: expected={expected!r}, actual={observed.get(key)!r}")
        if not missing:
            return
        time.sleep(1)
    raise RuntimeError("Ditto propagation timeout: " + "; ".join(missing[:8]))


def main():
    baseline = simulate(70, 60, 25)
    baseline_cfg = Scenario(name="BASELINE / RESET")
    baseline_ops = run_haul_shift(baseline_cfg)
    restore = build_scenario_updates(baseline, baseline, baseline_ops, baseline_ops, baseline_cfg)

    altered_cfg = Scenario(name="SMOKE / WET ROAD", road_slowdown_pct=45)
    altered_ops = run_haul_shift(altered_cfg)
    modified = build_scenario_updates(baseline, baseline, baseline_ops, altered_ops, altered_cfg)

    try:
        print("SMOKE: publish 7 scenario twins through MQTT → Ditto", flush=True)
        publish_messages(modified)
        wait_ditto(modified)
        print("SMOKE: PASS — all 7 linked twin states read back from Ditto", flush=True)
    finally:
        print("SMOKE: restore baseline sandbox scenario", flush=True)
        publish_messages(restore)
        wait_ditto(restore)
        print("SMOKE: baseline restored", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SMOKE: FAIL — {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
