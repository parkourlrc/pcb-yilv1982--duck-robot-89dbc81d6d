"""Apply a separate mechanical-hole copper clearance after repairing rule loading."""
import json

import pipeline


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/npth-clearance-20261031"
BASELINE = "9eaffba7b27272c2fcab16560dc50ad3e6bab830aa566b35d7d1b257bdf48ab4"
RULE = '''(rule "Mechanical NPTH copper clearance"
  (condition "A.Type == 'Pad' && !A.isPlated() && A.Hole_Size_X > 0mm")
  (constraint hole_clearance (min 0.25mm))
)
(rule "Mechanical via hole to copper"
  (condition "A.Type == 'Via'")
  (constraint hole_clearance (min 0.20mm))
)
(rule "Plated pad hole to copper"
  (condition "A.Type == 'Pad' && A.isPlated() && A.Hole_Size_X > 0mm")
  (constraint hole_clearance (min 0.30mm))
)
'''


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    candidate_path = EVIDENCE / "candidate.json"
    if candidate_path.exists():
        raise FileExistsError("Inspect the existing NPTH candidate")
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise RuntimeError("Primary changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    path = work / (pipeline.STEM + ".kicad_dru")
    original = path.read_text(encoding="utf-8")
    path.write_text(original.rstrip() + "\n" + RULE, encoding="utf-8")
    reports, summary = pipeline.check(work)
    pipeline.write_json(candidate_path, {"project": str(work), "baseline": BASELINE, "summary": str(reports / "summary.json"), "promoted": False})
    pipeline.write_json(EVIDENCE / "change-contract.json", {"added_rule": RULE, "nominal_npth_copper_clearance_mm": .25,
                        "source_of_need": "The repaired 0.15mm prototype rule yielded 0.1505mm NPTH-to-zone clearance; separate mechanical-hole constraint required",
                        "geometry_changes_allowed": "filled zone clearance around non-plated holes only; no pads, tracks, vias or hole movements"})
    print(json.dumps({"status": summary["status"], "drc": summary["drc"]}))


if __name__ == "__main__":
    main()
