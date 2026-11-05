import importlib.util
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/references/扩展板电路仿真工具/power-repair-20261030'


def main():
    spec=importlib.util.spec_from_file_location('i2s_renderer',ROOT/'scripts/render-hat-i2s-repair.py')
    renderer=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    renderer.COLORS={'+3V3':'#efb548','POWER_GND':'#45b090'}
    before=json.loads((EVIDENCE/'geometry-before.json').read_text(encoding='utf-8'))
    after=json.loads((EVIDENCE/'geometry-after.json').read_text(encoding='utf-8'))
    image=Image.new('RGB',(2700,1360),'#101b2a')
    configs=[
        (before,'B.Cu',(100,100,165,131),12,'修复前 · B.Cu电源/地'),
        (after,'B.Cu',(100,100,165,131),12,'修复后 · B.Cu电源/地'),
        (after,'F.Cu',(100,100,165,131),12,'修复后 · F.Cu电源/地'),
        (after,'F.Cu',(158.5,106,165,115),55,'IMU供电扇出 · F.Cu'),
        (after,'B.Cu',(146.5,110.5,152.5,116),85,'Codec局部 · U701.7仍待接'),
        (after,'B.Cu',(129.5,122.5,137,129),70,'TTL局部 · 地岛已接回'),
    ]
    for index,args in enumerate(configs):
        image.paste(renderer.panel(*args),((index%3)*900,(index//3)*620))
    draw=ImageDraw.Draw(image)
    draw.text((25,1250),'黄：+3V3；绿：POWER_GND；灰：其他铜。193个有网焊盘原连接保留，未连接22→1。',font=renderer.font(26),fill='white')
    draw.text((25,1290),'全部同一顶视坐标，底层未镜像；未显示填充铜，焊盘为外接框近似。实际地连通依据重铺铜后的KiCad连通图。',font=renderer.font(22),fill='#bac8d5')
    draw.text((25,1323),'来源：Rev A修复前后PCB几何，2026-10-30。仅为局部核对图，不是载流、实物功能或制造放行。',font=renderer.font(22),fill='#bac8d5')
    image.save(EVIDENCE/'power-route-review.png')


if __name__=='__main__':main()
