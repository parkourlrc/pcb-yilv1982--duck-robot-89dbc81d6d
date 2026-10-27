#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""受控实验（2026-10-27 深夜，独占窗口，servo-web 已停）：四步 SyncRead 实验。

物理状态：IMU 在 HAT 第二口、舵机总线在原口（15 颗在线）——故障配置。
口径：robotd 补丁 50Hz（20ms tick）、ID 顺序 200 第一 + [10..14, 20..24, 30..34]。
步骤：①单条单 ID(200) ②单 ID @50Hz×10s ③单条全 ID(16) ④全 ID @50Hz×10s。
输出：stdout 摘要 + logs/imu-poll-exp-20261027.json 全量。
"""
import json
import time

import feetech

IMU = 200
JOINT = [10, 11, 12, 13, 14, 20, 21, 22, 23, 24, 30, 31, 32, 33, 34]  # robotd JOINT_IDS 顺序
ADDR, N, HZ = 56, 15, 50

bus = feetech.FeetechBus("/dev/ttyS2", 1_000_000, timeout=0.02)
out = {"meta": {"hz": HZ, "addr": ADDR, "len": N, "imu_first_then": JOINT}}


def one(ids):
    s0 = dict(bus.stats)
    t0 = time.monotonic()
    r = bus.sync_read(ids, ADDR, N)
    ms = (time.monotonic() - t0) * 1000
    return {
        "ms": round(ms, 2),
        "ok": [i for i in ids if r.get(i)],
        "err": {k: bus.stats[k] - s0[k] for k in ("timeout", "bad_checksum", "bad_id")},
        "imu": list(r[IMU][1]) if (IMU in ids and r.get(IMU)) else None,
    }


def burst(ids, seconds):
    res = []
    t_start = time.monotonic()
    t_end = t_start + seconds
    next_t = time.monotonic()
    while time.monotonic() < t_end:
        res.append(one(ids))
        next_t += 1.0 / HZ
        gap = next_t - time.monotonic()
        if gap > 0:
            time.sleep(gap)
        else:
            next_t = time.monotonic()
    return res, time.monotonic() - t_start


def summarize(name, res, elapsed, ids):
    n = len(res)
    dts = [r["ms"] for r in res]
    errs = {k: sum(r["err"][k] for r in res) for k in ("timeout", "bad_checksum", "bad_id")}
    rate = {i: round(sum(1 for r in res if i in r["ok"]) / n, 4) for i in ids}
    imu_ok = [r["imu"] for r in res if r["imu"]]
    full = sum(1 for r in res if len(r["ok"]) == len(ids))
    print(f"[{name}] ticks={n} 实际频率={n/elapsed:.1f}Hz 全成功拍={full}/{n}")
    print(f"  批耗时 ms: min={min(dts):.1f} avg={sum(dts)/n:.1f} max={max(dts):.1f}")
    print(f"  错误计数: {errs}")
    print(f"  成功率: 200={rate.get(IMU)}; 舵机 min={min(v for k,v in rate.items() if k!=IMU)} "
          f"max={max(v for k,v in rate.items() if k!=IMU)}" if len(ids) > 1 else f"  成功率: 200={rate.get(IMU)}")
    if imu_ok:
        seq = [b[12] for b in imu_ok[:20]]
        print(f"  IMU 应答样本(前20个成功块的第12字节计数): {seq}")
    return {"ticks": n, "elapsed_s": round(elapsed, 2), "batch_ms": {"min": min(dts), "avg": round(sum(dts)/n,1), "max": max(dts)},
            "errors": errs, "rate": rate, "full_ticks": full}


print("=== 步骤1：单条 SyncRead 只带 200 ===", flush=True)
s1 = one([IMU])
print(json.dumps(s1, ensure_ascii=False))
out["step1_single_imu"] = s1

print("=== 步骤2：单 ID(200) @50Hz 连续 10 秒 ===", flush=True)
res2, el2 = burst([IMU], 10)
out["step2_imu_10s"] = {"summary": summarize("步骤2", res2, el2, [IMU]), "raw": res2}

print("=== 步骤3：单条 SyncRead 全 16 ID（200 第一 + robotd 顺序） ===", flush=True)
s3 = one([IMU] + JOINT)
print(json.dumps({**s3, "ok": s3["ok"], "miss": [i for i in [IMU]+JOINT if i not in s3["ok"]]}, ensure_ascii=False))
out["step3_single_full"] = s3

print("=== 步骤4：全 16 ID @50Hz 连续 10 秒 ===", flush=True)
res4, el4 = burst([IMU] + JOINT, 10)
out["step4_full_10s"] = {"summary": summarize("步骤4", res4, el4, [IMU] + JOINT), "raw": res4}

path = "logs/imu-poll-exp-20261027.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print(f"全量数据已写 {path}", flush=True)
bus.close()
