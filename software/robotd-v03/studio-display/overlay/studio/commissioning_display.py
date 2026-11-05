"""本机 commissioning 反馈的显示适配；不改原始 RPC，不用于控制或标定。"""
import math
import time

from .estop import STARTING_PHASES

MAX_AGE_MS = 3000
IDS = (20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _counter(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _sample(bus):
    sample = bus.get("last_sample")
    if not isinstance(sample, dict):
        return None
    if not all(_counter(sample.get(k)) for k in ("at_us", "cycle")):
        return None
    updated = bus.get("updated_at_us")
    if not _counter(updated) or updated < sample["at_us"]:
        return None
    return sample


def _session(bus):
    comm = bus.get("device_communication")
    return (comm.get("session") if isinstance(comm, dict) else None, bus.get("session"))


class CommissioningClock:
    """轮询时记录样本推进时刻；重复收到同一旧帧不会刷新其寿命。"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.session = self.key = self.advanced_at = None

    def observe(self, bus, now=None):
        now = time.monotonic() if now is None else now
        if not isinstance(bus, dict) or bus.get("mode") != "commissioning":
            self.reset()
            return
        sample = _sample(bus)
        if sample is None or bus.get("phase") in STARTING_PHASES:
            self.reset()
            return
        session = _session(bus)
        if session == (None, None):
            self.reset()
            return
        if session != self.session:
            self.reset()
            self.session = session
        key = sample["at_us"], sample["cycle"]
        if self.key is None or (key[0] > self.key[0] and key[1] > self.key[1]):
            self.key = key
            self.advanced_at = now - (bus["updated_at_us"] - sample["at_us"]) / 1_000_000


def snapshot(rd, now=None):
    """返回显示用反馈；其他运行模式返回 None，保留原有显示路径。"""
    bus_sample = getattr(rd, "bus", None)
    bus = getattr(bus_sample, "value", None)
    if not isinstance(bus, dict) or bus.get("mode") != "commissioning" or bus.get("phase") in STARTING_PHASES:
        return None
    now = time.monotonic() if now is None else now
    sample = _sample(bus)
    clock = getattr(rd, "commissioning_clock", None)
    receipt_s = bus_sample.age(now)
    hello_at = getattr(getattr(rd, "hello", None), "at", None)
    current = (getattr(rd, "present", None) is True and bus_sample.error is None
               and _number(receipt_s) and receipt_s >= 0
               and (hello_at is None or (bus_sample.at is not None and bus_sample.at >= hello_at)))
    age_ms = None
    if (sample is not None and clock is not None and clock.advanced_at is not None
            and clock.session == _session(bus) and clock.key == (sample["at_us"], sample["cycle"])):
        wire_ms = (bus["updated_at_us"] - sample["at_us"]) / 1000
        if _number(receipt_s) and receipt_s >= 0:
            age_ms = max((now - clock.advanced_at) * 1000, wire_ms + receipt_s * 1000)
    error = bus_sample.error or bus.get("last_cycle_error") or bus.get("error")
    fresh = bool(current and age_ms is not None and 0 <= age_ms < MAX_AGE_MS
                 and bus.get("phase") != "read_error" and not error)
    by_id = {}
    raw_rows = sample.get("servos") if sample is not None else None
    for row in raw_rows if isinstance(raw_rows, list) else []:
        if not isinstance(row, dict) or not _counter(row.get("id")) or row["id"] not in IDS:
            continue
        by_id[row["id"]] = row
    joints = []
    for sid, row in by_id.items():
        valid_position = isinstance(row.get("position_raw"), int) and not isinstance(row["position_raw"], bool)
        live = fresh and valid_position
        j = {"id": sid, "name": row.get("joint"), "feedback_fresh": live,
             "sample_age_ms": round(age_ms, 3) if age_ms is not None else None}
        for src, dst in (("position_raw", "position_raw"), ("speed_raw", "speed_raw"),
                         ("load_raw", "load_raw"), ("current_raw", "current_raw"),
                         ("voltage_v", "volts"), ("temperature_c", "temperature_c")):
            value = row.get(src)
            j[dst] = value if live and _number(value) else None
        joints.append(j)
    imu = sample.get("imu") if sample is not None else None
    imu = imu if isinstance(imu, dict) else {}
    gravity = imu.get("gravity")
    imu_live = fresh and imu.get("valid") is True and imu.get("ready") is True
    if not (imu_live and isinstance(gravity, list) and len(gravity) == 3 and all(_number(x) for x in gravity)):
        gravity = None
    return {"joints": joints, "online": sum(j["feedback_fresh"] for j in joints) if fresh else None,
            "fresh": fresh, "age_ms": round(age_ms, 3) if age_ms is not None else None,
            "error": error or ("调试模式本轮读取失败" if bus.get("phase") == "read_error" else None),
            "at_us": sample["at_us"] if sample is not None else None,
            "imu": {"ready": imu.get("ready") if fresh else None,
                    "valid": imu.get("valid") if fresh else None, "gravity": gravity,
                    "source": imu.get("source") if current else None,
                    "mount_verified": bus.get("imu_mount_verified") if current else None}}
