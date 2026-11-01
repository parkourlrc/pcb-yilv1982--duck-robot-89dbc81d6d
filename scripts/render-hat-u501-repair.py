import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/u501-repair-20261030"
REGION = (158.7, 106.9, 164.9, 112.2)
SCALE = 112
WIDTH, HEIGHT = 820, 710
COLORS = {"POWER_GND": "#4dab96", "+1V8_CODEC": "#bf84ed", "+3V3": "#e8b844", "I2C5_SCL": "#498dc9", "I2C5_SDA": "#c46e9e"}
REMOVED = {"ebdf4b90-3164-4fa7-8ca2-9c2850c48825", "9b58a3e5-36c2-440f-a1fb-3ec48dd252e1", "e97b81a0-7baf-4cb1-bec1-2dbb08172812"}


def font(size):
    return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", size)


def panel(items, title, layer):
    picture = Image.new("RGB", (WIDTH, HEIGHT), "#101b2a")
    draw = ImageDraw.Draw(picture)
    def pixel(position):
        return (round(60 + (position[0] - REGION[0]) * SCALE), round(75 + (position[1] - REGION[1]) * SCALE))
    def in_region(bounds):
        return not (bounds[2] < REGION[0] or bounds[0] > REGION[2] or bounds[3] < REGION[1] or bounds[1] > REGION[3])
    draw.text((24, 15), title, font=font(23), fill="white")
    for coordinate in range(159, 165):
        xpos = pixel((coordinate, 107))[0]
        draw.line((xpos, 65, xpos, 680), fill="#283445")
        draw.text((xpos - 18, 47), str(coordinate), font=font(13), fill="#9caabd")
    for coordinate in range(107, 113):
        ypos = pixel((159, coordinate))[1]
        draw.line((55, ypos, 770, ypos), fill="#283445")
        draw.text((15, ypos - 10), str(coordinate), font=font(13), fill="#9caabd")
    for item in items:
        if item["kind"] == "keepout" and item["layer"] == layer:
            draw.polygon([pixel(position) for position in item["points"]], outline="#ed9456", width=3)
            draw.text(pixel((160.05, 109.5)), "U501 禁布区", font=font(17), fill="#ed9456")
    for item in items:
        if item["kind"] != "track" or item["layer"] != layer:
            continue
        bounds = [min(item["start"][0], item["end"][0]), min(item["start"][1], item["end"][1]), max(item["start"][0], item["end"][0]), max(item["start"][1], item["end"][1])]
        if not in_region(bounds):
            continue
        color = "#ff5252" if item["uuid"] in REMOVED else COLORS.get(item["net"], "#728ba3")
        draw.line([pixel(item["start"]), pixel(item["end"])], fill=color, width=max(1, round(item["width"] * SCALE)))
    labels = {}
    for item in items:
        if item["kind"] != "pad" or layer not in item["layers"] or not in_region(item["bounds"]):
            continue
        left, top, right, bottom = item["bounds"]
        draw.rectangle([pixel((left, top)), pixel((right, bottom))], fill=COLORS.get(item["net"], "#8e99a6"), outline="white", width=1)
        number = item["number"]
        center = pixel(((left + right) / 2, (top + bottom) / 2))
        draw.text(center, number, font=font(13), fill="#071018", anchor="mm")
        if item["reference"].startswith("C"):
            labels.setdefault(item["reference"], (left, top))
    for item in items:
        if item["kind"] != "via":
            continue
        xpos, ypos = item["position"]
        if not in_region((xpos, ypos, xpos, ypos)):
            continue
        center = pixel((xpos, ypos))
        radius = item["width"] * SCALE / 2
        color = "#ff5252" if item["uuid"] in REMOVED else COLORS.get(item["net"], "#728ba3")
        draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=color)
        radius = item["drill"] * SCALE / 2
        draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill="#101b2a", outline="white")
    for reference, position in labels.items():
        coord = pixel(position)
        draw.text((coord[0], coord[1] - 26), reference, font=font(17), fill="white")
    return picture


def main():
    before = json.loads((EVIDENCE / "geometry-before.json").read_text(encoding="utf-8"))
    after = json.loads((EVIDENCE / "geometry-after.json").read_text(encoding="utf-8"))
    picture = Image.new("RGB", (WIDTH * 2, HEIGHT * 2 + 110), "#101b2a")
    for index, layer in enumerate(("F.Cu", "B.Cu")):
        picture.paste(panel(before, "修复前 · " + layer, layer), (0, index * HEIGHT))
        picture.paste(panel(after, "修复后 · " + layer, layer), (WIDTH, index * HEIGHT))
    draw = ImageDraw.Draw(picture)
    draw.text((30, HEIGHT * 2 + 12), "红色：移除的两段顶层短线和一个过孔；紫色：保留的 1.8V 路径；绿色：GND", font=font(20), fill="white")
    draw.text((30, HEIGHT * 2 + 46), "同一顶视坐标系，底层未镜像。图为原始几何派生；未显示填充铜和内层，焊盘以外接框表示。", font=font(18), fill="#bac9d8")
    draw.text((30, HEIGHT * 2 + 78), "来源：Rev A 修复前后 PCB · 2026-10-30 · 仅用于局部对照，不作实物接线或制造放行依据", font=font(18), fill="#bac9d8")
    picture.save(EVIDENCE / "u501-before-after.png")


if __name__ == "__main__":
    main()
