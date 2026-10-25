#!/usr/bin/env python3
"""让 servo-web 的方向表变更广播给所有已打开页面。

问题：`set_dir` 的回复原来只发回点击的那个 WebSocket。开两个标签页时，
一个页面点 ± 会写 directions.json，另一个页面仍保留自己的旧 dirs；
切回旧页面就像“方向又反回去了”。方向表是全局状态，应该广播。

用法（板上）：
    python3 servo-web-dirs-sync.py ~/servo-web --apply
"""

import argparse
import os
import shutil
import sys
import time

OLD = "            if reply:\n                await ws.send_text(json.dumps(reply))\n"
NEW = ("            if reply:\n"
       "                if reply.get(\"type\") == \"dirs\":\n"
       "                    # 方向表是全局状态：广播给所有标签页，避免别的页面还拿旧值\n"
       "                    await broadcast(json.dumps(reply))\n"
       "                else:\n"
       "                    await ws.send_text(json.dumps(reply))\n")

INDEX_OLD = "    else if (m.type === 'dirs') { dirs = {}; for (const [k, v] of Object.entries(m.dirs || {})) dirs[k] = v; }"
INDEX_NEW = ("    else if (m.type === 'dirs') { dirs = {}; for (const [k, v] of Object.entries(m.dirs || {})) dirs[k] = v;\n"
             "      // 广播来的方向也要同步每行 ± 按钮，否则别的标签页 3D 变了、按钮还显示旧符号\n"
             "      for (const [k, v] of Object.entries(dirs)) { const b = $('d' + k); if (b) b.textContent = v > 0 ? '+' : '−'; } }")


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
    ap.add_argument("dir")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(os.path.expanduser(a.dir))
    server = os.path.join(root, "server.py")
    index = os.path.join(root, "index.html")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    changed = 0

    s = read(server)
    if NEW in s:
        print("  = server.py：已经是广播版本")
    elif s.count(OLD) == 1:
        print("  * server.py：set_dir 回复改为广播")
        if a.apply:
            bak = server + f".bak-{stamp}"
            shutil.copy2(server, bak)
            print(f"备份：{bak}")
            write(server, s.replace(OLD, NEW))
        changed += 1
    else:
        print(f"  ! server.py：匹配 {s.count(OLD)} 处，跳过")

    h = read(index)
    if INDEX_NEW in h:
        print("  = index.html：± 按钮已同步")
    elif h.count(INDEX_OLD) == 1:
        print("  * index.html：广播时同步 ± 按钮")
        if a.apply:
            bak = index + f".bak-{stamp}"
            shutil.copy2(index, bak)
            print(f"备份：{bak}")
            write(index, h.replace(INDEX_OLD, INDEX_NEW))
        changed += 1
    else:
        print(f"  ! index.html：匹配 {h.count(INDEX_OLD)} 处，跳过")

    print(("完成" if changed else "没有需要改的") + ("（dry-run，未写入）" if a.dry_run else "（已写入）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
