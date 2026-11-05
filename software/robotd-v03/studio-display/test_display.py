"""用已归档真机反馈检查显示适配；不连接设备、不发送硬件命令。"""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNTIME = ROOT / "training/logs/b-feetech-walk-20261024/controller-preparation-20261031/software-runtime/studio"
sys.path[:0] = [str(RUNTIME), str(RUNTIME / "deps")]
import studio
studio.__path__.insert(0, str(HERE / "overlay/studio"))
from studio.commissioning_display import snapshot
from studio.robotd import Robotd
from studio.servo import view_from_robotd
from studio.state import summarize

EVIDENCE = ROOT / "docs/references/飞特策略模型上机核对/studio-commissioning-final-20261031.json"
FIXTURE = json.loads(EVIDENCE.read_text(encoding="utf-8-sig"))


class DisplayTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch("time.monotonic", return_value=100.0)
        self.now = self.clock.start()
        self.addCleanup(self.clock.stop)
        self.rd = Robotd("none", "none", None)
        self.rd.present = True
        self.rd.hello.set(FIXTURE["hello"]["result"])
        self.rd.health.set(FIXTURE["health"]["result"])
        self.bus = copy.deepcopy(FIXTURE["bus"]["result"])
        self.feed(self.bus)

    def feed(self, bus):
        self.rd.bus.set(bus)
        self.rd.commissioning_clock.observe(bus, self.rd.bus.at)

    def assert_unknown(self):
        summary = summarize(self.rd, "test")
        table = view_from_robotd(self.rd, None)
        self.assertIsNone(summary["servos"]["online"])
        self.assertIsNone(table["online"])
        self.assertTrue(all(row["raw"] is None and not row["fresh"] for row in table["rows"]))
        self.assertIsNone(summary["gravity"])

    def test_captured_feedback_reaches_overview_and_table_without_mutating_rpc(self):
        original = copy.deepcopy(self.bus)
        summary = summarize(self.rd, "test")
        table = view_from_robotd(self.rd, None)
        self.assertEqual(summary["servos"]["online"], 15)
        self.assertEqual(table["online"], 15)
        self.assertEqual(summary["imu"]["status"], "unverified")
        self.assertEqual(summary["gravity"], self.bus["last_sample"]["imu"]["gravity"])
        self.assertIsNone(summary["joints"])
        expected = {row["id"]: row for row in self.bus["last_sample"]["servos"]}
        for row in table["rows"]:
            self.assertEqual(row["raw"], expected[row["id"]]["position_raw"])
            self.assertEqual(row["volt"], expected[row["id"]]["voltage_v"])
            self.assertEqual(row["temp"], expected[row["id"]]["temperature_c"])
        self.assertEqual(self.bus, original)

    def test_repeated_rpc_receipts_cannot_revive_a_frozen_sample(self):
        self.now.return_value = 104.0
        self.feed(self.bus)
        self.assert_unknown()
        self.assertGreaterEqual(snapshot(self.rd)["age_ms"], 4000)
        resumed = copy.deepcopy(self.bus)
        resumed["last_sample"]["cycle"] += 1
        resumed["last_sample"]["at_us"] += 4_000_000
        resumed["updated_at_us"] += 4_000_000
        self.feed(resumed)
        self.assertEqual(view_from_robotd(self.rd, None)["online"], 15)

    def test_native_old_sample_is_expired_even_on_first_receipt(self):
        old = copy.deepcopy(self.bus)
        old["updated_at_us"] += 4_000_000
        self.rd.commissioning_clock.reset()
        self.feed(old)
        self.assert_unknown()

    def test_read_error_and_disconnect_do_not_claim_online(self):
        failed = copy.deepcopy(self.bus)
        failed.update(phase="read_error", last_cycle_error="IMU response timeout")
        self.feed(failed)
        self.assert_unknown()
        self.assertEqual(view_from_robotd(self.rd, None)["error"], "IMU response timeout")
        self.feed(self.bus)
        self.rd.bus.fail("disconnected")
        self.assert_unknown()

    def test_new_hello_and_session_cannot_reuse_previous_context(self):
        self.now.return_value = 101.0
        self.rd.hello.set(FIXTURE["hello"]["result"])
        self.rd.commissioning_clock.reset()
        self.assert_unknown()
        new = copy.deepcopy(self.bus)
        new["device_communication"]["session"] = "new-daemon-instance"
        self.rd.bus.set(new)
        self.assert_unknown()
        self.rd.commissioning_clock.observe(new, self.rd.bus.at)
        self.assertEqual(snapshot(self.rd)["online"], 15)
        self.rd.present = False
        self.assert_unknown()

    def test_other_modes_keep_their_native_display_path(self):
        motion = {"mode": "motion", "phase": "control", "native": {"joints": [
            {"id": 20, "name": "left_hip_yaw", "position_raw": 2100,
             "volts": 7.2, "temperature_c": 33, "feedback_fresh": True}]}}
        self.feed(motion)
        self.assertIsNone(snapshot(self.rd))
        self.assertEqual(summarize(self.rd, "test")["servos"]["online"], 1)
        table = view_from_robotd(self.rd, None)
        self.assertEqual(table["online"], 1)
        self.assertEqual(table["rows"][0]["raw"], 2100)
        self.feed({"mode": "commissioning", "phase": "configuring_bus"})
        self.assertIsNone(snapshot(self.rd))


if __name__ == "__main__":
    unittest.main(verbosity=2)
