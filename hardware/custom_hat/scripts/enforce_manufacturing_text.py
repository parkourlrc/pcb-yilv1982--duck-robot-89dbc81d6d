"""Enforce the selected fabricator's published silkscreen text dimensions."""
import json
import copy

import pcbnew

import pipeline
from add_i2c_pullups import vector


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/manufacturer-rules-20261031"
BASELINE = "b06b1051d84509c7434347d5889afb7908dffe1af99b67eea67eb4c3e33a9849"
def expected_project_settings(original):
    expected = copy.deepcopy(original)
    settings = expected["board"]["design_settings"]
    settings["rules"]["min_text_height"] = 1.0
    settings["rules"]["min_text_thickness"] = .15
    settings["rules"]["min_silk_clearance"] = .15
    settings["defaults"]["silk_text_thickness"] = .15
    return expected


def apply_settings(work):
    work = pipeline.managed(work)
    original_path = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pro")
    target_path = work / original_path.name
    original = json.loads(original_path.read_text(encoding="utf-8"))
    pipeline.write_json(target_path, expected_project_settings(original))
    source_rules = pipeline.PRIMARY / (pipeline.STEM + ".kicad_dru")
    (work / source_rules.name).write_bytes(source_rules.read_bytes())
    manifest_path = work.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["approved_project_settings_sha256"] = pipeline.digest(target_path)
    manifest["project_settings_reason"] = "Strengthen minimum silk text height/stroke and default stroke to published JLC limits; no electrical or copper rule relaxation"
    pipeline.write_json(manifest_path, manifest)
    pipeline.write_json(EVIDENCE / "project-settings-contract.json", {
        "before_sha256": pipeline.digest(original_path), "after_sha256": pipeline.digest(target_path),
        "allowed_changes": {"board.design_settings.rules.min_text_height": [original["board"]["design_settings"]["rules"]["min_text_height"], 1.0],
                            "board.design_settings.rules.min_text_thickness": [original["board"]["design_settings"]["rules"]["min_text_thickness"], .15],
                            "board.design_settings.rules.min_silk_clearance": [original["board"]["design_settings"]["rules"]["min_silk_clearance"], .15],
                            "board.design_settings.defaults.silk_text_thickness": [original["board"]["design_settings"]["defaults"]["silk_text_thickness"], .15]},
        "custom_rules_unchanged": True})


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    candidate_path = EVIDENCE / "candidate.json"
    if candidate_path.exists():
        raise FileExistsError("Inspect the existing manufacturing-text candidate")
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise RuntimeError("Source changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    path = work / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(path))
    changes = []
    for item in board.GetDrawings():
        if item.Type() != pcbnew.PCB_TEXT_T:
            continue
        if item.GetText() == "DUCK HAT Rev A":
            changes.append({"uuid": item.m_Uuid.AsString(), "text": item.GetText(), "before_position_mm": [pcbnew.ToMM(value) for value in item.GetPosition()],
                            "before_size_mm": [pcbnew.ToMM(value) for value in item.GetTextSize()], "before_stroke_mm": pcbnew.ToMM(item.GetTextThickness()),
                            "after_position_mm": [140, 126.5], "after_size_mm": [1, 1], "after_stroke_mm": .15})
            item.SetPosition(vector((140, 126.5)))
            item.SetTextSize(vector((1, 1)))
            item.SetTextThickness(pcbnew.FromMM(.15))
        elif item.GetText() == "1" and item.GetLayer() == pcbnew.F_SilkS:
            changes.append({"uuid": item.m_Uuid.AsString(), "text": "1", "before_stroke_mm": pcbnew.ToMM(item.GetTextThickness()), "after_stroke_mm": .15})
            item.SetTextThickness(pcbnew.FromMM(.15))
    for reference in ("R501", "R502"):
        label = board.FindFootprintByReference(reference).Reference()
        changes.append({"uuid": label.m_Uuid.AsString(), "text": reference, "before_layer": board.GetLayerName(label.GetLayer()), "after_layer": "F.Fab"})
        label.SetLayer(pcbnew.F_Fab)
    if len(changes) != 4:
        raise RuntimeError("Unexpected silk text baseline")
    pcbnew.SaveBoard(str(path), board)
    apply_settings(work)
    pipeline.write_json(EVIDENCE / "change-contract.json", {"text_changes": changes, "rule_storage": "Native project minimum text dimensions",
                        "basis": "JLCPCB PCB Capabilities: character height >=1.0mm, stroke >=0.15mm", "copper_changes_allowed": False})
    reports, summary = pipeline.check(work)
    pipeline.write_json(candidate_path, {"project": str(work), "baseline": BASELINE, "summary": str(reports / "summary.json"), "promoted": False})
    print(json.dumps({"status": summary["status"], "drc": summary["drc"]}))


if __name__ == "__main__":
    main()
