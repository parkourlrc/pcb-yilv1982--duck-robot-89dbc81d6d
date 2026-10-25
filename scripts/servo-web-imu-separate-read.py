#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把部署副本 servo-web 的 IMU 读取从舵机 sync_read 中拆出（2026-10-24）。

背景：`--imu-bus` 模式下 server.py 的 read_states_with_imu 把 ID 200 排在舵机前面
发同一条 sync_read（模仿主控）。本机实测（2026-10-24 13:45 启动实录）：板②偶发
缺答/晚答时整条混合帧被拖掉——15 颗舵机全部显示无应答（3 秒内各丢 7 帧），
之后 imu_bus 的降级逻辑把 200 移出列表才自愈；200 每 2 秒 PING 成功又被放回，
再缺答则再丢帧。协议本身也写明应答槽耦合（kit imu_to_dxl §4.2-4.3）。
稳态 4 分钟监测（2206 次收发）timeout=0，问题只在这些偶发窗口出现。

修法：调试台优先舵机读数稳定——舵机单独 sync_read；200 用独立 READ 事务读取，
缺答只影响 IMU 面板（走 imu_bus 原有 miss/degrade/ping 逻辑），不再连累舵机帧。
只改部署副本 server.py（先备份），参考库不动。

用法：
    python3 servo-web-imu-separate-read.py ~/servo-web --dry-run
    python3 servo-web-imu-separate-read.py ~/servo-web --apply
"""

import argparse
import os
import shutil
import sys
import time


class PatchError(Exception):
    pass


OLD = '''    else:
        ids_sent = ([imu_bus.IMU_ID] if with_imu else []) + servo_ids
        # 台架上只接小板、200 又暂时出列时列表是空的：不发空 ID 表的 sync_read
        got = BUS.sync_read(ids_sent, imu_bus.BLOCK_ADDR, imu_bus.BLOCK_LEN) if ids_sent else {}
        st = {sid: (feetech.FeetechBus._decode_state(*got[sid]) if got.get(sid) else None) for sid in servo_ids}'''

NEW = '''    else:
        # 2026-10-24 本机补丁：200 不再与舵机同一条 sync_read——实测它偶发缺答会把
        # 整条混合帧拖掉（应答槽耦合，kit imu_to_dxl 协议 §4.2-4.3），15 颗舵机全部
        # 显示无应答（13:45 启动实录各丢 7 帧，200 出列后自愈）。调试台优先舵机读数
        # 稳定：舵机单独 sync_read；200 用只含自己的独立 sync_read——注意不能用普通
        # READ 单读（实测该板对 READ 常 >60ms 晚答/不答，timeout 与 bad_id 大涨），
        # 而 sync_read 槽 0 应答实测 100% 及时。缺答只影响本事务，走 imu_bus 原有
        # miss 计数/降级/2 秒 PING 重试，语义不变。
        got = dict(BUS.sync_read(servo_ids, imu_bus.BLOCK_ADDR, imu_bus.BLOCK_LEN) or {}) if servo_ids else {}
        st = {sid: (feetech.FeetechBus._decode_state(*got[sid]) if got.get(sid) else None) for sid in servo_ids}
        if with_imu:
            got.update(BUS.sync_read([imu_bus.IMU_ID], imu_bus.BLOCK_ADDR, imu_bus.BLOCK_LEN) or {})'''

# v1 补丁（普通 READ 单读 200）→ v2（独立单 ID sync_read）：板上已打 v1 时用这段转换
V1 = '''        got = dict(BUS.sync_read(servo_ids, imu_bus.BLOCK_ADDR, imu_bus.BLOCK_LEN) or {}) if servo_ids else {}
        st = {sid: (feetech.FeetechBus._decode_state(*got[sid]) if got.get(sid) else None) for sid in servo_ids}
        if with_imu:
            try:
                _, blk = BUS.read(imu_bus.IMU_ID, imu_bus.BLOCK_ADDR, imu_bus.BLOCK_LEN)
                got[imu_bus.IMU_ID] = (imu_bus.BLOCK_ADDR, blk)
            except Exception:
                pass  # 缺答交给 service.feed(None) 计 miss；不再连累上面的舵机帧'''

V2 = '''        got = dict(BUS.sync_read(servo_ids, imu_bus.BLOCK_ADDR, imu_bus.BLOCK_LEN) or {}) if servo_ids else {}
        st = {sid: (feetech.FeetechBus._decode_state(*got[sid]) if got.get(sid) else None) for sid in servo_ids}
        if with_imu:
            # 2026-10-24 复盘：普通 READ 单读 200 时该板常 >60ms 晚答甚至不答
            # （timeout/bad_id 大涨），而 sync_read 槽 0 应答实测 100% 及时——
            # 改用只含 200 的独立 sync_read：既走它的快路径，又与舵机帧隔离。
            got.update(BUS.sync_read([imu_bus.IMU_ID], imu_bus.BLOCK_ADDR, imu_bus.BLOCK_LEN) or {})'''


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", help="servo-web 部署目录，例如 ~/servo-web")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    path = os.path.join(os.path.abspath(os.path.expanduser(args.dir)), "server.py")
    if not os.path.isfile(path):
        raise SystemExit(f"缺少 {path}")
    text = read(path)
    if V2 in text and V1 not in text and OLD not in text:
        print("  = 已是分离读取补丁版（独立单 ID sync_read）")
        return 0
    if text.count(V1) == 1:
        pair = (V1, V2)
    elif text.count(OLD) == 1:
        pair = (OLD, NEW)
    else:
        raise PatchError("既不是上游原文，也不是 v1 补丁版，无法定位，中止")
    if args.dry_run:
        print(f"  * dry-run：{'v1→v2' if pair[0] is V1 else '上游→v2'} 匹配唯一（未写入）")
        return 0
    backup = path + time.strftime(".bak-%Y%m%d-%H%M%S")
    shutil.copy2(path, backup)
    write(path, text.replace(pair[0], pair[1]))
    print(f"已写入；备份 {backup}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PatchError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(2)
