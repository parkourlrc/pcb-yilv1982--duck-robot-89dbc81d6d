from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import pcbnew


root=Path(__file__).resolve().parents[3]
path=root/"hardware/custom_hat/rev_b/custom_hat_rev_b.kicad_pcb"
output=root/"docs/references/扩展板乙版降本"
board=pcbnew.LoadBoard(str(path))
ground=[track for track in board.GetTracks() if track.Type()==pcbnew.PCB_VIA_T and track.GetNetname()=="POWER_GND"]
clocks=[]
for track in board.GetTracks():
    if track.Type()==pcbnew.PCB_VIA_T and track.GetNetname() in {"AUDIO_MCLK","I2S_BCLK","I2S_LRCK","I2S_SDO","I2S_SDI"}:
        distance=min(math.hypot(track.GetPosition().x-via.GetPosition().x,track.GetPosition().y-via.GetPosition().y) for via in ground)
        clocks.append({"net":track.GetNetname(),"position":pcbnew.ToMM(track.GetPosition()),"nearest_ground_via_mm":pcbnew.ToMM(distance)})
power=[]
for voltage in (6.0,7.4,8.4):
    nominal_ripple=5*(voltage-5)/(voltage*6.8e-6*1.1e6)
    illustrative_worst_ripple=5*(voltage-5)/(voltage*6.8e-6*0.8*1.1e6*0.94)
    power.append({"battery_v":voltage,"inductor_ripple_nominal_A":nominal_ripple,"ripple_L_minus20pct_and_FSS_minus6pct_A":illustrative_worst_ripple,"peak_at_2A":2+illustrative_worst_ripple/2})
thermal=[]
for efficiency in (0.88,0.90,0.93):
    loss=10*(1/efficiency-1)
    thermal.append({"assumed_efficiency":efficiency,"loss_upper_bound_all_at_IC_W":loss,"illustrative_Tj_at45C_using_datasheet_2oz_theta89":45+loss*89})
pins={reference:{pad.GetNumber():{"net":pad.GetNetname(),"position_mm":pcbnew.ToMM(pad.GetPosition())} for pad in board.FindFootprintByReference(reference).Pads() if pad.GetNumber()} for reference in ("J101","J401","J402","J502","J505","J507","J506","D301","U702","Q301")}
minimum=min(pcbnew.ToMM(track.GetWidth()) for track in board.GetTracks() if track.Type()!=pcbnew.PCB_VIA_T)
record={"pcb_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"source":"KiCad10 pcbnew native API; calculations are not bench measurements","ground_vias":len(ground),"clock_transitions":clocks,"minimum_trace_mm":minimum,"footprints":len(board.GetFootprints()),"via_sizes":dict(Counter(str((pcbnew.ToMM(track.GetFrontWidth()),pcbnew.ToMM(track.GetDrill()))) for track in board.GetTracks() if track.Type()==pcbnew.PCB_VIA_T)),"connector_and_polarity_pin_tables":pins,"buck_ripple_calculation":power,"thermal_sensitivity_only":thermal,"thermal_limits":"Efficiency assumptions are not measured and 89C/W refers to a 2oz vendor test board. Not a validated 1oz thermal design; IC losses are less than total converter loss but cannot be separated from these assumptions.","i2c_10k_capacitance_limit_1us_pf":1e-6/(0.8473*10000)*1e12,"mosfet_2A_loss_at_35mohm_W":4*0.035,"hardware_tested":False}
(output/"native-audit.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"ground_vias":record["ground_vias"],"clock_via_max_ground_distance_mm":max(row["nearest_ground_via_mm"] for row in clocks),"minimum_trace_mm":minimum,"worst_inductor_peak_A":max(row["peak_at_2A"] for row in power),"pin_tables":len(pins)},ensure_ascii=False))
