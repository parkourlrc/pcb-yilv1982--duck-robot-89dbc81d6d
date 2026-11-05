import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = Path(__file__).resolve().parent
    root = output.parents[3]
    project = root / "hardware/custom_hat/rev_a"
    stem = "custom_hat_rev_a"
    cli = Path(sys.base_prefix) / "kicad-cli.exe"
    source_hashes = {str(path.relative_to(project)): digest(path) for path in project.rglob("*") if path.is_file() and path.suffix not in {".kicad_prl", ".lck"}}
    result = {"kicad": pcbnew.GetBuildVersion(), "source_hashes": source_hashes, "commands": []}
    with tempfile.TemporaryDirectory(prefix="hat-audit-") as scratch:
        copied = Path(scratch) / "complete"
        shutil.copytree(project, copied)
        def run(name, arguments):
            process = subprocess.run([str(cli), *map(str, arguments)], capture_output=True, encoding="utf-8", errors="replace", timeout=120)
            result["commands"].append({"name": name, "args": list(map(str, arguments)), "returncode": process.returncode})
            (output / (name + ".log")).write_text(process.stdout + process.stderr, encoding="utf-8")
            if process.returncode:
                raise RuntimeError(f"{name}: exit {process.returncode}")
        for name, extra in [("drc-cached", []), ("drc-refilled", ["--refill-zones"]), ("drc-parity", ["--refill-zones", "--schematic-parity"])]:
            run(name, ["pcb", "drc", "--format", "json", "--severity-all", *extra, "--output", output / (name + ".json"), copied / (stem + ".kicad_pcb")])
        run("erc", ["sch", "erc", "--format", "json", "--severity-all", "--output", output / "erc.json", copied / (stem + ".kicad_sch")])
        run("netlist", ["sch", "export", "netlist", "--format", "kicadxml", "--output", output / "netlist.xml", copied / (stem + ".kicad_sch")])
        isolated = Path(scratch) / "pcb-only"
        isolated.mkdir()
        shutil.copy2(project / (stem + ".kicad_pcb"), isolated / (stem + ".kicad_pcb"))
        run("drc-missing-project-control", ["pcb", "drc", "--format", "json", "--severity-all", "--refill-zones", "--output", output / "drc-missing-project-control.json", isolated / (stem + ".kicad_pcb")])
    board = pcbnew.LoadBoard(str(project / (stem + ".kicad_pcb")))
    tracks = board.GetTracks()
    result["board"] = {
        "footprints": len(board.GetFootprints()),
        "segments": sum(item.Type() != pcbnew.PCB_VIA_T for item in tracks),
        "vias": sum(item.Type() == pcbnew.PCB_VIA_T for item in tracks),
        "zones": [{"layer": board.GetLayerName(zone.GetLayer()), "net": zone.GetNetname()} for zone in board.Zones()],
        "outline_vertices_mm": sorted(set((pcbnew.ToMM(item.GetStart().x), pcbnew.ToMM(item.GetStart().y)) for item in board.GetDrawings() if item.GetLayer() == pcbnew.Edge_Cuts)),
        "parts": {},
    }
    for footprint in board.GetFootprints():
        result["board"]["parts"][footprint.GetReference()] = {
            "value": footprint.GetValue(), "footprint": str(footprint.GetFPID().GetLibItemName()),
            "position_mm": [pcbnew.ToMM(footprint.GetPosition().x), pcbnew.ToMM(footprint.GetPosition().y)],
            "layer": footprint.GetLayerName(),
            "pads": [{"number": pad.GetNumber(), "net": pad.GetNetname()} for pad in footprint.Pads()],
        }
    nets = ET.parse(output / "netlist.xml").getroot()
    result["schematic_nets"] = {net.get("name"): [node.attrib for node in net.findall("node")] for net in nets.findall("nets/net")}
    result["summary"] = {}
    for path in output.glob("drc-*.json"):
        report = json.loads(path.read_text(encoding="utf-8"))
        result["summary"][path.stem] = {key: len(report.get(key, [])) for key in ("violations", "unconnected_items", "schematic_parity")}
    result["source_unchanged"] = all(digest(project / name) == value for name, value in source_hashes.items())
    (output / "inventory.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": result["summary"], "source_unchanged": result["source_unchanged"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
