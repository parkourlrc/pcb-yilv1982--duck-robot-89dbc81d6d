"""Separate fitted SMT coordinates from through-hole and DNP assembly intent."""
import argparse
import csv
import json
from pathlib import Path

import pipeline
from generate_rev_a import children, first, parse
from repair_release_metadata import properties


def write_assembly_plan(project, output):
    board_path = project / (pipeline.STEM + ".kicad_pcb")
    footprints = {properties(node)["Reference"]: node for node in children(parse(board_path.read_text(encoding="utf-8")), "footprint")}
    with (output / "bom-tracking.csv").open(encoding="utf-8-sig", newline="") as stream:
        bom = list(csv.DictReader(stream))
    with (output / "positions.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        position_fields = list(reader.fieldnames)
        positions = list(reader)
    fitted = {reference for row in bom if row["DNP"] == "False" for reference in row["Reference"].split(",")}
    position_refs = [row["Ref"] for row in positions]
    if len(position_refs) != len(set(position_refs)) or set(position_refs) != fitted:
        raise RuntimeError("Native position export must match fitted BOM references exactly")
    plan = []
    smt_refs, tht_refs, dnp_refs = [], [], []
    for row in bom:
        for reference in row["Reference"].split(","):
            footprint = footprints[reference]
            attributes = set(str(value) for value in (first(footprint, "attr") or [])[1:])
            if row["DNP"] == "True":
                method = "DNP / 不装"
                dnp_refs.append(reference)
            elif "smd" in attributes:
                method = "SMT / 拟贴装，服务待确认"
                smt_refs.append(reference)
            elif "through_hole" in attributes:
                method = "THT / 手焊或厂商通孔装配待确认"
                tht_refs.append(reference)
            else:
                raise RuntimeError("No explicit assembly class for " + reference)
            plan.append({"Reference": reference, "Value": row["Value"], "MPN": row["MPN"], "Footprint": row["Footprint"],
                         "Side": "top" if first(footprint, "layer")[1] == "F.Cu" else "bottom", "Assembly": method,
                         "Status": "Design intent only; no procurement or manufacturing release"})
    with (output / "positions-smt.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=position_fields)
        writer.writeheader()
        writer.writerows(row for row in positions if row["Ref"] in set(smt_refs))
    with (output / "assembly-plan.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(plan[0]))
        writer.writeheader()
        writer.writerows(sorted(plan, key=lambda row: row["Reference"]))
    for name, allowed in (("bom-fitted.csv", fitted), ("bom-smt.csv", set(smt_refs))):
        with (output / name).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(bom[0]))
            writer.writeheader()
            for row in bom:
                selected = [reference for reference in row["Reference"].split(",") if reference in allowed]
                if selected:
                    writer.writerow({**row, "Reference": ",".join(selected), "Qty": len(selected), "DNP": "False"})
    return {"pcb_sha256": pipeline.digest(board_path), "native_positions_sha256": pipeline.digest(output / "positions.csv"),
            "fitted_position_references_match_bom": True, "smt_count": len(smt_refs), "tht_count": len(tht_refs), "dnp_references": sorted(dnp_refs),
            "smt_references": sorted(smt_refs), "tht_references": sorted(tht_refs),
            "coordinate_policy": "Preserve native KiCad millimeter coordinates,rotation,andtop/bottom side; no manual mirror or origin conversion inCSV",
            "assembly_service_selected": False, "manufacturing_released": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    arguments = parser.parse_args()
    output, evidence = arguments.output.resolve(), arguments.evidence.resolve()
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["design_hashes"] != pipeline.fingerprints(pipeline.PRIMARY):
        raise RuntimeError("Current design differs from exported package")
    record = write_assembly_plan(pipeline.PRIMARY, output)
    for name in ("positions-smt.csv", "assembly-plan.csv", "bom-fitted.csv", "bom-smt.csv", "assembly-front.svg", "assembly-back.svg"):
        path = output / name
        if path.exists():
            manifest["outputs"][name] = pipeline.digest(path)
    manifest["assembly_policy"] = record
    pipeline.write_json(manifest_path, manifest)
    pipeline.write_json(evidence / "assembly-export.json", record)
    print(json.dumps({key: value for key, value in record.items() if key != "smt_references"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
