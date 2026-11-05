"""标注官方 C1 截图的 R33/TH1；不将参考位号映射到白色 V1.2。"""
from pathlib import Path
import hashlib
import json

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/references/扩展板双口惯性缺答复核/pcb-search/scrapmeta-wiki--assets--pcb--hat-3d-back-2026-09-04.png"
OUTPUT = ROOT / "docs/photos/hat-c1-r33-reference-20261027.png"
FONT = "C:/Windows/Fonts/msyh.ttc"


def font(size):
    return ImageFont.truetype(FONT, size)


def main():
    src = Image.open(SOURCE).convert("RGB")
    assert src.size == (1024, 577), "源图改变，须重核坐标"
    canvas = Image.new("RGB", (1600, 860), "#f5f7fa")
    draw = ImageDraw.Draw(canvas)
    ink, red, blue = "#193047", "#b62b24", "#1a64a0"
    draw.text((35, 25), "官方 HAT C1：DATA 串联电阻位置参考", fill=ink, font=font(38))
    draw.text((35, 85), "白色 V1.2 的对应位号、阻值与走线仍待确认", fill=red, font=font(28))
    draw.text((35, 139), "背面视角：40P 排针朝上，未镜像", fill=ink, font=font(25))
    crop_box = (230, 150, 798, 425)
    board = src.crop(crop_box).resize((1022, 495), Image.Resampling.LANCZOS)
    canvas.paste(board, (35, 188))

    def point(x, y):
        return (35 + round((x - crop_box[0]) * 1022 / 568),
                188 + round((y - crop_box[1]) * 495 / 275))

    draw.rectangle((*point(708, 266), *point(761, 335)), outline=red, width=4)
    zoom_box = (700, 250, 779, 355)
    zoom = src.crop(zoom_box).resize((316, 420), Image.Resampling.LANCZOS)
    canvas.paste(zoom, (1210, 195))

    def zp(x, y):
        return (1210 + (x - 700) * 4, 195 + (y - 250) * 4)

    # R33 为 D4 左侧的小型横向器件；TH1 为其右下方竖向器件。
    draw.rectangle((*zp(713, 276), *zp(734, 289)), outline=red, width=4)
    draw.rectangle((*zp(742, 299), *zp(757, 329)), outline=blue, width=4)
    draw.line([point(761, 266), (1100, 260), (1198, 260)], fill=red, width=3)
    draw.polygon([(1198, 260), (1185, 252), (1185, 268)], fill=red)
    draw.text((1130, 631), "红框 R33：150 Ω / 0402", fill=red, font=font(25))
    draw.text((1130, 670), "蓝框 TH1：100R 热敏件", fill=blue, font=font(25))
    draw.line((35, 722, 1565, 722), fill="#ccd5df", width=2)
    notes = [
        "位号与数值：官方 C1 PCB / BOM，提交 88d51fa；图中坐标仅适用于此参考版。",
        "原图：ScrapMeta 仓库的 C1 背面 CAD 截图；裁剪、等比放大，无生成细节。",
        "2026-10-27 制作；本图不构成白色 V1.2 的拆焊定位。",
    ]
    for i, text in enumerate(notes):
        draw.text((35, 740 + i * 36), text, fill=ink, font=font(23))
    canvas.save(OUTPUT)
    info = {
        "date": "2026-10-27",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "output": OUTPUT.relative_to(ROOT).as_posix(),
        "output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "source_board_version": "官方 C1，ScrapMeta 文档所引用版本",
        "transform": "crop and proportional resize; no mirror; no generated details",
        "r33_box_source_xyxy": [713, 276, 734, 289],
        "th1_box_source_xyxy": [742, 299, 757, 329],
        "limit": "未核对到用户白色 V1.2；不能据此拆焊用户板",
    }
    (ROOT / "docs/references/扩展板双口惯性缺答复核/c1-image-manifest.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
