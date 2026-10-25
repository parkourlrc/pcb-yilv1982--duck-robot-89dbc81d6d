#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ID 200 三种读法的时序对比实验（2026-10-24；只读，不写任何寄存器）。

背景：servo-web --imu-bus 下，混帧（200+15 舵机同一条 sync_read）稳态 4 分钟零超时，
但把 200 拆成独立事务（普通 READ 或单 ID sync_read）后 200 大量缺答/晚答。
本脚本停服独占总线，按 10 Hz 分别实测三种模式的 200 应答成功率与延迟：
  A) sync_read([200])            —— v2 补丁的读法
  B) sync_read([200]+15 舵机)    —— 上游原混帧读法
  C) sync_read(15 舵机) 后 sync_read([200]) —— v2 的完整时序
用法（板上）：python3 imu200-timing-test.py [每模式秒数，默认 30]
"""

import statistics
import sys
import time

import serial

PORT = "/dev/ttyS2"
BAUD = 1_000_000
IMU = 200
SERVOS = [20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14]
ADDR, NLEN = 56, 15


def frame(sid, inst, params=b""):
    body = bytes([sid, len(params) + 2, inst]) + params
    return b"\xFF\xFF" + body + bytes([(~sum(body)) & 0xFF])


def collect_reply(ser, expect_id, deadline_s=0.06):
    """收一帧指定 ID 的应答；返回延迟 ms 或 None。多余帧计入 extra。"""
    t_send = time.monotonic()
    dl = t_send + deadline_s
    buf = b""
    while time.monotonic() < dl:
        n = ser.in_waiting
        if n:
            buf += ser.read(n)
            while len(buf) >= 5 and buf[:2] == b"\xFF\xFF":
                total = 4 + buf[3]
                if len(buf) < total:
                    break
                f, buf = buf[:total], buf[total:]
                if ((~sum(f[2:total - 1])) & 0xFF) != f[total - 1]:
                    continue
                if f[2] == expect_id:
                    return (time.monotonic() - t_send) * 1000
                # 不是想要的 ID：继续等（记录在额外帧里由调用方统计）
    return None


def sync_read(ser, ids):
    ser.reset_input_buffer()
    t0 = time.monotonic()
    ser.write(frame(0xFE, 0x82, bytes([ADDR, NLEN]) + bytes(ids)))
    ser.flush()
    lat = {}
    for sid in ids:
        lat[sid] = collect_reply(ser, sid)
    return lat


def run_pattern(ser, name, tick_fn, seconds):
    n = ok = 0
    lats = []
    t_end = time.monotonic() + seconds
    while time.monotonic() < t_end:
        tick = tick_fn(ser)
        n += 1
        if tick:
            ok += 1
            lats.append(tick)
        time.sleep(0.1)
    lat_s = (f"中位 {statistics.median(lats):.2f} ms / p95 {sorted(lats)[int(len(lats)*0.95)]:.2f} ms / max {max(lats):.2f} ms"
             if lats else "无成功样本")
    print(f"  {name}: {ok}/{n} 成功（{ok/max(n,1)*100:.1f}%），200 应答延迟 {lat_s}")
    return ok, n


def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    ser = serial.Serial(PORT, BAUD, timeout=0.01)
    print(f"ping 200: {'在线' if collect_reply(ser, 200, 0.1) is not None else '无应答'}")

    def pat_a(s):
        return sync_read(s, [IMU])[IMU]

    def pat_b(s):
        return sync_read(s, [IMU] + SERVOS)[IMU]

    def pat_c(s):
        sync_read(s, SERVOS)
        return sync_read(s, [IMU])[IMU]

    for name, fn in (("A 独立 sync_read([200])", pat_a),
                     ("B 混帧 [200]+15 舵机", pat_b),
                     ("C 先舵机后 sync_read([200])", pat_c)):
        print(f"模式 {name}（{seconds}s @10Hz）:")
        run_pattern(ser, name.split()[0], fn, seconds)
    ser.close()


if __name__ == "__main__":
    main()
