"""Move four control passives near U301 and route bounded top-layer connections."""
import json
import math
from pathlib import Path

import pcbnew
import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from generate_rev_a import first, parse
from repair_release_metadata import child_spans
from inspect_buck_control import EVIDENCE, BASELINE


PLACEMENTS={"R301":(130.2,110.2,-90),"R302":(130.2,113.75,-90),"R304":(130.2,117.7,-90),"C301":(130.2,121.2,-90)}


def pad(board, reference, number):
    return next(item for item in board.FindFootprintByReference(reference).Pads() if item.GetNumber()==number)


def mm_position(item):
    return tuple(pcbnew.ToMM(value) for value in item.GetPosition())


def simplify(plan, items):
    points=plan["points"]
    grid=planner.occupancy(items,planner.WIDTH/2,["F.Cu"],plan["net"])
    def clear(start,end):
        delta_x,delta_y=end[0]-start[0],end[1]-start[1]
        if min(abs(delta_x),abs(delta_y))>0.0001 and abs(abs(delta_x)-abs(delta_y))>0.0001:
            return False
        count=max(1,math.ceil(math.hypot(delta_x,delta_y)/(planner.STEP/2)))
        for index in range(count+1):
            xpos=start[0]+delta_x*index/count
            ypos=start[1]+delta_y*index/count
            identifier=planner.node(xpos,ypos,0)
            if identifier<0 or identifier>=planner.SIZE or grid[identifier]:
                return False
        return True
    shortened=[points[0]]
    current=0
    while current<len(points)-1:
        following=current+1
        for option in range(len(points)-1,current+1,-1):
            if clear(points[current],points[option]):
                following=option
                break
        shortened.append(points[following])
        current=following
    plan["original_point_count"]=len(points)
    plan["points"]=shortened
    return plan


def main():
    if (EVIDENCE/"candidate.json").exists():
        raise FileExistsError("Inspect existing work before another attempt")
    source=pipeline.PRIMARY/(pipeline.STEM+".kicad_pcb")
    if pipeline.digest(source)!=BASELINE:
        raise RuntimeError("Source changed")
    baseline=json.loads((EVIDENCE/"before-control-routing.json").read_text(encoding="utf-8"))
    remove={item["uuid"] for item in baseline["control_objects"]}|{item["uuid"] for item in baseline["supply_terminal_branch"]}
    work=pipeline.prepare(pipeline.PRIMARY)
    pipeline.write_json(EVIDENCE/"candidate.json",{"project":str(work),"baseline":BASELINE,"promoted":False})
    board_path=work/source.name
    text=board_path.read_text(encoding="utf-8")
    found=set()
    for start,end,block in reversed(list(child_spans(text))):
        node=parse(block)
        if node[0] in {"segment","via"} and first(node,"uuid")[1] in remove:
            found.add(str(first(node,"uuid")[1]))
            text=text[:start]+text[end:]
    if found!=remove:
        raise RuntimeError("Removal contract changed")
    board_path.write_text(text,encoding="utf-8")
    board=pcbnew.LoadBoard(str(board_path))
    for reference,(xpos,ypos,angle) in PLACEMENTS.items():
        footprint=board.FindFootprintByReference(reference)
        footprint.SetPosition(vector((xpos,ypos)))
        footprint.SetOrientationDegrees(angle)
    pcbnew.SaveBoard(str(board_path),board)
    pipeline.write_json(EVIDENCE/"placement-contract.json",{"positions":PLACEMENTS,"removed_original_objects":sorted(remove)})
    planner.EVIDENCE=EVIDENCE
    planner.LAYERS=["F.Cu"]
    planner.STEP=0.025
    planner.XMIN,planner.YMIN,planner.XMAX,planner.YMAX=123.0,106.8,150.0,124.0
    planner.COLS=round((planner.XMAX-planner.XMIN)/planner.STEP)+1
    planner.ROWS=round((planner.YMAX-planner.YMIN)/planner.STEP)+1
    planner.SIZE=planner.COLS*planner.ROWS
    planner.POWER.add("+1V8_CODEC")
    routes=[]
    targets=[
        ("+5V_FB",("U301","5"),("R302","1"),0.25),
        ("+5V_FB",("R301","2"),("R302","1"),0.25),
        ("BUCK_COMP",("U301","6"),("R304","1"),0.25),
        ("COMP_RC",("R304","2"),("C301","1"),0.25),
        ("+5V",("C305","1"),("R301","1"),0.25),
    ]
    for net,start_key,end_key,width in targets:
        planner.WIDTH=width
        start=mm_position(pad(board,*start_key))
        end=mm_position(pad(board,*end_key))
        items=obstacles(board)
        try:
            plan=simplify(planner.solve(items,net,start,end,[0],0),items)
        except RuntimeError as error:
            pipeline.write_json(EVIDENCE/"routing-failure.json",{"net":net,"error":str(error),"completed_routes":routes})
            raise
        identifiers=[]
        for first_point,last_point in zip(plan["points"],plan["points"][1:]):
            if first_point[:2]==last_point[:2]:
                continue
            track=pcbnew.PCB_TRACK(board)
            track.SetStart(vector(first_point[:2]))
            track.SetEnd(vector(last_point[:2]))
            track.SetLayer(pcbnew.F_Cu)
            track.SetWidth(pcbnew.FromMM(width))
            track.SetNetCode(board.FindNet(net).GetNetCode())
            board.Add(track)
            identifiers.append(track.m_Uuid.AsString())
        plan["added_tracks"]=identifiers
        plan["from_pad"]=start_key
        plan["to_pad"]=end_key
        routes.append(plan)
        print(f"{net}: {len(identifiers)} segments",flush=True)
    pcbnew.SaveBoard(str(board_path),board)
    pipeline.write_json(EVIDENCE/"control-route-plan.json",{"routes":routes})
    reports,summary=pipeline.check(work)
    pipeline.write_json(EVIDENCE/"candidate.json",{"project":str(work),"baseline":BASELINE,"summary":str(reports/"summary.json"),"promoted":False})
    print(json.dumps({"drc":summary["drc"],"erc":summary["erc"],"status":summary["status"]}))


if __name__=="__main__":
    main()
