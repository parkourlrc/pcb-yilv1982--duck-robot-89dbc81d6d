"""Reserve the codec power fanout and reroute SDI without changing its endpoints."""
import json
import math
import itertools
import copy

import pcbnew

import pipeline
import repair_u501
import plan_i2s_sdo as planner
from power_local_detour import route
from power_repair_steps import load_state,attempt
from repair_power_connections import EVIDENCE


def main():
    state,work=load_state();label='codec-power-sdi-fanout'
    if any(record['label']==label for record in state['attempts']):return
    board=pcbnew.LoadBoard(str(work/(pipeline.STEM+'.kicad_pcb')))
    geometry=repair_u501.geometry(board)
    removed=[item for item in geometry if item['kind'] in {'track','via'} and item.get('net') in {'I2S_SDI','I2S_SDO','I2S_LRCK','I2S_BCLK'}]
    items=[item for item in geometry if item not in removed]
    for item in items:
        if item['kind']=='pad' and set(item['layers'])=={'F.Cu','B.Cu'}:item['layers']=planner.LAYERS[:]
    power_via=[149.5,111.35]
    power_points=route(items,'+3V3','B.Cu',[150.3625,112.1],power_via,.2)
    for first,last in zip(power_points,power_points[1:]):items.append({'kind':'track','net':'+3V3','layer':'B.Cu','start':first,'end':last,'width':.2})
    items.append({'kind':'via','net':'+3V3','position':power_via,'width':.5,'drill':.3})
    planner.EVIDENCE=EVIDENCE
    planner.XMIN,planner.YMIN,planner.XMAX,planner.YMAX=119.,100.5,158.5,120.
    planner.COLS=round((planner.XMAX-planner.XMIN)/planner.STEP)+1
    planner.ROWS=round((planner.YMAX-planner.YMIN)/planner.STEP)+1
    planner.SIZE=planner.COLS*planner.ROWS
    routes=[('I2S_SDI',(150.3625,113.1),(154.04,102.05)),('I2S_SDO',(150.3625,113.6),(156.58,102.05)),('I2S_LRCK',(150.3625,114.1),(151.5,104.59)),('I2S_BCLK',(150.3625,114.6),(121.02,102.05))]
    searches=[]
    for order in itertools.permutations(routes):
        candidates=copy.deepcopy(items)
        signals=[]
        try:
            for net,first,last in order:
                signal=planner.solve(candidates,net,first,last)
                signals.append(signal)
                for start,end in zip(signal['points'],signal['points'][1:]):
                    if start[2]!=end[2]:candidates.append({'kind':'via','net':net,'position':start[:2],'width':.5,'drill':.3})
                    else:candidates.append({'kind':'track','net':net,'layer':planner.LAYERS[start[2]],'start':start[:2],'end':end[:2],'width':.15})
        except RuntimeError as error:
            searches.append({'order':[item[0] for item in order],'completed':len(signals),'error':str(error)})
            pipeline.write_json(EVIDENCE/'codec-searches.json',searches)
            print('Ordering',len(searches),'completed',len(signals),flush=True)
            continue
        searches.append({'order':[item[0] for item in order],'completed':len(signals)})
        pipeline.write_json(EVIDENCE/'codec-searches.json',searches)
        break
    if len(signals)!=4:raise RuntimeError('No complete candidate with this power fanout')
    plans={'power_points':power_points,'power_via':power_via,'signals':signals,'removed':[item['uuid'] for item in removed]}
    pipeline.write_json(EVIDENCE/(label+'-plan.json'),plans)
    tracks={item.m_Uuid.AsString():item for item in board.GetTracks()}
    def add_segment(target,net,layer,first,last,width):
        item=pcbnew.PCB_TRACK(target)
        item.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(first[0]),pcbnew.FromMM(first[1])))
        item.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(last[0]),pcbnew.FromMM(last[1])))
        item.SetWidth(pcbnew.FromMM(width));item.SetLayer(target.GetLayerID(layer));item.SetNet(target.FindNet(net));target.Add(item)
    def add_via(target,net,position):
        via=pcbnew.PCB_VIA(target)
        via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(position[0]),pcbnew.FromMM(position[1])))
        via.SetWidth(pcbnew.FromMM(.5));via.SetDrill(pcbnew.FromMM(.3));via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);via.SetNet(target.FindNet(net));target.Add(via)
    def edit(target):
        for item in removed:target.Remove(tracks[item['uuid']])
        for first,last in zip(power_points,power_points[1:]):add_segment(target,'+3V3','B.Cu',first,last,.2)
        add_via(target,'+3V3',power_via)
        for signal in signals:
            for first,last in zip(signal['points'],signal['points'][1:]):
                if first[2]!=last[2]:add_via(target,signal['net'],first)
                else:add_segment(target,signal['net'],planner.LAYERS[first[2]],first,last,.15)
    attempt(state,work,label,edit,board=board)


if __name__=='__main__':main()
