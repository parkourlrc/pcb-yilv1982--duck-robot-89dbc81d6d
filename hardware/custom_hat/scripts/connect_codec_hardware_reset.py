"""Connect the codec reset to a documented spare GPIO in a complete candidate."""
import json
import argparse
import math
from datetime import datetime, timezone
from pathlib import Path

import pcbnew

import pipeline
from generate_rev_a import Sheet, parse, first, children, dump
from repair_release_metadata import child_spans, properties
from finish_ttl_local_bypass import route_layer


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/codec-reset-20261031"
BASELINE = "70586fc6d5c68f322d49f56fa657ac89537fdf7702ad5e5261a5b253e5ca8fbe"


def schematic(work, header_pin, gpio_name, gpio_offset):
    path = work / "radxa_40p.kicad_sch"
    original = path.read_text(encoding="utf-8")
    tree = parse(original)
    instance = next(node for node in children(tree, "symbol") if properties(node).get("Reference") == "J101")
    location = first(instance, "at")
    if float(location[3]) != 0 or first(instance, "mirror"):
        raise RuntimeError("Header symbol transform needs a new review")
    library = next(node for node in children(first(tree, "lib_symbols"), "symbol") if node[1] == first(instance, "lib_id")[1])
    pin = next(pin for unit in children(library, "symbol") for pin in children(unit, "pin") if first(pin, "number")[1] == str(header_pin))
    pin_at = first(pin, "at")
    position = (round(float(location[1]) + float(pin_at[1]), 4), round(float(location[2]) - float(pin_at[2]), 4))
    marker = [(start, end, block) for start, end, block in child_spans(original, "no_connect")
              if tuple(float(value) for value in first(parse(block), "at")[1:3]) == position]
    if len(marker) != 1:
        raise RuntimeError("Expected exactly one no-connect on the selected header pin")
    start, end, block = marker[0]
    text = original[:start] + original[end:]
    angle = float(pin_at[3])
    endpoint = (round(position[0] - 7.62 * math.cos(math.radians(angle)), 4), round(position[1] + 7.62 * math.sin(math.radians(angle)), 4))
    sheet = Sheet("radxa_40p", "Codec hardware reset addition")
    sheet.counter = 5000
    sheet.wire(position, endpoint)
    sheet.label("CODEC_RST", *endpoint, 0 if angle == 180 else 180)
    sheet.text(f"Pin{header_pin} {gpio_name} -> CODEC_RST. Assert low after supplies stabilize; release high before codec initialization.", 35.56, 154.94)
    additions = [node for node in sheet.tree if isinstance(node, list) and node[0] in {"wire", "global_label", "text"}]
    closing = text.rfind(")")
    text = text[:closing] + "\n" + "\n".join(dump(node, 1) for node in additions) + "\n" + text[closing:]
    path.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="utf-8")
    contract_path = work / "net-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    matches = [row for row in contract["pins"] if row["reference"] == "J101" and str(row["pin"]) == str(header_pin)]
    if len(matches) != 1 or matches[0]["net"] is not None:
        raise RuntimeError("Unexpected header contract")
    matches[0]["net"] = "CODEC_RST"
    contract["codec_hardware_reset"] = {"header_pin": header_pin, "soc_gpio": gpio_name, "bank": 3, "offset": gpio_offset,
        "active_low": True, "minimum_low_pulse_ns": 10, "after_supplies_stable": True, "runtime_verified": False}
    pipeline.write_json(contract_path, contract)
    return {"removed_nc": parse(block), "pin_position": position, "new_label_endpoint": endpoint}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--header-pin", type=int, choices=(15, 33, 36), default=33)
    parser.add_argument("--retry-header", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    arguments = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    candidate_path = EVIDENCE / "candidate.json"
    if candidate_path.exists() and not arguments.retry_header:
        raise FileExistsError("Inspect the existing codec-reset candidate")
    if arguments.retry_header:
        previous = json.loads(candidate_path.read_text(encoding="utf-8"))
        if previous.get("promoted"):
            raise RuntimeError("Cannot replace a promoted reset design")
        prefix = f"rejected-pin{previous['header_pin']}-{datetime.now(timezone.utc).strftime('%H%M%S')}-"
        pipeline.write_json(EVIDENCE / (prefix + "candidate.json"), previous)
        for name in ("change-contract.json", "geometry-connectivity-check.json", "reference-coverage-delta.json"):
            current = EVIDENCE / name
            if current.exists():
                pipeline.write_json(EVIDENCE / (prefix + name), json.loads(current.read_text(encoding="utf-8")))
                current.unlink()
    source = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(source) != BASELINE:
        raise RuntimeError("Primary changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    gpio_name, gpio_offset = {15: ("GPIO3_B0", 8), 33: ("GPIO3_C3", 19), 36: ("GPIO3_A7", 7)}[arguments.header_pin]
    candidate = {"project": str(work), "baseline": BASELINE, "promoted": False, "header_pin": arguments.header_pin, "gpio_name": gpio_name}
    pipeline.write_json(candidate_path, candidate)
    schematic_change = schematic(work, arguments.header_pin, gpio_name, gpio_offset)
    candidate["schematic_change"] = schematic_change
    pipeline.write_json(candidate_path, candidate)
    board_path = work / source.name
    board = pcbnew.LoadBoard(str(board_path))
    pad = next(item for item in board.FindFootprintByReference("J101").Pads() if item.GetNumber() == str(arguments.header_pin))
    old_net = pad.GetNetname()
    if old_net != f"unconnected-(J101-Pin_{arguments.header_pin}-Pad{arguments.header_pin})":
        raise RuntimeError("Selected header pin is not the expected unused pin")
    pad.SetNet(board.FindNet("CODEC_RST"))
    pad.SetPinType("passive")
    pad_uuid = pad.m_Uuid.AsString()
    start = tuple(pcbnew.ToMM(value) for value in pad.GetPosition())
    pcbnew.SaveBoard(str(board_path), board)
    if arguments.prepare_only:
        print(json.dumps(candidate))
        return
    failures, selected = [], None
    candidates = [("B.Cu", (145.94, 110.81)), ("F.Cu", (146.3246, 114.0141)),
                  ("In2.Cu", (146.3246, 114.0141)), ("In1.Cu", (146.3246, 114.0141))]
    if arguments.header_pin in (15, 33):
        candidates = candidates[:2]
    for layer, endpoint in candidates:
        board = pcbnew.LoadBoard(str(board_path))
        try:
            selected = route_layer(board, "CODEC_RST", layer, .15, start, endpoint, EVIDENCE, search_margin=6, protect_i2s_reference=arguments.header_pin == 15)
        except RuntimeError as error:
            failures.append({"layer": layer, "endpoint": endpoint, "error": str(error)})
            pipeline.write_json(EVIDENCE / "route-failures.json", failures)
            continue
        pcbnew.SaveBoard(str(board_path), board)
        break
    if selected is None:
        raise RuntimeError("No codec-reset branch found; primary remains unchanged")
    pipeline.write_json(EVIDENCE / "change-contract.json", {"schematic": schematic_change, "header_pin": arguments.header_pin, "header_pad_uuid": pad_uuid,
        "header_old_net": old_net, "header_new_net": "CODEC_RST", "header_new_pin_type": "passive", "route": selected,
        "removed_original_copper": [], "changed_existing_copper": [], "new_vias": [], "routes": [selected], "failed_routes": failures,
        "gpio_source": f"Radxa ZERO3 hardware interface: physical{arguments.header_pin} = {gpio_name},3.3V", "hardware_tested": False})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"route": selected, "status": summary["status"], "drc": summary["drc"], "erc": summary["erc"]}))


if __name__ == "__main__":
    main()
