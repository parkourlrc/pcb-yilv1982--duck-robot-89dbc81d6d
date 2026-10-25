#!/usr/bin/env python3
"""给 servo-web 加一层“软件零位”表，不写舵机 EEPROM。

用途：某颗舵机的物理零位不在 2048（比如 22 号直腿时读 1198），但不想再 CAL，
就在 ZERO_COUNTS 里记下“这颗的模型 0° 对应哪个计数”。页面据此：
- 3D 角度 = (count − zeroCount) × 360/4096 × dir
- 每行角度读数同样用 zeroCount
- 官方姿势/站姿目标 = zeroCount + 角度 × 4096/(2π) × dir

注意：这是本页软件层，不改舵机 EEPROM；它只让 servo-web 的显示和它自己发的官方姿势
按这个零位算。其他工具（hls、robotd、训练）要各自同步这张表，否则会不一致。
CAL 仍然按硬件 2048 工作，和这张表不是一回事。

用法（板上）：
    python3 servo-web-zero-offset.py ~/servo-web --dry-run
    python3 servo-web-zero-offset.py ~/servo-web --apply
"""

import argparse
import os
import shutil
import sys
import time

# 当前实测：22 号直腿时 pos=1198，其他 14 颗都在 2048 附近
ZERO_COUNTS = {22: 1198}

ZERO_OLD = "let dirs = {};   // 每颗 +1 / -1，来自服务端 directions.json，所有页面共用\n"
ZERO_NEW = ZERO_OLD + (
    "const ZERO_COUNTS = { 22: 1198 };   // 软件零位：这些 ID 的模型 0° 对应这个计数，不写 EEPROM\n"
    "function zeroCount(id) { return ZERO_COUNTS[id] !== undefined ? ZERO_COUNTS[id] : 2048; }\n"
)

POSE_OLD = "    const ang = (raw - 2048) * RAD * (dirs[id] || 1);"
POSE_NEW = "    const ang = (raw - zeroCount(id)) * RAD * (dirs[id] || 1);"

UPDATE_OLD = "    const deg = (dirs[id] || 1) * (s.pos - 2048) * 360 / 4096;"
UPDATE_NEW = "    const deg = (dirs[id] || 1) * (s.pos - zeroCount(id)) * 360 / 4096;"

STAND_OLD = "  present.forEach(id => { if (DEFAULT_POSITION[id] === undefined) return; goals[id] = Math.round(2048 + DEFAULT_POSITION[id] * 4096 / (2 * Math.PI) * (dirs[id] || 1)); });"
STAND_NEW = "  present.forEach(id => { if (DEFAULT_POSITION[id] === undefined) return; goals[id] = Math.round(zeroCount(id) + DEFAULT_POSITION[id] * 4096 / (2 * Math.PI) * (dirs[id] || 1)); });"

OFFICIAL_OLD = "  present.forEach(id => { if (rad[id] !== undefined) goals[id] = Math.round(2048 + rad[id] * 4096 / (2 * Math.PI) * (dirs[id] || 1)); });"
OFFICIAL_NEW = "  present.forEach(id => { if (rad[id] !== undefined) goals[id] = Math.round(zeroCount(id) + rad[id] * 4096 / (2 * Math.PI) * (dirs[id] || 1)); });"

CLEAR_OLD = """  else if (m.ok.length) hint(`${m.ok.length} 颗完成` + (big.length ? `；${big.join(' ')} 差 30° 以上，确认一下方向 ± 没设反（日志里有说明）` : ''));
  const refresh3d = () => { syncSliders(); if (window.duckRefreshPose) window.duckRefreshPose(); };"""
CLEAR_NEW = """  else if (m.ok.length) hint(`${m.ok.length} 颗完成` + (big.length ? `；${big.join(' ')} 差 30° 以上，确认一下方向 ± 没设反（日志里有说明）` : ''));
  // 校准成功说明硬件零位已经改好，清掉这些 ID 的软件零位，避免 CAL 后再叠加一层 offset
  (m.ok || []).forEach(id => { delete ZERO_COUNTS[id]; });
  const refresh3d = () => { syncSliders(); if (window.duckRefreshPose) window.duckRefreshPose(); };"""


def read(path):
    with open(path, "rb") as f:
        raw = f.read()
    return raw.decode("utf-8").replace("\r\n", "\n")


def write(path, text):
    with open(path, "rb") as f:
        raw = f.read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    with open(path, "wb") as f:
        f.write(text.replace("\n", nl).encode("utf-8"))


def replace(text, old, new, label):
    if new in text:
        print(f"  = {label}：已处理")
        return text
    if text.count(old) != 1:
        print(f"  ! {label}：匹配 {text.count(old)} 处，跳过")
        return text
    print(f"  * {label}")
    return text.replace(old, new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(os.path.expanduser(a.dir))
    path = os.path.join(root, "index.html")
    if not os.path.isfile(path):
        raise SystemExit(f"缺少 {path}")
    text = read(path)
    text = replace(text, ZERO_OLD, ZERO_NEW, "ZERO_COUNTS/zeroCount")
    text = replace(text, POSE_OLD, POSE_NEW, "3D 角度用 zeroCount")
    text = replace(text, UPDATE_OLD, UPDATE_NEW, "每行角度读数用 zeroCount")
    text = replace(text, STAND_OLD, STAND_NEW, "官方站姿目标用 zeroCount")
    text = replace(text, OFFICIAL_OLD, OFFICIAL_NEW, "官方姿势目标用 zeroCount")
    text = replace(text, CLEAR_OLD, CLEAR_NEW, "CAL 成功后清掉软件零位")
    if a.apply:
        bak = path + time.strftime(".bak-%Y%m%d-%H%M%S")
        shutil.copy2(path, bak)
        print(f"备份：{bak}")
        write(path, text)
    print("完成" + ("（dry-run，未写入）" if a.dry_run else "（已写入）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
