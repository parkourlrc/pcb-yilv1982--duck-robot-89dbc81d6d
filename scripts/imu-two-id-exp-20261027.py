#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两 ID 混读实验（2026-10-27 深夜，独占窗口）：只发 IMU(200) + 当前在线的那颗舵机。

目的：排除缺席 ID 的 R3 干扰后，看健康混读形态下 IMU 与舵机是否都正常应答、
数据内容是否正常（IMU 计数连续性/状态位；舵机位置/电压/温度合理性）。
输出：stdout 摘要 + logs/imu-two-id-exp-20261027.json。
"""
import json
import time

import feetech

IMU = 200
JOINT = [10, 11, 12, 13, 14, 20, 21, 22, 23, 24, 30, 31, 32, 33, 34]
ADDR, N, HZ = 56, 15, 50

bus = feetech.FeetechBus("/dev/ttyS2", 1_000_000, timeout=0.02)

print("=== 探测在线舵机 ===", flush=True)
online = [sid for sid in JOINT if bus.ping(sid) is not None]
print(f"在线: {online}", flush=True)
assert len(online) >= 1, "没探测到在线舵机"
sid = online[0]
ids = [IMU, sid]
out = {"meta": {"ids": ids, "hz": HZ, "addr": ADDR, "len": N}, "online": online}


def one():
    s0 = dict(bus.stats)
    t0 = time.monotonic()
    r = bus.sync_read(ids, ADDR, N)
    ms = (time.monotonic() - t0) * 1000
    return {
        "ms": round(ms, 2),
        "ok": [i for i in ids if r.get(i)],
        "err": {k: bus.stats[k] - s0[k] for k in ("timeout", "bad_checksum", "bad_id")},
        "imu": list(r[IMU][1]) if r.get(IMU) else None,
        "servo": list(r[sid][1]) if r.get(sid) else None,
    }


print(f"=== 步骤A：单条 sync_read([{IMU},{sid}]) ===", flush=True)
a = one()
print(json.dumps(a, ensure_ascii=False), flush=True)
if a["imu"]:
    print(f"  IMU 块: 计数={a['imu'][12]} 状态位=0x{a['imu'][13]:02X} 保留={a['imu'][14]} 陀螺={a['imu'][0:3]} 四元数位型={a['imu'][6:12]}", flush=True)
if a["servo"]:
    st = feetech.FeetechBus._decode_state(0, bytes(a["servo"]))
    print(f"  舵机 #{sid}: 位置={st['pos']} 电压={st['volt']}V 温度={st['temp']}°C 电流={st['current_ma']:.0f}mA 状态={st['status_text'] or '正常'}", flush=True)
out["stepA"] = a

print("=== 步骤B：@50Hz 连续 10 秒 ===", flush=True)
res = []
t_end = time.monotonic() + 10
next_t = time.monotonic()
while time.monotonic() < t_end:
    res.append(one())
    next_t += 1.0 / HZ
    gap = next_t - time.monotonic()
    if gap > 0:
        time.sleep(gap)
    else:
        next_t = time.monotonic()

n = len(res)
dts = [r["ms"] for r in res]
errs = {k: sum(r["err"][k] for r in res) for k in ("timeout", "bad_checksum", "bad_id")}
rate = {i: round(sum(1 for r in res if i in r["ok"]) / n, 4) for i in ids}
both = sum(1 for r in res if len(r["ok"]) == 2)
imu_cnts = [r["imu"][12] for r in res if r["imu"]]
diffs = [(imu_cnts[i + 1] - imu_cnts[i]) % 256 for i in range(len(imu_cnts) - 1)]
sv = [feetech.FeetechBus._decode_state(0, bytes(r["servo"])) for r in res if r["servo"]]
vs = [s["volt"] for s in sv]
ps = [s["pos"] for s in sv]
print(f"ticks={n} 实际频率={n/10:.1f}Hz 两全其美拍={both}/{n}", flush=True)
print(f"批耗时 ms: min={min(dts):.1f} avg={sum(dts)/n:.1f} max={max(dts):.1f}；错误: {errs}", flush=True)
print(f"成功率: 200={rate[IMU]} #{sid}={rate[sid]}", flush=True)
print(f"IMU 计数差分分布: {dict(sorted(((d, diffs.count(d)) for d in set(diffs)), key=lambda x: -x[1]))}", flush=True)
print(f"IMU 状态位分布: {dict((hex(b), sum(1 for r in res if r['imu'] and r['imu'][13]==b)) for b in set(r['imu'][13] for r in res if r['imu']))}", flush=True)
if vs:
    print(f"舵机数据: 电压 {min(vs)}~{max(vs)}V，位置 min={min(ps)} max={max(ps)}，温度 {sv[0]['temp']}°C", flush=True)
out["stepB"] = {"ticks": n, "rate": rate, "both": both, "errors": errs,
                "batch_ms": [min(dts), round(sum(dts)/n, 1), max(dts)], "raw": res}

with open("logs/imu-two-id-exp-20261027.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print("全量数据已写 logs/imu-two-id-exp-20261027.json", flush=True)
bus.close()
