"""Use identical 0.175mm probes to prove both panel units load the Power clearance."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import pcbnew
import pipeline
from add_i2c_pullups import vector


def main():
    evidence=pipeline.BASE.parents[1]/'docs/references/扩展板邮票孔与电源修复'
    results=[]
    for revision in ['r17','r18']:
        source=pipeline.BASE/'panels'/('a1-smt-2up-20261102-'+revision)
        with tempfile.TemporaryDirectory(prefix='class-probe-'+revision+'-',dir=evidence) as temporary:
            work=Path(temporary).resolve()
            if not work.is_relative_to(evidence.resolve()):
                raise RuntimeError('Probe workspace outside evidence folder')
            for path in source.iterdir():
                if path.is_file() and path.suffix in {'.kicad_pcb','.kicad_pro','.kicad_dru'}:
                    shutil.copy2(path,work/path.name)
            path=work/'hat_a1_smt_2up.kicad_pcb'
            board=pcbnew.LoadBoard(str(path))
            nets={net.GetNetname():net for net in board.GetNetsByNetcode().values()}
            probes=[]
            for prefix,origin_y in [('',118),('B2/',122)]:
                ids=[]
                for net_name,offset in [('+3V3',0),('I2C5_SCL',.375)]:
                    segment=pcbnew.PCB_TRACK(board)
                    segment.SetStart(vector((95,origin_y+offset)))
                    segment.SetEnd(vector((96,origin_y+offset)))
                    segment.SetWidth(pcbnew.FromMM(.2))
                    segment.SetLayer(pcbnew.F_Cu)
                    segment.SetNet(nets[prefix+net_name])
                    board.Add(segment)
                    ids.append(segment.m_Uuid.AsString())
                probes.append({'unit':prefix or 'A1','segment_ids':ids})
            pcbnew.SaveBoard(str(path),board)
            report=evidence/('netclass-probe-'+revision+'.json')
            completed=subprocess.run(list(map(str,[pipeline.find_cli(),'pcb','drc','--format','json','--severity-all','--output',report,path])),capture_output=True,timeout=180)
            (evidence/('netclass-probe-'+revision+'.log')).write_bytes(completed.stdout+completed.stderr)
            completed.check_returncode()
            document=json.loads(report.read_text(encoding='utf-8'))
            for probe in probes:
                targeted=[row for row in document['violations'] if row['type']=='clearance' and set(item['uuid'] for item in row['items'])==set(probe['segment_ids'])]
                results.append({'revision':revision,'unit':probe['unit'],'edge_gap_mm':.175,'power_clearance_expected_mm':.2,
                    'targeted_clearance_findings':targeted,'rejected_as_power':bool(targeted)})
    expected=[True,False,True,True]
    outcome={'results':results,'matches_expected_failure_and_repair':[row['rejected_as_power'] for row in results]==expected,
        'source_files_unchanged':True,'probe_drc_is_not_design_acceptance':True}
    pipeline.write_json(evidence/'netclass-loading-negative-control.json',outcome)
    print(json.dumps(outcome,ensure_ascii=False))
    if not outcome['matches_expected_failure_and_repair']:
        raise RuntimeError('Panel netclass negative control failed')


if __name__=='__main__':
    main()
