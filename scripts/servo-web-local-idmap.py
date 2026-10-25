#!/usr/bin/env python3
"""把 servo-web 部署副本的关节 ID 映射改成本项目本机映射。

上游 servo-web 0.15.2：20-24=左腿、10-14=右腿；30=neck_pitch、31=head_pitch。
本机：                  10-14=左腿、20-24=右腿；30=head_pitch、31=neck_pitch。
（见 docs/servo-id-mapping.md）

脚本只改传入目录里的部署副本，不碰 references/。会先做备份。
用法：
    python3 servo-web-local-idmap.py ~/servo-web --dry-run
    python3 servo-web-local-idmap.py ~/servo-web --apply
"""

import argparse
import json
import os
import shutil
import sys
import time

LEFT = {
    10: "left_hip_yaw", 11: "left_hip_roll", 12: "left_hip_pitch",
    13: "left_knee", 14: "left_ankle",
}
RIGHT = {
    20: "right_hip_yaw", 21: "right_hip_roll", 22: "right_hip_pitch",
    23: "right_knee", 24: "right_ankle",
}
HEAD = {
    30: "head_pitch", 31: "neck_pitch", 32: "head_yaw",
    33: "head_roll", 34: "mouth",
}
LOCAL_NAMES = {**LEFT, **RIGHT, **HEAD}
NAME_TO_ID = {v: k for k, v in LOCAL_NAMES.items()}
EXPECTED_IDS = sorted(LOCAL_NAMES)

JOINT_OLD = '''JOINT_NAMES = {
    20: "left_hip_yaw", 21: "left_hip_roll", 22: "left_hip_pitch", 23: "left_knee", 24: "left_ankle",
    30: "neck_pitch", 31: "head_pitch", 32: "head_yaw", 33: "head_roll", 34: "mouth",
    10: "right_hip_yaw", 11: "right_hip_roll", 12: "right_hip_pitch", 13: "right_knee", 14: "right_ankle",
}'''
JOINT_LEGS = '''JOINT_NAMES = {
    10: "left_hip_yaw", 11: "left_hip_roll", 12: "left_hip_pitch", 13: "left_knee", 14: "left_ankle",
    30: "neck_pitch", 31: "head_pitch", 32: "head_yaw", 33: "head_roll", 34: "mouth",
    20: "right_hip_yaw", 21: "right_hip_roll", 22: "right_hip_pitch", 23: "right_knee", 24: "right_ankle",
}'''
JOINT_FINAL = '''JOINT_NAMES = {
    10: "left_hip_yaw", 11: "left_hip_roll", 12: "left_hip_pitch", 13: "left_knee", 14: "left_ankle",
    30: "head_pitch", 31: "neck_pitch", 32: "head_yaw", 33: "head_roll", 34: "mouth",
    20: "right_hip_yaw", 21: "right_hip_roll", 22: "right_hip_pitch", 23: "right_knee", 24: "right_ankle",
}'''

FOLD_OLD = '''OFFICIAL_FOLD = {20: 0, 21: 0, 22: 1.57, 23: 1.57, 24: 0, 30: 1, 31: 1, 32: 0, 33: 0,
                 10: 0, 11: 0, 12: -1.57, 13: -1.57, 14: 0}'''
FOLD_NEW = '''OFFICIAL_FOLD = {10: 0, 11: 0, 12: 1.57, 13: 1.57, 14: 0, 30: 1, 31: 1, 32: 0, 33: 0,
                 20: 0, 21: 0, 22: -1.57, 23: -1.57, 24: 0}'''

DEFAULT_OLD = '''const DEFAULT_POSITION = { 20: 0, 21: -0.0873, 22: -0.4579, 23: -0.0049, 24: 0.4530, 30: 0.3491, 31: 0.3491, 32: 0, 33: 0, 34: 0,
                           10: 0, 11: 0.0873, 12: 0.4579, 13: 0.0049, 14: -0.4530 };'''
DEFAULT_NEW = '''const DEFAULT_POSITION = { 10: 0, 11: -0.0873, 12: -0.4579, 13: -0.0049, 14: 0.4530, 30: 0.3491, 31: 0.3491, 32: 0, 33: 0, 34: 0,
                           20: 0, 21: 0.0873, 22: 0.4579, 23: 0.0049, 24: -0.4530 };'''

SIT_OLD = "SIT:   { label: '坐', rad: { 20: 0, 21: 0, 22: -0.5236, 23: 1.0472, 24: 0, 30: 0.5, 31: 1.6, 32: 0, 33: 0, 10: 0, 11: 0, 12: 0.5236, 13: -1.0472, 14: 0 } },"
SIT_LEGS = "SIT:   { label: '坐', rad: { 10: 0, 11: 0, 12: -0.5236, 13: 1.0472, 14: 0, 30: 0.5, 31: 1.6, 32: 0, 33: 0, 20: 0, 21: 0, 22: 0.5236, 23: -1.0472, 24: 0 } },"
SIT_FINAL = "SIT:   { label: '坐', rad: { 10: 0, 11: 0, 12: -0.5236, 13: 1.0472, 14: 0, 30: 1.6, 31: 0.5, 32: 0, 33: 0, 20: 0, 21: 0, 22: 0.5236, 23: -1.0472, 24: 0 } },"

FOLD_POSE_OLD = "FOLD:  { label: '折叠', rad: { 20: 0, 21: 0, 22: 1.57, 23: 1.57, 24: 0, 30: 1, 31: 1, 32: 0, 33: 0, 10: 0, 11: 0, 12: -1.57, 13: -1.57, 14: 0 } },"
FOLD_POSE_NEW = "FOLD:  { label: '折叠', rad: { 10: 0, 11: 0, 12: 1.57, 13: 1.57, 14: 0, 30: 1, 31: 1, 32: 0, 33: 0, 20: 0, 21: 0, 22: -1.57, 23: -1.57, 24: 0 } },"

KNEE_OLD = "if (key === 'FOLD') { rad[23] = FOLD_KNEE_SEND; rad[13] = -FOLD_KNEE_SEND; }"
KNEE_NEW = "if (key === 'FOLD') { rad[13] = FOLD_KNEE_SEND; rad[23] = -FOLD_KNEE_SEND; }"

CN_OLD = """const CN = { 20: '左髋 yaw', 21: '左髋 roll', 22: '左髋 pitch', 23: '左膝', 24: '左踝', 30: '颈 pitch', 31: '头 pitch', 32: '头 yaw', 33: '头 roll', 34: '嘴',
             10: '右髋 yaw', 11: '右髋 roll', 12: '右髋 pitch', 13: '右膝', 14: '右踝' };"""
CN_LEGS = """const CN = { 10: '左髋 yaw', 11: '左髋 roll', 12: '左髋 pitch', 13: '左膝', 14: '左踝', 30: '颈 pitch', 31: '头 pitch', 32: '头 yaw', 33: '头 roll', 34: '嘴',
             20: '右髋 yaw', 21: '右髋 roll', 22: '右髋 pitch', 23: '右膝', 24: '右踝' };"""
CN_FINAL = """const CN = { 10: '左髋 yaw', 11: '左髋 roll', 12: '左髋 pitch', 13: '左膝', 14: '左踝', 30: '头 pitch', 31: '颈 pitch', 32: '头 yaw', 33: '头 roll', 34: '嘴',
             20: '右髋 yaw', 21: '右髋 roll', 22: '右髋 pitch', 23: '右膝', 24: '右踝' };"""

SELECT_ORDER_OLD = "const ORDER = [20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14];"
SELECT_ORDER_NEW = "const ORDER = [10, 11, 12, 13, 14, 30, 31, 32, 33, 34, 20, 21, 22, 23, 24];"

BUILD_OLD = '''JOINT_IDS = {
    "left_hip_yaw": 20, "left_hip_roll": 21, "left_hip_pitch": 22, "left_knee": 23, "left_ankle": 24,
    "neck_pitch": 30, "head_pitch": 31, "head_yaw": 32, "head_roll": 33, "mouth": 34,
    "right_hip_yaw": 10, "right_hip_roll": 11, "right_hip_pitch": 12, "right_knee": 13, "right_ankle": 14,
}'''
BUILD_LEGS = '''JOINT_IDS = {
    "left_hip_yaw": 10, "left_hip_roll": 11, "left_hip_pitch": 12, "left_knee": 13, "left_ankle": 14,
    "neck_pitch": 30, "head_pitch": 31, "head_yaw": 32, "head_roll": 33, "mouth": 34,
    "right_hip_yaw": 20, "right_hip_roll": 21, "right_hip_pitch": 22, "right_knee": 23, "right_ankle": 24,
}'''
BUILD_FINAL = '''JOINT_IDS = {
    "left_hip_yaw": 10, "left_hip_roll": 11, "left_hip_pitch": 12, "left_knee": 13, "left_ankle": 14,
    "head_pitch": 30, "neck_pitch": 31, "head_yaw": 32, "head_roll": 33, "mouth": 34,
    "right_hip_yaw": 20, "right_hip_roll": 21, "right_hip_pitch": 22, "right_knee": 23, "right_ankle": 24,
}'''

ORDER_OLD = "const order = [20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14];"
ORDER_NEW = "const order = [10, 11, 12, 13, 14, 30, 31, 32, 33, 34, 20, 21, 22, 23, 24];"
ORDER_COMMENT_OLD = "// robotd.toml 的 [bus.feetech] directions：关节顺序是左腿 20–24、颈头嘴 30–34、右腿 10–14"
ORDER_COMMENT_NEW = "// robotd.toml 的 [bus.feetech] directions：关节顺序是左腿 10–14、颈头嘴 30–34、右腿 20–24"

HEAD_LEFT_OLD = '<section><h2>左腿 20–24 '
HEAD_LEFT_NEW = '<section><h2>左腿 10–14 '
G20_OLD = '复制 robotd 方向表</button></h2><div id="g20"></div></section>'
G20_NEW = '复制 robotd 方向表</button></h2><div id="g10"></div></section>'
HEAD_RIGHT_OLD = '<section><h2>右腿 10–14</h2><div id="g10"></div></section>'
HEAD_RIGHT_NEW = '<section><h2>右腿 20–24</h2><div id="g20"></div></section>'


class PatchError(Exception):
    pass


def read(path):
    """按文本读，统一成 \\n 再匹配；写入时按原文件恢复 CRLF/LF。"""
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
        print(f"  = {label}：已是本机映射")
        return text
    if old not in text:
        raise PatchError(f"{label}：找不到待替换内容，可能版本不同，已中止")
    if text.count(old) != 1:
        raise PatchError(f"{label}：匹配到 {text.count(old)} 处，预期 1 处，已中止")
    print(f"  * {label}")
    return text.replace(old, new)


def replace_chain(text, stages, final, label):
    """按顺序兼容“上游原件 → 仅换左右腿 → 换 30/31”三个版本。"""
    if final in text:
        print(f"  = {label}：已是本机映射")
        return text
    for old, new in stages:
        if old in text:
            if text.count(old) != 1:
                raise PatchError(f"{label}：匹配到 {text.count(old)} 处，预期 1 处，已中止")
            text = text.replace(old, new)
    if final not in text:
        raise PatchError(f"{label}：找不到待替换内容，可能版本不同，已中止")
    print(f"  * {label}")
    return text


def patch_server(path, dry):
    text = read(path)
    text = replace_chain(text, [(JOINT_OLD, JOINT_LEGS), (JOINT_LEGS, JOINT_FINAL)],
                         JOINT_FINAL, "server.py JOINT_NAMES")
    text = replace(text, FOLD_OLD, FOLD_NEW, "server.py OFFICIAL_FOLD")
    if not dry:
        write(path, text)


def patch_index(path, dry):
    text = read(path)
    text = replace(text, HEAD_LEFT_OLD, HEAD_LEFT_NEW, "页面左腿标题")
    text = replace(text, G20_OLD, G20_NEW, "左腿分组容器 g20→g10")
    text = replace(text, HEAD_RIGHT_OLD, HEAD_RIGHT_NEW, "页面右腿标题与容器")
    text = replace(text, DEFAULT_OLD, DEFAULT_NEW, "DEFAULT_POSITION")
    text = replace_chain(text, [(SIT_OLD, SIT_LEGS), (SIT_LEGS, SIT_FINAL)],
                         SIT_FINAL, "OFFICIAL_POSES SIT")
    text = replace(text, FOLD_POSE_OLD, FOLD_POSE_NEW, "OFFICIAL_POSES FOLD")
    text = replace(text, KNEE_OLD, KNEE_NEW, "FOLD 膝发送角 13/23")
    text = replace_chain(text, [(CN_OLD, CN_LEGS), (CN_LEGS, CN_FINAL)],
                         CN_FINAL, "单颗操作中文关节名")
    text = replace(text, SELECT_ORDER_OLD, SELECT_ORDER_NEW, "单颗操作 ID 顺序")
    text = replace(text, ORDER_OLD, ORDER_NEW, "copyRobotdDirs 顺序")
    text = replace(text, ORDER_COMMENT_OLD, ORDER_COMMENT_NEW, "copyRobotdDirs 注释")
    if not dry:
        write(path, text)


def patch_model(path, dry):
    with open(path, encoding="utf-8") as f:
        m = json.load(f)
    changed = 0
    for b in m.get("bodies", []):
        j = b.get("joint")
        if not j:
            continue
        name = j.get("name")
        if name in NAME_TO_ID:
            want = NAME_TO_ID[name]
            if j.get("id") != want:
                j["id"] = want
                changed += 1
    ids = sorted(b["joint"]["id"] for b in m["bodies"] if b.get("joint") and b["joint"].get("id") is not None)
    if ids != EXPECTED_IDS:
        raise PatchError(f"model.json 关节 ID 校验失败：{ids} != {EXPECTED_IDS}")
    for b in m["bodies"]:
        j = b.get("joint")
        if not j or j.get("name") not in NAME_TO_ID:
            continue
        if LOCAL_NAMES[j["id"]] != j["name"]:
            raise PatchError(f"model.json 名字/ID 不一致：{j['name']} → {j['id']}")
    # 顶层的 joint_ids 是生成器一并写的名字→ID 表，前端不直接用，但必须同步，否则重跑 build_model.py 会漂回去
    jids = m.get("joint_ids")
    if isinstance(jids, dict):
        for name, want in NAME_TO_ID.items():
            if name in jids and jids[name] != want:
                jids[name] = want
                changed += 1
        for name, want in NAME_TO_ID.items():
            if name in jids and jids[name] != want:
                raise PatchError(f"model.json joint_ids 校验失败：{name} → {jids[name]}（应为 {want}）")
    print(f"  * model.json 交换 {changed} 个关节 ID，校验通过")
    if not dry:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, separators=(",", ":"))


def patch_build_model(path, dry):
    if not os.path.exists(path):
        print("  = build_model.py：不存在，跳过")
        return
    text = read(path)
    text = replace_chain(text, [(BUILD_OLD, BUILD_LEGS), (BUILD_LEGS, BUILD_FINAL)],
                         BUILD_FINAL, "build_model.py JOINT_IDS")
    if not dry:
        write(path, text)


def patch_dirs_note(path, dry):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    note = d.get("_note", "")
    old = " 2026-10-22 板上部署副本已按本机映射把左右腿 ID 组改为 10–14=左腿、20–24=右腿；方向数值仍是上游记录，本机未逐颗核对。"
    mid = " 2026-10-22 板上部署副本已按本机映射改为 10–14=左腿、20–24=右腿、30=head_pitch、31=neck_pitch；方向数值仍是上游记录，本机未逐颗核对。"
    final = " 2026-10-22 本机按正确 ID 映射逐颗核对：15 颗仍全 -1，3D 与实物方向/位置一致。"
    if final in note:
        print("  = directions.json 注释：已更新")
        return
    if old in note:
        note = note.replace(old, final)
    elif mid in note:
        note = note.replace(mid, final)
    else:
        note = (note + final).strip()
    d["_note"] = note
    print("  * directions.json 注释补充本机映射说明")
    if not dry:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)


def move_upstream_poses(root, dry):
    src = os.path.join(root, "poses")
    dst = os.path.join(src, "upstream-2026-09-20")
    moved = []
    for name in ("站-2026-09-20.json", "缩-2026-09-20.json"):
        p = os.path.join(src, name)
        if os.path.exists(p):
            moved.append(name)
            if not dry:
                os.makedirs(dst, exist_ok=True)
                shutil.move(p, os.path.join(dst, name))
    if moved:
        print(f"  * 上游姿态移入 poses/upstream-2026-09-20/：{moved}")
        if not dry:
            with open(os.path.join(dst, "README.txt"), "w", encoding="utf-8") as f:
                f.write("上游 servo-web 2026-09-20 的原始读数，关节名按上游 20-24=左腿。\n"
                        "不是本机姿态，勿发到本机舵机；留作来源记录。\n")
    else:
        print("  = 上游姿态：未发现（可能已移动）")


def backup(root):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = os.path.join(root, f".idmap-backup-{stamp}")
    os.makedirs(dst)
    for rel in ("server.py", "index.html", os.path.join("model", "model.json"), "build_model.py", "directions.json"):
        src = os.path.join(root, rel)
        if os.path.exists(src):
            out = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copy2(src, out)
    print(f"备份：{dst}")
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", help="servo-web 部署目录，例如 ~/servo-web")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="只检查，不写文件")
    g.add_argument("--apply", action="store_true", help="备份后写入")
    args = ap.parse_args()
    root = os.path.abspath(os.path.expanduser(args.dir))
    print(f"目标：{root}")
    for need in ("server.py", "index.html", os.path.join("model", "model.json")):
        if not os.path.isfile(os.path.join(root, need)):
            raise SystemExit(f"缺少 {need}，不像 servo-web 目录")
    dry = args.dry_run
    if not dry:
        backup(root)
    patch_server(os.path.join(root, "server.py"), dry)
    patch_index(os.path.join(root, "index.html"), dry)
    patch_model(os.path.join(root, "model", "model.json"), dry)
    patch_build_model(os.path.join(root, "build_model.py"), dry)
    patch_dirs_note(os.path.join(root, "directions.json"), dry)
    move_upstream_poses(root, dry)
    print("完成" + ("（dry-run，未写入）" if dry else "（已写入）"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PatchError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(2)
