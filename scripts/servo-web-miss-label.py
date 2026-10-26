#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 servo-web 部署副本的 IMU miss 文案从「连接中断」改为「应答率过低（附近期成功数）」。

背景（2026-10-26 定案）：本机 IMU 板②在 HAT 第二 3P 口支路上应答率仅 0–27%（干净总线
实测，见 docs/references/servo-web-imu-3d-20261024/research.md round3-20261026），但链路
并没有"断"——应答帧 0.28ms 正常返回、内容有效，只是多数请求无应答帧。imu_bus.py 的 miss
状态字是 disconnected，前端标签映射成「连接中断」，措辞与真实状态不符。

本脚本只改传入部署目录的两处显示（先备份），状态字/前端逻辑不动：
- imu_bus.py feed() 的 miss 文案 → 「IMU 应答率过低：连续 N 帧未应答，最近 60 秒成功 K 次…」
  （新增 success_times 记录，feed/probe_result 成功时登记，60s 滑窗计数）
- index.html 的标签映射 disconnected:'连接中断' → disconnected:'IMU 未应答'
  （初始"等待第一条 sync_read"与 miss 共用该状态字，"未应答"对两者都成立）

用法（板上或本机指向部署目录）：
  python3 servo-web-miss-label.py <部署目录> [--dry-run]
  python3 servo-web-miss-label.py ~/servo-web            # 实际修改（先备份 .bak-时间戳）
"""
import argparse
import shutil
import sys
import time

TARGETS = {
    "imu_bus.py": [
        # 导入 deque
        (
            "import math\nimport struct\nimport threading\nimport time\n",
            "import math\nimport struct\nimport threading\nimport time\nfrom collections import deque\n",
        ),
        # __init__ 记录成功时刻
        (
            "        self.misses = 0\n        self.total_misses = 0\n",
            "        self.misses = 0\n        self.total_misses = 0\n"
            "        self.success_times = deque()   # 2026-10-26 本机补丁：60s 滑窗成功应答时刻\n",
        ),
        # probe_result 成功（PING 放回）也登记
        (
            "        if answered and self.excluded_since is not None:\n"
            "            self.excluded_since = None\n"
            "            self.misses = 0\n",
            "        if answered and self.excluded_since is not None:\n"
            "            self.excluded_since = None\n"
            "            self.misses = 0\n"
            "            now2 = time.monotonic()\n"
            "            self.success_times.append(now2)\n"
            "            while self.success_times and now2 - self.success_times[0] > 60.0:\n"
            "                self.success_times.popleft()\n",
        ),
        # feed 成功登记 + 60s 滑窗修剪
        (
            "        self.misses = 0\n"
            "        self.excluded_since = None\n"
            "        d = decode_block(block)\n",
            "        self.misses = 0\n"
            "        self.excluded_since = None\n"
            "        self.success_times.append(now)\n"
            "        while self.success_times and now - self.success_times[0] > 60.0:\n"
            "            self.success_times.popleft()\n"
            "        d = decode_block(block)\n",
        ),
        # miss 文案
        (
            '            frame = self._frame("disconnected",\n'
            '                                f"ID 200 连续 {self.misses} 帧没应答：检查小板供电、总线接线（J1/J2 的 DATA）"\n'
            '                                f"和固件是不是飞特协议版；舵机已改为单独读，每 {RETRY_S:.0f} 秒单独 PING 一次 200。",\n'
            "                                misses=self.total_misses)",
            '            k = sum(1 for t in self.success_times if now - t <= 60.0)\n'
            '            frame = self._frame("disconnected",\n'
            '                                f"IMU 应答率过低：连续 {self.misses} 帧未应答，最近 60 秒成功 {k} 次"\n'
            '                                f"（链路未断，应答帧内容正常）；小板已隔离单独 PING（每 {RETRY_S:.0f} 秒），"\n'
            '                                f"可排查小板供电、DATA 接线和固件协议。",\n'
            "                                misses=self.total_misses)",
        ),
    ],
    "index.html": [
        (
            "disconnected:'连接中断'",
            "disconnected:'IMU 未应答'",
        ),
    ],
}


class PatchError(Exception):
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deploy_dir")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    changed_any = False
    for fname, replaces in TARGETS.items():
        path = f"{args.deploy_dir.rstrip('/')}/{fname}"
        try:
            text = open(path, encoding="utf-8").read()
        except OSError as e:
            raise PatchError(f"读不了 {path}: {e}")
        for i, (old, new) in enumerate(replaces, 1):
            if new in text and old not in text:
                print(f"  = {fname} 第 {i} 段已是新版：{new.splitlines()[0][:46]}…")
                continue
            n = text.count(old)
            if n != 1:
                raise PatchError(f"{fname} 第 {i} 段匹配 {n} 处（预期 1）：{old.splitlines()[0][:60]}…")
            text = text.replace(old, new)
            changed_any = True
            print(f"  * {fname} 第 {i} 段已替换")
        if args.dry_run:
            continue
        backup = path + time.strftime(".bak-%Y%m%d-%H%M%S")
        shutil.copy2(path, backup)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"  已写入 {path}；备份 {backup}")

    if args.dry_run:
        print("完成（dry-run，未写入）")
    elif not changed_any:
        print("全部段落均已是新版，无改动")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PatchError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(2)
