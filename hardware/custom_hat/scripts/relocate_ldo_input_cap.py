"""Move C308 out from beneath the buck thermal pad in a complete copy."""
import json
from pathlib import Path

import pcbnew
import pipeline
from generate_rev_a import q
from repair_release_metadata import replace_children
from add_i2c_pullups import vector
from plan_buck_thermal_vias import EVIDENCE, BASELINE


def main():
    if (EVIDENCE / "candidate.json").exists():
        raise FileExistsError("Inspect existing candidate before retrying")
    source = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(source) != BASELINE:
        raise RuntimeError("Baseline changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    pipeline.write_json(EVIDENCE / "candidate.json", {"project": str(work), "baseline": BASELINE, "promoted": False})
    changes = []
    for filename, replacements in {
        "power.kicad_sch": {
            "SMBJ12A fitted: hot-plug sweep peaks 14-16V over 1-10uH cable, below the 35V abs-max; TVS is defensive.":
            "SMBJ12A: 19.9V clamp at 30.2A, 10/1000us (Vishay88392). AP64350 VIN max40V recommended,42V DC absolute max. Board transient coordination is unverified.",
            "Vout=0.8V*(1+52.3k/10k)=4.98V; fsw=500kHz via RT=200k; C305+C306 fitted (44uF), C307 22uF reserved DNP.":
            "Vout nominal4.984V; fsw nominal500kHz via RT200k. C305+C306:22uF each NOMINAL; DC-biased capacitance and loop/transient validation pending. C307 is DNP.",
        },
        "audio.kicad_sch": {
            "This page is a pin contract pending full C1 audio schematic re-implementation; no fabricated analog values are implied.":
            "Codec, electret microphone and mono amplifier are implemented in this design; driver/electrical validation is pending. J504 AC-coupled output is not qualified for low-impedance headphones."
        },
    }.items():
        path = work / filename
        def update(node):
            if len(node)>1 and str(node[1]) in replacements:
                previous = str(node[1])
                node[1] = q(replacements[previous])
                changes.append({"file": filename, "from": previous, "to": str(node[1])})
                return True
            return False
        path.write_text(replace_children(path.read_text(encoding="utf-8"), "text", update), encoding="utf-8")
    if len(changes) != 3:
        raise RuntimeError("Expected schematic notes changed")
    board_path = work / source.name
    board = pcbnew.LoadBoard(str(board_path))
    footprint = board.FindFootprintByReference("C308")
    footprint.SetPosition(vector((123.7, 116.1)))
    footprint.SetOrientationDegrees(90)
    power = next(pad for pad in footprint.Pads() if pad.GetNumber()=="1")
    via = next(item for item in board.GetTracks() if item.m_Uuid.AsString()=="3e74bf04-f4e0-4bfa-9e62-b26ff8b4ed4c")
    via.SetPosition(vector((122.3,115.15)))
    track = next(item for item in board.GetTracks() if item.m_Uuid.AsString()=="bce30e35-3e5a-4e8a-b5bc-e6d6e2860bb4")
    track.SetStart(power.GetPosition())
    track.SetEnd(via.GetPosition())
    pcbnew.SaveBoard(str(board_path), board)
    pipeline.write_json(EVIDENCE/"cap-relocation.json", {
        "reference": "C308", "from": [126.13,114.62,0], "to": [123.7,116.1,90],
        "moved_via": via.m_Uuid.AsString(), "via_from": [123.755,114.62], "via_to": [122.3,115.15],
        "changed_track": track.m_Uuid.AsString(), "corrected_notes": changes,
    })
    reports, summary = pipeline.check(work)
    pipeline.write_json(EVIDENCE/"candidate.json", {"project":str(work),"baseline":BASELINE,"summary":str(reports/"summary.json"),"promoted":False})
    print(json.dumps({"drc":summary["drc"],"erc":summary["erc"],"status":summary["status"]}))


if __name__=="__main__":
    main()
