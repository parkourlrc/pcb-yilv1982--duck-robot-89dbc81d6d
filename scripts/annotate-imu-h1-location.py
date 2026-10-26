"""Locate H1 on the archived single-port IMU photo; do not infer physical pin order.

Source: docs/photos/imu-board-b-20261014-b.jpg (received 2026-10-14).
Output: docs/photos/imu-single-port-h1-location-20261026.png.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/photos/imu-board-b-20261014-b.jpg"
OUTPUT = ROOT / "docs/photos/imu-single-port-h1-location-20261026.png"


def main():
    source = Image.open(SOURCE).convert("RGB")
    if source.size != (1080, 1440):
        raise ValueError("Source changed; recheck annotation coordinates")
    canvas = Image.new("RGB", (1460, 1090), "#F4F7FA")
    draw = ImageDraw.Draw(canvas)
    navy, red, muted = "#172E44", "#D22E36", "#54677A"

    def text(x, y, value, size=28, color=navy, bold=False):
        path = "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"
        font = ImageFont.truetype(path, size)
        if draw.textbbox((x, y), value, font=font)[2] > canvas.width - 25:
            raise ValueError("Text exceeds canvas")
        draw.text((x, y), value, font=font, fill=color)

    text(38, 22, "单口 GD32 IMU：H1 日志接口位置", 40, bold=True)
    text(40, 83, "观察方向：元件面朝向你，白色 3P 插座在右侧。", 28)
    crop = (85, 285, 790, 890)
    scale = 1.30
    photo = source.crop(crop).resize((round(705 * scale), round(605 * scale)), Image.Resampling.LANCZOS)
    offset = (35, 145)
    canvas.paste(photo, offset)

    def point(x, y):
        return (round(offset[0] + (x - crop[0]) * scale), round(offset[1] + (y - crop[1]) * scale))

    # H1 is the lower vertical group of four pads, beside the crystal.
    a, b = point(129, 621), point(179, 779)
    draw.rounded_rectangle((*a, *b), radius=9, outline=red, width=6)
    text(b[0] + 16, b[1] - 24, "H1 · 四个焊盘", 29, red, True)
    # H2/H3 references are for disambiguation, without pin numbering.
    text(*point(162, 416), "H2", 25, "#FFFFFF", True)
    text(*point(184, 293), "H3", 25, "#FFFFFF", True)

    text(1000, 158, "H1 局部放大", 30, red, True)
    detail = source.crop((126, 615, 224, 806)).resize((294, 573), Image.Resampling.LANCZOS)
    canvas.paste(detail, (1030, 215))
    draw.rounded_rectangle((1037, 233, 1189, 707), radius=12, outline=red, width=5)
    text(995, 820, "靠近左下安装孔，", 25)
    text(995, 858, "在金属晶振左侧。", 25)
    text(40, 955, "本图仅定位 H1；TX / GND 的实物针序仍需核对，先不要按上下顺序接线。", 28, red, True)
    text(40, 1008, "来源：用户原图（2026-10-14 收到）｜标注：2026-10-26｜原图保留，非当前接线照片", 23, muted)
    canvas.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
