import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/references/扩展板电路仿真工具/i2s-sdo-repair-20261030'
COLORS={'I2S_SDO':'#f7bc49','I2S_SDI':'#48c6e8','I2S_LRCK':'#c28cf2','I2S_BCLK':'#e87898'}


def font(size):return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',size)


def panel(items,layer,region,scale,title):
    width,height=900,620
    image=Image.new('RGB',(width,height),'#101b2a')
    draw=ImageDraw.Draw(image)
    def pixel(position):return (round(65+(position[0]-region[0])*scale),round(70+(position[1]-region[1])*scale))
    def visible(bounds):return not(bounds[2]<region[0] or bounds[0]>region[2] or bounds[3]<region[1] or bounds[1]>region[3])
    draw.text((20,12),title,font=font(25),fill='white')
    spacing=5 if scale<30 else 1
    for xpos in range(math.ceil(region[0]),math.floor(region[2])+1):
        if xpos%spacing:continue
        screen=pixel((xpos,region[1]))[0]
        draw.line((screen,60,screen,height-40),fill='#273748')
        draw.text((screen-14,43),str(xpos),font=font(13),fill='#a0b4c5')
    for ypos in range(math.ceil(region[1]),math.floor(region[3])+1):
        if ypos%spacing:continue
        screen=pixel((region[0],ypos))[1]
        draw.line((60,screen,width-35,screen),fill='#273748')
        draw.text((18,screen-8),str(ypos),font=font(13),fill='#a0b4c5')
    for item in sorted(items,key=lambda item:{'track':0,'pad':1,'via':2}.get(item['kind'],3)):
        color=COLORS.get(item.get('net'),'#50647a')
        if item['kind']=='track' and item['layer']==layer:
            first,last=item['start'],item['end']
            bounds=(min(first[0],last[0]),min(first[1],last[1]),max(first[0],last[0]),max(first[1],last[1]))
            if visible(bounds):draw.line([pixel(first),pixel(last)],fill=color,width=max(2,round(item['width']*scale)))
        elif item['kind']=='pad':
            layers=item['layers']
            present=layer in layers or set(layers)=={'F.Cu','B.Cu'}
            if not present or not visible(item['bounds']):continue
            left,top,right,bottom=item['bounds']
            draw.rectangle([pixel((left,top)),pixel((right,bottom))],fill=color,outline='#b1bfcd')
            if scale>30 or item.get('net') in COLORS:
                draw.text(pixel(((left+right)/2,(top+bottom)/2)),item['number'],font=font(13),fill='white',anchor='mm')
        elif item['kind']=='via':
            xpos,ypos=item['position']
            if not visible((xpos,ypos,xpos,ypos)):continue
            center=pixel((xpos,ypos));radius=item['width']*scale/2
            draw.ellipse((center[0]-radius,center[1]-radius,center[0]+radius,center[1]+radius),fill=color)
            radius=item['drill']*scale/2
            draw.ellipse((center[0]-radius,center[1]-radius,center[0]+radius,center[1]+radius),fill='#101b2a',outline='#b1bfcd')
    draw.rectangle((0,0,width,42),fill='#101b2a')
    draw.text((20,12),title,font=font(25),fill='white')
    return image


def main():
    before=json.loads((EVIDENCE/'geometry-before.json').read_text(encoding='utf-8'))
    after=json.loads((EVIDENCE/'geometry-after.json').read_text(encoding='utf-8'))
    image=Image.new('RGB',(2700,1360),'#101b2a')
    for index,layer in enumerate(['F.Cu','B.Cu','In1.Cu']):
        image.paste(panel(after,layer,(119,100.5,159,117),19,'修复后 · '+layer+' · I2S路径'),(index*900,0))
    image.paste(panel(before,'B.Cu',(147.7,110.5,151.5,115.5),105,'修复前 · codec底层扇出'),(0,620))
    image.paste(panel(after,'B.Cu',(147.7,110.5,151.5,115.5),105,'修复后 · codec底层扇出'),(900,620))
    image.paste(panel(after,'F.Cu',(147.7,110.5,151.5,115.5),105,'修复后 · 同区域顶层'),(1800,620))
    draw=ImageDraw.Draw(image)
    draw.text((25,1250),'黄 I2S_SDO｜蓝 I2S_SDI｜紫 I2S_LRCK｜粉 I2S_BCLK；其他铜以灰色表示。位置/针序不变。',font=font(26),fill='white')
    draw.text((25,1290),'全部采用同一顶视坐标，底层未镜像；未显示填充铜。焊盘为外接框近似，不能代替DRC/实际时序与制造验收。',font=font(22),fill='#bac8d5')
    draw.text((25,1323),'来源：本项目Rev A修复前后PCB几何，2026-10-30。',font=font(22),fill='#bac8d5')
    image.save(EVIDENCE/'i2s-route-review.png')


if __name__=='__main__':main()
