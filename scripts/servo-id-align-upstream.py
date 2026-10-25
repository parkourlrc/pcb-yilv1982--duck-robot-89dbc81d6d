#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HD-1910 舵机 ID 对齐上游 microduck_feetech 映射（EEPROM 改号，2026-10-24）。

背景：本机 2026-10-17 定案 10-14=左腿、20-24=右腿，2026-10-22 又确认
30=head_pitch、31=neck_pitch——两者都与上游（方案 B 飞特版 microduck_feetech /
hls provision 原表）相反。2026-10-24 用户指示「id 做一次对齐，和方案 B 的
飞特版一致」：把 12 颗舵机的 EEPROM ID 改回上游排布，软件层另行同步回退。

目标映射（上游 microduck_feetech）：
  20-24 = 左腿 left_hip_yaw/roll/pitch、left_knee、left_ankle
  10-14 = 右腿 right_hip_yaw/roll/pitch、right_knee、right_ankle
  30 = neck_pitch、31 = head_pitch、32 = head_yaw、33 = head_roll、34 = mouth
  200 = IMU（链末，不参与、不触碰）

改号顺序（防撞号；临时 ID 40-45，执行前先确认总线空闲）：
  1) 左腿   10→40 11→41 12→42 13→43 14→44
  2) 右腿   20→10 21→11 22→12 23→13 24→14
  3) 临时   40→20 41→21 42→22 43→23 44→24
  4) 头颈   30→45 31→30 45→31

单颗流程与 hls provision._write_eeprom / duck-control bus.rs 相同（本机
2026-10-17 用它完成 15 颗改号的实测路径）：
  ping(旧) → 写 55=[0]（关写保护，EPROM 写入掉电保存）→ 写 5=[新] → 50ms
  → 写 新/55=[1]（重新上锁）→ 回读 5 号==新、55 号==1、旧 ID 静默。

安全边界：
- 只写 5 号(ID) 和 55 号(写锁) 两个寄存器；不发位置/速度/扭矩指令，舵机不动。
- 不触碰 200 号 IMU；临时 ID 40-45 占用前先 ping 确认空闲。
- 中途失败立即中止并报告；状态文件记录进度，可安全续跑（含补锁修复）。
- 完成后凭状态文件拒绝重复执行（ID 集合改号前后相同，扫描无法自检已完成，
  重复执行等于再换一次方向）。

用法（板上，先停 servo-web 释放 /dev/ttyS2）：
  python3 servo-id-align-upstream.py            # 默认预检 + 计划，不写任何东西
  python3 servo-id-align-upstream.py --apply    # 执行改号
"""

import argparse
import json
import os
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("缺少 pyserial：sudo apt-get install python3-serial")

DEFAULT_PORT = "/dev/ttyS2"
BAUD = 1_000_000
ADDR_ID = 5
ADDR_LOCK = 55
ADDR_POS = 56
LOCK_WRITE_ARMED = 0   # 写 0：关写保护，EPROM 写入掉电保存（provision: LOCK_EPROM_SAVED）
LOCK_WRITE_PROTECT = 1  # 写 1：重新上锁（provision: LOCK_EPROM_VOLATILE）
EEPROM_SETTLE = 0.05

# (旧行=本机 2026-10-17/10-22 定案, 新=上游 microduck_feetech)
MOVES = [
    (10, 40), (11, 41), (12, 42), (13, 43), (14, 44),   # 左腿 → 临时
    (20, 10), (21, 11), (22, 12), (23, 13), (24, 14),   # 右腿 → 最终 10-14
    (40, 20), (41, 21), (42, 22), (43, 23), (44, 24),   # 左腿临时 → 最终 20-24
    (30, 45), (31, 30), (45, 31),                       # 头颈 30/31 互换
]

EXPECTED_BEFORE = set(range(10, 15)) | set(range(20, 25)) | set(range(30, 35))
TEMP_IDS = {40, 41, 42, 43, 44, 45}

# 上游 ID → 关节名（对齐后生效；仅用于终报打印）
UPSTREAM_NAMES = {
    20: "left_hip_yaw", 21: "left_hip_roll", 22: "left_hip_pitch",
    23: "left_knee", 24: "left_ankle",
    30: "neck_pitch", 31: "head_pitch", 32: "head_yaw",
    33: "head_roll", 34: "mouth",
    10: "right_hip_yaw", 11: "right_hip_roll", 12: "right_hip_pitch",
    13: "right_knee", 14: "right_ankle",
}

STATE_FILE = os.path.expanduser("~/id-align-20261024.state.json")
SNAPSHOT_FILE = os.path.expanduser("~/id-align-20261024-snapshot.json")


class Abort(Exception):
    pass


def frame(sid, inst, params=b""):
    length = len(params) + 2
    body = bytes([sid, length, inst]) + params
    return b"\xFF\xFF" + body + bytes([(~sum(body)) & 0xFF])


def transact(ser, sid, inst, params=b"", timeout=0.06):
    """发一帧、收一帧状态包；返回 bytes(参数区) 或 None（无应答/校验错）。"""
    ser.reset_input_buffer()
    ser.write(frame(sid, inst, params))
    ser.flush()
    deadline = time.monotonic() + timeout
    buf = b""
    while time.monotonic() < deadline:
        n = ser.in_waiting
        if n:
            buf += ser.read(n)
            if len(buf) >= 5 and buf[:2] == b"\xFF\xFF":
                total = 4 + buf[3]
                if len(buf) >= total:
                    if ((~sum(buf[2:total - 1])) & 0xFF) != buf[total - 1]:
                        return None  # 校验错当无应答，由上层回读判定
                    if buf[2] != sid:
                        return None
                    return bytes(buf[5:total - 1])  # 跳过 ERR 字节
    return None


def ping(ser, sid, tries=1):
    for _ in range(tries):
        if transact(ser, sid, 0x01) is not None:
            return True
    return False


def read_reg(ser, sid, addr, length, tries=2):
    for _ in range(tries):
        data = transact(ser, sid, 0x02, bytes([addr, length]))
        if data is not None and len(data) == length:
            return list(data)
    return None


def write_reg(ser, sid, addr, data):
    """写指令；应答级别 0 的舵机对写静默，成败一律靠回读判定。"""
    transact(ser, sid, 0x03, bytes([addr] + list(data)))


def scan(ser, ids):
    return {sid for sid in ids if ping(ser, sid, tries=2)}


def read_pos(ser, sid):
    d = read_reg(ser, sid, ADDR_POS, 2)
    if d is None:
        return None
    return (d[1] << 8 | d[0]) & 0x0FFF


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"done": [], "complete": False}


def save_state(st):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def check_preconditions(ser):
    alive = scan(ser, list(range(0, 61)))
    extras = alive - EXPECTED_BEFORE
    temps_busy = alive & TEMP_IDS
    imu = ping(ser, 200, tries=2)
    print(f"总线扫描 0-60：{sorted(alive)}")
    print(f"IMU 200：{'在线' if imu else '无应答（不影响改号，仅记录）'}")
    if temps_busy:
        raise Abort(f"临时 ID {sorted(temps_busy)} 已被占用，拒绝执行")
    if extras:
        raise Abort(f"总线上有意外的 ID {sorted(extras)}（预期只有 10-14/20-24/30-34），拒绝执行")
    missing = EXPECTED_BEFORE - alive
    if missing:
        raise Abort(f"缺少预期舵机 {sorted(missing)}，拒绝执行")
    return alive


def snapshot_pre(ser):
    snap = {"time": time.strftime("%F %T"), "pre": {}}
    for sid in sorted(EXPECTED_BEFORE):
        snap["pre"][str(sid)] = {
            "reg5": read_reg(ser, sid, ADDR_ID, 1),
            "reg55": read_reg(ser, sid, ADDR_LOCK, 1),
            "pos": read_pos(ser, sid),
        }
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    print(f"改号前快照：{SNAPSHOT_FILE}")
    for sid in sorted(EXPECTED_BEFORE):
        info = snap["pre"][str(sid)]
        print(f"  ID {sid:>3}  reg5={info['reg5']}  reg55={info['reg55']}  pos={info['pos']}")


def do_move(ser, old, new):
    print(f"→ {old} 改为 {new} ...", end=" ", flush=True)
    if not ping(ser, old, tries=3):
        raise Abort(f"源 ID {old} 无应答，中止")
    if ping(ser, new, tries=2):
        raise Abort(f"目标 ID {new} 已有舵机应答（撞号风险），中止")
    for attempt in (1, 2):
        write_reg(ser, old, ADDR_LOCK, [LOCK_WRITE_ARMED])
        time.sleep(0.02)
        write_reg(ser, old, ADDR_ID, [new])
        time.sleep(EEPROM_SETTLE)
        write_reg(ser, new, ADDR_LOCK, [LOCK_WRITE_PROTECT])
        time.sleep(0.02)
        reg5 = read_reg(ser, new, ADDR_ID, 1)
        reg55 = read_reg(ser, new, ADDR_LOCK, 1)
        old_alive = ping(ser, old, tries=2)
        if reg5 == [new] and reg55 == [1] and not old_alive:
            print(f"成功（回读 5 号={reg5[0]}、55 号={reg55[0]}，旧 {old} 已静默）")
            return
        print(f"\n  第 {attempt} 次未通过校验（5 号={reg5}、55 号={reg55}、旧 {old} "
              f"{'仍在' if old_alive else '静默'}）", end=" ")
        if old_alive and read_reg(ser, old, ADDR_ID, 1) == [old]:
            print("- 旧 ID 仍可读，ID 写入未生效，重试 ...", end=" ")
            continue
        raise Abort(f"ID {old}→{new} 状态不明（旧 ID{'可读但值异常' if old_alive else '静默'}），"
                    "中止；请人工核bus，勿盲目重跑")
    raise Abort(f"ID {old}→{new} 两次写入均未生效，中止")


def repair_done(ser, done):
    """续跑前对已完成的目标 ID 补一次写锁，防上次中途断在『已改号未上锁』。"""
    for old, new in done:
        if not ping(ser, new, tries=3):
            raise Abort(f"状态文件记录 {old}→{new} 已完成，但 {new} 无应答，中止")
        reg55 = read_reg(ser, new, ADDR_LOCK, 1)
        if reg55 != [1]:
            write_reg(ser, new, ADDR_LOCK, [LOCK_WRITE_PROTECT])
            time.sleep(0.02)
            reg55 = read_reg(ser, new, ADDR_LOCK, 1)
            if reg55 != [1]:
                raise Abort(f"{new} 写锁修复失败（55 号={reg55}），中止")
            print(f"补锁：{new}（源 {old}）55 号已回到 1")


def final_verify(ser, snap_pre):
    alive = scan(ser, list(range(0, 61)))
    if alive != EXPECTED_BEFORE:
        raise Abort(f"终扫异常：{sorted(alive)}（预期 {sorted(EXPECTED_BEFORE)}）")
    print(f"终扫通过：{sorted(alive)}；临时 ID 40-45 均已释放")
    # 合成映射：旧原始 ID → 最终 ID（临时号 40-45 只桥接，不作为源记录）
    final_of = {}
    for old, new in MOVES:
        for k in [k for k, v in final_of.items() if v == old]:
            final_of[k] = new
        if old in EXPECTED_BEFORE:
            final_of[old] = new
    # 位置指纹：改号不动机器人，同一颗舵机位置应基本不变（容差 ±40 计数）
    print("位置核对（改号前原始 ID → 最终 ID 读数）：")
    bad = []
    for old, new in sorted(final_of.items()):
        pre = snap_pre.get(str(old), {}).get("pos")
        now = read_pos(ser, new)
        ok = pre is not None and now is not None and abs(now - pre) <= 40
        print(f"  旧 {old:>2} pre={pre}  →  新 {new:>2} now={now}  "
              f"{'OK' if ok else '!! 偏差超 40'}")
        if not ok:
            bad.append((old, new, pre, now))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=DEFAULT_PORT)
    ap.add_argument("--apply", action="store_true", help="执行改号（默认只预检）")
    ap.add_argument("--force", action="store_true",
                    help="忽略状态文件强制执行（仅排障用，正常勿用）")
    args = ap.parse_args()

    st = load_state()
    if st["complete"] and not args.force:
        sys.exit(f"状态文件标记已完成（{STATE_FILE}）。ID 集合改号前后相同，扫描无法"
                 "自检已完成；重复执行等于再换一次方向。确有必要请 --force。")

    ser = serial.Serial(args.port, BAUD, timeout=0.01)
    try:
        check_preconditions(ser)
        if not args.apply:
            print("\n[dry-run] 未写任何寄存器。计划改号顺序：")
            for old, new in MOVES:
                print(f"  {old:>2} → {new:>2}")
            print("完成后映射：20-24=左腿、10-14=右腿、30=neck_pitch、31=head_pitch")
            return 0

        if not st["done"]:
            snapshot_pre(ser)
        else:
            print(f"续跑：状态文件记录已完成 {len(st['done'])} 步，先补锁核对")
            repair_done(ser, [tuple(m) for m in st["done"]])
            if not os.path.exists(SNAPSHOT_FILE):
                raise Abort("缺少改号前快照，位置指纹无法核对，中止（可删状态文件重来）")
            with open(SNAPSHOT_FILE, encoding="utf-8") as f:
                snap = json.load(f)
            if set(snap.get("pre", {})) != {str(i) for i in EXPECTED_BEFORE}:
                raise Abort("快照内容不完整，中止")

        done = {tuple(m) for m in st["done"]}
        for old, new in MOVES:
            if (old, new) in done:
                print(f"= {old}→{new} 已完成，跳过")
                continue
            do_move(ser, old, new)
            st["done"].append([old, new])
            save_state(st)

        with open(SNAPSHOT_FILE, encoding="utf-8") as f:
            snap = json.load(f)
        bad = final_verify(ser, snap.get("pre", {}))
        snap["post_time"] = time.strftime("%F %T")
        snap["moves"] = MOVES
        snap["fingerprint_bad"] = bad
        with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=1)
        st["complete"] = True
        save_state(st)
        print("\n全部完成。改号后 ID → 关节（上游 microduck_feetech）：")
        for sid in sorted(UPSTREAM_NAMES):
            print(f"  {sid:>3} = {UPSTREAM_NAMES[sid]}")
        if bad:
            print(f"\n!! 位置指纹有 {len(bad)} 项超差 {bad}——改号本身已通过回读校验，"
                  "但请在 servo-web 里逐颗核对左右/头颈归属后再用。")
        return 0
    finally:
        ser.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Abort as e:
        print(f"\n中止：{e}", file=sys.stderr)
        sys.exit(2)
