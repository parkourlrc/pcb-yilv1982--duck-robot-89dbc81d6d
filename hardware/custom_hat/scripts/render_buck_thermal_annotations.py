"""Annotate the native buck-region images without replacing the source renders."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT=Path(__file__).resolve().parents[3]
EVIDENCE=ROOT/"docs/references/扩展板电路仿真工具/buck-thermal-20261031"


def main():
    front=Image.open(EVIDENCE/"buck-F-detail.png").convert("RGB")
    back=Image.open(EVIDENCE/"buck-B-detail.png").convert("RGB")
    font=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",23)
    heading=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",29)
    canvas=Image.new("RGB",(front.width+back.width+60,max(front.height,back.height)+180),"white")
    draw=ImageDraw.Draw(canvas)
    draw.text((20,12),"HAT 电源局部修复：文件验证通过，未制造/未测温",font=heading,fill="#182b3a")
    origins=[(20,70),(front.width+40,70)]
    for origin,picture in zip(origins,(front,back)):
        canvas.paste(picture,origin)
    def point(origin,xpos,ypos):
        return (origin[0]+(xpos-119.48)/(133.151-119.48)*front.width,
                origin[1]+(ypos-105.368)/(121.02-105.368)*front.height)
    def box(origin,bounds,color,label):
        start=point(origin,bounds[0],bounds[1])
        end=point(origin,bounds[2],bounds[3])
        draw.rectangle((*start,*end),outline=color,width=4)
        position=(start[0],max(origin[1]+3,start[1]-33))
        text_bounds=draw.textbbox(position,label,font=font)
        draw.rectangle(text_bounds,fill="white")
        draw.text(position,label,font=font,fill=color)
    box(origins[0],(124.635,107.65,129.045,109.95),"#008000","C303：输入10µF")
    box(origins[0],(124.249,112.6935,127.751,115.3065),"#ffbb00","U301 EP：5个地热孔")
    box(origins[1],(122.725,113.95,124.675,117.25),"#008000","C308：靠近LDO输入")
    box(origins[1],(124.249,112.6935,127.751,115.3065),"#ffbb00","热孔已避开背面焊盘")
    footer=max(front.height,back.height)+88
    draw.text((20,footer),"左：F.Cu   右：B.Cu（同一顶视坐标，未镜像）",font=font,fill="#182b3a")
    draw.text((20,footer+34),"新增VIN线约2.70mm；5个热孔需填孔盖铜。几何连通不等于热能力/制造放行。",font=font,fill="#182b3a")
    canvas.save(EVIDENCE/"thermal-layout-review.png")
    print(EVIDENCE/"thermal-layout-review.png")


if __name__=="__main__":
    main()
