"""在用户单口 GD32 IMU 原照片上标出 R31、R5、F1。

来源：docs/photos/imu-board-b-20261014-b.jpg，2026-10-14 收到。
坐标针对原图 1080×1440；不镜像、不重绘器件，不推定连接器针序。
PCB 仅用于位号/布局交叉核对；图纸参数不等于实物测量。
"""
from pathlib import Path
import hashlib
import json
import math
import re

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PHOTO = ROOT / "docs/photos/imu-board-b-20261014-b.jpg"
PCB = ROOT / "references/microduck-community-kit/hardware/imu_to_dxl/imu_to_dxl.kicad_pcb"
OUT = ROOT / "docs/photos/imu-single-port-r31-r5-f1-location-20261027.png"
CROP_OUT = ROOT / "docs/photos/imu-single-port-data-front-end-crop-20261027.png"
MANIFEST = ROOT / "docs/references/扩展板双口惯性缺答复核/imu-photo-components-20261027.json"
DETAIL = (475, 655, 755, 850)
BOXES = {
    "R31": (596, 804, 617, 839),
    "R5": (593, 770, 644, 795),
    "F1": (620, 706, 675, 736),
}
COLORS = {"R31": "#E64343", "R5": "#FFD454", "F1": "#27B9F2"}


def main():
    source = Image.open(PHOTO).convert("RGB")
    if source.size != (1080, 1440):
        raise ValueError("原图尺寸变化，须重新核对标注坐标")
    canvas = Image.new("RGB", (1740, 1100), "#F3F6FA")
    draw = ImageDraw.Draw(canvas)
    navy, muted = "#17314A", "#506579"

    def text(x, y, value, size=27, color=navy, bold=False):
        font = ImageFont.truetype(
            "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc", size
        )
        bounds = draw.textbbox((x, y), value, font=font)
        if bounds[2] > canvas.width - 24 or bounds[3] > canvas.height - 18:
            raise ValueError(f"文字越界：{value}")
        draw.text((x, y), value, font=font, fill=color)

    def arrow(points, color):
        draw.line(points, fill=color, width=5, joint="curve")
        x, y = points[-1]
        px, py = points[-2]
        theta = math.atan2(y-py, x-px)
        wings = [(x-17*math.cos(theta+a), y-17*math.sin(theta+a)) for a in (-0.48, 0.48)]
        draw.polygon([(x, y), *wings], fill=color)

    text(38, 24, "单口 GD32 IMU｜R31、R5、F1 实物位置", 43, bold=True)
    text(40, 88, "元件面朝向你，白色 3P 插座在右侧；沿用原照片方向，未镜像。", 28)
    text(40, 152, "整板定位", 29, bold=True)
    overview = (90, 290, 780, 880)
    origin = (40, 211)
    canvas.paste(source.crop(overview), origin)
    region = tuple(round(origin[i % 2] + DETAIL[i] - overview[i % 2]) for i in range(4))
    draw.rounded_rectangle(region, radius=7, outline="#EF8654", width=5)
    text(40, 835, "放大区域：白色插座下方，", 28)
    text(40, 879, "右下安装孔的左侧。", 28)

    text(800, 152, "局部放大 · 原照片 3 倍", 29, bold=True)
    detail_origin = (800, 270)
    scale = 3
    detail = source.crop(DETAIL)
    detail.resize((1120, 780), Image.Resampling.LANCZOS).save(CROP_OUT)
    canvas.paste(detail.resize((840, 585), Image.Resampling.LANCZOS), detail_origin)

    mapped = {}
    for ref, box in BOXES.items():
        screen = tuple(round(detail_origin[i % 2] + (box[i]-DETAIL[i % 2])*scale) for i in range(4))
        mapped[ref] = screen
        draw.rounded_rectangle(screen, radius=5, outline=COLORS[ref], width=4)

    text(1240, 208, "F1 · PTC 保险丝", 28, "#0878A4", True)
    x1,y1,x2,y2 = mapped['F1']
    arrow([(1323, 251), (1323, y1-7)], COLORS['F1'])

    # 标签置于器件右侧空白区域，箭头不遮挡本体。
    draw.rounded_rectangle((1430, 521, 1711, 618), radius=12, fill="#17314A")
    text(1450, 530, "R5 · 串联电阻", 27, COLORS['R5'], True)
    text(1450, 572, "表面标记：510", 22, "#FFFFFF")
    x1,y1,x2,y2 = mapped['R5']
    arrow([(1445, 620), (1394, 620), (1394, (y1+y2)//2), (x2+6, (y1+y2)//2)], COLORS['R5'])

    text(1064, 897, "R31 · 上拉电阻", 30, "#C63035", True)
    x1,y1,x2,y2 = mapped['R31']
    arrow([((x1+x2)//2, 887), ((x1+x2)//2, y2+7)], COLORS['R31'])
    text(40, 974, "[照片识别] 位号与布局已对照公开 PCB；R31 阻值、F1 参数未由照片确认。", 27, bold=True)
    text(40, 1023, "原图：2026-10-14 用户提供｜标注：2026-10-27｜仅作元件定位，不标针序、不作改阻依据", 23, muted)
    canvas.save(OUT)

    designs = {}
    pcb_text = PCB.read_text(encoding="utf-8")
    for block in pcb_text.split('\n\t(footprint ')[1:]:
        found = re.search(r'\(property "Reference" "([^"]+)"', block)
        if found and found.group(1) in BOXES:
            ref = found.group(1)
            designs[ref] = {
                "footprint": re.match(r'"([^"]+)"', block).group(1),
                "at_mm_and_degrees": re.search(r'\n\t\t\(at ([^\n]+)', block).group(1).rstrip(')'),
                "reference_design_value": re.search(r'\(property "Value" "([^"]+)"', block).group(1),
                "photo_box_xyxy": list(BOXES[ref]),
            }
    if set(designs) != set(BOXES):
        raise ValueError("PCB 位号缺失")
    manifest = {
        "date": "2026-10-27",
        "photo": PHOTO.relative_to(ROOT).as_posix(),
        "photo_received_date": "2026-10-14",
        "photo_sha256": hashlib.sha256(PHOTO.read_bytes()).hexdigest(),
        "photo_size_px": list(source.size),
        "pcb": PCB.relative_to(ROOT).as_posix(),
        "pcb_sha256": hashlib.sha256(PCB.read_bytes()).hexdigest(),
        "evidence": "照片位号/相对布局与公开 PCB 交叉核对，非实测阻值；参考设计批次未与实物逐件对应",
        "orientation": "用户原图元件面，白色3P朝右；无镜像、无旋转",
        "detail_crop_xyxy": list(DETAIL),
        "components": designs,
        "photo_observations": {"R5": "表面可见510标记，未实测电阻", "R31": "无可辨阻值", "F1": "位号F1，非普通电阻；表面类似X的标记不用于确定规格"},
        "outputs": [OUT.relative_to(ROOT).as_posix(), CROP_OUT.relative_to(ROOT).as_posix()],
        "generator": Path(__file__).relative_to(ROOT).as_posix(),
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(OUT)
    print(CROP_OUT)
    print(MANIFEST)


if __name__ == "__main__":
    main()
