"""Select final BOM parts and align two power footprints with manufacturer lands."""
import json
from pathlib import Path
import uuid

import pcbnew
import pipeline
from generate_rev_a import children, first, q
from repair_release_metadata import properties, replace_children, set_property
from select_header_connectors import rectangle, line


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/final-bom-20261031"
BASELINE = "ac2df1571ac0fe778bbbf427bd90e8d548cdb644fca0e0728c79e034d6767abc"
JST_CATALOGUE = "https://www.jst.fr/doc/jst/pdf/jst-connector-catalogue-vol-120e.pdf"
JST_SH = "https://cdn.sparkfun.com/assets/0/e/1/5/8/JST-SH_right_angle_PRT-25271.pdf"
PARTS = {
    "J401": ("B3B-EH-A(LF)(SN)", "JST", JST_CATALOGUE, "EH 2.5mm top entry; catalog p35-36; 3A with AWG22 under manufacturer conditions"),
    "J402": ("B3B-EH-A(LF)(SN)", "JST", JST_CATALOGUE, "EH 2.5mm top entry; catalog p35-36; 3A with AWG22 under manufacturer conditions"),
    "J502": ("BM04B-SRSS-TB(LF)(SN)", "JST", JST_SH, "SH 1.0mm 4P top entry; p1-2; 1A with AWG28; no 5V I2C pull-up"),
    "J504": ("BM03B-SRSS-TB(LF)(SN)", "JST", JST_SH, "SH 1.0mm 3P top entry; p1-2; audio output load/bandwidth still requires validation"),
    "J505": ("BM02B-SRSS-TB(LF)(SN)", "JST", JST_SH, "SH 1.0mm 2P top entry; p1-2; electret microphone input"),
    "J506": ("BM02B-SRSS-TB(LF)(SN)", "JST", JST_SH, "SH 1.0mm 2P top entry; p1-2; 1A with AWG28; class-D speaker, neither pin is ground"),
    "L301": ("IHLP4040DZER5R6M5A", "Vishay", "https://www.vishay.com/docs/34315/ihlp-4040dz-5a.pdf",
             "5.6uH 20%; DCR<=17.6mOhm at25C; typical Isat20%=9A and heat current9.3A; 4mm max height; p1-2/4; circuit thermal validation pending"),
    "R309": ("WSL120600000ZEA9", "Vishay", "https://www.vishay.com/docs/30192/wsl-9.pdf",
             "Solid copper jumper <=0.2mOhm; p1-2; nominal zero-ohm; component current rating is not board/connector rating"),
}
LOCAL_FOOTPRINTS = {"L301": "duck:IHLP4040DZ_5A_Above2u2", "R309": "duck:Vishay_WSL1206_Jumper"}


def power_footprint(node, reference):
    node[1] = q(LOCAL_FOOTPRINTS[reference])
    if reference == "L301":
        for pad in children(node, "pad"):
            first(pad, "at")[1:3] = [-4.4705 if pad[1] == "1" else 4.4705, 0]
            first(pad, "size")[1:3] = [3.124, 3.251]
            pad[3] = "rect"
            pad[:] = [entry for entry in pad if not (isinstance(entry, list) and entry and entry[0] == "roundrect_rratio")]
        node[:] = [entry for entry in node if not (isinstance(entry, list) and entry and entry[0] in {"fp_line", "fp_rect", "fp_arc", "fp_circle", "fp_poly", "model"})]
        node.extend(rectangle((-5.08, -5.08, 5.08, 5.08), "F.Fab", 0.1))
        node.extend(rectangle((-6.3, -5.4, 6.3, 5.4), "F.CrtYd", 0.05))
        node.extend([line((-5.25, -5.25), (5.25, -5.25), "F.SilkS", 0.12), line((-5.25, 5.25), (5.25, 5.25), "F.SilkS", 0.12)])
        first(node, "descr")[1] = q("Vishay IHLP4040DZ-5A >=2.2uH: pads3.124x3.251, centers8.941, gap5.817; doc34315 p2; body10.16x10.16, max height4mm")
        set_property(node, "Assembly Height", "4.0mm max", board=True)
    else:
        for pad in children(node, "pad"):
            first(pad, "at")[1:3] = [-1.165 if pad[1] == "1" else 1.165, 0]
            first(pad, "size")[1:3] = [1.57, 1.78]
            pad[3] = "rect"
            pad[:] = [entry for entry in pad if not (isinstance(entry, list) and entry and entry[0] == "roundrect_rratio")]
        node[:] = [entry for entry in node if not (isinstance(entry, list) and entry and entry[0] == "model")]
        first(node, "descr")[1] = q("Vishay WSL1206...9 copper jumper; pads1.57x1.78, gap0.76; document30192 p2; generic 1206 body envelope")
        set_property(node, "Assembly Height", "0.635mm nominal; 0.889mm maximum", board=True)


def main():
    if (EVIDENCE / "candidate.json").exists():
        raise FileExistsError("Inspect existing candidate before rerunning")
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise ValueError("Primary changed since selection review")
    work = pipeline.prepare(pipeline.PRIMARY)
    pipeline.write_json(EVIDENCE / "candidate.json", {"project": str(work), "baseline": BASELINE, "promoted": False})
    seen = {"pcb": set(), "schematic": set()}
    def update(node, board=False):
        fields = properties(node)
        reference = fields.get("Reference")
        if reference not in PARTS:
            return False
        if fields.get("MPN"):
            raise ValueError("Existing selected MPN: " + reference)
        if reference in LOCAL_FOOTPRINTS:
            if board:
                power_footprint(node, reference)
            else:
                set_property(node, "Footprint", LOCAL_FOOTPRINTS[reference])
        if reference == "L301":
            if fields.get("Value") != "5.5uH":
                raise ValueError("Inductor baseline changed")
            set_property(node, "Value", "5.6uH", board=board)
        mpn, manufacturer, datasheet, note = PARTS[reference]
        for key, value in {"MPN": mpn, "Manufacturer": manufacturer, "Datasheet": datasheet, "BOM Comments": "Design-selected, not production released; " + note}.items():
            set_property(node, key, value, board=board)
        if not board and reference in LOCAL_FOOTPRINTS:
            set_property(node, "Assembly Height", "4.0mm max" if reference == "L301" else "0.635mm nominal; 0.889mm maximum")
        seen["pcb" if board else "schematic"].add(reference)
        return True
    for path in sorted(work.glob("*.kicad_sch")):
        original = path.read_text(encoding="utf-8")
        changed = replace_children(original, "symbol", update)
        if changed != original:
            path.write_text("\n".join(row.rstrip() for row in changed.splitlines())+"\n", encoding="utf-8")
    path = work / (pipeline.STEM + ".kicad_pcb")
    path.write_text(replace_children(path.read_text(encoding="utf-8"), "footprint", lambda node: update(node, True)), encoding="utf-8")
    if any(references != set(PARTS) for references in seen.values()):
        raise RuntimeError("Missing components in PCB/schematic")
    board = pcbnew.LoadBoard(str(path))
    for reference, library in LOCAL_FOOTPRINTS.items():
        footprint = board.FindFootprintByReference(reference)
        if footprint.GetLayer() == pcbnew.B_Cu:
            footprint.Flip(footprint.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        footprint.SetPosition(pcbnew.VECTOR2I(0, 0))
        footprint.SetOrientationDegrees(0)
        pcbnew.FootprintSave(str(work / "duck.pretty"), footprint)
        if not (work / "duck.pretty" / (library.split(":")[1] + ".kicad_mod")).exists():
            raise RuntimeError("Footprint library save failed")
    pipeline.write_json(EVIDENCE / "selected-parts.json", {reference: {"MPN": part[0], "Manufacturer": part[1], "Datasheet": part[2], "selection_note": part[3]} for reference, part in PARTS.items()})
    reports, summary = pipeline.check(work)
    pipeline.write_json(EVIDENCE / "candidate.json", {"project": str(work), "baseline": BASELINE, "summary": str(reports/"summary.json"), "promoted": False})
    print(json.dumps({"work": str(work), "drc": summary["drc"], "erc": summary["erc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
