"""无网络、无舵机：检验真实恢复后端的所有权与取消边界。"""
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".work/studio"))
from studio.pad_recovery import RecoveryMixin, Refused
from studio.updates import safe_during_update, neutral_robot_command


class Pad(RecoveryMixin):
    def __init__(self):
        self._send_lk = threading.Lock()
        self._lk = threading.RLock()
        self._recovery_owner = None
        self._robot = {"bus": {"walk_recovery": {"phase": "idle"}, "policy_enabled": False}}
        self._robot["bus"]["loaded_models"] = {"walk": {"sha256": "1cbf8730eadd75a5704332c9f3c10f60bfa9412135b907831c9dbd731ce1795f"}}
        self._gone, self._closed = {}, {}
        self._relax_at = 0
        self._driver = None
        self._cmd_busy, self._action = False, None
        self.motion_studio = SimpleNamespace(session=None, request_current=lambda: True)
        self.calls = []
        self.before_reply = None
    def clock(self): return 100
    def _base_block(self, _): return None
    def _relax_block(self, _): return None
    def _pad_attached(self, _): return False, None
    def _job_alive(self): return False
    def _take_lease(self, conn, by, now):
        if self._driver and self._driver["conn"] != conn: raise Refused("owned")
        self._driver = {"conn": conn}
    def _touch_lease(self, conn, now): pass
    def _call_rpc(self, what, method, params, by):
        self.calls.append((method, dict(params)))
        if self.before_reply:
            f, self.before_reply = self.before_reply, None
            f()
        return {"accepted": True, "request_id": 71}


class RecoveryTests(unittest.TestCase):
    def start(self, p):
        return p._recovery_op("recover", {}, "page-a", "test")

    def test_owner_and_sequence_are_checked_before_forwarding(self):
        p = Pad(); self.start(p)
        hb = {"request_id": 71, "sequence": 1}
        with self.assertRaises(Refused): p._recovery_op("recover_keepalive", hb, "page-b", "test")
        self.assertEqual(len(p.calls), 1)
        p._recovery_op("recover_keepalive", hb, "page-a", "test")
        with self.assertRaises(Refused): p._recovery_op("recover_keepalive", hb, "page-a", "test")
        self.assertEqual(len(p.calls), 2)

    def test_closed_page_and_relax_cannot_renew(self):
        for closed in (True, False):
            p = Pad(); self.start(p)
            if closed: p._closed["page-a"] = True
            else: p._relax_at = 101
            with self.assertRaises(Refused):
                p._recovery_op("recover_keepalive", {"request_id": 71, "sequence": 1}, "page-a", "test")
            self.assertEqual(len(p.calls), 1)

    def test_page_leaving_during_start_reply_cancels_the_same_request(self):
        p = Pad(); p.before_reply = lambda: p._closed.update({"page-a": True})
        with self.assertRaises(Refused): self.start(p)
        self.assertEqual(p.calls[-1], ("robot.recover", {"action": "cancel", "request_id": 71}))
        self.assertIsNone(p._recovery_owner)
        self.assertFalse(p._cmd_busy)

    def test_ordinary_actions_disabled_but_stop_remains_available(self):
        p = Pad(); p._robot["bus"]["walk_recovery"] = {"phase": "recovering"}
        buttons = {"stand": {"ok": True}, "walk": {"ok": True}, "sit": {"ok": True}}
        skills = [{"ok": True}]
        view = p._recovery_buttons(100, buttons, skills, [], [])
        self.assertTrue(view["active"])
        self.assertFalse(buttons["stand"]["ok"])
        self.assertFalse(skills[0]["ok"])
        self.assertEqual(buttons["walk"]["op"], "recover_cancel")
        self.assertTrue(buttons["walk"]["ok"])

    def test_old_daemon_has_no_recovery_button(self):
        p = Pad(); p._robot["bus"].pop("walk_recovery")
        self.assertFalse(p._recovery_view(100)["ok"])
        with self.assertRaises(Refused): self.start(p)
        self.assertEqual(p.calls, [])

    def test_update_guard_allows_cancel_but_never_start_or_renew(self):
        for action, op in (("start", "recover"), ("keepalive", "recover_keepalive"), ("cancel", "recover_cancel")):
            self.assertEqual(safe_during_update("pad.op", {"op": op}), action == "cancel")
            self.assertEqual(neutral_robot_command("robot.recover", {"action": action, "request_id": 71}), action == "cancel")

    def test_wrong_model_is_refused_before_rpc(self):
        p = Pad(); p._robot["bus"]["loaded_models"]["walk"]["sha256"] = "another-model"
        with self.assertRaises(Refused): self.start(p)
        self.assertEqual(p.calls, [])


if __name__ == "__main__": unittest.main()
