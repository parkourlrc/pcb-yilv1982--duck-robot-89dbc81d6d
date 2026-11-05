"""Constrain the filled codec via solder-side land to the original QFN pad width."""
import json
from pathlib import Path

import pcbnew
import pipeline


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板音频芯片焊盘'
IDENTIFIER='c6ad78c2-361f-4c03-a650-a32f6c415d72'


def main():
    EVIDENCE.mkdir(exist_ok=False)
    checkpoint=pipeline.current_checkpoint();work=pipeline.prepare(pipeline.PRIMARY)
    path=work/(pipeline.STEM+'.kicad_pcb');board=pcbnew.LoadBoard(str(path))
    via=next(item for item in board.GetTracks() if item.m_Uuid.AsString()==IDENTIFIER)
    pad=next(pad for pad in board.FindFootprintByReference('U701').Pads() if pad.GetNumber()=='7')
    if via.GetPosition()!=pad.GetPosition() or via.GetFrontWidth()!=350000 or via.GetDrill()!=150000:
        raise RuntimeError('Unexpected codec via baseline')
    via.Padstack().SetMode(pcbnew.PADSTACK.MODE_FRONT_INNER_BACK)
    via.SetWidth(pcbnew.F_Cu,pcbnew.FromMM(.35))
    via.SetWidth(pcbnew.In1_Cu,pcbnew.FromMM(.35))
    via.SetWidth(pcbnew.B_Cu,pcbnew.FromMM(.25))
    pcbnew.SaveBoard(str(path),board)
    rule='''
(rule "Codec solder-side filled via land"
  (layer B.Cu)
  (condition "A.Type == 'Via' && A.Via_Type == 'Through' && A.NetName == '+3V3' && A.insideCourtyard('U701') && A.Hole == 0.15mm")
  (constraint annular_width (min 0.05mm))
  (constraint via_diameter (min 0.25mm))
  (constraint hole_size (min 0.15mm)))
'''
    rules=work/(pipeline.STEM+'.kicad_dru')
    rules.write_text(rules.read_text(encoding='utf-8').rstrip()+'\n'+rule,encoding='utf-8')
    reports,summary=pipeline.check(work)
    result={'baseline':checkpoint['pcb_sha256'],'project':str(work),'summary':str(reports/'summary.json'),'status':summary['status'],'drc':summary['drc'],
            'changed_via':IDENTIFIER,'diameters_mm':{board.GetLayerName(layer):pcbnew.ToMM(via.GetWidth(layer)) for layer in (pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu)},
            'drill_mm':.15,'original_qfn_pad_size_mm':[pcbnew.ToMM(value) for value in pad.GetSize()],
            'filled':via.GetFillingMode()==pcbnew.FILLING_MODE_FILLED,'capped':via.GetCappingMode()==pcbnew.CAPPING_MODE_CAPPED,
            'added_rule':rule,'promoted':False,'manufacturer_job_acceptance':False}
    pipeline.write_json(EVIDENCE/'candidate.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
