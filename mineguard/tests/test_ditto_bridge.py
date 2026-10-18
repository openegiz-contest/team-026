"""Test scenario twin contracts without requiring an OpenEgiz server or MQTT."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ditto_bridge import ASSETS, NAMESPACE, build_scenario_updates, make_ditto_command, twin_document
from operations_sim import Scenario, run_haul_shift
from what_if import simulate


class DittoBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = simulate(70, 60, 25)
        cls.after = simulate(95, 12, 35)
        cls.base = run_haul_shift(Scenario())
        cls.config = Scenario(name="Overload", payload_t=95, fuel_pct=12, loaded_speed_kmh=35)
        cls.result = run_haul_shift(cls.config)

    def test_all_original_twins_have_relations_and_policy(self):
        self.assertEqual(len(ASSETS), 9)
        for name in ASSETS:
            with self.subTest(name=name):
                d = twin_document(name)
                self.assertEqual(d["policyId"], "default:basic_policy")
                self.assertTrue(d["attributes"]["connected_to"])
                self.assertIn("features", d)
                self.assertTrue(all(x.startswith(NAMESPACE + ":") for x in d["attributes"]["connected_to"]))

    def test_scenario_updates_all_seven_related_twins(self):
        updates = build_scenario_updates(self.before, self.after, self.base, self.result, self.config)
        self.assertEqual(set(updates), set(ASSETS) - {"live-truck-01", "live-truck-02"})
        self.assertEqual(updates["truck-01"]["payload_t"][0], 90)
        self.assertEqual(updates["truck-01"]["requested_payload_t"][0], 95)
        self.assertEqual(updates["truck-01"]["risk_score"], 80)
        self.assertEqual(updates["pit-01"]["shift_tonnes"][0], self.result["tonnes"])

    def test_native_ditto_protocol_and_telemetry_topic(self):
        updates = build_scenario_updates(self.before, self.after, self.base, self.result, self.config)
        command = make_ditto_command("crusher-01", updates["crusher-01"])
        self.assertEqual(command["topic"], NAMESPACE + "/crusher-01/things/twin/commands/modify")
        self.assertEqual(command["path"], "/features")
        self.assertEqual(command["value"]["throughput_tph"]["properties"]["unit"], "t/h")
        self.assertEqual(json.loads(json.dumps(command)), command)

    def test_road_scenario_changes_connected_road_and_output(self):
        altered = Scenario(name="Slippery road", road_slowdown_pct=45)
        result = run_haul_shift(altered)
        updates = build_scenario_updates(self.before, self.before, self.base, result, altered)
        self.assertEqual(updates["haul-road-01"]["state"], "slippery")
        self.assertEqual(updates["haul-road-01"]["slowdown_pct"][0], 45)
        self.assertLess(updates["pit-01"]["shift_tonnes"][0], self.base["tonnes"])

    def test_recreation_does_not_replace_existing_twins(self):
        # Seed logic checks GET first; no destructive PUT to an existing twin.
        from ditto_bridge import seed_twins
        with patch('ditto_bridge.fetch_twin', return_value={"thingId": "exists"}) as get, \
             patch('ditto_bridge._request') as request:
            seed_twins(retries=1)
            self.assertEqual(get.call_count, len(ASSETS))
            request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
