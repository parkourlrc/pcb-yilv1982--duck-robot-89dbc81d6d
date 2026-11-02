"""Read archived typical-model raster curves and calculate labelled sensitivity cases."""
import json
import math
import statistics

from PIL import Image

from collect_capacitor_models import EVIDENCE


PROFILES={
    "C1206C226M4PACTU":{"nominal_uf":22,"rated_v":16,"tolerance":0.20,"aging_pct_per_decade":5,"voltages":[4.852137,4.984,5.119211]},
    "C1206C106K3RACTU":{"nominal_uf":10,"rated_v":25,"tolerance":0.10,"aging_pct_per_decade":3,"voltages":[6.6,7.4,8.4]},
    "C0805C105K5RACTU":{"nominal_uf":1,"rated_v":50,"tolerance":0.10,"aging_pct_per_decade":3,"voltages":[1.8,3.3]},
    "C0805C225K5RACTU":{"nominal_uf":2.2,"rated_v":50,"tolerance":0.10,"aging_pct_per_decade":3,"voltages":[1.8,3.3]},
    "C1210C226K3RACTU":{"nominal_uf":22,"rated_v":25,"tolerance":0.10,"aging_pct_per_decade":3,"voltages":[5.119211,8.4]},
}


def decode_curve(part, profile):
    image=Image.open(EVIDENCE/"sources"/(part+"-dc-bias.png")).convert("RGB")
    if image.size!=(640,480):
        raise RuntimeError("Unexpected manufacturer plot size")
    rows=[]
    for ypos in range(34,430):
        count=sum(1 for red,green,blue in [image.getpixel((xpos,ypos)) for xpos in range(82,559)]
                  if abs(red-green)<=1 and abs(green-blue)<=1 and 50<red<200)
        if count>350:
            rows.append(ypos)
    if len(rows)<5 or rows[0]!=34:
        raise RuntimeError("Grid calibration failed for "+part)
    indices=list(range(len(rows)))
    mean_index=statistics.mean(indices)
    mean_row=statistics.mean(rows)
    slope=sum((index-mean_index)*(row-mean_row) for index,row in zip(indices,rows))/sum((index-mean_index)**2 for index in indices)
    intercept=mean_row-slope*mean_index
    if max(abs(row-(intercept+slope*index)) for index,row in zip(indices,rows))>0.7:
        raise RuntimeError("Nonlinear axis calibration")
    points=[]
    for voltage in profile["voltages"]:
        xpos=80+voltage/profile["rated_v"]*480
        column_values=[]
        for column in (math.floor(xpos),math.ceil(xpos)):
            candidates=[]
            for ypos in range(34,431):
                red,green,blue=image.getpixel((column,ypos))
                if red<100 and green<110 and blue>85 and blue>green+20 and green>=red:
                    candidates.append(ypos)
            if not candidates:
                raise RuntimeError("Curve color not found")
            column_values.append(statistics.median(candidates))
        fraction=xpos-math.floor(xpos)
        ypos=column_values[0]+fraction*(column_values[1]-column_values[0])
        change=-10*(ypos-intercept)/slope
        retention=max(0,1+change/100)
        cases=[]
        for hours in (48,8760,87600):
            aging=profile["aging_pct_per_decade"]/100*math.log10(hours/48)
            conservative=max(0,retention-0.02)*(1-profile["tolerance"])*0.85*(1-aging)
            cases.append({"age_hours_from_reference":hours,"assumed_aging_loss_fraction":aging,"scenario_effective_uf":profile["nominal_uf"]*conservative})
        points.append({"dc_v":voltage,"pixel_x":xpos,"pixel_y":ypos,"model_capacitance_change_pct":change,
                       "typical_model_effective_uf":profile["nominal_uf"]*retention,"sensitivity_cases":cases})
    return {"profile":profile,"axis_major_rows":rows,"percent_per_major_grid":-10,"x_axis_pixels":[80,560],
            "linear_axis_fit_pixels_per_major":slope,"points":points}


def main():
    results={part:decode_curve(part,profile) for part,profile in PROFILES.items()}
    minimum_cout=14140/(4670*4.852137029702971*45000)*1e6
    output_cases=[]
    for part,quantity in (("C1206C226M4PACTU",2),("C1206C226M4PACTU",3),("C1210C226K3RACTU",2)):
        point=next(point for point in results[part]["points"] if abs(point["dc_v"]-5.119211)<1e-5)
        for case in point["sensitivity_cases"]:
            total=case["scenario_effective_uf"]*quantity
            output_cases.append({"part":part,"quantity":quantity,"age_hours":case["age_hours_from_reference"],"scenario_combined_uf":total,
                                 "eq17_crossover_hz_internal_parameters_typical":14140/(4670*4.852137029702971*total*1e-6)})
    result={"method":"Read the original 640x480 manufacturer DC-bias plots from per-part PDFs; grey major rows calibrated to 10-percentage-point spacing and blue curve interpolated.",
            "not_hardware_measurement":True,"manufacturer_model_is_typical_not_guaranteed":True,
            "scenario_assumptions":"Multiply independent worst-direction tolerance,15% TCC,logarithmic aging referenced to48h, and an additional2-percentage-point retention allowance. Combined bias/temperature/process interactions are not modelled. The2-point allowance is a design sensitivity assumption, not a vendor guarantee or statistical confidence interval.",
            "operating_lifetime_not_specified_by_user":"48h,1year and10year are sensitivity cases, not claimed service-life requirements or evidence of actual capacitor age.",
            "unmodelled_effects":"Resistor TCR, AC-drive amplitude and frequency dependence are not combined with these DC-bias curves; the PDF does not enumerate every simulation setting.",
            "models":results,"output_cases":output_cases,"eq17_minimum_effective_cout_for_45khz_uf":minimum_cout,
            "equation17_limit":"AP64350 p18 first-order design equation with typical internal gm/Rt; 45kHz=10% of450kHz; not a stability or phase-margin verification.",
            "eq12_note":"The archived manufacturer p17 visibly prints gm*R5 in Eq12. Figure27 passive-network derivation and Eq17 suggest an R2 prefactor instead; possible document inconsistency, no manufacturer correction obtained. Eq12 was not used to claim stability.",
            "cad_values_changed":False}
    (EVIDENCE/"bias-sensitivity.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"effective_cout_requirement_first_order_uf":minimum_cout,
                      "typical_points":{part:[(point["dc_v"],round(point["model_capacitance_change_pct"],2),round(point["typical_model_effective_uf"],3)) for point in entry["points"]] for part,entry in results.items()},
                      "output_scenarios":output_cases},ensure_ascii=False))


if __name__=="__main__":
    main()
