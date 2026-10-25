#!/usr/bin/env python3
"""修 servo-web 刷新/重连后的状态同步：
1) 页面打开时读取 40 号扭矩开关，恢复每颗的扭矩勾选；
2) 第一帧状态到达时把滑块/目标对齐到实际读数（此前滑块固定从 2048 开始，
   实际读数在 1198/424 时看起来“滑块不是当前读数”）。

服务端 hello / reconnect 增加 torque 字段；页面 applyTorque() 设置勾选；
update() 第一帧调用 syncSliders()。只改部署副本，幂等，先备份；服务端改动需重启。
用法（板上）：
    python3 servo-web-state-sync.py ~/servo-web --dry-run
    python3 servo-web-state-sync.py ~/servo-web --apply
"""

import argparse
import os
import shutil
import sys
import time

SERVER_FUNC_OLD = "async def ws_endpoint(ws):\n"
SERVER_FUNC_NEW = '''def read_torques(ids):
    """读一次 40 号扭矩开关，页面刷新/重连时恢复勾选；失败返回空，不阻塞页面。"""
    out = {}
    try:
        tq = BUS.sync_read(ids, 40, 1)
        for i in ids:
            v = tq.get(i)
            if v and v[1]:
                out[i] = 1 if v[1][0] else 0
    except Exception as e:
        log(f"读扭矩状态失败：{type(e).__name__}: {e}", "系统", "warn")
    return out


async def ws_endpoint(ws):
'''

HELLO_OLD = '"fake": is_fake(), "logs": LOG[-150:], "cats": LOG_CATS, "dirs": load_dirs(),'
HELLO_NEW = '"fake": is_fake(), "logs": LOG[-150:], "cats": LOG_CATS, "dirs": load_dirs(),\n                                   "torque": read_torques(PRESENT or IDS),'

RECONNECT_OLD = """        return {"type": "reconnect", **r, "port": PORT, "fake": is_fake(), "present": PRESENT,
                "ports": list_ports()}"""
RECONNECT_NEW = """        return {"type": "reconnect", **r, "port": PORT, "fake": is_fake(), "present": PRESENT,
                "torque": read_torques(PRESENT or IDS), "ports": list_ports()}"""

STATE_OLD = "let isServoDemo = false;\n"
STATE_NEW = "let isServoDemo = false;\nlet stateSynced = false;\n"

HELLO_BUILD_OLD = "build(); fillRegSelect();"
HELLO_BUILD_NEW = "build(); applyTorque(m.torque); stateSynced = false; fillRegSelect();"

APPLY_OLD = "function update(states, stats) {\n"
APPLY_NEW = """function applyTorque(map) {
  if (!map) return;
  present.forEach(id => { const t = $('t' + id); if (t) t.checked = map[id] === 1; });
}
function update(states, stats) {
"""

SYNC_OLD = "  if (stats && !isServoDemo) $('busInfo').textContent"
SYNC_NEW = "  if (!stateSynced) { stateSynced = true; syncSliders(); }\n  if (stats && !isServoDemo) $('busInfo').textContent"

RECON_UI_OLD = "if (m.ok) { present = m.present || []; build(); hint(m.msg); }"
RECON_UI_NEW = "if (m.ok) { present = m.present || []; build(); applyTorque(m.torque); stateSynced = false; hint(m.msg); }"

SCAN_UI_OLD = "else if (m.type === 'scan') { present = m.present; build(); }"
SCAN_UI_NEW = "else if (m.type === 'scan') { present = m.present; build(); stateSynced = false; }"


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
    server = os.path.join(root, "server.py")
    index = os.path.join(root, "index.html")
    for p in (server, index):
        if not os.path.isfile(p):
            raise SystemExit(f"缺少 {p}")
    stamp = time.strftime("%Y%m%d-%H%M%S")

    s = read(server)
    s = replace(s, SERVER_FUNC_OLD, SERVER_FUNC_NEW, "read_torques 函数")
    s = replace(s, HELLO_OLD, HELLO_NEW, "hello 带 torque")
    s = replace(s, RECONNECT_OLD, RECONNECT_NEW, "reconnect 带 torque")
    if a.apply:
        shutil.copy2(server, server + f".bak-{stamp}")
        write(server, s)

    h = read(index)
    h = replace(h, STATE_OLD, STATE_NEW, "stateSynced 变量")
    h = replace(h, HELLO_BUILD_OLD, HELLO_BUILD_NEW, "hello 应用 torque")
    h = replace(h, APPLY_OLD, APPLY_NEW, "applyTorque 函数")
    h = replace(h, SYNC_OLD, SYNC_NEW, "首帧同步滑块")
    h = replace(h, RECON_UI_OLD, RECON_UI_NEW, "reconnect 应用 torque")
    h = replace(h, SCAN_UI_OLD, SCAN_UI_NEW, "scan 后重新同步滑块")
    if a.apply:
        shutil.copy2(index, index + f".bak-{stamp}")
        write(index, h)
    print("完成" + ("（dry-run，未写入）" if a.dry_run else "（已写入，服务端改动需重启）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
