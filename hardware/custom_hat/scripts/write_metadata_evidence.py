"""Record raw-board checks and source fingerprints for the metadata review."""
from datetime import datetime
import json
from pathlib import Path

import pcbnew
import pipeline
from repair_release_metadata import PARTS


def main():
    evidence = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/metadata-repair-20261030"
    board_path = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(board_path))
    vias = [item for item in board.GetTracks() if item.Type() == pcbnew.PCB_VIA_T]
    thermal = []
    for reference, number in (("U301", "9"), ("U701", "33"), ("U702", "2")):
        footprint = board.FindFootprintByReference(reference)
        pad = max((pad for pad in footprint.Pads() if pad.GetNumber() == number), key=lambda pad: pad.GetSize().x * pad.GetSize().y)
        bounds = pad.GetBoundingBox()
        matching = [via for via in vias if via.GetNetname() == pad.GetNetname() and bounds.Contains(via.GetPosition())]
        thermal.append({"reference": reference, "pad": number, "net": pad.GetNetname(), "same_net_vias_in_pad_bbox": len(matching)})
    fiducials = []
    for footprint in board.GetFootprints():
        if not footprint.GetReference().startswith("FID"):
            continue
        for pad in footprint.Pads():
            position = pad.GetPosition()
            fiducials.append({"reference": footprint.GetReference(), "layer": footprint.GetLayerName(),
                              "x_mm": pcbnew.ToMM(position.x), "y_mm": pcbnew.ToMM(position.y),
                              "paste": pad.IsOnLayer(pcbnew.F_Paste) or pad.IsOnLayer(pcbnew.B_Paste)})
    pipeline.write_json(evidence / "raw-board-audit.json", {
        "pcb_sha256": pipeline.digest(board_path), "thermal": thermal, "fiducials": fiducials,
        "ground_vias": sum(via.GetNetname() == "POWER_GND" for via in vias),
        "signal_net_count": sum(bool(net.GetNetname()) and not net.GetNetname().startswith("unconnected-") for net in board.GetNetsByNetcode().values()),
        "nc_net_count": sum(net.GetNetname().startswith("unconnected-") for net in board.GetNetsByNetcode().values()),
        "production_ready": False,
    })
    filenames = {"U301": "AP64350.pdf", "U501": "bst-bmi088-ds001.pdf", "U701": "tlv320aic3104.pdf",
                 "U702": "lp38691.pdf", "U801": "sn74lvc1g126.pdf", "U802": "sn74lvc1g125.pdf", "U803": "PAM8302A.pdf"}
    sources = []
    for reference, (mpn, manufacturer, url) in PARTS.items():
        path = evidence / "sources" / filenames[reference]
        sources.append({"reference": reference, "MPN": mpn, "manufacturer": manufacturer, "url": url,
                        "file": path.relative_to(evidence).as_posix(), "sha256": pipeline.digest(path),
                        "origin": "archived manufacturer PDF from audit-20261029" if reference in {"U301", "U501", "U701"} else "downloaded manufacturer PDF 2026-10-30",
                        "selection_status": "design selected; procurement unverified"})
    for filename, url in {
        "radxa_zero_3w_schematic_v1.11_20250116.pdf": "https://dl.radxa.com/zero3/docs/hw/3w/radxa_zero_3w_schematic_v1.11_20250116.pdf",
        "jlc-hdi-faq.html": "https://jlcpcb.com/help/article/hdi-pcb-capabilities-faq",
    }.items():
        path = evidence / "sources" / filename
        sources.append({"url": url, "file": path.relative_to(evidence).as_posix(), "sha256": pipeline.digest(path)})
    pipeline.write_json(evidence / "sources-manifest.json", {"recorded_at": datetime.now().astimezone().isoformat(), "sources": sources})
    outputs = pipeline.PRIMARY / "production-20261031-review"
    pipeline.write_json(outputs / "manifest.json", {"created_at": datetime.now().astimezone().isoformat(),
        "design_hashes": pipeline.fingerprints(pipeline.PRIMARY), "outputs": {path.name: pipeline.digest(path) for path in outputs.iterdir() if path.is_file() and path.name != "manifest.json"},
        "production_ready": False, "limits": ["45 fitted component MPNs missing", "I2C5 pullups not implemented", "thermal and HDI stackup unresolved"]})
    print(json.dumps({"thermal": thermal, "fiducials_without_paste": sum(not entry["paste"] for entry in fiducials), "selected_mpns": len(PARTS)}))


if __name__ == "__main__":
    main()
