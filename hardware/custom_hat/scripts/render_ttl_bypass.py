"""Render native TTL copper views and the added schematic bypasses."""
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


EVIDENCE = Path(__file__).resolve().parents[3] / "docs/references/扩展板电路仿真工具/ttl-bypass-20261031"


def main():
    panels = []
    bounds_list = [(131.2, 123.5, 139.7, 128.5), (138.8, 117.5, 147.3, 122.5)]
    with fitz.open(EVIDENCE / "after-back.svg") as source:
        with fitz.open("pdf", source.convert_to_pdf()) as pdf:
            page = pdf[0]
            for index, bounds in enumerate(bounds_list):
                clip = fitz.Rect((bounds[0] - 100) / 64.9986 * page.rect.width, (bounds[1] - 100) / 29.9974 * page.rect.height,
                                 (bounds[2] - 100) / 64.9986 * page.rect.width, (bounds[3] - 100) / 29.9974 * page.rect.height)
                path = EVIDENCE / ("ttl-" + str(index + 1) + "-detail.png")
                page.get_pixmap(matrix=fitz.Matrix(25, 25), clip=clip, alpha=False).save(path)
                panels.append(Image.open(path).convert("RGB"))
    width, height = panels[0].size
    canvas = Image.new("RGB", (2 * width + 60, height + 200), "white")
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    draw.text((20, 12), "TTL 本地去耦：两颗100nF，同面VCC短线及各自地过孔", font=title, fill="#203444")
    records = [("U801", (133.75, 126.05), "C329", (138.0, 126.3), (138.7, 126.22), "VCC 3.135mm；电容到地孔 0.806mm"),
               ("U802", (141.37, 119.7), "C330", (143.9, 119.8), (144.7, 119.32), "VCC 1.441mm；电容到地孔 0.800mm")]
    for index, (panel, bounds, record) in enumerate(zip(panels, bounds_list, records)):
        device, center, capacitor, cap_center, via, detail = record
        origin = (20 + index * (width + 20), 90)
        canvas.paste(panel, origin)
        draw.text((origin[0], 54), device + " / " + capacitor + "：" + detail, font=small, fill="#203444")
        def point(coords):
            return origin[0] + (coords[0] - bounds[0]) / (bounds[2] - bounds[0]) * width, origin[1] + (coords[1] - bounds[1]) / (bounds[3] - bounds[1]) * height
        first, last = point((center[0] - .8, center[1] - 1.4)), point((center[0] + .8, center[1] + 1.4))
        draw.rectangle((*first, *last), outline="#ffe49c", width=3)
        draw.rectangle((first[0], first[1] - 29, first[0] + 69, first[1] - 2), fill="white")
        draw.text((first[0] + 3, first[1] - 28), device, font=font, fill="#203444")
        first, last = point((cap_center[0] - .45, cap_center[1] - .95)), point((cap_center[0] + .45, cap_center[1] + .95))
        draw.rectangle((*first, *last), outline="#ffb649", width=3)
        draw.rectangle((first[0] - 8, first[1] - 30, first[0] + 63, first[1] - 2), fill="white")
        draw.text((first[0] - 5, first[1] - 29), capacitor, font=font, fill="#203444")
        location = point(via)
        radius = .4 * width / (bounds[2] - bounds[0])
        draw.ellipse((location[0] - radius, location[1] - radius, location[0] + radius, location[1] + radius), outline="#ffe49c", width=3)
        label = (location[0] - 19, location[1] + radius + 6)
        draw.rectangle((label[0] - 3, label[1], label[0] + 45, label[1] + 25), fill="white")
        draw.text(label, "GND", font=small, fill="#203444")
    footer = height + 108
    draw.text((20, footer), "B.Cu采用顶视坐标，未镜像；彩框及文字是标注，不是新增铜。原铜对象与原焊盘连接均保留。", font=small, fill="#203444")
    draw.text((20, footer + 29), "两个新地孔为0.6/0.3mm，原生填铜确认连接F/In1/B地。线长不包含平面回流或孔桶。", font=small, fill="#203444")
    draw.text((20, footer + 58), "规则/连通检查通过；不能据此宣称TTL波形、ESL、抗扰度或整板性能实测通过。", font=small, fill="#203444")
    canvas.save(EVIDENCE / "ttl-bypass-layout.png")
    with fitz.open(EVIDENCE / "schematic-preview/custom_hat_rev_a-servo_ttl.svg") as source:
        with fitz.open("pdf", source.convert_to_pdf()) as pdf:
            page = pdf[0]
            page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False).save(EVIDENCE / "ttl-schematic.png")
            clip = fitz.Rect(190 / 420 * page.rect.width, 160 / 297 * page.rect.height, 275 / 420 * page.rect.width, 187 / 297 * page.rect.height)
            page.get_pixmap(matrix=fitz.Matrix(5, 5), clip=clip, alpha=False).save(EVIDENCE / "ttl-schematic-detail.png")
    print(EVIDENCE / "ttl-bypass-layout.png")


if __name__ == "__main__":
    main()
