"""Create a source-bound overview of the relocated feedback and compensation parts."""
import json
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont


ROOT=Path(__file__).resolve().parents[3]
EVIDENCE=ROOT/"docs/references/扩展板电路仿真工具/buck-control-20261031"


def main():
    picture=Image.open(EVIDENCE/"control-F-detail.png").convert("RGB")
    canvas=Image.new("RGB",(picture.width+420,picture.height+160),"white")
    origin=(20,85)
    canvas.paste(picture,origin)
    draw=ImageDraw.Draw(canvas)
    title=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",27)
    font=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",22)
    small=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",19)
    draw.text((20,12),"Buck 反馈/补偿重排：参数不变，原连接保留",font=title,fill="#203444")
    draw.text((20,48),"文件检查通过；未测环路稳定性或瞬态响应",font=small,fill="#52616b")
    placements=json.loads((EVIDENCE/"placement-contract.json").read_text(encoding="utf-8"))["positions"]
    def point(xpos,ypos):
        return (origin[0]+(xpos-122.735)/(135.104-122.735)*picture.width,
                origin[1]+(ypos-106.572)/(125.535-106.572)*picture.height)
    descriptions={
        "R301":["52.3k，高端反馈电阻","由输出电容附近取样"],
        "R302":["10k，低端反馈电阻","FB全网：19.96 → 6.33mm"],
        "R304":["14k，补偿电阻","COMP：26.16 → 4.51mm"],
        "C301":["3.3nF，补偿电容","RC连线：3.14 → 1.64mm"],
    }
    text_x=picture.width+50
    for reference,(xpos,ypos,_) in placements.items():
        color="#9b4f00" if reference in {"R301","R302"} else "#007660"
        top=point(xpos-.95,ypos-1.7)
        bottom=point(xpos+.95,ypos+1.7)
        draw.rectangle((*top,*bottom),outline=color,width=3)
        center=point(xpos,ypos)
        label_y=int(center[1]-35)
        draw.line((bottom[0],center[1],text_x-12,center[1]),fill=color,width=2)
        draw.text((text_x,label_y),reference,font=title,fill=color)
        for index,text in enumerate(descriptions[reference]):
            draw.text((text_x,label_y+36+index*31),text,font=font,fill="#203444")
    footer=picture.height+99
    draw.text((20,footer),"F.Cu 原生图派生；长度取自已验证铜对象。6处填孔盖铜要求仍需制造确认。",font=small,fill="#203444")
    canvas.save(EVIDENCE/"control-layout-review.png")
    print(EVIDENCE/"control-layout-review.png")


if __name__=="__main__":
    main()
