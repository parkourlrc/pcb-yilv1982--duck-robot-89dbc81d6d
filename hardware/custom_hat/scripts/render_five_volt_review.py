"""Show the widened 5V header feed as a labelled inner-layer projection."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/five-volt-paths-20261031"


def main():
    data = json.loads((EVIDENCE / "header-route-contract.json").read_text(encoding="utf-8"))
    scale = 21
    panel_width, panel_height = 920, 330
    canvas = Image.new("RGB", (panel_width + 40, panel_height * 2 + 240), "white")
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 19)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
    draw.text((20, 10), "5V 公共过孔至主控排母：主干和入口改为1.2mm", font=title, fill="#203444")
    draw.text((20, 49), "内层投影示意；未显示电感到公共过孔的F面线路、反馈支路及其他铜。", font=font, fill="#52616b")
    for index, stage in enumerate(("before", "after")):
        origin = (20, 125 + index * (panel_height + 40))
        def point(coords):
            return (origin[0] + (coords[0] - 104.5) * scale, origin[1] + (coords[1] - 101) * scale)
        draw.text((origin[0], origin[1] - 35), "修改前：0.45/0.6mm" if stage == "before" else "修改后：1.2mm，原端点保留", font=font, fill="#203444")
        routes = [(entry["layer"], entry[stage]) for entry in data["changes"] if entry[stage] is not None]
        if stage == "after":
            for route in data["trunk_routes"]:
                routes.extend(("In1.Cu", {"start": start[:2], "end": end[:2], "width_mm": 1.2}) for start, end in zip(route["points"], route["points"][1:]))
        for layer, route in routes:
            color = "#2563a6" if layer == "In2.Cu" else "#a35400"
            width = max(1, round(route["width_mm"] * scale))
            start, end = point(route["start"]), point(route["end"])
            draw.line((*start, *end), fill=color, width=width)
            for center in (start, end):
                draw.ellipse((center[0] - width / 2, center[1] - width / 2, center[0] + width / 2, center[1] + width / 2), fill=color)
        for label, coords, delta in (("J101.2 / .4", (108.32, 102.05), (7, -25)),
                                     ("原换层孔", (122.1278, 106.838), (-45, -35)),
                                     ("分支点", (133.605, 112.1717), (-24, 17)),
                                     ("5V公共过孔", (145.8126, 115.015), (-95, 24))):
            center = point(coords)
            draw.ellipse((center[0] - 4, center[1] - 4, center[0] + 4, center[1] + 4), fill="#222222")
            draw.text((center[0] + delta[0], center[1] + delta[1]), label, font=small, fill="#203444")
    footer = panel_height * 2 + 165
    draw.text((20, footer), "棕：In1.Cu；蓝：In2.Cu。反馈元件、取样连接、过孔及全部焊盘保持。", font=small, fill="#203444")
    draw.text((20, footer + 30), "原生DRC/连接检查通过；图和铜段模型不构成主控电压、温升或制造放行。", font=small, fill="#203444")
    canvas.save(EVIDENCE / "five-volt-path-review.png")
    print(EVIDENCE / "five-volt-path-review.png")


if __name__ == "__main__":
    main()
