"""Deterministic, simplified 2-truck haul-cycle model for contest what-if studies.

It is an *illustrative* operations model, not a calibrated mine digital twin.
The queueing resources (one loader, one crusher) and material flow are explicit;
all assumptions are disclosed in the README and the application.
No MQTT commands are issued, and changing scenarios cannot control equipment.
"""
from dataclasses import asdict, dataclass
import math

TRUCK_CAPACITY_T = 90.0
ROUTE_KM = 3.2
LOADER_BUCKET_T = 22.0
LOADER_PASS_SECONDS = 35.0
DUMP_SECONDS = 60.0
EMPTY_SPEED_KMH = 35.0
FUEL_LOADED_PCT_PER_KM = 0.9
FUEL_EMPTY_PCT_PER_KM = 0.5
REFUEL_THRESHOLD_PCT = 15.0
REFUEL_SECONDS = 600.0


@dataclass(frozen=True)
class Scenario:
    name: str = "Base operations"
    payload_t: float = 70.0
    fuel_pct: float = 60.0
    loaded_speed_kmh: float = 25.0
    road_slowdown_pct: int = 0
    crusher_delay_seconds: int = 0
    maintenance_minutes: int = 0
    shift_hours: int = 8


@dataclass
class _Truck:
    state: str = "waiting_loader"
    timer: float = 0.0
    fuel_pct: float = 60.0
    trips: int = 0
    carrying_t: float = 0.0
    breakdown_done: bool = False
    cycle_start: float = 0.0


def _validate(s: Scenario) -> None:
    fields = (s.payload_t, s.fuel_pct, s.loaded_speed_kmh)
    if any(not math.isfinite(float(x)) for x in fields):
        raise ValueError("All scenario inputs must be finite numbers")
    if not 0 <= s.payload_t <= 120:
        raise ValueError("Payload must be 0–120 tonnes")
    if not 0 <= s.fuel_pct <= 100:
        raise ValueError("Fuel must be 0–100%")
    if not 1 <= s.loaded_speed_kmh <= 80:
        raise ValueError("Loaded speed must be 1–80 km/h")
    if not 0 <= s.road_slowdown_pct <= 80:
        raise ValueError("Road slowdown must be 0–80%")
    if not 0 <= s.crusher_delay_seconds <= 900:
        raise ValueError("Crusher delay must be 0–900 seconds")
    if not 0 <= s.maintenance_minutes <= 240:
        raise ValueError("Maintenance must be 0–240 minutes")
    if not 1 <= s.shift_hours <= 24:
        raise ValueError("Shift must be 1–24 hours")


def run_haul_shift(scenario: Scenario) -> dict:
    """Run two trucks against one loader and one crusher, at 10 s resolution.

    The requested payload is capped at the modelled 90 t truck capacity. A
    maintenance delay is applied once to truck 01 when it next reaches the
    loader after the first quarter of the simulated shift. Throughput counts
    only material completely dumped before the end of the shift.
    """
    s = scenario
    _validate(s)
    dt = 10
    horizon = s.shift_hours * 3600
    delivered = 0.0
    delivered_by_half_hour = []
    capacity = min(s.payload_t, TRUCK_CAPACITY_T)
    actual_speed = max(1.0, s.loaded_speed_kmh * (1 - s.road_slowdown_pct / 100))
    return_speed = max(1.0, EMPTY_SPEED_KMH * (1 - s.road_slowdown_pct / 100))
    loading_seconds = (math.ceil(capacity / LOADER_BUCKET_T) * LOADER_PASS_SECONDS) if capacity else 0
    haul_seconds = ROUTE_KM / actual_speed * 3600
    return_seconds = ROUTE_KM / return_speed * 3600
    trucks = [_Truck(fuel_pct=s.fuel_pct) for _ in range(2)]
    loader_owner = None
    crusher_owner = None
    waiting_loader_s = 0.0
    waiting_crusher_s = 0.0
    refuel_s = 0.0
    repair_s = 0.0
    cycle_lengths = []
    fuel_used_pct_points = 0.0
    maintenance_at = horizon / 4

    for t in range(0, horizon, dt):
        # Complete active stages before allocating shared resources.
        for i, truck in enumerate(trucks):
            if truck.state in ("loading", "hauling", "dumping", "returning", "refueling", "repair"):
                truck.timer -= dt
                if truck.state == "refueling":
                    refuel_s += dt
                if truck.state == "repair":
                    repair_s += dt
                if truck.timer > 0:
                    continue
                previous = truck.state
                if previous == "loading":
                    loader_owner = None
                    truck.carrying_t = capacity
                    truck.state = "hauling"
                    truck.timer = haul_seconds
                elif previous == "hauling":
                    used = ROUTE_KM * FUEL_LOADED_PCT_PER_KM
                    truck.fuel_pct -= used
                    fuel_used_pct_points += used
                    truck.state = "waiting_crusher"
                elif previous == "dumping":
                    crusher_owner = None
                    delivered += truck.carrying_t
                    truck.carrying_t = 0.0
                    truck.trips += 1
                    cycle_lengths.append(t + dt - truck.cycle_start)
                    truck.state = "returning"
                    truck.timer = return_seconds
                elif previous == "returning":
                    used = ROUTE_KM * FUEL_EMPTY_PCT_PER_KM
                    truck.fuel_pct -= used
                    fuel_used_pct_points += used
                    truck.state = "waiting_loader"
                elif previous == "refueling":
                    truck.fuel_pct = 100.0
                    truck.state = "waiting_loader"
                elif previous == "repair":
                    truck.state = "waiting_loader"

        # Service & maintenance take priority over dispatching new loads.
        for i, truck in enumerate(trucks):
            if truck.state != "waiting_loader":
                continue
            if i == 0 and s.maintenance_minutes and t >= maintenance_at and not truck.breakdown_done:
                truck.breakdown_done = True
                truck.state = "repair"
                truck.timer = 60 * s.maintenance_minutes
            elif truck.fuel_pct < REFUEL_THRESHOLD_PCT:
                truck.state = "refueling"
                truck.timer = REFUEL_SECONDS

        for truck in trucks:
            if truck.state == "waiting_loader":
                waiting_loader_s += dt
            if truck.state == "waiting_crusher":
                waiting_crusher_s += dt

        if loader_owner is None and capacity > 0:
            for i, truck in enumerate(trucks):
                if truck.state == "waiting_loader":
                    loader_owner = i
                    truck.cycle_start = t
                    truck.state = "loading"
                    truck.timer = loading_seconds
                    break
        if crusher_owner is None:
            for i, truck in enumerate(trucks):
                if truck.state == "waiting_crusher":
                    crusher_owner = i
                    truck.state = "dumping"
                    truck.timer = DUMP_SECONDS + s.crusher_delay_seconds
                    break
        if (t + dt) % 1800 == 0:
            delivered_by_half_hour.append({
                "hour": round((t + dt) / 3600, 2),
                "tonnes": round(delivered, 1),
            })

    trips = sum(truck.trips for truck in trucks)
    return {
        "scenario": s.name,
        "tonnes": round(delivered, 1),
        "tonnes_per_hour": round(delivered / s.shift_hours, 1),
        "trips": trips,
        "average_cycle_minutes": round(sum(cycle_lengths) / len(cycle_lengths) / 60, 1) if cycle_lengths else 0.0,
        "loader_queue_minutes": round(waiting_loader_s / 60, 1),
        "crusher_queue_minutes": round(waiting_crusher_s / 60, 1),
        "refuel_minutes": round(refuel_s / 60, 1),
        "maintenance_minutes": round(repair_s / 60, 1),
        "fuel_consumed_pct_points": round(fuel_used_pct_points, 1),
        "effective_payload_t": capacity,
        "requested_payload_t": s.payload_t,
        "effective_loaded_speed_kmh": round(actual_speed, 1),
        "timeline": delivered_by_half_hour,
        "assumptions": {
            "fleet_size": 2,
            "truck_capacity_t": TRUCK_CAPACITY_T,
            "route_one_way_km": ROUTE_KM,
            "loader_bucket_t": LOADER_BUCKET_T,
            "seconds_per_bucket": LOADER_PASS_SECONDS,
            "base_dump_seconds": DUMP_SECONDS,
            "empty_speed_kmh": EMPTY_SPEED_KMH,
            "timestep_seconds": dt,
            "description": "Simplified deterministic queue-and-haul process; not a calibrated prediction",
        },
    }


if __name__ == "__main__":
    import json
    reference = run_haul_shift(Scenario())
    wet = run_haul_shift(Scenario(name="Wet road", road_slowdown_pct=40))
    print(json.dumps({"baseline": reference, "wet_road": wet}, indent=2, ensure_ascii=False))
