"""Record part-specific evidence without inferring missing assembly ratings."""
import argparse
import csv
import json
from pathlib import Path

import pipeline


ROOT = pipeline.BASE.parents[1]
EVIDENCE = ROOT / 'docs/references/归档扩展板贴片与层叠复核'
PRIOR = ROOT / 'docs/references/扩展板电路仿真工具'
EXACT = {
    'TLV320AIC3104IRHBR': ('2;260C;1YEAR', '260C package classification', '3000 large T&R', 'metadata-repair-20261030/sources/tlv320aic3104.pdf', '95', '不是整板回流曲线'),
    'LP38691DT-1.8/NOPB': ('2;260C;1YEAR', '260C package classification', '75 TUBE', 'metadata-repair-20261030/sources/lp38691.pdf', '22', '管装；需管料送料、转托盘或人工贴装'),
    'SN74LVC1G125DBVT': ('1;260C;UNLIM', '260C package classification', '250 small T&R', 'metadata-repair-20261030/sources/sn74lvc1g125.pdf', '19', '来料标签另验'),
    'SN74LVC1G126DBVR': ('1;260C;UNLIM', '260C package classification', '3000 large T&R', 'metadata-repair-20261030/sources/sn74lvc1g126.pdf', '20', '来料标签另验'),
    'AP64350SP-13': ('1', '260C lead temperature; not full reflow profile', '-13 T&R code', 'metadata-repair-20261030/sources/AP64350.pdf', '4,24', 'Diodes回流规范网页403，完整窗口未取得'),
    'PAM8302AADCR': ('1', '300C/5s soldering rating; not reflow peak', 'T&R code', 'metadata-repair-20261030/sources/PAM8302A.pdf', '2,13', '不得把300C焊接条件当回流峰值'),
    'BMI088': ('1', '260C peak; stencil 80-150um; aperture 70-90%', 'T&R', 'metadata-repair-20261030/sources/bst-bmi088-ds001.pdf', '57-58', '拼板开口81%；禁超声和干冰清洗'),
    'SMBJ12A-E3/52': ('1', 'LF peak260C', '52 tape code', 'bom-passives-20261031/sources/vishay-smbj.pdf', '1', '阴极与条带方向见原厂图'),
    'IHLP4040DZER5R6M5A': ('未取得5A系列明确等级', '未取得5A系列完整回流窗口', 'ER500/reel', 'final-bom-20261031/sources/vishay-ihlp4040dz-5a.pdf', '1-2', '不能借用DZ-11系列260C/30s/MSL1'),
    '08055A332JAT2A': ('未列', '260C solder-heat test; not full reflow profile', 'T2A code', 'bom-passives-20261031/sources/kyocera-c0g.pdf', '2-3', '0805支持回流；耐焊热试验不是生产曲线'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path)
    parser.add_argument('--supplement',type=Path)
    arguments = parser.parse_args()
    output = arguments.evidence.resolve() if arguments.evidence else EVIDENCE
    supplement = json.loads(arguments.supplement.read_text(encoding='utf-8')) if arguments.supplement else {}
    checkpoint = pipeline.current_checkpoint()
    package = ROOT / checkpoint['review_binding']['production_package']
    groups = {}
    with (package / 'bom-fitted.csv').open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            item = groups.setdefault(row['MPN'], {**row, 'Reference': [], 'Qty': 0})
            item['Reference'].extend(row['Reference'].split(','))
            item['Qty'] += int(row['Qty'])
    rows = []
    for mpn, group in sorted(groups.items()):
        source_base, assembly = PRIOR, 'SMT'
        if mpn in EXACT:
            msl, heat, packaging, source, pages, note = EXACT[mpn]
        elif group['Manufacturer'] == 'KEMET':
            x5r = 'PACTU' in mpn
            msl, heat, packaging = '族手册未单列', 'matte Sn peak<=260C; <=30s within5C; <=3 reflows', 'ACTU code'
            source = 'bom-passives-20261031/sources/' + ('kemet-x5r-c1006.pdf' if x5r else 'kemet-x7r.pdf')
            pages, note = ('10' if x5r else '13'), '150-200C/60-120s；TL217C/60-150s；升温<=3C/s；降温<=6C/s；不是整板设定'
        elif mpn.startswith('CRCW'):
            msl, heat, packaging = '未列', 'Reflow supported; 260+/-5C bath test is not a reflow profile', 'EA/ED tape code'
            source, pages, note = 'i2c-pullups-20261031/sources/vishay-dcrcwe3.pdf', '4,10', '完整曲线需系列规范和实板测温配套'
        elif mpn.startswith(('WSL1206', 'WSLP0603')):
            source_base = EVIDENCE
            msl, heat, packaging = '未列', '31052 Pb-free table:235C min/250C recommended/260C max', 'EA tape code'
            source, pages = 'material-evidence/vishay-solder-31052-resolved.pdf', '2'
            note = '本体手册引用31052；同页文字另写<=250C/20s；采用保守交集并实板测温，不抹去差异'
        elif mpn.startswith('BM0'):
            msl, heat, packaging = '未取得', 'SH sheet does not state full reflow window', 'TB T&R code'
            source, pages, note = 'final-bom-20261031/sources/jst-sh-sparkfun.pdf', '1-3', 'JST原厂内容的第三方存档，官网403；镀层回熔不是整件回流参数'
        else:
            assembly = 'THT后焊'
            msl, heat, packaging = '不纳入双面回流', 'After both SMT reflows; soldering limits remain part-specific', '未取得实际供料'
            source = 'final-bom-20261031/sources/jst-catalogue-120.pdf' if mpn.startswith('B3B') else ''
            pages, note = ('35-36' if source else ''), '6件每板后焊；后焊窗口、尾针和实装另核'
        rows.append({'MPN': mpn, 'Reference': ','.join(sorted(group['Reference'])), 'Qty': group['Qty'], 'Assembly': assembly,
                     'MSL': msl, 'Thermal_basis': heat, 'Packaging_basis': packaging,
                     'Source': str((source_base / source).relative_to(ROOT)) if source else '既有Samtec连接器证据',
                     'PDF_pages': pages, 'Status_note': note, 'Lot_verified': False})
    if len(rows) != 35 or sum(row['Qty'] for row in rows) != 58:
        raise RuntimeError('Unexpected BOM inventory')
    for row in rows:
        if row['MPN'] in supplement:
            update = supplement[row['MPN']]
            if set(update)-{'MSL','Thermal_basis','Packaging_basis','Source','PDF_pages','Status_note'}:
                raise RuntimeError('Supplement attempts to change BOM identity')
            row.update(update)
            if not (ROOT/row['Source']).is_file():
                raise FileNotFoundError(row['Source'])
    with (output / 'material-process-matrix.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    pipeline.write_json(output / 'material-process-matrix.json', {'pcb_sha256': checkpoint['pcb_sha256'], 'unique_mpn': 35,
        'fitted': 58, 'smt': 52, 'tht': 6, 'rows': rows, 'whole_board_reflow_profile_approved': False, 'hardware_tested': False})
    print(json.dumps({'unique_mpn': len(rows), 'fitted': sum(row['Qty'] for row in rows)}))


if __name__ == '__main__':
    main()
