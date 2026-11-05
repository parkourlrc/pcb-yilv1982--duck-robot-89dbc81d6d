"""Put locked MPNs in the portal's recognized Comment column without changing parts."""
import csv
import json
import re
from pathlib import Path

import pipeline


def main():
    checkpoint = pipeline.current_checkpoint()
    root = pipeline.BASE.parents[1]
    directory = pipeline.BASE / 'order-submission/20261103-five-hats'
    with (directory/'jlc-bom-smt.csv').open(encoding='utf-8-sig', newline='') as stream:
        previous = list(csv.DictReader(stream))
    explicit = {'U301':'SO-8-EP', 'U501':'LGA-16(3x4.5)', 'U701':'HVQFN-32-EP(5x5)',
                'U702':'TO-252', 'U801':'SOT-23-5', 'U802':'SOT-23-5', 'U803':'SOIC-8',
                'D301':'SMB', 'L301':'SMD,10.2x10.8mm', 'R309':'1206', 'R703':'0603'}
    converted=[]
    for row in previous:
        refs=row['Designator'].split(',')
        dimensions=re.search(r'[CR]_(0402|0805|1210)_',row['Footprint'])
        footprint=dimensions[1] if dimensions else explicit.get(refs[0],row['Footprint'].split(':')[-1])
        converted.append({'Comment':row['MPN'],'Designator':row['Designator'],'Footprint':footprint,
                          'Manufacturer':row['Manufacturer'],'Quantity':row['Quantity'],
                          'Value':row['Comment'],'MPN':row['MPN'],'KiCadFootprint':row['Footprint']})
    output=directory/'jlc-bom-exact-mpn.csv'
    with output.open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(converted[0]));writer.writeheader();writer.writerows(converted)
    if sum(int(row['Quantity']) for row in converted)!=52:
        raise RuntimeError('Component count changed')
    if any(old['MPN']!=new['Comment'] or old['Designator']!=new['Designator'] or old['Quantity']!=new['Quantity'] for old,new in zip(previous,converted)):
        raise RuntimeError('MPN/reference/quantity changed')
    report={'date':'2026-11-03','pcb_sha256':checkpoint['pcb_sha256'],'source_bom_sha256':pipeline.digest(directory/'jlc-bom-smt.csv'),
            'output':str(output.relative_to(root)),'output_sha256':pipeline.digest(output),
            'row_count':len(converted),'smt_components_per_unit':52,'mpn_reference_quantity_unchanged':True,
            'reason':'Portal recognized Comment as the model; a separate MPN column was not used by automatic matching',
            'automatic_matches_are_not_approved':True,'source_cad_unchanged':pipeline.current_checkpoint()['pcb_sha256']==checkpoint['pcb_sha256']}
    pipeline.write_json(root/'docs/references/自主扩展板下单记录/exact-bom-conversion.json',report)
    print(json.dumps(report))


if __name__=='__main__':
    main()
