"""Render the native reference-copper change with a clear projection legend."""
import json
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/扩展板电路仿真工具/i2s-reference-stitch-20261031"


def main():
    panels = []
    for label in ("before", "after"):
        with fitz.open(EVIDENCE / ("ground-map-" + label + ".svg")) as source:
            with fitz.open("pdf", source.convert_to_pdf()) as pdf:
                pixmap = pdf[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                path = EVIDENCE / ("ground-map-" + label + ".png")
                pixmap.save(path)
                panels.append(Image.open(path).convert("RGB"))
    width, height = panels[0].size
    canvas = Image.new("RGB", (width * 2 + 60, height + 210), "white")
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 26)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    record = json.loads((EVIDENCE / "geometry-connectivity-check.json").read_text(encoding="utf-8"))
    draw.text((20, 12), "LRCK 相邻地铜修复：信号线保持原位", font=title, fill="#243b35")
    for index, panel in enumerate(panels):
        xpos = 20 + index * (width + 20)
        key = "coverage_before" if index == 0 else "coverage_after"
        caption = ("修改前" if index == 0 else "修改后") + f'：线中心地铜覆盖 {record[key]["coverage_pct"]:.2f}%'
        draw.text((xpos, 62), caption, font=font, fill="#243b35")
        canvas.paste(panel, (xpos, 100))
        draw.rectangle((xpos, 100, xpos + width, 100 + height), outline="#b2bcb7", width=1)
    draw.text((20, height + 117), "绿色：F.Cu地铜；白色：无该地铜（可能含其它网络铜）。", font=font, fill="#243b35")
    draw.text((20, height + 148), "紫线：In1.Cu的LRCK投影；深绿圆：新增0.6/0.3mm地过孔。", font=font, fill="#243b35")
    draw.text((20, height + 179), "恢复约1.35mm参考地铜；文件几何结果，不是阻抗、EMI或实物验收。", font=font, fill="#243b35")
    canvas.save(EVIDENCE / "reference-stitch-review.png")
    print(EVIDENCE / "reference-stitch-review.png")


if __name__ == "__main__":
    main()
