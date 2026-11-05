"""Check panel replication, copper isolation, tooling and optical clearances."""
from collections import Counter
import copy
import csv
import argparse
import json
import math
from pathlib import Path

import pcbnew
import pipeline
from audit_panel_edges import analyze_panel_edges
from verify_release_metadata import snapshot


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/归档扩展板贴片规范复查"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--drc',default='panel-drc-r5.json')
    arguments=parser.parse_args()
    checkpoint = pipeline.current_checkpoint()
    contract = json.loads((EVIDENCE / "panel-candidate.json").read_text(encoding="utf-8"))
    path = Path(contract["panel"])
    report = json.loads((EVIDENCE / arguments.drc).read_text(encoding="utf-8"))
    source = snapshot(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb"))
    panel = snapshot(path)
    board = pcbnew.LoadBoard(str(path))
    source_board=pcbnew.LoadBoard(str(pipeline.PRIMARY/(pipeline.STEM+'.kicad_pcb')))
    source_project=json.loads((pipeline.PRIMARY/(pipeline.STEM+'.kicad_pro')).read_text(encoding='utf-8'))
    panel_project=json.loads(path.with_suffix('.kicad_pro').read_text(encoding='utf-8'))
    expected_project=copy.deepcopy(source_project)
    settings=expected_project['net_settings']
    original_patterns=list(settings.get('netclass_patterns',[]))
    settings['netclass_patterns']=[*original_patterns,*({**row,'pattern':'B2/'+row['pattern']} for row in original_patterns)]
    for field in ['netclass_assignments','net_colors']:
        original_values=dict(settings.get(field,{}))
        settings[field]={**original_values,**{'B2/'+name:value for name,value in original_values.items()}}
    inherited_netclasses_and_settings=panel_project==expected_project
    if not inherited_netclasses_and_settings:
        raise RuntimeError('Panel project does not preserve both units net classes and all original settings')
    edge_audit=analyze_panel_edges(source_board,board,contract)
    edge_audit.update(source_pcb_sha256=checkpoint['pcb_sha256'],panel_sha256=pipeline.digest(path),
                      panel_project_sha256=pipeline.digest(path.with_suffix('.kicad_pro')),
                      panel_rules_sha256=pipeline.digest(path.with_suffix('.kicad_dru')))
    pipeline.write_json(path.parent/'edge-copper-reference-check.json',edge_audit)
    label_errors=[]
    copied_labels=[item for item in board.GetDrawings() if item.Type()==pcbnew.PCB_TEXT_T]
    for footprint in source_board.GetFootprints():
        label=footprint.Reference()
        if not label.IsVisible():
            continue
        target=label.GetPosition()+pcbnew.VECTOR2I(0,32000000)
        matches=[item for item in copied_labels if item.GetText()==label.GetText() and item.GetPosition()==target]
        if len(matches)!=1 or any((matches[0].GetDrawRotation().AsDegrees()!=label.GetDrawRotation().AsDegrees(),
                matches[0].GetTextSize()!=label.GetTextSize(),matches[0].GetTextThickness()!=label.GetTextThickness(),
                matches[0].GetHorizJustify()!=label.GetHorizJustify(),matches[0].GetVertJustify()!=label.GetVertJustify(),
                matches[0].IsMirrored()!=label.IsMirrored(),matches[0].GetLayer()!=label.GetLayer())):
            label_errors.append(footprint.GetReference())
    source_vias={item.m_Uuid.AsString():item for item in source_board.GetTracks() if item.Type()==pcbnew.PCB_VIA_T}
    panel_vias={item.m_Uuid.AsString():item for item in board.GetTracks() if item.Type()==pcbnew.PCB_VIA_T}
    via_layer_mismatches=[]
    for row in contract['maps']['tracks']:
        if row['source'] not in source_vias:continue
        original_via=source_vias[row['source']]
        for identifier in (row['source'],row['panel']):
            actual_via=panel_vias[identifier]
            if any(actual_via.GetWidth(layer)!=original_via.GetWidth(layer) for layer in (pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu)):
                via_layer_mismatches.append(identifier)
    originals_same = all(panel["pads"].get(identifier) == values and panel["nets"].get(identifier) == source["nets"][identifier] for identifier, values in source["pads"].items())
    original_tracks_same = all(panel["tracks"].get(identifier) == values for identifier, values in source["tracks"].items())
    footprint_map = {row["source"]: row["panel"] for row in contract["maps"]["footprints"]}
    panel_pads = {(row["reference"], row["pin"], tuple(row["position"]), row["layers"]): identifier for identifier, row in panel["pads"].items()}
    duplicate_pad_map, errors = {}, []
    for identifier, values in source["pads"].items():
        copied = panel_pads.get((footprint_map[values["reference"]], values["pin"],
                                (values["position"][0],values["position"][1]+32000000),values["layers"]))
        if not copied:
            errors.append([identifier,"missing copied pad"])
            continue
        duplicate_pad_map[identifier] = copied
        expected = {**values, "reference":footprint_map[values["reference"]],"position":[values["position"][0],values["position"][1]+32000000]}
        if panel["pads"][copied] != expected or panel["nets"][copied] != ("B2/"+source["nets"][identifier] if source["nets"][identifier] else ""):
            errors.append([identifier,"copied geometry/net differs"])
    for row in contract["maps"]["tracks"]:
        values = source["tracks"][row["source"]]
        expected = {**values,"start":[values["start"][0],values["start"][1]+32000000],"end":[values["end"][0],values["end"][1]+32000000],"net":"B2/"+values["net"]}
        if panel["tracks"].get(row["panel"]) != expected:
            errors.append([row["source"],"copied track/via differs"])
    lost, cross_unit = [], []
    source_ids = set(source["pads"])
    copied_ids = set(duplicate_pad_map.values())
    for identifier, group in source["connections"].items():
        if not set(group).issubset(panel["connections"].get(identifier, [])):
            lost.append([identifier,"unit1"])
        copied = duplicate_pad_map[identifier]
        required = {duplicate_pad_map[other] for other in group}
        if not required.issubset(panel["connections"].get(copied, [])):
            lost.append([identifier,"unit2"])
        if set(panel["connections"].get(identifier,[])) & copied_ids or set(panel["connections"].get(copied,[])) & source_ids:
            cross_unit.append(identifier)
    marks = []
    for footprint in board.GetFootprints():
        if not footprint.GetReference().startswith("PFID_"):
            continue
        pad = next(iter(footprint.Pads()))
        point = pad.GetPosition()
        layer = footprint.GetLayer()
        point_mm = [pcbnew.ToMM(value) for value in point]
        probe = pcbnew.PCB_VIA(board)
        probe.SetPosition(point)
        probe.SetWidth(pcbnew.FromMM(6))
        hits = []
        for other in board.GetFootprints():
            if other.m_Uuid == footprint.m_Uuid:
                continue
            for other_pad in other.Pads():
                if other_pad.IsOnLayer(layer) and other_pad.GetEffectiveShape(layer).Collide(probe.GetEffectiveShape(layer),0):
                    hits.append(other.GetReference())
        for track in board.GetTracks():
            if track.IsOnLayer(layer) and track.GetEffectiveShape(layer).Collide(probe.GetEffectiveShape(layer),0):
                hits.append(track.m_Uuid.AsString())
        for zone in board.Zones():
            if zone.IsOnLayer(layer) and zone.GetFilledPolysList(layer).Collide(probe.GetEffectiveShape(layer),0):
                hits.append(zone.m_Uuid.AsString())
        edge_distance = min(point_mm[0]-90,175-point_mm[0],point_mm[1]-90,172-point_mm[1])
        marks.append({"reference":footprint.GetReference(),"position_mm":point_mm,"layer":board.GetLayerName(layer),
                      "copper_diameter_mm":pcbnew.ToMM(pad.GetSize().x),"mask_diameter_mm":pcbnew.ToMM(pad.GetSize().x+2*pad.GetSolderMaskExpansion(pcbnew.F_Mask if layer==pcbnew.F_Cu else pcbnew.B_Mask)),
                      "nearest_outer_straight_edge_mm":edge_distance,"foreign_copper_within_3mm":hits})
    process_notes = ["自主HAT A.1双联拼板候选：尚未制造放行，不直接下单。",
                     "A1与A2两单元相同；A2坐标位号带B2_前缀，对应原位号丝印，映射见unit-reference-map.csv。",
                     "标准型双面SMT，两单元各52个SMT件；C307/B2_C307不装且不印锡膏。",
                     "每单元6个通孔件安排在双面回流后后焊，不采用要求插件脚周围5mm净空的整板波峰焊。",
                     "U501/B2_U501为BMI088 MEMS：禁用整板干冰/超声清洗，局部清洗剂和方法需按器件资料核相容性。",
                     "BMI088信号焊盘钢网面积按81%导出；Bosch第57页建议70%～90%。全板钢网设计基线0.125mm，实际厚度公差/孔壁/SPI及曲线另核，不按80～150um任意选。",
                     "BMI088 MSL1、峰值260℃是器件手册上限，不直接当整板炉温设定；其余器件须核对应包装/耐温及暴露时间。",
                     "含L301的F面作为第二回流设计基线；B面U702/SH等保持、曲线及必要治具仍须实际工艺评估。全部THT后焊。",
                     "设备使用工艺边PFID全局点定位；单元内FID不能替代该组工艺边定位点。",
                     "邮票孔列位于单元名义边线，连接带全铜层局部清铜。分板需支撑PCB，毛刺/凹口/应力及实际机械配合另验，不能掰裂铜或器件。",
                     "U701.7焊接面via铜盘按当前分层padstack为0.25mm，另三铜层0.35mm，机械孔0.15mm；必须填孔盖铜，详见逐层工艺CSV。",
                     "C305与C310已移位并采用0.25mm热连接臂及0.2mm隔离；原连接及I2S参考铜保持，焊接良率和电源瞬态尚无实测。",
                     "U702精确料号LP38691DT-1.8/NOPB为75支管装，需管料送料、转托盘或人工贴装。",
                     "U701与U702为MSL2、260C分类、1YEAR floor life；U801与U802为MSL1；开封和干燥记录按来料标签执行。",
                     "层叠设计参考JLC041611-7628：外铜35um、内铜30um；尚未接单或实测。完整材料曲线缺口见本轮物料矩阵。"]
    (path.parent / "ASSEMBLY-NOTES.txt").write_text("\n".join(process_notes)+"\n",encoding="utf-8")
    source_package = pipeline.BASE.parents[1] / checkpoint["review_binding"]["production_package"]
    with (source_package / "positions-smt.csv").open(encoding="utf-8-sig",newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        placements = list(reader)
    with (path.parent / "panel-positions-smt.csv").open("w",encoding="utf-8-sig",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=columns)
        writer.writeheader()
        writer.writerows(placements)
        writer.writerows({**row,"Ref":"B2_"+row["Ref"],"PosY":format(float(row["PosY"])-32,".6f")} for row in placements)
    with (path.parent / "unit-reference-map.csv").open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.writer(stream)
        writer.writerow(["Unit","PanelReference","SilkscreenReference","OffsetX_mm","OffsetY_mm"])
        for row in placements:
            writer.writerow(["A1",row["Ref"],row["Ref"],0,0])
            writer.writerow(["A2","B2_"+row["Ref"],row["Ref"],0,32])
    result={"source_pcb_sha256":checkpoint["pcb_sha256"],"panel_sha256":pipeline.digest(path),"unit_count":2,
            "panel_project_sha256":pipeline.digest(path.with_suffix('.kicad_pro')),
            "panel_rules_sha256":pipeline.digest(path.with_suffix('.kicad_dru')),
            "edge_audit_sha256":pipeline.digest(path.parent/'edge-copper-reference-check.json'),
            "original_pad_geometry_nets_preserved":originals_same,"original_tracks_preserved":original_tracks_same,
            "duplicate_errors":errors,"lost_connections":lost,"cross_unit_connections":cross_unit,
            "per_layer_via_diameter_mismatches":via_layer_mismatches,"copied_label_style_errors":label_errors,"edge_copper_reference_check_pass":edge_audit['accepted'],
            "both_units_netclasses_and_original_project_settings_preserved":inherited_netclasses_and_settings,
            "drc_violations":len(report["violations"]),"unconnected":len(report["unconnected_items"]),"fiducials":marks,
            "panel_smt_positions":len(placements)*2,"smt_unit_counts":[len(placements),len(placements)],
            "all_mark_geometry_checks_pass":len(marks)==6 and all(row["copper_diameter_mm"]==1 and row["mask_diameter_mm"]==2 and row["nearest_outer_straight_edge_mm"]>=3.85 and not row["foreign_copper_within_3mm"] for row in marks),
            "manufacturing_released":False,"source_board_remaining_findings_preserved":True}
    result["replication_and_panel_drc_pass"] = all((originals_same,original_tracks_same,not errors,not lost,not cross_unit,
                                                   not report["violations"],not report["unconnected_items"],not via_layer_mismatches,not label_errors,edge_audit['accepted'],result["all_mark_geometry_checks_pass"]))
    pipeline.write_json(EVIDENCE/"panel-verification.json",result)
    print(json.dumps(result,ensure_ascii=False))
    if not result["replication_and_panel_drc_pass"]:
        raise RuntimeError("Panel validation failed")


if __name__ == "__main__":
    main()
