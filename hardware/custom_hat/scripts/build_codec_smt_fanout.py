"""Try a bounded codec escape reroute in an isolated project under existing rules."""
import argparse
import json
import math
from pathlib import Path

import pcbnew
import pipeline
from add_i2c_pullups import vector
from finish_ttl_local_bypass import route_layer
from replace_codec_microvia import REMOVED, POWER_VIA, SDO_VIA, via_positions


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/归档扩展板贴片规范复查"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--sdo-x", type=float, default=148.8)
    parser.add_argument("--sdo-y", type=float, default=111.15)
    parser.add_argument("--power-x", type=float, default=149.65)
    parser.add_argument("--automatic-sdo", action="store_true")
    parser.add_argument("--power-diameter", type=float, default=.45)
    parser.add_argument("--power-drill", type=float, default=.2)
    parser.add_argument("--move-sdi", action="store_true")
    parser.add_argument("--sdi-x", type=float, default=149.55)
    parser.add_argument("--sdi-y", type=float, default=109.85)
    parser.add_argument("--sdi-bridge",action="store_true")
    parser.add_argument("--bridge-layer",choices=('F.Cu','In1.Cu','In2.Cu'),default='In2.Cu')
    parser.add_argument("--search-margin",type=float,default=3)
    parser.add_argument("--reroute-bclk",action="store_true")
    parser.add_argument("--source",type=Path)
    arguments = parser.parse_args()
    evidence = EVIDENCE / arguments.attempt
    evidence.mkdir(exist_ok=False)
    checkpoint = pipeline.current_checkpoint()
    source=pipeline.managed(arguments.source) if arguments.source else pipeline.PRIMARY
    work = pipeline.prepare(source)
    path = work / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(path))
    original_nets = {item.m_Uuid.AsString(): item.GetNetname() for item in board.GetTracks()}
    for zone in board.Zones():
        zone.UnFill()
    tracks = {item.m_Uuid.AsString(): item for item in board.GetTracks()}
    removal_ids = set(REMOVED)
    if arguments.move_sdi:
        removal_ids.add("fff083ab-41be-4a01-a647-23c2126eec58")
    if arguments.reroute_bclk:
        removal_ids.update(identifier for identifier,item in tracks.items() if item.Type()!=pcbnew.PCB_VIA_T and item.GetNetname()=='I2S_BCLK' and item.GetLayer()==pcbnew.B_Cu and min(item.GetStart().x,item.GetEnd().x)>=pcbnew.FromMM(147.5))
    if not removal_ids.issubset(tracks):
        raise RuntimeError("Local routing baseline differs")
    removed = [{"uuid": identifier, "net": tracks[identifier].GetNetname()} for identifier in sorted(removal_ids)]
    for identifier in removal_ids:
        board.Remove(tracks[identifier])
    power = tracks[POWER_VIA]
    power.SetPosition(vector((arguments.power_x, 112.1)))
    power.SetWidth(pcbnew.FromMM(arguments.power_diameter))
    power.SetDrill(pcbnew.FromMM(arguments.power_drill))
    sdo = tracks[SDO_VIA]
    sdo.SetPosition(vector((180, 180) if arguments.automatic_sdo else (arguments.sdo_x, arguments.sdo_y)))
    if arguments.automatic_sdo:
        layers = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
        foreign = {layer: [(item.GetNetname(), item.GetEffectiveShape(layer)) for component in board.GetFootprints() for item in component.Pads()
                           if item.IsOnLayer(layer) and item.GetNetname() != "I2S_SDO"] +
                          [(item.GetNetname(), item.GetEffectiveShape(layer)) for item in board.GetTracks()
                           if item.IsOnLayer(layer) and item.GetNetname() != "I2S_SDO"] for layer in layers}
        options = []
        for xpos in range(1470, 1521, 5):
            for ypos in range(1080, 1141, 5):
                point = (xpos / 10, ypos / 10)
                sdo.SetPosition(vector(point))
                if any(shape.Collide(sdo.GetEffectiveShape(layer), pcbnew.FromMM(.205)) for layer in layers for _, shape in foreign[layer]):
                    continue
                options.append(point)
        options.sort(key=lambda point: math.dist(point, (150.0, 110.0)))
        pipeline.write_json(evidence / "sdo-options.json", options)
        if not options:
            raise RuntimeError("No native-clear SDO via position")
        arguments.sdo_x, arguments.sdo_y = options[0]
        sdo.SetPosition(vector(options[0]))
        print("Selected SDO via " + str(options[0]), flush=True)
    board.BuildConnectivity()
    for item in board.GetTracks():
        name = original_nets[item.m_Uuid.AsString()]
        item.SetNetCode(board.FindNet(name).GetNetCode())
    sdi_position = (149.55, 111.25)
    if arguments.move_sdi:
        sdi_position = (arguments.sdi_x, arguments.sdi_y)
        tracks["10ae63f1-45a3-4521-bfae-6a7c0e1458f3"].SetPosition(vector(sdi_position))
    if arguments.sdi_bridge:
        bridge=pcbnew.PCB_VIA(board)
        bridge.SetPosition(vector((149.125,112.525)))
        bridge.SetViaType(pcbnew.VIATYPE_THROUGH)
        bridge.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
        bridge.SetWidth(pcbnew.FromMM(.45))
        bridge.SetDrill(pcbnew.FromMM(.2))
        bridge.SetNetCode(board.FindNet('I2S_SDI').GetNetCode())
        board.Add(bridge)
    routes = []
    record = {"baseline_pcb_sha256": checkpoint["pcb_sha256"], "project": str(work), "removed": removed,
              "power_via_position": [arguments.power_x, 112.1], "power_via_dimensions": [arguments.power_diameter, arguments.power_drill],
              "sdo_via_position": [arguments.sdo_x, arguments.sdo_y], "promoted": False}
    record['sdi_via_position']=list(sdi_position)
    record['candidate_source_pcb_sha256']=pipeline.digest(source/(pipeline.STEM+'.kicad_pcb'))
    pipeline.write_json(evidence / "candidate.json", record)
    try:
        jobs = [("+3V3", "B.Cu", .2, (150.3625, 112.1), (arguments.power_x, 112.1)),
                ("I2S_SDO", "F.Cu", .15, (arguments.sdo_x, arguments.sdo_y), (152.6, 108.95)),
                ("I2S_SDI", "B.Cu", .15, (150.3625, 113.1), sdi_position),
                ("I2S_SDO", "B.Cu", .15, (150.3625, 113.6), (arguments.sdo_x, arguments.sdo_y))]
        if arguments.move_sdi and sdi_position != (149.55,109.85):
            jobs.insert(3,("I2S_SDI","F.Cu",.15,sdi_position,(149.55,109.85)))
        if arguments.sdi_bridge:
            jobs[2]=('I2S_SDI','B.Cu',.15,(150.3625,113.1),(149.125,112.525))
            jobs.insert(3,('I2S_SDI',arguments.bridge_layer,.15,(149.125,112.525),sdi_position))
        if arguments.reroute_bclk:
            jobs.append(('I2S_BCLK','B.Cu',.15,(150.3625,114.6),(147.55,110.35)))
        for net, layer, width, start, end in jobs:
            print("Routing " + net + " " + layer, flush=True)
            routes.append(route_layer(board, net, layer, width, start, end, evidence,search_margin=arguments.search_margin))
            for item in board.GetTracks():
                identifier = item.m_Uuid.AsString()
                if identifier in original_nets and item.GetNetname() != original_nets[identifier]:
                    raise RuntimeError("Routing mutated an original net: " + identifier)
        pcbnew.SaveBoard(str(path), board)
        pipeline.write_json(evidence / "routes.json", routes)
        reports, summary = pipeline.check(work)
        record.update(summary=str(reports / "summary.json"), status=summary["status"], drc=summary["drc"])
    except Exception as error:
        pcbnew.SaveBoard(str(path), board)
        record.update(error=str(error), partial_routes=routes)
    pipeline.write_json(evidence / "candidate.json", record)
    if pipeline.fingerprints(pipeline.PRIMARY) != checkpoint["design_hashes"]:
        raise RuntimeError("Main design changed")
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
