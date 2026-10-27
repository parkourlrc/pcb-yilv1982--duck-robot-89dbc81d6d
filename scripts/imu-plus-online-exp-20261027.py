#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IMU+全部在线舵机混读实验（2026-10-27 深夜，独占窗口）：自动探测在线舵机，与 IMU 一起 sync_read。

同 two-id 版的泛化：任意在线数量。
输出：stdout 摘要 + logs/imu-plus-online-exp-20261027.json。
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
assert 1 <= len(online) <= 15
# 全部在线舵机与 IMU 一起混读
ids = [IMU] + online
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
        "servo": {i: list(r[i][1]) for i in online if r.get(i)},
    }


print(f"=== 步骤A：单条 sync_read({ids}) ===", flush=True)
a = one()
print(json.dumps(a, ensure_ascii=False), flush=True)
if a["imu"]:
    print(f"  IMU 块: 计数={a['imu'][12]} 状态位=0x{a['imu'][13]:02X} 保留={a['imu'][14]} 陀螺={a['imu'][0:3]} 四元数位型={a['imu'][6:12]}", flush=True)
for i, blk in (a.get("servo") or {}).items():
    st = feetech.FeetechBus._decode_state(0, bytes(blk))
    print(f"  舵机 #{i}: 位置={st['pos']} 电压={st['volt']}V 温度={st['temp']}°C 电流={st['current_ma']:.0f}mA 状态={st['status_text'] or '正常'}", flush=True)
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
all_on = sum(1 for r in res if len(r["ok"]) == len(ids))
imu_cnts = [r["imu"][12] for r in res if r["imu"]]
diffs = [(imu_cnts[i + 1] - imu_cnts[i]) % 256 for i in range(len(imu_cnts) - 1)]
sv_last = {}
for r in res:
    for i, blk in (r.get("servo") or {}).items():
        sv_last[i] = feetech.FeetechBus._decode_state(0, bytes(blk))
vs = [s["volt"] for s in sv_last.values()]
print(f"ticks={n} 实际频率={n/10:.1f}Hz 全员成功拍={all_on}/{n}", flush=True)
print(f"批耗时 ms: min={min(dts):.1f} avg={sum(dts)/n:.1f} max={max(dts):.1f}；错误: {errs}", flush=True)
print("成功率:", {f"#{k}" if k!=IMU else "IMU": v for k, v in rate.items()}, flush=True)
print(f"IMU 计数差分分布: {dict(sorted(((d, diffs.count(d)) for d in set(diffs)), key=lambda x: -x[1]))}", flush=True)
print(f"IMU 状态位分布: {dict((hex(b), sum(1 for r in res if r['imu'] and r['imu'][13]==b)) for b in set(r['imu'][13] for r in res if r['imu']))}", flush=True)
if vs:
    detail = "; ".join(f"#{i} 位置{st['pos']} {st['volt']}V {st['temp']}°C" for i, st in sv_last.items())
    print(f"舵机数据: 电压 {min(vs)}~{max(vs)}V | {detail}", flush=True)
out["stepB"] = {"ticks": n, "rate": rate, "all_on": all_on, "errors": errs,
                "batch_ms": [min(dts), round(sum(dts)/n, 1), max(dts)], "raw": res}

with open("logs/imu-plus-online-exp-20261027.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print("全量数据已写 logs/imu-plus-online-exp-20261027.json", flush=True)
bus.close()
