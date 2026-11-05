# -*- coding: utf-8 -*-
"""串口日志抓取工具（Radxa Zero 3W 启动日志定位用，通用亦可）。

用法:
  python tools/serial-log.py                 # 列出 COM 口并交互选择
  python tools/serial-log.py -p COM5         # 指定串口, 默认 1500000 8N1
  python tools/serial-log.py -p COM5 -b 115200 -o D:\\logs

Radxa Zero 3W 调试串口: 排针 8(TX)/10(RX)/9(GND), 1500000 8N1 无流控。
抓日志只接 板8->适配器RX 与 GND 共地 两根线即可; Ctrl+C 停止后打印日志路径。
"""
import argparse
import datetime
import sys
import time
from pathlib import Path

import serial
import serial.tools.list_ports

RADXA_BAUD = 1500000
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "docs" / "references" / "瑞莎开发板存储线刷" / "serial-logs"


def ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def pick_port(arg_port: str | None) -> str | None:
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("未发现任何 COM 口。请插入 DAPLink/USB 串口适配器后重试。")
        return None
    print("可用串口:")
    for i, p in enumerate(ports, 1):
        print(f"  {i}) {p.device}  |  {p.description}  |  {p.hwid}")
    if arg_port:
        return arg_port
    hint = "DAPLink 通常显示为 'DAPLink CDC UART' / 'mbed Composite Device'"
    choice = input(f"输入序号或 COM 号(如 COM5), 直接回车退出 [{hint}]: ").strip()
    if not choice:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(ports):
        return ports[int(choice) - 1].device
    return choice.upper() if choice.lower().startswith("com") else choice


def main() -> int:
    ap = argparse.ArgumentParser(description="串口日志抓取(实时打印+落盘)")
    ap.add_argument("-p", "--port", help="串口名, 如 COM5; 省略则交互选择")
    ap.add_argument("-b", "--baud", type=int, default=RADXA_BAUD, help=f"波特率, 默认 {RADXA_BAUD}")
    ap.add_argument("-o", "--out", default=str(DEFAULT_OUT), help="日志输出目录")
    args = ap.parse_args()

    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    port = pick_port(args.port)
    if not port:
        return 1

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / f"serial-{datetime.datetime.now():%Y%m%d-%H%M%S}.log"

    header = (f"=== serial-log 开始 {datetime.datetime.now():%Y-%m-%d %H:%M:%S} | "
              f"{port} @ {args.baud} 8N1 ===\n")
    print(header, end="", flush=True)
    with open(log_path, "wb") as f:
        f.write(header.encode("utf-8"))
        f.flush()
        print("抓取中... Ctrl+C 停止。USB 适配器掉线时自动重连（需设备自行重新枚举）。")
        ser = None
        try:
            while True:
                if ser is None:
                    try:
                        ser = serial.Serial(port=port, baudrate=args.baud, bytesize=8,
                                            parity=serial.PARITY_NONE, stopbits=1, timeout=0.5)
                    except serial.SerialException as e:
                        print(f"[{ts()}] 串口未就绪({e})，2s 后重试...")
                        time.sleep(2)
                        continue
                try:
                    line = ser.readline()  # 遇 \n 或 0.5s 超时返回
                except serial.SerialException as e:
                    print(f"[{ts()}] 串口掉线: {e} — 等待重新枚举...", flush=True)
                    try:
                        ser.close()
                    except Exception:
                        pass
                    ser = None
                    time.sleep(2)
                    continue
                if not line:
                    continue
                text = line.decode("utf-8", "replace").rstrip("\r\n")
                stamped = f"[{ts()}] {text}\n"
                print(stamped, end="", flush=True)
                f.write(stamped.encode("utf-8"))
                f.flush()
        except KeyboardInterrupt:
            pass
        finally:
            if ser is not None:
                try:
                    ser.close()
                except Exception:
                    pass
            tail = f"=== 结束 {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ===\n"
            f.write(tail.encode("utf-8"))
            f.flush()
    print(f"\n日志已保存: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
