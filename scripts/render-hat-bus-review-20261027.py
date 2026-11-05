"""生成 HAT 共总线原理图对比；只读源 PDF，不改变原件或实物。"""
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/references/扩展板双口惯性缺答复核"
SOURCES = OUT / "sources"
LOCAL = ROOT / "docs/schematics/microduck-hat-v1.0-sch/SCH_Microduck-Hat-for-Radxa-Zero_2026-10-06.pdf"
FONT = "C:/Windows/Fonts/msyh.ttc"


def page(path, index, scale=4):
    doc = pdfium.PdfDocument(str(path))
    return doc[index].render(scale=scale).to_pil().convert("RGB")


def font(size):
    return ImageFont.truetype(FONT, size)


def panel(canvas, source, crop, origin, resistor, ports):
    w, h = source.size
    box = tuple(round(v * (w if i % 2 == 0 else h)) for i, v in enumerate(crop))
    clipped = source.crop(box)
    resized = ImageOps.contain(clipped, (750, 550))
    px, py = origin[0] + (750 - resized.width) // 2, origin[1]
    canvas.paste(resized, (px, py))
    d = ImageDraw.Draw(canvas)
    sx, sy = resized.width / clipped.width, resized.height / clipped.height
    for rect, color in [(resistor, "#c43c2f"), (ports, "#1766af")]:
        coords = [(px + (rect[0] * w - box[0]) * sx, py + (rect[1] * h - box[1]) * sy),
                  (px + (rect[2] * w - box[0]) * sx, py + (rect[3] * h - box[1]) * sy)]
        d.rectangle(coords, outline=color, width=4)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    local = page(LOCAL, 3)
    upstream = page(SOURCES / "upstream-hat-D1.pdf", 3)
    canvas = Image.new("RGB", (1640, 1040), "#f5f7fa")
    d = ImageDraw.Draw(canvas)
    d.text((40, 25), "HAT 共用 DATA 路径：串联电阻对比", font=font(35), fill="#10243a")
    d.text((40, 80), "2026-10-27 静态读图 · 社区图 V1.0 ≠ 本机实物 V1.2 · 实物阻值待核", font=font(23), fill="#526174")
    for x in [25, 840]:
        d.rounded_rectangle((x, 130, x + 775, 900), radius=12, fill="white", outline="#d1dbe5")
    d.text((45, 150), "社区 HAT V1.0：R31 = 1 kΩ", font=font(28), fill="#c43c2f")
    d.text((860, 150), "官方 HAT D1：R33 = 150 Ω", font=font(28), fill="#1766af")
    panel(canvas, local, (.39, .18, .668, .485), (37, 215),
          (.544, .381, .579, .418), (.621, .381, .659, .483))
    panel(canvas, upstream, (.40, .263, .915, .50), (852, 215),
          (.662, .408, .699, .441), (.824, .409, .863, .490))
    d.text((45, 790), "红框：DATA 串联电阻；F1 也在 DATA 上", font=font(23), fill="#34465c")
    d.text((45, 833), "蓝框：CN11 / CN12，共用 DATA、+BATT、GND", font=font(22), fill="#1766af")
    d.text((860, 790), "红框：对应电阻；后接 TH1（图标 100 Ω）", font=font(23), fill="#34465c")
    d.text((860, 833), "蓝框：J13 / J14，同样是共总线双口", font=font(23), fill="#1766af")
    d.text((40, 925), "位号属于各自板卡：社区 HAT R31、官方 HAT R33、IMU R31 不可混用。", font=font(25), fill="#10243a")
    d.text((40, 970), "图纸 pin 1=GND / 2=+BATT / 3=DATA；不是照片上下针序，也不是改阻或接线放行。", font=font(23), fill="#526174")
    canvas.save(OUT / "hat-data-path-comparison.png")
    old = Image.open(ROOT / "docs/photos/sch/page4.png")
    old.crop((690, 80, 1670, 1200)).save(OUT / "hat-servo-crop.png")
    upstream.save(SOURCES / "upstream-servo-page.png")
    for name in ["sn74lvc1g125-ti", "sn74lvc1g126-ti"]:
        for i in [4, 10]:
            page(SOURCES / (name + ".pdf"), i, 1.7).save(SOURCES / f"{name}-p{i+1}.png")
    print(OUT / "hat-data-path-comparison.png")


if __name__ == "__main__":
    main()
