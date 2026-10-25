#!/usr/bin/env python3
"""给 servo-web 部署副本的 3D 模型加缓存刷新，并在 HUD 显示 30/31 的实际模型映射。

背景：页面 HTML 是 no-store，但 model/model.json 原来只带 ETag/Last-Modified。
WebSocket 重连后数据面板会更新，3D 模型却可能还是打开页面时缓存的旧文件，
表现就是“数据板对、3D 的 30/31 反了”。这个脚本：
1) /model 文件响应加 Cache-Control: no-store；
2) 页面 fetch 加 ?v= 版本参数，强制拿新 URL；
3) HUD 显示当前加载模型里 30/31 各是什么关节，方便确认浏览器到底用了哪份模型。

用法（板上）：
    python3 servo-web-model-cache.py ~/servo-web --dry-run
    python3 servo-web-model-cache.py ~/servo-web --apply
"""

import argparse
import os
import shutil
import sys
import time

SERVER_OLD = "    return FileResponse(path)\n"
SERVER_NEW = '    return FileResponse(path, headers={"Cache-Control": "no-store, max-age=0"})\n'

FETCH_OLD = "fetch('model/model.json')"
FETCH_NEW = "fetch('model/model.json?v=20261022-2')"
BIN_OLD = "fetch('model/meshes.bin')"
BIN_NEW = "fetch('model/meshes.bin?v=20261022-2')"

HUD_OLD = "  hud.textContent = `模型：${mj.source}（${Object.keys(joints).length} 个关节跟随舵机${(mj.notes || []).length ? '；' + mj.notes.join('；') : ''}）`;"
HUD_NEW = "  hud.textContent = `模型：${mj.source}（30→${joints[30] ? joints[30].name : '—'}，31→${joints[31] ? joints[31].name : '—'}；${Object.keys(joints).length} 个关节跟随舵机${(mj.notes || []).length ? '；' + mj.notes.join('；') : ''}）`;"


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
    if new in text and old not in text:
        print(f"  = {label}：已处理")
        return text
    if text.count(old) != 1:
        print(f"  ! {label}：匹配 {text.count(old)} 处，跳过")
        return text
    print(f"  * {label}")
    return text.replace(old, new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", help="servo-web 部署目录，例如 ~/servo-web")
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

    dry = not a.apply
    print(f"目标：{root}")
    if not dry:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for p in (server, index):
            bak = p + f".bak-{stamp}"
            shutil.copy2(p, bak)
            print(f"备份：{bak}")

    s = read(server)
    s = replace(s, SERVER_OLD, SERVER_NEW, "server.py /model no-store")
    if not dry:
        write(server, s)

    h = read(index)
    h = replace(h, FETCH_OLD, FETCH_NEW, "index.html model.json 版本参数")
    h = replace(h, BIN_OLD, BIN_NEW, "index.html meshes.bin 版本参数")
    h = replace(h, HUD_OLD, HUD_NEW, "index.html HUD 显示 30/31 映射")
    if not dry:
        write(index, h)
    print("完成" + ("（dry-run，未写入）" if dry else "（已写入）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
