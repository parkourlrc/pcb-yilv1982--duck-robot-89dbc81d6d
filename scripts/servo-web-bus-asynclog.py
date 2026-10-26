#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""servo-web 总线帧异步日志（2026-10-27）：bus_trace 改入队 + 独立 writer 线程写盘。

背景：要全量记录总线收发帧（含 sync_read/sync_write 轮询流量）时，原 bus_trace→log()
路径在**串口锁内**每行 open/write/close 文件 + print(flush=True)，正常 1~3ms、eMMC 延迟
尾部可达几十 ms——直接插进"发请求→读应答"的间隙，人为制造丢帧（测量干扰被测系统）；
170 行/s 的量还会逼近 journald 限流。

修法（feetech.py 不动）：
- bus_trace 只做 queue.put_nowait((time.time(), 行))——µs 级、永不阻塞；
- daemon 线程 servo-web-buslog 批量取行写 logs/bus-日期.log（毫秒时间戳、行缓冲、
  跨天自动换文件），与串口锁路径完全解耦；队列 20000 行（约 2 分钟余量），
  满则丢新行并记丢弃计数，绝不反压总线；
- open_bus 里运行时 bus.trace_skip.discard(SYNC_READ/SYNC_WRITE) 打开同步帧记录。
[总线][调试] 行自本补丁起从 servo-web-日期.log 迁至 bus-日期.log（页面本就不显示这类行）。

用法：
    python3 servo-web-bus-asynclog.py ~/servo-web --dry-run
    python3 servo-web-bus-asynclog.py ~/servo-web --apply
"""
import argparse
import os
import py_compile
import shutil
import sys
import time


class PatchError(Exception):
    pass


OLD_TRACE = '''def bus_trace(line):
    """串口收发的原始字节，只进日志文件（页面不显示，不然刷屏）。
    出问题时 grep 日志文件里的 → / ← 就能还原当时总线上到底发生了什么。"""
    log(line, "总线", "debug")'''

NEW_TRACE = '''# ---- 2026-10-27 本机补丁：总线帧异步日志（writer 线程与串口锁路径解耦）----
import queue as _queue

_bus_q = _queue.Queue(maxsize=20000)
_bus_q_dropped = [0]


def bus_trace(line):
    """串口收发的原始字节，异步写 logs/bus-日期.log（页面不显示，不然刷屏）。
    2026-10-27 起改为入队：原实现同步走 log()（每行 open/write/close + print(flush)
    都在串口锁内，全量记录时 eMMC 延迟尾部会插进收发间隙、人为制造丢帧）。"""
    try:
        _bus_q.put_nowait((time.time(), line))
    except _queue.Full:
        _bus_q_dropped[0] += 1


def _bus_log_writer():
    day, f = None, None
    while True:
        try:
            item = _bus_q.get(timeout=0.5)
        except _queue.Empty:
            continue
        batch = [item]
        while len(batch) < 5000:
            try:
                batch.append(_bus_q.get_nowait())
            except _queue.Empty:
                break
        try:
            today = time.strftime("%Y-%m-%d")
            if f is None or today != day:
                if f is not None:
                    f.close()
                os.makedirs(LOG_DIR, exist_ok=True)
                f = open(os.path.join(LOG_DIR, f"bus-{today}.log"), "a",
                         encoding="utf-8", buffering=1)
                day = today
            if _bus_q_dropped[0]:
                print(f"{time.strftime('%H:%M:%S')} # 队列满丢弃 {_bus_q_dropped[0]} 行", file=f)
                _bus_q_dropped[0] = 0
            for t, line in batch:
                ms = int(t * 1000) % 1000
                print(f"{time.strftime('%H:%M:%S', time.localtime(t))}.{ms:03d} {line}", file=f)
        except Exception as e:
            try:
                print(f"bus-log writer 异常：{type(e).__name__}: {e}", flush=True)
            except Exception:
                pass


threading.Thread(target=_bus_log_writer, name="servo-web-buslog", daemon=True).start()'''

OLD_HOOK = '''    bus.trace = bus_trace'''

NEW_HOOK = '''    bus.trace = bus_trace
    # 2026-10-27 本机补丁：全量记录同步读/写帧（上游 trace_skip 默认排除它们）；
    # 写盘走 bus_trace 的异步 writer。FakeBus 无 trace_skip 时跳过。
    if hasattr(bus, "trace_skip"):
        bus.trace_skip.discard(feetech.SYNC_READ)
        bus.trace_skip.discard(feetech.SYNC_WRITE)'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deploy_dir", help="板上部署目录，如 ~/servo-web")
    ap.add_argument("--apply", action="store_true", help="实际写入（默认 dry-run）")
    args = ap.parse_args()
    path = os.path.join(os.path.expanduser(args.deploy_dir), "server.py")
    src = open(path, encoding="utf-8").read()

    for name, old, new in (("bus_trace", OLD_TRACE, NEW_TRACE), ("hook", OLD_HOOK, NEW_HOOK)):
        n = src.count(old)
        print(f"[{name}] 匹配 {n} 处（期望 1）")
        if n != 1:
            raise PatchError(f"{name} 匹配数不是 1，中止")
        if not args.apply:
            continue
        src = src.replace(old, new)

    if not args.apply:
        print("dry-run 通过，未写入。加 --apply 执行。")
        return

    bak = path + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(path, bak)
    open(path, "w", encoding="utf-8", newline="").write(src)
    py_compile.compile(path, doraise=True)
    print(f"备份 {bak}")
    print("写入并 py_compile 通过")


if __name__ == "__main__":
    main()
