"""Mark the actual J301 battery input pair without changing electrical geometry."""
import json

import pcbnew

import pipeline
from add_i2c_pullups import vector
from analyze_buck_compensation import EVIDENCE, BASELINE


def main():
    candidate_path = EVIDENCE / "candidate.json"
    if candidate_path.exists():
        raise FileExistsError("Inspect the existing power-label candidate")
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise RuntimeError("Power-label baseline changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    path = work / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(path))
    pins = {pad.GetNumber(): pad for pad in board.FindFootprintByReference("J301").Pads()}
    if pins["1"].GetNetname() != "VBATT_2S_IN" or pins["2"].GetNetname() != "POWER_GND":
        raise RuntimeError("Input connector contract differs")
    labels = []
    for number, label, offset in (("1", "2S+", .52), ("2", "GND", -.54)):
        position = (pcbnew.ToMM(pins[number].GetPosition().x) + offset, pcbnew.ToMM(pins[number].GetPosition().y) - 2.72)
        text = pcbnew.PCB_TEXT(board)
        text.SetText(label)
        text.SetPosition(vector(position))
        text.SetTextSize(vector((1, 1)))
        text.SetTextThickness(pcbnew.FromMM(.15))
        text.SetLayer(pcbnew.F_SilkS)
        board.Add(text)
        labels.append({"uuid": text.m_Uuid.AsString(), "text": label, "position_mm": position, "layer": "F.Silkscreen", "pin": "J301." + number})
    pcbnew.SaveBoard(str(path), board)
    pipeline.write_json(EVIDENCE / "label-contract.json", {"labels": labels, "font_mm": 1, "stroke_mm": .15,
                        "view": "F component side; J301 pin1 is the rightmost pin in this board orientation", "copper_changes_allowed": False})
    reports, summary = pipeline.check(work)
    pipeline.write_json(candidate_path, {"project": str(work), "baseline": BASELINE, "summary": str(reports / "summary.json"), "promoted": False})
    print(json.dumps({"status": summary["status"], "drc": summary["drc"]}))


if __name__ == "__main__":
    main()
