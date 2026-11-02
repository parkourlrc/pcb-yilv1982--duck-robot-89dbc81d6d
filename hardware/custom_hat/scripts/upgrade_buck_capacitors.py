"""Increase buck capacitance margin using a documented 1210 X7R part."""
import copy
import json
from pathlib import Path
import uuid

import pipeline
from generate_rev_a import children, first, parse, q
from repair_release_metadata import properties, replace_children, set_property


EVIDENCE=pipeline.BASE.parents[1]/"docs/references/hat-simulation-tools-20261029/capacitor-upgrade-20261031"
BASELINE="09f1d958da205e4707848f6fb08b4cddaf02255d2f333e774bc5bb97b277f4fe"
MPN="C1210C226K3RACTU"
FOOTPRINT="Capacitor_SMD:C_1210_3225Metric"
POSITIONS={"C303":(126.84,108.5),"C304":(115.5,123.0),"C305":(149.0,114.5),"C306":(154.0,114.0)}
PREVIOUS_MPN={"C303":"C1206C106K3RACTU","C304":"C1206C106K3RACTU","C305":"C1206C226M4PACTU","C306":"C1206C226M4PACTU"}
FIELDS={"MPN":MPN,"Manufacturer":"KEMET","Voltage Rating":"25V","Dielectric":"X7R","Tolerance":"10%",
        "Datasheet":"https://search.kemet.com/component-documentation/download/specsheet/"+MPN,
        "Assembly Height":"2.5mm nominal; 2.8mm maximum",
        "BOM Comments":"Design-selected using archived per-part DC-bias model; nominal22uF is not effective capacitance; combined-condition and hardware verification pending"}


def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    if (EVIDENCE/"candidate.json").exists():
        raise FileExistsError("Inspect existing candidate before rerunning")
    if pipeline.digest(pipeline.PRIMARY/(pipeline.STEM+".kicad_pcb"))!=BASELINE:
        raise RuntimeError("Primary baseline changed")
    template_path=pipeline.find_cli().parent.parent/"share/kicad/footprints/Capacitor_SMD.pretty/C_1210_3225Metric.kicad_mod"
    template=parse(template_path.read_text(encoding="utf-8"))
    work=pipeline.prepare(pipeline.PRIMARY)
    pipeline.write_json(EVIDENCE/"candidate.json",{"project":str(work),"baseline":BASELINE,"promoted":False})
    seen={"pcb":set(),"schematic":set()}
    def update(node,board=False):
        fields=properties(node)
        reference=fields.get("Reference")
        if reference not in POSITIONS:
            return False
        if fields.get("MPN")!=PREVIOUS_MPN[reference]:
            raise RuntimeError("Capacitor selection changed: "+reference)
        set_property(node,"Value","22uF",board=board)
        for key,value in FIELDS.items():
            set_property(node,key,value,board=board)
        if not board:
            set_property(node,"Footprint",FOOTPRINT)
        else:
            node[1]=q(FOOTPRINT)
            first(node,"at")[1:3]=list(POSITIONS[reference])
            for key in ("descr","tags"):
                previous=first(node,key)
                replacement=copy.deepcopy(first(template,key))
                if previous:
                    node[node.index(previous)]=replacement
                elif replacement:
                    node.append(replacement)
            geometry_keys={"fp_line","fp_rect","fp_circle","fp_arc","fp_poly","fp_text","model"}
            node[:]=[entry for entry in node if not (isinstance(entry,list) and entry and entry[0] in geometry_keys)]
            for entry in template:
                if isinstance(entry,list) and entry and entry[0] in geometry_keys:
                    copied=copy.deepcopy(entry)
                    if entry[0]!="model":
                        copied.append(["uuid",q(uuid.uuid4())])
                    node.append(copied)
            for pad in children(node,"pad"):
                original=next(item for item in children(template,"pad") if item[1]==pad[1])
                pad[3]=original[3]
                for key in ("at","size","roundrect_rratio"):
                    existing=first(pad,key)
                    new=copy.deepcopy(first(original,key))
                    if existing:
                        pad[pad.index(existing)]=new
                    elif new:
                        pad.append(new)
        seen["pcb" if board else "schematic"].add(reference)
        return True
    for path in work.glob("*.kicad_sch"):
        original=path.read_text(encoding="utf-8")
        updated=replace_children(original,"symbol",update)
        if updated!=original:
            path.write_text("\n".join(line.rstrip() for line in updated.splitlines())+"\n",encoding="utf-8")
    path=work/"power.kicad_sch"
    note_changes=[]
    def note(node):
        if len(node)>1 and str(node[1]).startswith("Vout nominal4.984V;"):
            note_changes.append(str(node[1]))
            node[1]=q("Vout nominal4.984V; fsw nominal500kHz. C303/C304 input and C305/C306 output:22uF/25V X7R1210 each NOMINAL. Use DC-biased model values; C307 remains DNP.")
            return True
        return False
    path.write_text("\n".join(line.rstrip() for line in replace_children(path.read_text(encoding="utf-8"),"text",note).splitlines())+"\n",encoding="utf-8")
    if len(note_changes)!=1:
        raise RuntimeError("Expected power-sheet note")
    board_path=work/(pipeline.STEM+".kicad_pcb")
    board_path.write_text(replace_children(board_path.read_text(encoding="utf-8"),"footprint",lambda node:update(node,True)),encoding="utf-8")
    if any(references!=set(POSITIONS) for references in seen.values()):
        raise RuntimeError("Incomplete capacitor synchronization")
    pipeline.write_json(EVIDENCE/"change-contract.json",{"positions":POSITIONS,"previous_mpns":PREVIOUS_MPN,"new_mpn":MPN,"new_footprint":FOOTPRINT,
                         "new_fields":FIELDS,"library_template":str(template_path),"library_sha256":pipeline.digest(template_path),
                         "previous_power_note":note_changes[0],"c307_remains_dnp":True})
    reports,summary=pipeline.check(work)
    pipeline.write_json(EVIDENCE/"candidate.json",{"project":str(work),"baseline":BASELINE,"summary":str(reports/"summary.json"),"promoted":False})
    print(json.dumps({"project":str(work),"drc":summary["drc"],"erc":summary["erc"],"status":summary["status"]}))


if __name__=="__main__":
    main()
