# -*- coding: utf-8 -*-
"""Radxa Zero 3W 串口控制台 1500000 → 115200 切换工具（DAPLink 克隆防丢字/防挂死版）。

实测教训(2026-10-14): 克隆 CDC 累计输出约 150-200 字节即挂死(假在线, 需拔插)。
因此 modify 阶段输出压到约 6 字节(仅 M1/M2 标记), 校验全部移到 115200 的 verify 阶段。

用法:
  python tools/serial-baud-switch.py --stage modify   # 备份+改两处+daemon-reload+立即重启(输出极小)
  python tools/serial-baud-switch.py --stage verify   # 115200 登录 radxa/radxa + 校验文件 + WiFi状态等
  python tools/serial-baud-switch.py --stage probe    # 只读探测(1.5M, 有挂死风险, 仅供诊断)

修改内容:
  /boot/extlinux/extlinux.conf            1500000→115200 (内核 cmdline, 含两个 label)
  /lib/systemd/system/serial-getty@.service 1500000→115200 (getty 波特率)
  各留 .bak 备份; U-Boot 波特率不改(开机头 2 秒输出在 115200 下为乱码, 已知代价)。
"""
import argparse
import datetime
import sys
import time
from pathlib import Path

import serial

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = (REPO_ROOT / "docs" / "references" / "瑞莎开发板存储线刷" / "serial-logs")
USER, PASS = "radxa", "radxa"
EXTLINUX = "/boot/extlinux/extlinux.conf"
GETTY_TPL = "/lib/systemd/system/serial-getty@.service"


def ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


class Session:
    def __init__(self, log, port="COM3", baud=1500000):
        self.log = log
        print(f"[{ts()}] 打开 {port} @ {baud} ...", flush=True)
        self.ser = serial.Serial(port, baud, timeout=1, write_timeout=6)

    def send(self, text, size=30, pause=0.08):
        for i in range(0, len(text), size):
            self.ser.write(text[i:i + size].encode())
            self.ser.flush()
            time.sleep(pause)

    def read_until(self, marker: bytes, seconds: float):
        buf = b""
        t0 = time.time()
        while time.time() - t0 < seconds:
            d = self.ser.read(512)
            if d:
                buf += d
                print(d.decode("utf-8", "replace"), end="", flush=True)
                self.log.write(f"[RX {ts()}] {d!r}\n".encode("utf-8"))
                self.log.flush()
                if marker and marker in buf:
                    time.sleep(0.8)
                    d2 = self.ser.read(512)
                    if d2:
                        buf += d2
                        print(d2.decode("utf-8", "replace"), end="", flush=True)
                        self.log.write(f"[RX {ts()}] {d2!r}\n".encode("utf-8"))
                    return buf, True
        return buf, False

    def run(self, cmd, marker, seconds):
        print(f"\n[{ts()}] TX: {cmd}", flush=True)
        self.log.write(f"[TX {ts()}] {cmd}\n".encode("utf-8"))
        self.send(cmd + "\r\n")
        return self.read_until(marker.encode() if marker else None, seconds)

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


def stage_probe(s: Session) -> int:
    s.run("grep -o 'console=[^ ]*' " + EXTLINUX + "; echo P1END", "P1END", 10)
    s.run("grep -n 1500000 " + GETTY_TPL + " 2>/dev/null | head -3; echo P2END", "P2END", 10)
    s.run("ls /etc/systemd/system/serial-getty@ttyFIQ0.service.d 2>/dev/null; echo P3END", "P3END", 10)
    return 0


def stage_modify(s: Session) -> int:
    """一条 sudo 命令完成: 备份→改两处→daemon-reload→1 秒后重启。
    输出仅 M1/M2 两个标记(~6B)。成功与否最终由 verify 阶段裁决。"""
    payload = (
        "echo " + PASS + " | sudo -S -p '' sh -c '"
        "cp -n " + EXTLINUX + " " + EXTLINUX + ".bak"
        "&&sed -i s/1500000/115200/g " + EXTLINUX + "&&echo M1;"
        "cp -n " + GETTY_TPL + " " + GETTY_TPL + ".bak"
        "&&sed -i s/1500000/115200/g " + GETTY_TPL + "&&echo M2;"
        "systemctl daemon-reload;sleep 1;reboot'"
    )
    buf, _ = s.run(payload, "M2", 15)
    print(f"\n[{ts()}] M1={'M1' in buf!r} M2={b'M2' in buf!r}; 重启已并入本命令, "
          f"60s 后无论标记是否可见都进入 115200 验证(板子重启期间串口输出会冲挂克隆属预期)。", flush=True)
    return 0


def stage_verify(args) -> int:
    log_path = LOG_DIR / f"verify115200-{datetime.datetime.now():%Y%m%d-%H%M%S}.log"
    with open(log_path, "wb") as log:
        print(f"\n[{ts()}] ===== 115200 登录验证 =====", flush=True)
        s = Session(log, args.port, 115200)
        try:
            t0 = time.time()
            hit = False
            while time.time() - t0 < args.wait:
                buf, hit = s.read_until(b"login:", 5)
                if hit:
                    break
                s.send("\r\n")
            if not hit:
                print(f"\n[{ts()}] ** 未等到 login: **", flush=True)
                return 5
            print(f"\n[{ts()}] -- 见登录提示, 开始登录 --", flush=True)
            s.run(USER, "assword", 10)
            s.run(PASS, "$", 12)
            checks = [
                ("grep -o 'console=[^ ]*' " + EXTLINUX + "; echo V1END", "V1END"),
                ("grep -c 115200 " + GETTY_TPL + "; ls /etc/systemd/system/serial-getty@ttyFIQ0.service.d 2>/dev/null | wc -l; echo V2END", "V2END"),
                ("uname -r; uptime | cut -d, -f1; echo V3END", "V3END"),
                ("nmcli --fields DEVICE,TYPE,STATE,CONNECTION dev status; echo V4END", "V4END"),
                ("ip -br a | grep -v '^lo'; iw dev wlan0 link 2>/dev/null | head -4; echo VEND", "VEND"),
            ]
            ok = True
            for cmd, marker in checks:
                buf, hit = s.run(cmd, marker, 25)
                if not hit:
                    print(f"\n[{ts()}] !! {marker} 超时", flush=True)
                    ok = False
            print(f"\n[{ts()}] 验证{'完成' if ok else '部分超时'}; 日志 {log_path}", flush=True)
            return 0 if ok else 6
        finally:
            s.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="串口波特率切换 1.5M→115200(分块防丢字)")
    ap.add_argument("--stage", default="modify", choices=["probe", "modify", "verify"])
    ap.add_argument("--port", default="COM3")
    ap.add_argument("--wait", type=int, default=180, help="verify 等登录提示秒数")
    args = ap.parse_args()

    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"baud-switch-{datetime.datetime.now():%Y%m%d-%H%M%S}.log"

    if args.stage == "verify":
        return stage_verify(args)

    with open(log_path, "wb") as log:
        print(f"日志: {log_path}", flush=True)
        try:
            s = Session(log, args.port, 1500000)
        except Exception as e:
            print(f"打开串口失败: {e}\n→ 写超时=假在线需拔插; 拒绝访问=PuTTY/其他程序占用。")
            return 2
        try:
            if args.stage == "probe":
                return stage_probe(s)
            if args.stage == "modify":
                stage_modify(s)
        finally:
            s.close()
    print(f"\n[{ts()}] 等 60s 让板子完成重启...", flush=True)
    time.sleep(60)
    return stage_verify(args)


if __name__ == "__main__":
    sys.exit(main())
