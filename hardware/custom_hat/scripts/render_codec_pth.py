"""Render aligned native layers around the codec supply through-via."""
from pathlib import Path
import argparse

import fitz
from PIL import Image, ImageDraw, ImageFont


EVIDENCE = Path(__file__).resolve().parents[3] / "docs/references/扩展板电路仿真工具/codec-pth-20261031"
BOUNDS = (148.3, 110.2, 153.0, 114.6)


def main():
    global EVIDENCE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path)
    arguments = parser.parse_args()
    EVIDENCE = arguments.evidence.resolve() if arguments.evidence else EVIDENCE
    panels = []
    for side in ("F", "In1", "B"):
        path = EVIDENCE / ("codec-" + side + ".svg")
        with fitz.open(path) as svg:
            with fitz.open("pdf", svg.convert_to_pdf()) as pdf:
                page = pdf[0]
                clip = fitz.Rect((BOUNDS[0] - 100) / 64.9986 * page.rect.width, (BOUNDS[1] - 100) / 29.9974 * page.rect.height,
                                 (BOUNDS[2] - 100) / 64.9986 * page.rect.width, (BOUNDS[3] - 100) / 29.9974 * page.rect.height)
                page.get_pixmap(matrix=fitz.Matrix(25, 25), clip=clip, alpha=False).save(path.with_suffix(".png"))
                panels.append(Image.open(path.with_suffix(".png")).convert("RGB"))
    width, height = panels[0].size
    canvas = Image.new("RGB", (width * 3 + 80, height + 205), "white")
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    draw.text((20, 13), "U701.7：原尺寸盲孔改为机械贯通孔，要求填孔盖铜", font=title, fill="#203444")
    for index, (panel, label) in enumerate(zip(panels, ("F.Cu：新增+3V3焊环", "In1.Cu：新增+3V3焊环", "B.Cu：焊盘与位置不变"))):
        origin = (20 + index * (width + 20), 88)
        canvas.paste(panel, origin)
        draw.text((origin[0], 54), label, font=font, fill="#203444")
        xpos = origin[0] + (150.3625 - BOUNDS[0]) / (BOUNDS[2] - BOUNDS[0]) * width
        ypos = origin[1] + (112.1 - BOUNDS[1]) / (BOUNDS[3] - BOUNDS[1]) * height
        radius = .33 * width / (BOUNDS[2] - BOUNDS[0])
        draw.ellipse((xpos - radius, ypos - radius, xpos + radius, ypos + radius), outline="#ffc949", width=3)
    footer = height + 106
    draw.text((20, footer), "铜盘0.35mm / 设计孔径0.15mm；坐标(150.3625,112.1)mm，孔型由In2–B改为F–B。", font=font, fill="#203444")
    draw.text((20, footer + 29), "所有层采用同一顶视坐标，B未镜像；空心圆为钻孔标记，成品要求填孔盖铜，非开放孔。", font=font, fill="#203444")
    draw.text((20, footer + 58), "原走线与元件焊盘保持。原生规则/连接检查通过，不代表制造商接受或实物性能通过。", font=font, fill="#203444")
    canvas.save(EVIDENCE / "codec-pth-layout.png")
    print(EVIDENCE / "codec-pth-layout.png")


if __name__ == "__main__":
    main()
