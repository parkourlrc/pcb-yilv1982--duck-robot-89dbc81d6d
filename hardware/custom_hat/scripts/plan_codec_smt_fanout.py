"""Look for a standalone codec supply via without moving existing pads or signals."""
import json
import math
from pathlib import Path

import pcbnew
import pipeline


TARGET = "c6ad78c2-361f-4c03-a650-a32f6c415d72"
EVIDENCE = pipeline.BASE.parents[1] / "docs/references/归档扩展板贴片规范复查"


def vector(point):
    return pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in point))


def main():
    EVIDENCE.mkdir(exist_ok=True)
    checkpoint = pipeline.current_checkpoint()
    board = pcbnew.LoadBoard(str(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")))
    footprint = board.FindFootprintByReference("U701")
    pad = next(pad for pad in footprint.Pads() if pad.GetNumber() == "7")
    layers = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    foreign = {layer: [] for layer in layers}
    all_pads = []
    for item_footprint in board.GetFootprints():
        for item in item_footprint.Pads():
            for layer in layers:
                if item.IsOnLayer(layer):
                    all_pads.append((layer, item.GetEffectiveShape(layer)))
                    if item.GetNetname() != "+3V3":
                        foreign[layer].append((item_footprint.GetReference() + "." + item.GetNumber(), item.GetEffectiveShape(layer)))
    for item in board.GetTracks():
        if item.m_Uuid.AsString() == TARGET:
            continue
        for layer in layers:
            if item.IsOnLayer(layer) and item.GetNetname() != "+3V3":
                foreign[layer].append((item.m_Uuid.AsString(), item.GetEffectiveShape(layer)))
    probe = pcbnew.PCB_VIA(board)
    probe.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    probe.SetViaType(pcbnew.VIATYPE_THROUGH)
    line = pcbnew.PCB_TRACK(board)
    line.SetWidth(pcbnew.FromMM(.2))
    line.SetLayer(pcbnew.B_Cu)
    line.SetStart(pad.GetPosition())
    results = []
    for diameter, drill in ((.55, .3), (.45, .2), (.35, .15)):
        accepted = []
        standalone = []
        probe.SetWidth(pcbnew.FromMM(diameter))
        probe.SetDrill(pcbnew.FromMM(drill))
        for xpos in range(14880, 15161, 5):
            for ypos in range(11080, 11331, 5):
                point = (xpos / 100, ypos / 100)
                if math.dist(point, (150.3625, 112.1)) < .55:
                    continue
                probe.SetPosition(vector(point))
                line.SetEnd(vector(point))
                if any(shape.Collide(probe.GetEffectiveShape(layer), pcbnew.FromMM(.205)) for layer in layers for _, shape in foreign[layer]):
                    continue
                if any(shape.Collide(probe.GetEffectiveShape(layer), pcbnew.FromMM(.02)) for layer, shape in all_pads):
                    continue
                standalone.append({"position_mm": point, "straight_length_mm": math.dist(point, (150.3625, 112.1))})
                if any(shape.Collide(line.GetEffectiveShape(pcbnew.B_Cu), pcbnew.FromMM(.205)) for _, shape in foreign[pcbnew.B_Cu]):
                    continue
                accepted.append({"position_mm": point, "straight_length_mm": math.dist(point, (150.3625, 112.1))})
        accepted.sort(key=lambda entry: entry["straight_length_mm"])
        standalone.sort(key=lambda entry: entry["straight_length_mm"])
        results.append({"diameter_mm": diameter, "drill_mm": drill, "native_foreign_copper_clear_positions": accepted, "standalone_positions": standalone})
    record = {"pcb_sha256": checkpoint["pcb_sha256"], "results": results,
              "scope": "Read-only native pad/track clearance screen; zones refill and full DRC must follow", "primary_unchanged": pipeline.fingerprints(pipeline.PRIMARY) == checkpoint["design_hashes"]}
    pipeline.write_json(EVIDENCE / "codec-fanout-options.json", record)
    print(json.dumps([{**row, "native_foreign_copper_clear_positions": row["native_foreign_copper_clear_positions"][:8],
                       "standalone_positions": row["standalone_positions"][:5], "count": len(row["native_foreign_copper_clear_positions"])} for row in results]))


if __name__ == "__main__":
    main()
