#!/usr/bin/env python3
"""修 servo-web 的单颗 CAL：0x0B 后必须回读位置，没到 2048 就用写偏移兜底。

背景（2026-10-23 #22 实测）：
- HD-1910 固件 3.46 的 0x0B 把偏移加反了，位置变成 `2×旧位置−目标`；
  例：1233→418、1636→1224，目标都是 2048。
- `calibrate_one` 原来只看“偏移变没变”，不看位置到没到，所以把错误当成功。
- 这个补丁在 0x0B 后加 `abs(pos-target) > CALIB_TOLERANCE` 检查，改走
  `calibrate_by_offset` 兜底：它按 `旧偏移 + sign×(target−旧读数)` 写，
  对这台 sign=-1 就得到正确偏移；写完回读验证 `pos==target`。
- 同时让兜底在 `OFFSET_SIGN` 已探出时也试另一个符号（防止探针探反/探不出）。

只改部署副本 `server.py`，不碰 references/。幂等，先备份；改完需重启服务。
用法（板上）：
    python3 servo-web-cal-fix.py ~/servo-web --dry-run
    python3 servo-web-cal-fix.py ~/servo-web --apply
"""

import argparse
import os
import shutil
import sys
import time

SIGNS_OLD = "    signs = [OFFSET_SIGN] if OFFSET_SIGN else [1, -1]"
SIGNS_NEW = "    signs = [OFFSET_SIGN, -OFFSET_SIGN] if OFFSET_SIGN else [1, -1]"

VERIFY_OLD = """        if ok:
            step = "算下垂并补偿"
"""
VERIFY_NEW = """        if ok and abs(pos - target) > CALIB_TOLERANCE:
            step = "0x0B 后位置未到，改走写偏移"
            trail.append(f"0x0B 后读数 {pos} 未到 {target}，改走写偏移兜底")
            ok, pos, off = calibrate_by_offset(i, target, trail)
            method = "写偏移31"
            if not ok:
                why = f"0x0B 后 {pos} 未到 {target}，写偏移兜底也失败"
        if ok:
            step = "算下垂并补偿"
"""

DROOP_OLD = """        if ok:
            step = "算下垂并补偿"
            sign = OFFSET_SIGN or 1
"""
DROOP_NEW = """        # 位置校准的语义是“当前位置 = target”。0x0B 后位置不对已走写偏移兜底并回读验证；
        # 这里不再做“把校准前姿态补回 target”的下垂补偿，否则会把刚校好的位置又改走。
        if ok and method == "0x0B" and abs(pos - target) > CALIB_TOLERANCE:
            step = "算下垂并补偿"
            sign = OFFSET_SIGN or 1
"""


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
    path = os.path.join(root, "server.py")
    if not os.path.isfile(path):
        raise SystemExit(f"缺少 {path}")
    text = read(path)
    text = replace(text, SIGNS_OLD, SIGNS_NEW, "兜底符号也试反方向")
    text = replace(text, VERIFY_OLD, VERIFY_NEW, "0x0B 后回读位置并兜底")
    text = replace(text, DROOP_OLD, DROOP_NEW, "不再做会改走位置的下垂补偿")
    if a.apply:
        bak = path + time.strftime(".bak-%Y%m%d-%H%M%S")
        shutil.copy2(path, bak)
        print(f"备份：{bak}")
        write(path, text)
    print("完成" + ("（dry-run，未写入）" if a.dry_run else "（已写入）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
