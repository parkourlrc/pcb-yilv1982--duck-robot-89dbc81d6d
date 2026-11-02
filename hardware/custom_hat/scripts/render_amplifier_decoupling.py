"""Render aligned front/back native views of the amplifier decoupling repair."""
import json
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/amp-decoupling-20261031"
BOUNDS = (143.8, 122.6, 154.6, 129.4)


def main():
    panels = []
    for side in ("F", "B"):
        path = EVIDENCE / ("board-" + side + ".svg")
        with fitz.open(path) as source:
            with fitz.open("pdf", source.convert_to_pdf()) as pdf:
                page = pdf[0]
                page.get_pixmap(matrix=fitz.Matrix(7, 7), alpha=False).save(path.with_suffix(".png"))
                clip = fitz.Rect((BOUNDS[0] - 100) / 64.9986 * page.rect.width, (BOUNDS[1] - 100) / 29.9974 * page.rect.height,
                                 (BOUNDS[2] - 100) / 64.9986 * page.rect.width, (BOUNDS[3] - 100) / 29.9974 * page.rect.height)
                crop = page.get_pixmap(matrix=fitz.Matrix(24, 24), clip=clip, alpha=False)
                crop_path = EVIDENCE / ("amp-" + side + "-detail.png")
                crop.save(crop_path)
                panels.append(Image.open(crop_path).convert("RGB"))
    width, height = panels[0].size
    canvas = Image.new("RGB", (width * 2 + 60, height + 195), "white")
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 25)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    draw.text((20, 12), "U803 就近去耦：正面电容、背面功放、成对VDD/GND通孔", font=title, fill="#203444")
    for index, panel in enumerate(panels):
        origin = (20 + index * (width + 20), 91)
        canvas.paste(panel, origin)
        draw.text((origin[0], 56), "F.Cu：C323 22µF + C328 2.2µF" if index == 0 else "B.Cu：U803原位，局部电源/地短线", font=font, fill="#203444")
        def point(coords):
            return (origin[0] + (coords[0] - BOUNDS[0]) / (BOUNDS[2] - BOUNDS[0]) * width,
                    origin[1] + (coords[1] - BOUNDS[1]) / (BOUNDS[3] - BOUNDS[1]) * height)
        if index == 0:
            for label, center, half in (("C323", (148.1, 125.8), (1.6, 2.3)), ("C328", (150.8, 126.05), (1.0, 1.85))):
                first = point((center[0] - half[0], center[1] - half[1]))
                last = point((center[0] + half[0], center[1] + half[1]))
                draw.rectangle((*first, *last), outline="#ffe49c", width=3)
                draw.rectangle((first[0] + 3, first[1] + 3, first[0] + 78, first[1] + 31), fill="white")
                draw.text((first[0] + 7, first[1] + 4), label, font=font, fill="#203444")
        for label, coords, color in (("VDD", (151.95, 125.415), "#6f167f"), ("GND", (151.95, 126.685), "#005b36")):
            center = point(coords)
            radius = 0.4 * width / (BOUNDS[2] - BOUNDS[0])
            draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), outline=color, width=3)
            draw.rectangle((center[0] + radius + 4, center[1] - 12, center[0] + radius + 60, center[1] + 17), fill="white")
            draw.text((center[0] + radius + 7, center[1] - 12), label, font=small, fill=color)
    footer = height + 111
    draw.text((20, footer), "F/B使用同一顶视坐标，B未镜像；彩框/圆为标注，不是新增铜。", font=small, fill="#203444")
    draw.text((20, footer + 29), "VDD至C328平面铜线约2.95mm，至C323约5.76mm；均另跨1个通孔，不含孔桶/ESL。", font=small, fill="#203444")
    draw.text((20, footer + 58), "原生规则/连通检查通过，尚未实测音频噪声、PSRR、瞬态或温升。", font=small, fill="#203444")
    canvas.save(EVIDENCE / "amp-decoupling-review.png")
    print(EVIDENCE / "amp-decoupling-review.png")


if __name__ == "__main__":
    main()
