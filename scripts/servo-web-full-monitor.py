#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""servo-web 常驻监控：随服务启动、每秒实时落盘、风暴/掉线/ID 异常自动记事件（2026-10-25）。

服务端：monitor 线程每秒写 logs/monitor-YYYYMMDD.csv（主机 SoC/GPU/频率/负载 + 每颗电压/
温度/电流汇总 + 总线统计 + 分 ID 丢帧 TOP + UART 驱动错误计数 TIOCICOUNTER）；事件行：
STORM_START/STORM_END/ALL_OFFLINE/ID_SET_CHANGE；stream 把最新状态帧喂给监控并在
state 广播中附带 mon 字段。
页面：顶栏新增「最低电压」与会话值着色、「监控✓行数·事件N」芯片（悬停见 CSV 名、
丢帧 TOP、UART 错误）。
依赖 servo-web-host-monitor.py（先打）。只改部署副本，先备份。用法：
    python3 servo-web-full-monitor.py ~/servo-web --dry-run|--apply
"""

import argparse
import os
import shutil
import sys
import time


class PatchError(Exception):
    pass


MON_BLOCK = '''# ── 2026-10-25 本机补丁：常驻监控线程（每秒实时落盘 + 风暴/掉线/ID 异常事件） ──
MON = {"last": {}, "miss": {}, "events": 0, "rows": 0, "csv": None, "uart": None}


def _mon_uart():
    """TIOCICOUNTER：串口驱动级错误计数（frame/parity/break/overrun），不可用返回 None。"""
    try:
        import fcntl
        import struct
        ser = getattr(BUS, "ser", None)
        if ser is None or not getattr(ser, "is_open", False):
            return None
        v = struct.unpack("10i", fcntl.ioctl(ser.fileno(), 0x545E, bytearray(40)))
        return {"rx": v[4], "tx": v[5], "fe": v[6], "pe": v[7], "brk": v[8], "oe": v[9]}
    except Exception:
        return None


def monitor_row(event=""):
    h = host_stats()
    st = MON["last"].get("st", {})
    live = {k: v for k, v in st.items() if v}
    volts = [v.get("volt") for v in live.values() if v.get("volt")]
    temps = [v.get("temp") for v in live.values() if v.get("temp")]
    cur = [v.get("current_ma") for v in live.values() if v.get("current_ma") is not None]
    stats = BUS.stats if hasattr(BUS, "stats") else {}
    miss = ",".join(f"{k}:{v}" for k, v in sorted(MON["miss"].items(), key=lambda x: -x[1])[:8] if v)
    u = MON["uart"] or {}
    return [time.strftime("%Y-%m-%d %H:%M:%S"), h.get("soc_temp", ""), h.get("gpu_temp", ""),
            h.get("cpu_mhz", ""), h.get("load1", ""), len(live),
            min(volts) if volts else "", round(sum(volts) / len(volts), 2) if volts else "",
            max(temps) if temps else "", round(sum(cur)) if cur else "",
            stats.get("tx", ""), stats.get("rx_ok", ""), stats.get("timeout", ""),
            stats.get("bad_checksum", ""), stats.get("bad_id", ""),
            u.get("fe", ""), u.get("pe", ""), u.get("oe", ""), miss, event]


def monitor_loop():
    import csv as _csv
    os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
    path = os.path.join(HERE, "logs", "monitor-" + time.strftime("%Y%m%d") + ".csv")
    MON["csv"] = path
    new = not os.path.exists(path)
    f = open(path, "a", buffering=1, encoding="utf-8", newline="")
    w = _csv.writer(f)
    if new:
        w.writerow(["time", "soc_c", "gpu_c", "cpu_mhz", "load1", "online", "v_min", "v_avg",
                    "t_max", "i_sum_ma", "tx", "rx_ok", "timeout", "bad_ck", "bad_id",
                    "uart_fe", "uart_pe", "uart_oe", "miss_top", "event"])
        f.flush()
    prev = {"to": 0, "online": None, "ids": None, "storm": False}
    while True:
        try:
            MON["uart"] = _mon_uart()
            st = MON["last"].get("st", {})
            fresh = MON["last"].get("t", 0) and time.time() - MON["last"]["t"] < 2
            live = {k: v for k, v in st.items() if v}
            if fresh:
                for sid, v in st.items():
                    if v is None:
                        MON["miss"][sid] = MON["miss"].get(sid, 0) + 1
            stats = BUS.stats if hasattr(BUS, "stats") else {}
            event = ""
            to_now = stats.get("timeout", 0)
            rate = to_now - prev["to"]
            prev["to"] = to_now
            ids_now = tuple(sorted(k for k, v in st.items() if v)) if st else None
            if fresh and live and rate >= 15 and not prev["storm"]:
                event = "STORM_START"
                prev["storm"] = True
                log(f"监控：检测到总线风暴（1s 超时 +{rate}），快照见 {os.path.basename(path)}", "总线", "warn")
            elif prev["storm"] and rate == 0:
                prev["storm"] = False
                event = "STORM_END"
            if fresh and prev["online"] and len(live) == 0:
                event = (event + ";" if event else "") + "ALL_OFFLINE"
                log("监控：全部舵机无应答", "总线", "error")
            if fresh and len(live) > 0:
                prev["online"] = len(live)
            if ids_now and prev["ids"] and ids_now != prev["ids"]:
                event = (event + ";" if event else "") + "ID_SET_CHANGE"
                log(f"监控：在线 ID 集合变化 {list(ids_now)}", "系统", "error")
            if ids_now:
                prev["ids"] = ids_now
            w.writerow(monitor_row(event))
            if event:
                MON["events"] += 1
            MON["rows"] += 1
            f.flush()
        except Exception as e:
            try:
                log(f"监控线程异常：{type(e).__name__}: {e}", "系统", "warn")
            except Exception:
                pass
        time.sleep(1)


def start_monitor():
    threading.Thread(target=monitor_loop, name="servo-web-monitor", daemon=True).start()


async def info(request):'''

INFO_OLD = '''async def info(request):'''

BCAST_OLD = '''                await broadcast(json.dumps({"type": "state", "t": time.time(), "states": st, "stats": BUS.stats, "host": host_stats()}))'''
BCAST_NEW = '''                MON["last"] = {"t": time.time(), "st": st}
                await broadcast(json.dumps({"type": "state", "t": time.time(), "states": st, "stats": BUS.stats,
                                            "host": host_stats(),
                                            "mon": {"rows": MON["rows"], "events": MON["events"],
                                                    "csv": os.path.basename(MON["csv"] or ""),
                                                    "miss": dict(sorted(MON["miss"].items(), key=lambda x: -x[1])[:6]),
                                                    "uart": MON["uart"]}}))'''

LIFE_OLD = '''    tasks = [asyncio.create_task(stream())]'''
LIFE_NEW = '''    tasks = [asyncio.create_task(stream())]
    start_monitor()   # 2026-10-25 本机补丁：常驻监控线程（每秒实时落盘）'''

DISP_OLD = '''    else if (m.type === 'state') { update(m.states, m.stats); if (m.host) showHost(m.host); }'''
DISP_NEW = '''    else if (m.type === 'state') { update(m.states, m.stats); if (m.host) showHost(m.host); if (m.mon) showMon(m.mon); }'''

VMIN_OLD = '''  if (live.length) $('stVolt').textContent = (live.reduce((a, x) => a + x.volt, 0) / live.length).toFixed(1) + ' V';
}'''
VMIN_NEW = '''  if (live.length) $('stVolt').textContent = (live.reduce((a, x) => a + x.volt, 0) / live.length).toFixed(1) + ' V';
  if (live.length) { const vm = Math.min(...live.map(x => x.volt)); if (window._vmin === undefined || vm < window._vmin) { window._vmin = vm; $('stVmin').textContent = vm.toFixed(1) + ' V'; $('stVmin').style.color = vm < 6.6 ? 'var(--bad)' : vm < 7.0 ? 'var(--warn)' : 'var(--acc)'; } }
}'''

SHOWMON = '''

function showMon(mon) {   // 2026-10-25 本机补丁：监控落盘状态（事件黄标、正常绿标）
  if (mon.rows != null) {
    $('stMon').textContent = mon.events ? `监控✓${mon.rows}行·事件${mon.events}` : `监控✓${mon.rows}行`;
    $('stMon').style.color = mon.events ? 'var(--warn)' : 'var(--acc)';
  }
  const missTxt = mon.miss && Object.keys(mon.miss).length ? ' 丢帧TOP ' + Object.entries(mon.miss).map(([k, v]) => `#${k}×${v}`).join(' ') : '';
  const uart = mon.uart ? ` UART错误 fe=${mon.uart.fe || 0} pe=${mon.uart.pe || 0} oe=${mon.uart.oe || 0}` : '';
  $('stMon').title = (mon.csv ? 'CSV ' + mon.csv : '') + missTxt + uart;
}'''

SHOWHOST_END_OLD = '''  if (h.load1 != null) $('stCpu').title = 'load1 ' + h.load1.toFixed(2);
}'''
SHOWHOST_END_NEW = '''  if (h.load1 != null) $('stCpu').title = 'load1 ' + h.load1.toFixed(2);
}''' + SHOWMON

TOPBAR_OLD = '''<span>CPU <b id="stCpu">–</b></span></span>'''
TOPBAR_NEW = '''<span>CPU <b id="stCpu">–</b></span><span>最低 <b id="stVmin" title="本会话舵机电压最低值（<6.6V 红、<7.0V 黄）">–</b></span><span id="stMon" title="常驻监控：CSV 落盘行数与事件数；悬停见丢帧TOP与UART错误">监控–</span></span>'''


def read(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8").replace("\r\n", "\n")


def write(path, text):
    with open(path, "rb") as f:
        raw = f.read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    with open(path, "wb") as f:
        f.write(text.replace("\n", nl).encode("utf-8"))


def replace(text, old, new, label):
    n = text.count(old)
    if n == 0:
        if new in text:
            print(f"  = {label}：已打过")
            return text
        raise PatchError(f"{label}：找不到目标文本")
    if n != 1:
        raise PatchError(f"{label}：匹配 {n} 处（预期 1）")
    print(f"  * {label}")
    return text.replace(old, new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(os.path.expanduser(args.dir))
    sp, ih = os.path.join(root, "server.py"), os.path.join(root, "index.html")
    for p in (sp, ih):
        if not os.path.isfile(p):
            raise SystemExit(f"缺少 {p}")

    stext = read(sp)
    stext = replace(stext, INFO_OLD, MON_BLOCK, "server.py 监控线程模块")
    stext = replace(stext, BCAST_OLD, BCAST_NEW, "server.py stream 喂监控+mon 字段")
    stext = replace(stext, LIFE_OLD, LIFE_NEW, "server.py lifespan 启动监控线程")

    itext = read(ih)
    itext = replace(itext, DISP_OLD, DISP_NEW, "index.html 分发挂 showMon")
    itext = replace(itext, VMIN_OLD, VMIN_NEW, "index.html 会话最低电压")
    itext = replace(itext, SHOWHOST_END_OLD, SHOWHOST_END_NEW, "index.html showMon 函数")
    itext = replace(itext, TOPBAR_OLD, TOPBAR_NEW, "index.html 顶栏 最低/监控")

    if args.dry_run:
        print("完成（dry-run，未写入）")
        return 0
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for p, t in ((sp, stext), (ih, itext)):
        shutil.copy2(p, p + ".bak-" + stamp)
        write(p, t)
    print(f"已写入；备份 server.py/index.html .bak-{stamp}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PatchError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(2)
