"""Select table-supported capacitor and TVS MPNs in a guarded workspace."""
import json

import pipeline
from repair_release_metadata import properties, replace_children, set_property
from generate_rev_a import parse


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/bom-passives-20261031"
BASELINE = "d0e549e27994542f50850702add9ddbb8fb4d80f2a5dee9ebf907d9754c03959"
X7R = "https://content.kemet.com/datasheets/KEM_C1002_X7R_SMD.pdf"
X5R = "https://content.kemet.com/datasheets/KEM_C1006_X5R_SMD.pdf"
GROUPS = [
    (["C301"], "3.3nF", "C_0805_", "08055A332JAT2A", "KYOCERA AVX", "50V", "C0G", "5%",
     "https://datasheets.kyocera-avx.com/C0GNP0-Dielectric.pdf", "Rev4 p1 coding, p3 availability; compensation capacitor"),
    (["C302"], "100nF", "C_0805_", "C0805C104K5RACTU", "KEMET", "50V", "X7R", "10%",
     X7R, "p2 coding, p5 availability; bootstrap capacitor voltage is BST minus SW"),
    (["C303", "C304"], "10uF", "C_1206_", "C1206C106K3RACTU", "KEMET", "25V", "X7R", "10%",
     X7R, "p2/p5; input bus 2S; effective capacitance at DC bias and surge coordination still require review"),
    (["C305", "C306"], "22uF", "C_1206_", "C1206C226M4PACTU", "KEMET", "16V", "X5R", "20%",
     X5R, "p1/p2/p6; effective output capacitance and regulator transient response still require review"),
    (["C307"], "22uF reserve", "C_1206_", "C1206C226M4PACTU", "KEMET", "16V", "X5R", "20%",
     X5R, "p1/p2/p6; DNP reserve remains DNP"),
    (["C308", "C309"], "1uF", "C_0805_", "C0805C105K5RACTU", "KEMET", "50V", "X7R", "10%",
     X7R, "p2/p5; LP38691 effective capacitance and 5-500mOhm output ESR still require model/data review"),
    (["C310", "C312", "C319", "C320", "C327"], "100nF", "C_0402_", "C0402C104K3RACTU", "KEMET", "25V", "X7R", "10%",
     X7R, "p2/p5; bypass/reset/mic-bias capacitors"),
    (["C311", "C313", "C315", "C321", "C322", "C325", "C326"], "1uF", "C_0402_", "C0402C105K4PACTU", "KEMET", "16V", "X5R", "10%",
     X5R, "p1/p2/p5; decoupling or AC coupling; bias-dependent capacitance"),
    (["C317", "C318"], "10uF", "C_0402_", "C0402C106M9PACTU", "KEMET", "6.3V", "X5R", "20%",
     X5R, "p1/p2/p5; AC audio coupling; low-impedance headphone bandwidth is not approved"),
    (["C323"], "10uF", "C_0805_", "C0805C106K3PACTU", "KEMET", "25V", "X5R", "10%",
     X5R, "p1/p2/p5; amplifier bypass on 5V; bias and load transients still require review"),
    (["D301"], "SMBJ12A (fitted)", "D_SMB", "SMBJ12A-E3/52", "Vishay", "12V VRWM", "", "",
     "https://www.vishay.com/docs/88392/smbj.pdf", "p2 electrical, p3 ordering, p5 package; 19.9V clamp at 30.2A 10/1000us, not a general surge guarantee"),
]


def main():
    if (EVIDENCE / "candidate.json").exists():
        raise FileExistsError("Inspect existing candidate before rerunning")
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise ValueError("Source changed since review")
    work = pipeline.prepare(pipeline.PRIMARY)
    pipeline.write_json(EVIDENCE / "candidate.json", {"project": str(work), "source_pcb_sha256": BASELINE, "promoted": False})
    parts = {}
    for references, value, footprint, mpn, manufacturer, voltage, dielectric, tolerance, datasheet, note in GROUPS:
        for reference in references:
            parts[reference] = {"value": value, "footprint_contains": footprint, "MPN": mpn, "Manufacturer": manufacturer,
                                "Voltage Rating": voltage, "Dielectric": dielectric, "Tolerance": tolerance, "Datasheet": datasheet,
                                "BOM Comments": "Design selection, not procurement release; " + note}
    seen = {"schematic": set(), "pcb": set()}
    def update(node, board=False):
        fields = properties(node)
        reference = fields.get("Reference")
        if reference not in parts:
            return False
        part = parts[reference]
        footprint = str(node[1]) if board else fields.get("Footprint", "")
        if fields.get("Value") != part["value"] or part["footprint_contains"] not in footprint:
            raise ValueError("Unexpected value or footprint: " + reference)
        if fields.get("MPN"):
            raise ValueError("Existing selection must be reviewed: " + reference)
        for key, choice in part.items():
            if key not in {"value", "footprint_contains"} and choice:
                set_property(node, key, choice, board=board)
        seen["pcb" if board else "schematic"].add(reference)
        return True
    for path in sorted(work.glob("*.kicad_sch")):
        original = path.read_text(encoding="utf-8")
        modified = replace_children(original, "symbol", update)
        if modified != original:
            clean = "\n".join(line.rstrip() for line in modified.splitlines()) + "\n"
            if parse(clean) != parse(modified):
                raise ValueError("Normalization changed syntax")
            path.write_text(clean, encoding="utf-8")
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    board_path.write_text(replace_children(board_path.read_text(encoding="utf-8"), "footprint", lambda node: update(node, True)), encoding="utf-8")
    if any(references != set(parts) for references in seen.values()):
        raise RuntimeError("Some components were not synchronized")
    pipeline.write_json(EVIDENCE / "selected-parts.json", parts)
    reports, result = pipeline.check(work)
    pipeline.write_json(EVIDENCE / "candidate.json", {"project": str(work), "source_pcb_sha256": BASELINE, "summary": str(reports / "summary.json"), "promoted": False})
    print(json.dumps({"project": str(work), "selected_including_dnp": len(parts), "status": result["status"], "drc": result["drc"], "erc": result["erc"]}))


if __name__ == "__main__":
    main()
