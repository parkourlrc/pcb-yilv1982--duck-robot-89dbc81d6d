"""Remove broad prototype relaxations from the manufacturing-rule candidate."""
import json
from pathlib import Path

import pipeline
from generate_rev_a import parse, dump
from restore_npth_clearance import EVIDENCE


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_dru")
    original = path.read_text(encoding="utf-8")
    document = parse("(rules\n" + original + "\n)")
    names = {"prototype fine geometry", "BMI088 fine pitch"}
    removed = [node for node in document[1:] if isinstance(node, list) and node[0] == "rule" and node[1] in names]
    if len(removed) != 2:
        raise RuntimeError("Expected exactly the two legacy prototype rules")
    retained = [node for node in document[1:] if node not in removed]
    rendered = "\n".join(dump(node, 0) for node in retained)
    path.write_text("\n".join(line.rstrip() for line in rendered.splitlines()) + "\n", encoding="utf-8")
    pipeline.write_json(EVIDENCE / "retired-prototype-rules.json", {"removed": removed, "before_text": original,
        "after_sha256": pipeline.digest(path), "basis": "The U501 courtyard condition matched a whole zone; the unchanged board can use its reviewed netclass clearances instead",
        "default_net_clearance_mm": .15, "power_net_clearance_mm": .2, "remaining_hole_limits_mm": {"via": .2, "npth": .25, "pth_pad": .3}})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"status": summary["status"], "drc": summary["drc"]}))


if __name__ == "__main__":
    main()
