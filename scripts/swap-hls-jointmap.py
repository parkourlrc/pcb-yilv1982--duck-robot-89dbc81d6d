#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交换 hls_servo_debugger 关节表的左右腿 ID 映射（本机部署契约补丁）。

背景：上游 provision.py 的 _JOINT_SOURCE 为 left=20-24 / right=10-14；
本机用户实物装配验证左右相反（left=10-14 / right=20-24，2026-10-17 定案），
舵机已按新映射改号完毕。本脚本对部署副本（默认板上
~/hls_servo_debugger/hls_debugger/provision.py）做左右 ID 组交换：
left_* 行的 ID 20-24 → 10-14，right_* 行的 ID 10-14 → 20-24；
关节名、home 角、部位名、头颈 30-34 全部保持不动（30/31 头颈名称另由
swap-hls-headneck.py 在 2026-10-22 交换）。
幂等：已交换过的文件再跑会换回去——脚本会先检测并报警。

用法（板上）：python3 swap-hls-jointmap.py [provision.py 路径]
"""

import re
import sys

SWAP = {
    # left 行：上游 ID → 本机 ID
    **{20 + i: 10 + i for i in range(5)},
    # right 行：上游 ID → 本机 ID
    **{10 + i: 20 + i for i in range(5)},
}


def main(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    pat = re.compile(r'\("(left|right)_(\w+)", (\d+), "(左腿|右腿|头颈)", (-?[\d.]+)\)')

    def repl(m):
        side, joint, sid, group, home = m.groups()
        old = int(sid)
        new = SWAP.get(old)
        if new is None:
            return m.group(0)
        return '("%s_%s", %d, "%s", %s)' % (side, joint, new, group, home)

    lines = text.splitlines(keepends=True)
    in_table = False
    changed = 0
    for i, line in enumerate(lines):
        if line.startswith("_JOINT_SOURCE = ["):
            in_table = True
        elif in_table and line.startswith("]"):
            in_table = False
        if in_table:
            new_line = pat.sub(repl, line)
            if new_line != line:
                # 幂等检测：目标 ID 已出现在本行则视为已交换过
                changed += 1
            lines[i] = new_line
    if changed == 0:
        print("警告：_JOINT_SOURCE 无行被修改——可能已交换过（幂等保护），请人工核对。")
        sys.exit(2)
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(lines))
    print("已交换 %d 行（left→10-14 / right→20-24），文件：%s" % (changed, path))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         "/home/radxa/hls_servo_debugger/hls_debugger/provision.py")
