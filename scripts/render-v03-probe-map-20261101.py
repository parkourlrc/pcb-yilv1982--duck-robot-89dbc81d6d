#!/usr/bin/env python3
"""Render probe candidates from the archived manufacturing pad coordinates."""
import hashlib
import json
import math
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'docs/schematics/imu-to-dxl-scrapmeta-v0.3/production/imu_to_dxl_v03_gerber.zip'
OUT = ROOT/'docs/references/飞特策略模型上机核对'
FONT = Path('C:/Windows/Fonts/msyh.ttc')
COLORS = {'A': '#006da8', 'B': '#a45b00', 'C': '#d04b26', 'D': '#7845ad', 'G': '#168447'}
POINTS = {
    'A': ('U6_2', 'USART2_TX', 'MCU 发送 → U6 输入'),
    'B': ('R6_1', 'DXL_BUS', '外部 DATA，与 J1/J3 第 3 脚同网'),
    'C': ('R6_2', 'DXL_DATA', '芯片侧 DATA，与 U6-4、PA3 同网'),
    'D': ('R3_2', 'DXL_OE_', '发送使能 OE#，低电平使能'),
    'G': ('U6_3', 'GND', '附近地线候选点；不是测量通道'),
}


def main():
    with ZipFile(SOURCE) as z:
        raw = z.read('FlyingProbeTesting.json')
        data = json.loads(raw)
    pads = {}
    for row in data['pins']['rows']:
        pad = dict(zip(data['pins']['fields'], row))
        if pad['PIN_NAME'] in pads:
            previous = dict(pads[pad['PIN_NAME']])
            previous.pop('PIN_NO')
            current = dict(pad)
            current.pop('PIN_NO')
            assert previous == current, pad['PIN_NAME']
        pads[pad['PIN_NAME']] = pad
    for label, (name, net, _) in POINTS.items():
        assert pads[name]['NET_NAME'] == net, (label, name)
    assert pads['R6_1']['PIN_X'] > pads['R6_2']['PIN_X']
    assert pads['J1_3']['NET_NAME'] == pads['J3_3']['NET_NAME'] == 'DXL_BUS'
    assert pads['J2_5']['NET_NAME'] == 'UART1_TX'
    im = Image.new('RGB', (2100, 1370), '#f5f7fa')
    draw = ImageDraw.Draw(im)

    def text(xy, value, size=28, fill='#1c2e40', anchor=None):
        draw.text(xy, value, font=ImageFont.truetype(str(FONT), size), fill=fill, anchor=anchor)

    text((55, 34), 'v0.3 IMU：发送端与总线测点', 46)
    text((55, 103), '2026-11-01 · 依据已下单 Gerber 的 FlyingProbeTesting.json · 元件面顶视，不镜像', 27)
    text((55, 147), '这是生产焊盘坐标图，并非实物照片；先核对板型、朝向与丝印，再断电固定探头。', 27)
    text((65, 215), '整板定位：J2 在上，J1/J3 在下', 31)
    text((1150, 215), '左下通信区放大：未画铜线与实物焊锡', 30)
    board = (65, 275, 1052, 933)
    draw.rounded_rectangle(board, radius=26, fill='#e5efe9', outline='#456151', width=3)
    zoom = (1140, 275, 2035, 933)
    draw.rounded_rectangle(zoom, radius=20, fill='white', outline='#b7c3d0', width=2)

    def transform(p, expanded=False):
        if expanded:
            return 1190 + (p['PIN_X']-35)*1.76, 365 + (-p['PIN_Y']-470)*1.76
        return 65+p['PIN_X']*.7597, 275-p['PIN_Y']*.7597

    def pad_shape(p, expanded=False):
        x, y = transform(p, expanded)
        scale = 1.76 if expanded else .7597
        sx, sy = p['PAD_SIZEX']*scale, p['PAD_SIZEY']*scale
        angle = math.radians(p['PAD_ANGLE'])
        corners = [(x + dx*math.cos(angle)-dy*math.sin(angle),
                    y + dx*math.sin(angle)+dy*math.cos(angle))
                   for dx,dy in [(-sx/2,-sy/2),(sx/2,-sy/2),(sx/2,sy/2),(-sx/2,sy/2)]]
        color = '#bca77b'
        for label,(name,_,_) in POINTS.items():
            if p['PIN_NAME'] == name:
                color = COLORS[label]
        if p['PAD_SHAPE'] == 'C':
            draw.ellipse((x-sx/2,y-sy/2,x+sx/2,y+sy/2),fill=color,outline='#64717c',width=1)
        else:
            draw.polygon(corners,fill=color,outline='#64717c',width=2)
        if p['HOLE_SIZE']:
            r=p['HOLE_SIZE']*scale/2
            draw.ellipse((x-r,y-r,x+r,y+r),fill='#f5f7fa',outline='#64717c')

    for p in pads.values():
        pad_shape(p)
        if p['PIN_NAME'].split('_')[0] in ['U6','R3','R4','R6']:
            pad_shape(p,True)
    for x,y in [(59.055,-59.055),(1240.157,-59.055),(59.055,-807.087),(1240.157,-807.087)]:
        a,b=transform({'PIN_X':x,'PIN_Y':y})
        rr=43.307*.7597
        draw.ellipse((a-rr,b-rr,a+rr,b+rr),fill='#f5f7fa',outline='#789687',width=2)
    # Only labels and pads, not an invented copper connectivity drawing.
    for name,xy in {'J2':(560,292),'U2':(320,435),'U1':(540,540),'U3':(835,680),
                    'J1':(373,917),'J3':(703,917)}.items():
        text(xy,name,27,anchor='mm')
    for label in ['A','B','C','D','G']:
        p=pads[POINTS[label][0]]
        x,y=transform(p)
        draw.ellipse((x-9,y-9,x+9,y+9),outline=COLORS[label],width=4)
    draw.rectangle((101,621,437,803),outline='#bf3535',width=3)
    text((490,737),'红框为右侧放大区域',24)
    for name in ['J1_1','J1_2','J1_3','J3_1','J3_2','J3_3']:
        x,y=transform(pads[name])
        value={'1':'GND','2':'VBATT','3':'DATA'}[name[-1]]
        text((x,y-49),value,17,anchor='mm')

    # Enlarged pad numbers and individual callouts.
    for name in ['U6_1','U6_2','U6_3','U6_4','U6_5']:
        x,y=transform(pads[name],True)
        text((x+(-44 if name[-1] in '123' else 44),y),name[-1],24,anchor='mm')
    for label,xy in {'A':(1175,845),'B':(1920,815),'C':(1750,815),'D':(1410,318),'G':(1375,895)}.items():
        x,y=transform(pads[POINTS[label][0]],True)
        lx,ly=xy
        draw.line([(x,y),(lx,ly)],fill=COLORS[label],width=3)
        draw.ellipse((x-8,y-8,x+8,y+8),fill=COLORS[label],outline='white',width=2)
        draw.rounded_rectangle((lx-25,ly-24,lx+25,ly+24),radius=8,fill=COLORS[label])
        text((lx,ly),label,27,'white',anchor='mm')
    text((1375,641),'U6',25,anchor='mm')
    for component in ['R3','R4','R6']:
        members=[p for name,p in pads.items() if name.startswith(component+'_')]
        x=sum(transform(p,True)[0] for p in members)/2
        y=sum(transform(p,True)[1] for p in members)/2
        text((x,y-44),component,25,anchor='mm')
    text((1155,954),'A、G 位于相邻小焊盘：不能用粗探头横跨两脚。',23)
    descriptions=[
        ('A','U6 第 2 脚：USART2_TX；两通道时接 CH1。'),
        ('B','R6 第 1 焊盘（图中右端）：外部 DATA；CH2。'),
        ('C','R6 第 2 焊盘（图中左端）：芯片侧 DATA；可加 CH3。'),
        ('D','R3 第 2 焊盘（图中右端）：OE#；可加 CH4。'),
        ('G','U6 第 3 脚或确认的公共 GND：探头地线。'),
    ]
    for i,(label,desc) in enumerate(descriptions):
        y=1005+i*53
        draw.rounded_rectangle((65,y,104,y+37),radius=7,fill=COLORS[label])
        text((84,y+17),label,25,'white',anchor='mm')
        text((121,y+1),desc,27)
    text((65,1291),'注意：J2-5 是 UART1 调试日志 TX，不是 A。所有地夹只接公共 GND，不接 DATA、3V3 或 VBATT。',25)
    png=OUT/'imu-v03-probe-map-20261101.png'
    im.save(png)
    manifest={'date':'2026-11-01','kind':'Derived manufacturing pad-coordinate annotation, not a photograph or electrical measurement',
              'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'member':'FlyingProbeTesting.json','member_sha256':hashlib.sha256(raw).hexdigest(),
              'orientation':'Top component view, X right, PCB negative Y displayed down; J2 above J1/J3',
              'points':{label:{'pad':pads[name],'meaning':meaning} for label,(name,net,meaning) in POINTS.items()},
              'image_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),
              'limitations':['Must match actual manufactured board orientation and labels before probing',
                             'Copper traces and solder appearance are not rendered',
                             'Pad identity comes from manufacture export, not a new continuity measurement']}
    (OUT/'imu-v03-probe-map-source-20261101.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(png)


if __name__=='__main__':
    main()
