#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只把左右腿两组 ID 互换回来（EEPROM，2026-10-25 凌晨；头颈 30/31 不动）。

背景：2026-10-24 13:12 已把全机对齐上游（20-24=左腿、10-14=右腿）；当日 15:24 日志
证据显示总线上仍是正确上游状态（30=1812/31=1815 与改号后吻合），但之后 15:24–15:45
总线风暴（累计超时 232→7500+）、15:45:25 servo-web 日志写到一半被硬杀、板上 01:37 重启，
其间发生过程不明的腿组换回（无 servo-web 校准/改号日志；一次 hls 会话日志已被后续启动
覆盖）。2026-10-25 凌晨用户实测：动左脚 servo-web（已验证为上游映射）3D 动右脚——
即物理左腿现挂 10-14。本脚本把腿组换回上游排布：左腿 10-14 → 20-24，右腿 20-24 → 10-14
（临时号 40-44 防撞号）；30/31/32/33/34 与 IMU 200 一律不动。
单颗流程与 hls/duck-control 相同：55=[0] → 5=[新] → 50ms → 新/55=[1] → 回读校验。
用法（板上，先停 servo-web）：
  python3 servo-id-legs-reswap-20261025.py           # 预检
  python3 servo-id-legs-reswap-20261025.py --apply   # 执行
"""

import argparse
import json
import os
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("缺少 pyserial")

ADDR_ID, ADDR_LOCK, ADDR_POS = 5, 55, 56
EEPROM_SETTLE = 0.05

MOVES = [
    (10, 40), (11, 41), (12, 42), (13, 43), (14, 44),   # 左腿 → 临时
    (20, 10), (21, 11), (22, 12), (23, 13), (24, 14),   # 右腿 → 10-14
    (40, 20), (41, 21), (42, 22), (43, 23), (44, 24),   # 左腿临时 → 20-24
]
EXPECTED = set(range(10, 15)) | set(range(20, 25)) | set(range(30, 35))
STATE = os.path.expanduser("~/id-legs-reswap-20261025.state.json")
SNAP = os.path.expanduser("~/id-legs-reswap-20261025-snapshot.json")


class Abort(Exception):
    pass


def frame(sid, inst, params=b""):
    body = bytes([sid, len(params) + 2, inst]) + params
    return b"\xFF\xFF" + body + bytes([(~sum(body)) & 0xFF])


def transact(ser, sid, inst, params=b"", timeout=0.06):
    ser.reset_input_buffer()
    ser.write(frame(sid, inst, params))
    ser.flush()
    dl = time.monotonic() + timeout
    buf = b""
    while time.monotonic() < dl:
        n = ser.in_waiting
        if n:
            buf += ser.read(n)
            if len(buf) >= 5 and buf[:2] == b"\xFF\xFF":
                total = 4 + buf[3]
                if len(buf) >= total:
                    if ((~sum(buf[2:total - 1])) & 0xFF) != buf[total - 1] or buf[2] != sid:
                        return None
                    return bytes(buf[5:total - 1])
    return None


def ping(ser, sid, tries=1):
    for _ in range(tries):
        if transact(ser, sid, 0x01) is not None:
            return True
    return False


def read_reg(ser, sid, addr, n, tries=2):
    for _ in range(tries):
        d = transact(ser, sid, 0x02, bytes([addr, n]))
        if d is not None and len(d) == n:
            return list(d)
    return None


def do_move(ser, old, new):
    if not ping(ser, old, tries=3):
        raise Abort(f"源 {old} 无应答")
    if ping(ser, new, tries=2):
        raise Abort(f"目标 {new} 已有应答（撞号），中止")
    for attempt in (1, 2):
        transact(ser, old, 0x03, bytes([ADDR_LOCK, 0]))
        time.sleep(0.02)
        transact(ser, old, 0x03, bytes([ADDR_ID, new]))
        time.sleep(EEPROM_SETTLE)
        transact(ser, new, 0x03, bytes([ADDR_LOCK, 1]))
        time.sleep(0.02)
        r5 = read_reg(ser, new, ADDR_ID, 1)
        r55 = read_reg(ser, new, ADDR_LOCK, 1)
        if r5 == [new] and r55 == [1] and not ping(ser, old, tries=2):
            print(f"  {old}→{new} 成功（5号={r5[0]} 55号={r55[0]} 旧号静默）")
            return
        if ping(ser, old) and read_reg(ser, old, ADDR_ID, 1) == [old]:
            print(f"  {old}→{new} 第 {attempt} 次未生效，重试")
            continue
        raise Abort(f"{old}→{new} 状态不明，中止")
    raise Abort(f"{old}→{new} 两次未生效，中止")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if os.path.exists(STATE) and json.load(open(STATE)).get("complete"):
        sys.exit("状态文件标记已完成；重复执行=再换一次方向。确要执行先删 " + STATE)
    ser = serial.Serial("/dev/ttyS2", 1_000_000, timeout=0.01)
    try:
        alive = {s for s in range(0, 61) if ping(ser, s, tries=2)}
        print("扫描 0-60：", sorted(alive))
        if alive & set(range(40, 45)):
            raise Abort("临时号被占用")
        if alive - EXPECTED:
            raise Abort(f"意外 ID：{sorted(alive - EXPECTED)}")
        if EXPECTED - alive:
            raise Abort(f"缺舵机：{sorted(EXPECTED - alive)}")
        if not args.apply:
            print("[预检通过] 计划：左腿 10-14→20-24、右腿 20-24→10-14（30-34 不动）")
            return 0
        snap = {"time": time.strftime("%F %T"), "pre": {}}
        for s in sorted(EXPECTED):
            p = read_reg(ser, s, ADDR_POS, 2)
            snap["pre"][str(s)] = (p[1] << 8 | p[0]) & 0xFFF if p else None
        json.dump(snap, open(SNAP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        for old, new in MOVES:
            do_move(ser, old, new)
        alive2 = {s for s in range(0, 61) if ping(ser, s, tries=2)}
        print("终扫：", sorted(alive2))
        if alive2 != EXPECTED:
            raise Abort(f"终扫异常（预期 {sorted(EXPECTED)}）")
        snap["post"] = {str(s): ((read_reg(ser, s, ADDR_POS, 2) or [0, 0])[1] << 8 | (read_reg(ser, s, ADDR_POS, 2) or [0, 0])[0]) & 0xFFF for s in EXPECTED}
        json.dump(snap, open(SNAP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump({"complete": True}, open(STATE, "w", encoding="utf-8"))
        print("完成：20-24=左腿、10-14=右腿（与 servo-web 上游映射一致）")
        return 0
    finally:
        ser.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Abort as e:
        print("中止：", e, file=sys.stderr)
        sys.exit(2)
