"""Read-only KiCad/source audit; run using KiCad's bundled Python."""
import collections
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pcbnew

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
REV = ROOT / "hardware/custom_hat/rev_a"
tree = ET.parse(OUT / "netlist.xml")
comps = {c.attrib["ref"]: {"value": c.findtext("value"), "footprint": c.findtext("footprint"),
         "libsource": c.find("libsource").attrib if c.find("libsource") is not None else {}}
         for c in tree.findall("./components/comp")}
nets = {n.attrib["name"]: [dict(p.attrib) for p in n.findall("node")]
        for n in tree.findall("./nets/net")}

def describe_board(path):
    b = pcbnew.LoadBoard(str(path))
    footprints = {}
    for fp in b.GetFootprints():
        footprints[fp.GetReference()] = {
            "value": fp.GetValue(), "library": str(fp.GetFPID().GetLibNickname()) + ":" + str(fp.GetFPID().GetLibItemName()),
            "pos": [round(pcbnew.ToMM(fp.GetPosition().x)-100, 4), round(pcbnew.ToMM(fp.GetPosition().y)-100, 4)],
            "side": b.GetLayerName(fp.GetLayer()),
            "pads": [{"number": p.GetNumber(), "net": p.GetNetname(),
                      "pos": [round(pcbnew.ToMM(p.GetPosition().x)-100, 4), round(pcbnew.ToMM(p.GetPosition().y)-100, 4)],
                      "size": [pcbnew.ToMM(p.GetSize().x), pcbnew.ToMM(p.GetSize().y)]}
                     for p in fp.Pads()]}
    track_counts = collections.Counter()
    widths = collections.defaultdict(collections.Counter)
    for track in b.GetTracks():
        if isinstance(track, pcbnew.PCB_VIA):
            track_counts["vias"] += 1
        else:
            track_counts[b.GetLayerName(track.GetLayer())] += 1
            widths[track.GetNetname()][round(pcbnew.ToMM(track.GetWidth()), 4)] += 1
    zones = [{"net": z.GetNetname(), "layer": b.GetLayerName(z.GetLayer()),
              "clearance": pcbnew.ToMM(z.GetLocalClearance()),
              "min_thickness": pcbnew.ToMM(z.GetMinThickness())} for z in b.Zones()]
    return {"layers": b.GetCopperLayerCount(), "footprint_count": len(footprints),
            "track_counts": dict(track_counts), "widths": {k: dict(v) for k,v in widths.items()},
            "zones": zones, "footprints": footprints}

boards = {p.name: describe_board(p) for p in [REV / "custom_hat_rev_a.kicad_pcb", REV / "best.kicad_pcb", REV / "base-clean.kicad_pcb"] if p.exists()}
files = [p for p in REV.iterdir() if p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".net")]
files += [p for p in (REV / "production").iterdir() if p.is_file()]
manifest = [{"path": str(p.relative_to(ROOT)).replace("\\", "/"), "bytes": p.stat().st_size,
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
result = {"components": comps, "nets": nets, "boards": boards, "files": manifest}
(OUT / "design-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"component_count_including_flags": len(comps), "boards": {k:{x:v[x] for x in ("layers", "footprint_count", "track_counts", "zones")} for k,v in boards.items()},
                 "key_nets": {n: nets.get(n) for n in ["UART2_TX", "UART2_RX", "DXL_DATA", "SERVO_VBAT", "VBATT_2S_IN", "I2S_SDI", "I2S_SDO"]}}, ensure_ascii=False, indent=2))
