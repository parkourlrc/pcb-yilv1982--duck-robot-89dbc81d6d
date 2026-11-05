import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/references/扩展板电路仿真工具/j506-repair-20261030"
REGION = (109.4, 117.8, 119.2, 130)
SCALE = 61
WIDTH, HEIGHT = 720, 860
COLORS = {"SPK_P": "#59bfea", "SPK_N": "#eeaa55", "POWER_GND": "#45a58e", "+1V8_CODEC": "#b98cde", "SERVO_VBAT": "#df6577", "VBATT_2S_IN": "#d89a6d"}


def font(size):
    return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", size)


def panel(items, label, socket_center):
    picture = Image.new("RGB", (WIDTH, HEIGHT), "#101b2a")
    draw = ImageDraw.Draw(picture)
    def pixel(position):
        return (round(65 + (position[0] - REGION[0]) * SCALE), round(80 + (position[1] - REGION[1]) * SCALE))
    def visible(bounds):
        return not (bounds[2] < REGION[0] or bounds[0] > REGION[2] or bounds[3] < REGION[1] or bounds[1] > REGION[3])
    draw.text((20, 14), label, font=font(24), fill="white")
    for xpos in range(110, 120):
        screen = pixel((xpos, 118))[0]
        draw.line((screen, 76, screen, 825), fill="#293646")
        draw.text((screen - 14, 53), str(xpos), font=font(13), fill="#a4b3c3")
    for ypos in range(118, 131):
        screen = pixel((110, ypos))[1]
        draw.line((60, screen, 680, screen), fill="#293646")
        draw.text((20, screen - 9), str(ypos), font=font(13), fill="#a4b3c3")
    for item in sorted(items, key=lambda item: {"track": 0, "pad": 1, "via": 2}.get(item["kind"], 3)):
        if item["kind"] == "track" and item["layer"] == "B.Cu":
            start, end = item["start"], item["end"]
            if not visible((min(start[0], end[0]), min(start[1], end[1]), max(start[0], end[0]), max(start[1], end[1]))):
                continue
            draw.line([pixel(start), pixel(end)], fill=COLORS.get(item["net"], "#677e94"), width=max(1, round(item["width"] * SCALE)))
        elif item["kind"] == "pad" and "B.Cu" in item["layers"] and visible(item["bounds"]):
            left, top, right, bottom = item["bounds"]
            draw.rectangle([pixel((left, top)), pixel((right, bottom))], fill=COLORS.get(item["net"], "#8a96a4"), outline="white")
            draw.text(pixel(((left + right) / 2, (top + bottom) / 2)), item["number"], font=font(12), fill="#07131c", anchor="mm")
        elif item["kind"] == "via":
            xpos, ypos = item["position"]
            if not visible((xpos, ypos, xpos, ypos)):
                continue
            center = pixel((xpos, ypos))
            radius = item["width"] * SCALE / 2
            draw.ellipse((center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius), fill=COLORS.get(item["net"], "#677e94"))
            radius = item["drill"] * SCALE / 2
            draw.ellipse((center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius), fill="#101b2a", outline="white")
    xpos, ypos = socket_center
    draw.rectangle([pixel((xpos-2.945, ypos-2.645)), pixel((xpos+2.945, ypos+2.645))], outline="#f9df62", width=2)
    draw.text(pixel((xpos-2.85, ypos-0.5)), "J506\n垂直插座", font=font(16), fill="#f9df62")
    draw.text(pixel((116.1, 122.2)), "R309", font=font(17), fill="white")
    draw.text(pixel((112.2, 128.5)), "J301 通孔排", font=font(18), fill="white")
    return picture


def main():
    image = Image.new("RGB", (WIDTH*2, HEIGHT+100), "#101b2a")
    for index, (label, center) in enumerate((("before", (113.43, 126.05)), ("after", (113.0, 122.3)))):
        items = json.loads((EVIDENCE / ("geometry-" + label + ".json")).read_text(encoding="utf-8"))
        image.paste(panel(items, "修复前 · B.Cu" if index == 0 else "修复后 · B.Cu", center), (index*WIDTH, 0))
    draw = ImageDraw.Draw(image)
    draw.text((22, HEIGHT+4), "蓝：SPK_P；橙：SPK_N；黄框：J506 courtyard。型号、朝向、针序保持不变。", font=font(20), fill="white")
    draw.text((22, HEIGHT+34), "同一顶视坐标，底层未镜像；仅显示局部焊盘/走线/孔，未画填充铜。焊盘外接框为近似。", font=font(17), fill="#b6c7d7")
    draw.text((22, HEIGHT+64), "来源：Rev A 前后PCB几何，2026-10-30。用于局部设计核对；不代表装配高度或制造放行。", font=font(17), fill="#b6c7d7")
    image.save(EVIDENCE / "j506-before-after.png")


if __name__ == "__main__":
    main()
