# -*- coding: utf-8 -*-
"""串口登录全流程测试（Radxa Zero 3W 串口"登录后没反应"定位用）。

用法:
  python tools/serial-login-test.py              # 默认 COM3 @ 1500000
  python tools/serial-login-test.py -p COM5 -u radxa -w radxa

流程: 开口 → 敲回车探提示 → 见 login: 输用户名 → 见 Password: 输密码
      → 登录后持续收 15 秒并逐字节落盘（带时间戳）→ 最后发 echo OK 验交互。
每一步超时会如实标注 TIMEOUT 而不是卡死; 所有原始字节以 repr 记录, 乱码可辨。
"""
import argparse
import datetime
import sys
import time
from pathlib import Path

import serial

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG = (REPO_ROOT / "docs" / "references" / "瑞莎开发板存储线刷"
               / "serial-logs" / f"login-test-{datetime.datetime.now():%Y%m%d-%H%M%S}.log")


def ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def wait_for(ser, pattern: str, seconds: float, log) -> bytes:
    """收数据直到出现 pattern(已收字节里) 或超时。返回累计收到的字节。"""
    buf = b""
    t0 = time.time()
    while time.time() - t0 < seconds:
        d = ser.read(256)
        if d:
            buf += d
            print(f"[{ts()}] RX {repr(d)}", flush=True)
            log.write(f"[{ts()}] RX {repr(d)}\n".encode("utf-8"))
            log.flush()
            if pattern.encode() in buf:
                return buf
    print(f"[{ts()}] -- 等待 {pattern!r} {seconds}s 超时, 已收 {len(buf)}B --", flush=True)
    return buf


def send(ser, data: bytes, label: str, log) -> None:
    print(f"[{ts()}] TX {label}: {repr(data)}", flush=True)
    log.write(f"[{ts()}] TX {label}: {repr(data)}\n".encode("utf-8"))
    ser.write(data)
    ser.flush()


def main() -> int:
    ap = argparse.ArgumentParser(description="串口登录全流程测试")
    ap.add_argument("-p", "--port", default="COM3")
    ap.add_argument("-b", "--baud", type=int, default=1500000)
    ap.add_argument("-u", "--user", default="radxa")
    ap.add_argument("-w", "--password", default="radxa")
    args = ap.parse_args()

    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    DEFAULT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(DEFAULT_LOG, "wb") as log:
        hdr = (f"=== login-test {datetime.datetime.now():%Y-%m-%d %H:%M:%S} | "
               f"{args.port} @ {args.baud} 8N1 ===\n")
        print(hdr, end="", flush=True)
        log.write(hdr.encode("utf-8"))

        try:
            ser = serial.Serial(args.port, args.baud, timeout=1, write_timeout=5)
        except Exception as e:
            print(f"打开 {args.port} 失败: {e}")
            return 2
        print(f"[{ts()}] {args.port} 已打开 (写通道即测)", flush=True)

        # 第 0 步: 写通道自检——假在线时 2 字节都发不出去
        try:
            send(ser, b"\r\n", "回车探针", log)
        except Exception as e:
            print(f"[{ts()}] ** 写超时/失败: {e} —— DAPLink 假在线, 拔插后重试 **", flush=True)
            return 3

        # 第 1 步: 看有没有 login 提示或残存活 shell
        buf = wait_for(ser, "login:", 6, log)
        low = buf.lower()
        if b"$" in low or b"#" in low or b"radxa@" in low:
            print(f"[{ts()}] ** 检测到疑似已登录 shell（上次会话还活着）, 跳过登录 **", flush=True)
        elif b"login" in low:
            send(ser, f"{args.user}\r\n".encode(), "用户名", log)
            wait_for(ser, "assword", 8, log)   # Password/password
            send(ser, f"{args.password}\r\n".encode(), "密码", log)
        else:
            print(f"[{ts()}] 6 秒内未见 login 提示（静默/乱码/已在 shell）, 继续尝试登录流程", flush=True)
            send(ser, f"{args.user}\r\n".encode(), "用户名(盲发)", log)
            wait_for(ser, "assword", 6, log)
            send(ser, f"{args.password}\r\n".encode(), "密码(盲发)", log)

        # 第 2 步: 登录后收 15 秒——"没反应"问题就发生在这段
        print(f"[{ts()}] === 登录后输出, 收 15 秒 ===", flush=True)
        got = wait_for(ser, "$", 15, log)
        print(f"[{ts()}] 此段共收 {len(got)} 字节", flush=True)

        # 第 3 步: 交互验证
        try:
            send(ser, b"echo SERIAL-OK-$((9+1))\r\n", "交互验证", log)
        except Exception as e:
            print(f"[{ts()}] ** 交互验证发送失败: {e} **", flush=True)
            return 4
        wait_for(ser, "SERIAL-OK-10", 8, log)

        ser.close()
        tail = f"=== 结束 {datetime.datetime.now():%H:%M:%S} ===\n"
        log.write(tail.encode("utf-8"))
        print(f"\n日志: {DEFAULT_LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
