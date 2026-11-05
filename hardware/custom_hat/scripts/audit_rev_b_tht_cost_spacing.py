"""Screen opposite-face THT solder access; never modify the source board.

Fab graphic envelopes and nominal pad bounding boxes are conservative 2D
proxies, not factory tooling approval or measured component bodies/heights.
"""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "hardware/custom_hat/rev_b/custom_hat_rev_b.kicad_pcb"
OUTPUT = ROOT / "docs/references/扩展板乙版降本/tht-cost-spacing.json"


def bounds(item):
    box = item.GetBoundingBox()
    return [pcbnew.ToMM(x) for x in
            (box.GetLeft(), box.GetTop(), box.GetRight(), box.GetBottom())]


def distance(a, b):
    return math.hypot(max(a[0] - b[2], b[0] - a[2], 0),
                      max(a[1] - b[3], b[1] - a[3], 0))


def main():
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    board = pcbnew.LoadBoard(str(SOURCE))
    parts, missing = [], []
    for footprint in board.GetFootprints():
        if not any(p.GetNumber() for p in footprint.Pads()):
            continue
        side = footprint.GetLayer()
        fab = pcbnew.F_Fab if side == pcbnew.F_Cu else pcbnew.B_Fab
        graphics = [bounds(g) for g in footprint.GraphicalItems()
                    if g.GetLayer() == fab and g.Type() == pcbnew.PCB_SHAPE_T]
        if not graphics:
            missing.append(footprint.GetReference())
            continue
        envelope = [min(g[0] for g in graphics), min(g[1] for g in graphics),
                    max(g[2] for g in graphics), max(g[3] for g in graphics)]
        parts.append((footprint.GetReference(), side, envelope))
    pads = []
    for footprint in board.GetFootprints():
        side = pcbnew.B_Cu if footprint.GetLayer() == pcbnew.F_Cu else pcbnew.F_Cu
        neighbors = [(ref, box) for ref, face, box in parts
                     if face == side and ref != footprint.GetReference()]
        for pad in footprint.Pads():
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_PTH or not pad.GetNumber():
                continue
            candidates = sorted([(round(distance(bounds(pad), box), 6), ref)
                                 for ref, box in neighbors])
            nearest = candidates[0] if candidates else (None, None)
            pads.append({"pad": footprint.GetReference() + "." + pad.GetNumber(),
                         "welding_face": board.GetLayerName(side),
                         "pad_bbox_mm": bounds(pad),
                         "nearest_fab_envelope": nearest[1],
                         "bbox_gap_mm": nearest[0],
                         "envelopes_within_3mm": [ref for gap, ref in candidates if gap < 3],
                         "envelopes_within_5mm": [ref for gap, ref in candidates if gap < 5]})
    screened = [p for p in pads if p["envelopes_within_3mm"]]
    result = {
        "date": "2026-11-04", "source": str(SOURCE.relative_to(ROOT)),
        "pcb_sha256": before, "source_unchanged": before == hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "confidence": "heuristic", "evidence_source": "KiCad nominal PTH pad bbox and opposite-face Fab graphic envelope",
        "trust_summary": {"trust_level": "mixed", "geometry_source": "current CAD", "factory_acceptance": "unverified"},
        "limits": ["Not actual component body, height, solder fillet, mask-edge or nozzle clearance.",
                   "Envelope overlap can be conservative; per-part and factory review required.",
                   "JLC tooltip requires 3mm when mounted height <4mm, and 5mm for height >=4mm.",
                   "No quote reduction or manufacturing clearance is inferred from this screen."],
        "tht_pad_count": len(pads), "pads_screened_below_3mm": len(screened),
        "affected_connectors": dict(Counter(p["pad"].split('.')[0] for p in screened)),
        "neighbor_references": sorted({ref for p in screened for ref in p["envelopes_within_3mm"]}),
        "missing_fab_envelopes": sorted(missing), "pads": pads,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "pads"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
