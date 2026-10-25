#!/usr/bin/env python3
"""给 servo-web 每颗舵机的操作行加一个 CAL 按钮，并在校准后强制刷新 3D。

- 按钮放在该行 ± 方向键后面，用「一键校准」区当前选中的基准；
- 点击后走和“校准这一颗”相同的 calib_plan → 确认 → calibrate 流程；
- 校准完成 showCalibResult 里同步滑块并调用 window.duckRefreshPose()，
  让 3D 在 300 ms / 800 ms 各重画一次，避免只刷新了数字、3D 还是旧姿态。

只改部署副本，不碰 references/。幂等，先备份。
用法（板上）：
    python3 servo-web-row-cal.py ~/servo-web --dry-run
    python3 servo-web-row-cal.py ~/servo-web --apply
"""

import argparse
import os
import shutil
import sys
import time

CSS_SERVO_OLD = "  .servo { display:grid; grid-template-columns:30px 1fr 60px 22px 22px; gap:8px; align-items:center; padding:5px 0; border-top:1px dashed var(--line); }"
CSS_SERVO_NEW = "  .servo { display:grid; grid-template-columns:30px 1fr 60px 22px 22px 40px; gap:8px; align-items:center; padding:5px 0; border-top:1px dashed var(--line); }"

CSS_NAME_OLD = "  .servo .name { font-size:11px; color:var(--muted); grid-column:2/6; margin-top:-5px; display:flex; gap:10px; flex-wrap:wrap; }"
CSS_NAME_NEW = "  .servo .name { font-size:11px; color:var(--muted); grid-column:2/7; margin-top:-5px; display:flex; gap:10px; flex-wrap:wrap; }"

CSS_DIR_OLD = "  .dir { width:22px; height:22px; padding:0; font-size:11px; line-height:20px; text-align:center; }"
CSS_DIR_NEW = CSS_DIR_OLD + "\n  .cal { width:40px; height:22px; padding:0; font-size:10px; line-height:20px; text-align:center; }"

ROW_OLD = """      <input type="checkbox" class="tq" id="t${id}" title="扭矩" ${on ? '' : 'disabled'}>
      <button class="dir" id="d${id}" title="3D 显示方向取反">${(dirs[id] || 1) > 0 ? '+' : '−'}</button>
"""
ROW_NEW = ROW_OLD + """      <button class="cal" id="c${id}" title="按「一键校准」选的基准校准这一颗" ${on ? '' : 'disabled'}>CAL</button>
"""

HANDLER_OLD = "    $('d' + id).onclick = () => { const d = -(dirs[id] || 1); dirs[id] = d; $('d' + id).textContent = d > 0 ? '+' : '−'; send({ op: 'set_dir', id, dir: d }); };\n"
HANDLER_NEW = HANDLER_OLD + "    $('c' + id).onclick = () => calibRow(id);\n"

CALIB_ONE = """function calibOne() {
  const id = v('opId'), r = calibRefText(); if (!r.text) { hint('基准姿态找不到了，重新选'); return; }
  calibPending = { for: 'one', id, ids: [id], ref: r.ref, text: r.text };
  send({ op: 'calib_plan', ids: [id], ref: r.ref, for: 'one', id });
}
"""
CALIB_ROW = CALIB_ONE + """
function calibRow(id) {
  const r = calibRefText(); if (!r.text) { hint('基准姿态找不到了，重新选'); return; }
  calibPending = { for: 'one', id, ids: [id], ref: r.ref, text: r.text };
  send({ op: 'calib_plan', ids: [id], ref: r.ref, for: 'one', id });
}
"""

SHOW_OLD = """  setTimeout(syncSliders, 300);
}
// 开扭矩的回包"""
SHOW_NEW = """  const refresh3d = () => { syncSliders(); if (window.duckRefreshPose) window.duckRefreshPose(); };
  setTimeout(refresh3d, 300);
  setTimeout(refresh3d, 800);
}
// 开扭矩的回包"""

CONFIRM_OLD = "  if (!confirm(`${head}\\n\\n确认鸭子已经摆成${p.text}\\n\\n现在 → 写成（差多少）：\\n${lines.join('\\n')}${tail}`)) return;"
CONFIRM_NEW = "  if (!confirm(`${head}\\n\\n确认鸭子已经摆成${p.text}\\n\\n⚠️ 校准会短暂关扭矩；这颗要托住/垫住，别让它因重力掉下去。掉多少，零点就偏多少。\\n\\n现在 → 写成（差多少）：\\n${lines.join('\\n')}${tail}`)) return;"

POSE_OLD = "let lastPoseSig = '', lastTrunkSig = '', needRender = true;\n"
POSE_NEW = POSE_OLD + "window.duckRefreshPose = () => { lastPoseSig = ''; needRender = true; };\n"


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
    # 这个补丁多处是“在原片段后追加”，new 会包含 old；只要 new 已出现就说明处理过
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
    path = os.path.join(root, "index.html")
    if not os.path.isfile(path):
        raise SystemExit(f"缺少 {path}")
    text = read(path)
    text = replace(text, CSS_SERVO_OLD, CSS_SERVO_NEW, "CSS 行加一列")
    text = replace(text, CSS_NAME_OLD, CSS_NAME_NEW, "CSS 名称跨到 CAL 列")
    text = replace(text, CSS_DIR_OLD, CSS_DIR_NEW, "CSS CAL 按钮尺寸")
    text = replace(text, ROW_OLD, ROW_NEW, "每行加 CAL 按钮")
    text = replace(text, HANDLER_OLD, HANDLER_NEW, "CAL 按钮点击")
    text = replace(text, CALIB_ONE, CALIB_ROW, "calibRow 函数")
    text = replace(text, SHOW_OLD, SHOW_NEW, "校准后刷新 3D")
    text = replace(text, CONFIRM_OLD, CONFIRM_NEW, "确认框加托住警告")
    text = replace(text, POSE_OLD, POSE_NEW, "duckRefreshPose 接口")
    if a.apply:
        bak = path + time.strftime(".bak-%Y%m%d-%H%M%S")
        shutil.copy2(path, bak)
        print(f"备份：{bak}")
        write(path, text)
    print("完成" + ("（dry-run，未写入）" if a.dry_run else "（已写入）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
