#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给部署副本 servo-web 加 Radxa 主机遥测：顶栏 SoC 温度/CPU 频率（2026-10-25）。

服务端：新增 host_stats()（SoC/GPU 温度、CPU 频率、load1，1s 缓存）与 /api/host 路由，
并把 host 字段并入每帧 state 广播。
页面：顶栏新增「SoC xx°C · CPU xxxMHz」——≥75°C 黄（降频区）、≥85°C 红（二级降频），
GPU 温度悬停 SoC 标签可见，load 悬停 CPU 标签可见。与内核 thermal trips（75/85/115°C）对齐。
只改部署副本（先备份），参考库不动。用法：
    python3 servo-web-host-monitor.py ~/servo-web --dry-run|--apply
"""

import argparse
import os
import shutil
import sys
import time


class PatchError(Exception):
    pass


HOST_FUNCS = '''def host_stats():
    """2026-10-25 本机补丁：Radxa 主机遥测（SoC/GPU 温度、CPU 频率、负载），1s 缓存。"""
    import glob
    now = time.monotonic()
    if host_stats.cached is not None and now - host_stats.t < 1.0:
        return host_stats.cached
    out = {}
    zones = {}
    for p in glob.glob("/sys/class/thermal/thermal_zone*"):
        try:
            zones[open(p + "/type").read().strip()] = int(open(p + "/temp").read().strip()) / 1000.0
        except Exception:
            pass
    if "soc-thermal" in zones:
        out["soc_temp"] = round(zones["soc-thermal"], 1)
    if "gpu-thermal" in zones:
        out["gpu_temp"] = round(zones["gpu-thermal"], 1)
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq") as f:
            out["cpu_mhz"] = int(f.read().strip()) // 1000
    except Exception:
        pass
    try:
        out["load1"] = round(os.getloadavg()[0], 2)
    except Exception:
        pass
    host_stats.cached, host_stats.t = out, now
    return out


host_stats.cached, host_stats.t = None, 0.0


async def host_api(request):
    return JSONResponse(host_stats())


async def info(request):'''

INFO_OLD = '''async def info(request):'''

STATE_OLD = '''await broadcast(json.dumps({"type": "state", "t": time.time(), "states": st, "stats": BUS.stats}))'''
STATE_NEW = '''await broadcast(json.dumps({"type": "state", "t": time.time(), "states": st, "stats": BUS.stats, "host": host_stats()}))'''

ROUTE_OLD = '''    Route("/api/info", info),'''
ROUTE_NEW = '''    Route("/api/info", info),
    Route("/api/host", host_api),'''

DISPATCH_OLD = '''    else if (m.type === 'state') update(m.states, m.stats);'''
DISPATCH_NEW = '''    else if (m.type === 'state') { update(m.states, m.stats); if (m.host) showHost(m.host); }'''

SHOWHOST = '''function showHost(h) {   // 2026-10-25 本机补丁：顶栏 Radxa 遥测（对齐内核 trips：75/85/115°C）
  if (h.soc_temp != null) { $('stSoc').textContent = h.soc_temp.toFixed(0) + '°C'; $('stSoc').style.color = h.soc_temp >= 85 ? 'var(--bad)' : h.soc_temp >= 75 ? 'var(--warn)' : 'var(--acc)'; }
  if (h.gpu_temp != null) $('stSoc').title = 'GPU ' + h.gpu_temp.toFixed(0) + '°C';
  if (h.cpu_mhz != null) $('stCpu').textContent = h.cpu_mhz + 'MHz';
  if (h.load1 != null) $('stCpu').title = 'load1 ' + h.load1.toFixed(2);
}'''

VOLT_END_OLD = '''  if (live.length) $('stVolt').textContent = (live.reduce((a, x) => a + x.volt, 0) / live.length).toFixed(1) + ' V';
}'''
VOLT_END_NEW = '''  if (live.length) $('stVolt').textContent = (live.reduce((a, x) => a + x.volt, 0) / live.length).toFixed(1) + ' V';
}
''' + SHOWHOST

TOPBAR_OLD = '''<span>电压 <b id="stVolt">–</b></span></span>'''
TOPBAR_NEW = '''<span>电压 <b id="stVolt">–</b></span><span>SoC <b id="stSoc" title="Radxa SoC 温度；≥75°C 黄=降频区、≥85°C 红；GPU 温度悬停可见">–</b></span><span>CPU <b id="stCpu">–</b></span></span>'''


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


def replace(text, old, new, label, count=1):
    n = text.count(old)
    if n == 0:
        if new in text:
            print(f"  = {label}：已打过")
            return text
        raise PatchError(f"{label}：找不到目标文本")
    if n != count:
        raise PatchError(f"{label}：匹配 {n} 处（预期 {count}）")
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
    sp = os.path.join(root, "server.py")
    ih = os.path.join(root, "index.html")
    for p in (sp, ih):
        if not os.path.isfile(p):
            raise SystemExit(f"缺少 {p}")

    stext = read(sp)
    stext = replace(stext, INFO_OLD, HOST_FUNCS, "server.py host_stats()+/api/host 函数")
    stext = replace(stext, STATE_OLD, STATE_NEW, "server.py state 帧并入 host")
    stext = replace(stext, ROUTE_OLD, ROUTE_NEW, "server.py 路由注册")

    itext = read(ih)
    itext = replace(itext, DISPATCH_OLD, DISPATCH_NEW, "index.html state 分发挂 showHost")
    itext = replace(itext, VOLT_END_OLD, VOLT_END_NEW, "index.html showHost 函数")
    itext = replace(itext, TOPBAR_OLD, TOPBAR_NEW, "index.html 顶栏 SoC/CPU")

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
