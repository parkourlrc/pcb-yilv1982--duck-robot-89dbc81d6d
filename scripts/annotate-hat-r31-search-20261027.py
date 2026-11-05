"""在既有 HAT 背面照片标注待核范围，不将照片候选误作已确认 R31。"""
from pathlib import Path
import hashlib
import json

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PHOTOS = ROOT / "docs/photos"
SRC = PHOTOS / "hat-v1.2-back.jpg"
OUT = PHOTOS / "hat-v1.2-r31-search-area-20261027.png"
CROP = PHOTOS / "hat-v1.2-data-region-crop-20261027.png"
FONT = "C:/Windows/Fonts/msyh.ttc"
AREA = (890, 542, 1270, 755)
CROP_BOX = (835, 486, 1368, 885)


def font(size):
    return ImageFont.truetype(FONT, size)


def main():
    raw_sha = hashlib.sha256(SRC.read_bytes()).hexdigest()
    src = ImageOps.exif_transpose(Image.open(SRC)).convert("RGB")
    if src.size != (1440, 1080):
        raise ValueError("源图显示尺寸改变，须重新核对坐标")
    # 仅作确定性旋转、裁剪、等比例缩放；不锐化或生成器件细节。
    crop = src.crop(CROP_BOX)
    crop.resize((1066, 798), Image.Resampling.LANCZOS).save(CROP)
    canvas = Image.new("RGB", (1800, 1070), "#f4f6f9")
    d = ImageDraw.Draw(canvas)
    ink, red, blue = "#192c43", "#c33c2d", "#1766a7"
    d.text((35, 24), "HAT V1.2 背面：R31 对应器件尚未定位", font=font(36), fill=ink)
    d.text((35, 80), "红框仅标待核局部，不表示框内某颗已经确认为 R31。", font=font(26), fill=red)
    d.text((35, 130), "① 找位置：40P 黑色排母朝上", font=font(27), fill=ink)
    d.text((940, 130), "② 同一局部放大", font=font(27), fill=ink)
    origin, scale = (35, 190), .6
    canvas.paste(src.resize((864, 648), Image.Resampling.LANCZOS), origin)
    def xy(point):
        return (round(origin[0] + point[0]*scale), round(origin[1] + point[1]*scale))
    d.rectangle((*xy(AREA[:2]), *xy(AREA[2:])), outline=red, width=4)
    # 明确只标整组插座焊点，不在照片上指派上下针脚编号。
    d.rectangle((*xy((1160, 660)), *xy((1320, 840))), outline=blue, width=3)
    zoom_origin, zoom_scale = (940, 210), 1.5
    zoom = crop.resize((800, 599), Image.Resampling.LANCZOS)
    canvas.paste(zoom, zoom_origin)
    def zp(point):
        return (round(zoom_origin[0]+(point[0]-CROP_BOX[0])*zoom.width/crop.width),
                round(zoom_origin[1]+(point[1]-CROP_BOX[1])*zoom.height/crop.height))
    d.rectangle((*zp(AREA[:2]), *zp(AREA[2:])), outline=red, width=4)
    d.line([xy((AREA[2], AREA[1])), (920, 455), (935, 455)], fill=red, width=3)
    d.polygon([(935,455),(923,448),(923,462)], fill=red)
    d.text((45, 843), "蓝框：两个 SERVOS 3P 插座背面的焊点组", font=font(25), fill=blue)
    d.text((950, 843), "现有分辨率不足：位号、阻值和走线无法核准", font=font(24), fill=red)
    d.line((35, 900, 1765, 900), fill="#d2dce6", width=2)
    notes = [
        "要找的是 V1.0 原理图 DATA 路径的 R31（图标 1 kΩ）；实物 V1.2 的对应位号与阻值待核。",
        "请补拍右侧放大图这一片的清晰近照，尽量垂直、对焦到小器件；本图不能用于确定拆焊目标。",
        "源图：2026-10-10 收到的用户背面照；2026-10-27 制作。按 EXIF 转正、未镜像，原件保留。",
    ]
    for i,t in enumerate(notes):
        d.text((35, 922+43*i), t, font=font(25 if i<2 else 22), fill=ink if i<2 else "#596a7d")
    canvas.save(OUT)
    assert hashlib.sha256(SRC.read_bytes()).hexdigest() == raw_sha
    manifest = {
        "date": "2026-10-27", "source": SRC.relative_to(ROOT).as_posix(),
        "source_sha256": raw_sha, "original_size": [1080,1440], "exif_orientation": 8,
        "display_size": [1440,1080], "transform": "EXIF transpose, no mirror; crop and proportional resize",
        "area_xyxy_in_display": AREA, "crop_xyxy_in_display": CROP_BOX,
        "evidence": "照片定位辅助；不能辨认 R31 单颗位号/阻值/网络", "outputs": []}
    for p in [OUT,CROP]:
        manifest["outputs"].append({"path":p.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
    (ROOT/"docs/references/扩展板双口惯性缺答复核/photo-location-manifest.json").write_text(
        json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
