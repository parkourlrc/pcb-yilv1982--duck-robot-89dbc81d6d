"""Annotate a native B.Cu view with the verified LDO branch positions."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/ldo-capacitors-20261031"


def main():
    source = Image.open(EVIDENCE / "board-B.png").convert("RGB")
    scale_x, scale_y = source.width / 64.9986, source.height / 29.9974
    crop_box = (round(19 * scale_x), round(12 * scale_y), round(39 * scale_x), round(29 * scale_y))
    picture = source.crop(crop_box).resize(((crop_box[2] - crop_box[0]) * 2, (crop_box[3] - crop_box[1]) * 2))
    canvas = Image.new("RGB", (picture.width + 480, picture.height + 170), "white")
    origin = (18, 90)
    canvas.paste(picture, origin)
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 25)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    draw.text((18, 12), "LDO 输出电容回路重排 / B.Cu 文件视图", font=title, fill="#203444")
    draw.text((18, 50), "原生规则与连接检查通过；控制环、温升及实装未测", font=font, fill="#52616b")
    def point(xpos, ypos):
        return (origin[0] + 2 * ((xpos - 100) * scale_x - crop_box[0]),
                origin[1] + 2 * ((ypos - 100) * scale_y - crop_box[1]))
    contract = json.loads((EVIDENCE / "change-contract.json").read_text(encoding="utf-8"))
    labels = [
        ("C308", (123.7, 115.6), (1.05, 1.9), 130, "2.2µF 输入电容，原位置保留"),
        ("U702", (131.21, 119.7), (7.0, 3.5), 275, "LP38691DT-1.8 / 三脚TO-252"),
        ("R703", contract["resistor_position"], (0.8, 1.55), 420, "47mΩ，仅串在C309回地支路"),
        ("C309", contract["capacitor_position"], (1.9, 1.05), 565, "2.2µF，OUT到电容走线2.227mm"),
    ]
    text_x = picture.width + 42
    for reference, center, half, label_y, description in labels:
        color = "#075d43" if reference.startswith("C") else "#8f3700"
        start = point(center[0] - half[0], center[1] - half[1])
        end = point(center[0] + half[0], center[1] + half[1])
        draw.rectangle((*start, *end), outline=color, width=3)
        target = point(*center)
        draw.line((end[0], target[1], text_x - 10, label_y + 15), fill=color, width=2)
        draw.text((text_x, label_y), reference, font=title, fill=color)
        draw.text((text_x, label_y + 38), description, font=font, fill="#203444")
    draw.text((18, picture.height + 112), "B面未镜像；不是实物图。R703不串负载地，C311并联影响已单列。", font=font, fill="#203444")
    canvas.save(EVIDENCE / "ldo-layout-review.png")
    print(EVIDENCE / "ldo-layout-review.png")


if __name__ == "__main__":
    main()
