"""Try additional existing reset anchors in the reviewed pin36 candidate."""
import json
from pathlib import Path

import pcbnew

import pipeline
from connect_codec_hardware_reset import EVIDENCE
from finish_ttl_local_bypass import route_layer
from generate_rev_a import parse,first
from repair_release_metadata import child_spans


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if (EVIDENCE / "change-contract.json").exists():
        raise RuntimeError("An accepted route already exists")
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    failures = []
    attempts = [("F.Cu", (149.7261, 117.6977), .2), ("B.Cu", (151.55, 115.7875), .15),
                ("In2.Cu", (149.7261, 117.6977), .2), ("In1.Cu", (149.7261, 117.6977), .2),
                ("F.Cu", (146.3246, 114.0141), .15), ("B.Cu", (145.94, 110.81), .15),
                ("In2.Cu", (146.3246, 114.0141), .15), ("In1.Cu", (146.3246, 114.0141), .15)]
    selected = None
    for layer, endpoint, width in attempts:
        board = pcbnew.LoadBoard(str(path))
        pad = next(item for item in board.FindFootprintByReference("J101").Pads() if item.GetNumber() == "36")
        try:
            selected = route_layer(board, "CODEC_RST", layer, width, tuple(pcbnew.ToMM(value) for value in pad.GetPosition()), endpoint, EVIDENCE, search_margin=6)
        except RuntimeError as error:
            failures.append({"layer": layer, "endpoint": endpoint, "width_mm": width, "error": str(error)})
            pipeline.write_json(EVIDENCE / "expanded-route-failures.json", failures)
            continue
        pcbnew.SaveBoard(str(path), board)
        break
    if selected is None:
        raise RuntimeError("Expanded same-layer route search did not find a connection")
    original=(pipeline.PRIMARY/"radxa_40p.kicad_sch").read_text(encoding="utf-8")
    marker=next(parse(block) for _,_,block in child_spans(original,"no_connect") if [float(value) for value in first(parse(block),"at")[1:3]]==[134.62,110.49])
    pipeline.write_json(EVIDENCE/"change-contract.json",{"schematic":{"removed_nc":marker,"pin_position":[134.62,110.49],"new_label_endpoint":[142.24,110.49]},
        "header_pad_uuid":pad.m_Uuid.AsString(),"header_old_net":"unconnected-(J101-Pin_36-Pad36)","header_new_net":"CODEC_RST","header_new_pin_type":"passive",
        "route":selected,"removed_original_copper":[],"changed_existing_copper":[],"new_vias":0,"expanded_failed_routes":failures,
        "gpio_source":"Radxa ZERO3 physical36 GPIO3_A7,3.3V","hardware_tested":False})
    reports,summary=pipeline.check(work);candidate["summary"]=str(reports/"summary.json");pipeline.write_json(candidate_path,candidate)
    print(json.dumps({"route":selected,"status":summary["status"],"drc":summary["drc"],"erc":summary["erc"]}))


if __name__ == "__main__":
    main()
