"""Render the checked positive power paths in a clearly labelled layer projection."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/扩展板电路仿真工具/power-paths-20261031"


def main():
    contract = json.loads((EVIDENCE / "power-route-contract.json").read_text(encoding="utf-8"))
    scale = 20
    panel_width, panel_height = 1060, 310
    canvas = Image.new("RGB", (panel_width + 40, panel_height * 2 + 235), "white")
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 26)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 17)
    draw.text((20, 12), "电池共用入口与舵机路径：0.6mm → 1.2mm", font=title, fill="#203444")
    draw.text((20, 50), "B.Cu / In1.Cu 投影；其余铜省略。实际间距以同版DRC及原生图为准。", font=font, fill="#52616b")
    for stage_index, stage in enumerate(("before", "after")):
        origin = (20, 115 + stage_index * (panel_height + 45))
        def point(coords):
            return (origin[0] + (coords[0] - 104) * scale, origin[1] + (coords[1] - 116) * scale)
        draw.text((origin[0], origin[1] - 35), "修改前" if stage == "before" else "修改后：保持全部接口及焊盘位置", font=font, fill="#203444")
        draw.line((*point((104, 130)), *point((157, 130))), fill="#222222", width=2)
        paths = []
        for entry in contract["changes"]:
            if entry[stage] is not None:
                paths.append((entry["net"], entry["layer"], entry[stage]))
        if stage == "after":
            for start, end in zip(contract["right_servo_route"], contract["right_servo_route"][1:]):
                paths.append(("SERVO_VBAT", "In1.Cu", {"start": start[:2], "end": end[:2], "width_mm": 1.2}))
        for net, layer, path in paths:
            color = "#2166ac" if net == "VBATT_2S_IN" else "#b85d00"
            width = round(path["width_mm"] * scale)
            start, end = point(path["start"]), point(path["end"])
            draw.line((*start, *end), fill=color, width=width)
            for center in (start, end):
                draw.ellipse((center[0] - width / 2, center[1] - width / 2, center[0] + width / 2, center[1] + width / 2), fill=color)
        bridge_top = point((116.44, 118.1))
        bridge_bottom = point((118.04, 121.3))
        draw.rectangle((*bridge_top, *bridge_bottom), outline="#777777", width=2)
        labels = [("J402.2", (108.35, 118.47), (0, -29)), ("J401.2", (151.49, 119.7), (14, -25)),
                  ("J301.1 输入", (126.13, 127.32), (15, -28)), ("J301.7", (110.89, 127.32), (-88, -25)),
                  ("R309 铜桥", (117.24, 119.7), (8, -20))]
        for text, coords, offset in labels:
            center = point(coords)
            draw.ellipse((center[0] - 4, center[1] - 4, center[0] + 4, center[1] + 4), fill="#222222")
            draw.text((center[0] + offset[0], center[1] + offset[1]), text, font=small, fill="#203444")
    footer = panel_height * 2 + 163
    draw.text((20, footer), "蓝：电池共用输入；棕：舵机正极。地回程、接点/孔壁电阻未纳入图中的路径模型。", font=small, fill="#203444")
    draw.text((20, footer + 30), "模型只比较选定铜段的压降/损耗，不能据此标整板额定电流或温升已通过。", font=small, fill="#203444")
    canvas.save(EVIDENCE / "power-path-review.png")
    print(EVIDENCE / "power-path-review.png")


if __name__ == "__main__":
    main()
