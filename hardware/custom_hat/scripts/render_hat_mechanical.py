"""Render the measured mechanical scenario and native J301 pin order."""
import json
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont


ROOT=Path(__file__).resolve().parents[3]
EVIDENCE=ROOT/'docs/references/归档扩展板机械适配复核'


def main():
    data=json.loads((EVIDENCE/'mechanical-range.json').read_text(encoding='utf-8'))
    canvas=Image.new('RGB',(1280,700),'white')
    drawing=ImageDraw.Draw(canvas)
    heading=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',28)
    text=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
    small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
    drawing.text((35,20),'自主HAT：J301已改在B面插接，针孔和网络不变',font=heading,fill='#162d42')
    drawing.text((35,65),'从B面（插接端）观察；40P排母孔在上方，J301在下方。不是旧白色HAT接线图。',font=text,fill='#405568')
    names={1:'2S输入+',2:'GND',3:'5V输出',4:'3V3节点',5:'NC',6:'1V8节点',7:'舵机电池',8:'GND'}
    drawing.rounded_rectangle((80,145,1200,275),radius=12,outline='#364e60',width=3)
    for index,row in enumerate(data['j301_pins']):
        center=150+index*140
        color='#bc3131' if row['pin']==1 else '#1b2631' if row['pin'] in {2,8} else '#385f82'
        drawing.ellipse((center-22,188,center+22,232),outline=color,width=5)
        drawing.text((center-8,153),str(row['pin']),font=text,fill=color)
        drawing.text((center-49,242),names[row['pin']],font=small,fill=color)
    drawing.text((35,300),'F面焊尾视角的左右顺序相反：8 → 1。B面板上新增“1:2S+”“2:GND”。',font=text,fill='#243b53')
    drawing.text((35,338),'只把1、2针作为当前定义的2S输入；其它电压节点不能并接或反向灌电。',font=text,fill='#9b3030')
    drawing.text((35,398),'对插间距D：两块PCB相向表面之间的距离',font=heading,fill='#162d42')
    for index,gap in enumerate([12,12.5,13]):
        row=next(row for row in data['scenarios'] if row['board_front_face_gap_mm']==gap)
        drawing.text((50,447+index*42),f"D={gap:g}mm：SSW名义插深 {row['nominal_ssw_insertion_mm']:.2f}mm；J402含插头壳余隙 {row['minimum_selected_rigid_clearance_mm']:.2f}mm",font=text,fill='#243b53')
    drawing.text((35,590),'仅参考CAD/目录名义尺寸：线材弯曲、装配公差、散热片及头壳尚未纳入。',font=text,fill='#9b3030')
    drawing.text((35,630),'未指定隔离柱长度，未实装验证。源：'+data['pcb_sha256'][:12]+'；2026-11-02。',font=small,fill='#526879')
    canvas.save(EVIDENCE/'j301-and-spacing.png')
    print(EVIDENCE/'j301-and-spacing.png')


if __name__=='__main__':
    main()
