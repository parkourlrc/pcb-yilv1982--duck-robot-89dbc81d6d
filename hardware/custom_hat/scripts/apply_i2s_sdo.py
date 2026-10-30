"""Apply the reviewed I2S route plan in a full workspace and verify connectivity."""
from collections import Counter
import json
from pathlib import Path
import shutil
import tempfile

import pcbnew

import pipeline
import repair_u501
from verify_u501_connectivity import partitions


def point(position):
    return pcbnew.VECTOR2I(pcbnew.FromMM(position[0]),pcbnew.FromMM(position[1]))


def main():
    evidence=pipeline.BASE.parents[1]/'docs/references/hat-simulation-tools-20261029/i2s-sdo-repair-20261030'
    if (evidence/'result.json').exists():raise FileExistsError('Existing result must be reviewed first')
    plan=json.loads((evidence/'route-plan.json').read_text(encoding='utf-8'))
    nets={route['net'] for route in plan['plans']}
    assert nets=={'I2S_SDO','I2S_SDI','I2S_LRCK','I2S_BCLK'}
    work=pipeline.prepare(pipeline.PRIMARY)
    before_dir,before=pipeline.check(work)
    path=work/(pipeline.STEM+'.kicad_pcb')
    shutil.copy2(path,evidence/'before.kicad_pcb')
    board=pcbnew.LoadBoard(str(path))
    targets={item.m_Uuid.AsString():item for item in board.GetTracks() if item.GetNetname() in nets}
    if set(targets)!=set(plan['removed_uuids']):raise ValueError('Routing baseline changed')
    for item in targets.values():board.Remove(item)
    layers=[pcbnew.F_Cu,pcbnew.B_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu]
    created=[]
    for route in plan['plans']:
        net=board.FindNet(route['net'])
        for start,end in zip(route['points'],route['points'][1:]):
            if start[2]!=end[2]:
                assert start[:2]==end[:2]
                item=pcbnew.PCB_VIA(board)
                item.SetPosition(point(start))
                item.SetWidth(pcbnew.FromMM(route['via_diameter']))
                item.SetDrill(pcbnew.FromMM(route['via_drill']))
                item.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
            else:
                if start[:2]==end[:2]:continue
                item=pcbnew.PCB_TRACK(board)
                item.SetStart(point(start))
                item.SetEnd(point(end))
                item.SetWidth(pcbnew.FromMM(route['width']))
                item.SetLayer(layers[start[2]])
            item.SetNet(net)
            board.Add(item)
            created.append(item.m_Uuid.AsString())
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(path),board)
    after_dir,after=pipeline.check(work)
    shutil.copy2(path,evidence/'after.kicad_pcb')
    for label,directory in [('before',before_dir),('after',after_dir)]:
        for name in ['drc.json','summary.json','erc.json']:
            shutil.copy2(directory/name,evidence/(label+'-'+name))
    pipeline.write_json(evidence/'geometry-after.json',repair_u501.geometry(pcbnew.LoadBoard(str(path))))
    reports={label:json.loads((evidence/(label+'-drc.json')).read_text(encoding='utf-8')) for label in ['before','after']}
    changes={}
    for category in ['violations','unconnected_items','schematic_parity']:
        old=Counter(repair_u501.signature(item) for item in reports['before'][category])
        new=Counter(repair_u501.signature(item) for item in reports['after'][category])
        changes[category]={'added':list((new-old).elements()),'removed':list((old-new).elements())}
    groups={}
    commands=[]
    endpoints={}
    with tempfile.TemporaryDirectory(prefix='hat-i2s-connectivity-') as temporary:
        for label,source in [('before',pipeline.PRIMARY),('after',work)]:
            copied=Path(temporary)/label
            copied.mkdir()
            for source_path in pipeline.design_files(source):
                destination=copied/source_path.relative_to(source)
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source_path,destination)
            copied_board=copied/path.name
            report=copied/'filled-drc.json'
            pipeline.run_command([pipeline.find_cli(),'pcb','drc','--format','json','--severity-all','--refill-zones','--save-board','--output',report,copied_board],evidence,'connectivity-'+label,commands,report)
            loaded=pcbnew.LoadBoard(str(copied_board))
            groups[label]=partitions(loaded)
            endpoints[label]={}
            for footprint in loaded.GetFootprints():
                for pad in footprint.Pads():
                    if pad.GetNetname() in nets:endpoints[label][footprint.GetReference()+'.'+pad.GetNumber()]=pad.m_Uuid.AsString()
    splits={identifier:group for identifier,group in groups['before'].items() if not set(group).issubset(groups['after'].get(identifier,[]))}
    mapping=endpoints['after']
    connected=mapping['J101.40'] in groups['after'][mapping['U701.4']]
    accepted=not changes['violations']['added'] and not changes['schematic_parity']['added'] and not splits and connected
    accepted=accepted and not after['netlist_check']['mismatches'] and not after['netlist_check']['contract_differences']
    accepted=accepted and after['drc']['unconnected_items']['count']<before['drc']['unconnected_items']['count']
    pipeline.write_json(evidence/'connectivity-verification.json',{'commands':commands,'groups':groups,'endpoints':endpoints,'lost_connections':splits,'sdo_connected':connected})
    result={'work':str(work),'before_hash':pipeline.digest(evidence/'before.kicad_pcb'),'candidate_hash':pipeline.digest(path),'removed':plan['removed_uuids'],'created':created,'changes':changes,'local_acceptance':bool(accepted),'promoted':False}
    pipeline.write_json(evidence/'result.json',result)
    print(json.dumps({'acceptance':bool(accepted),'sdo_connected':connected,'lost_connections':len(splits),'before':before['drc'],'after':after['drc']}))
    if not accepted:raise SystemExit('Candidate rejected; main PCB unchanged')


if __name__=='__main__':main()
