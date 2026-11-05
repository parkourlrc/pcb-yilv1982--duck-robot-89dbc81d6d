import copy
import csv
import hashlib
import json
from pathlib import Path
import uuid

import generate_rev_a as schematic


base = Path(__file__).resolve().parents[1]
project = base / "rev_b"
repository = base.parents[1]
stem = "custom_hat_rev_b"
schematic.OUT = project
schematic.PROJECT = stem
schematic.NS = uuid.UUID("4b230ec0-957d-4d63-a11d-acb83fb38225")
schematic.LIB_CACHE.clear()
quoted = schematic.q
first = schematic.first
children = schematic.children
parts = []


def part(sheet, reference, symbol, value, mpn, code, footprint, nets, position, manufacturer, datasheet="", description="", side="F"):
    parts.append({"sheet": sheet, "ref": reference, "symbol": symbol, "value": value, "mpn": mpn, "code": code, "footprint": footprint, "pins": {str(number): net for number, net in nets.items()}, "position": position, "manufacturer": manufacturer, "datasheet": datasheet, "description": description, "side": side})


def capacitor(reference, value, net1, net2, position, sheet="audio"):
    choices = {
        "100nF": ("CC0603KRX7R9BB104", "C14663", "0603", "YAGEO"),
        "1uF": ("CL10A105KB8NNNC", "C15849", "0603", "SAMSUNG"),
        "10uF": ("C1608X5R1A106KT000E", "C76608", "0603", "TDK"),
        "10uF35V": ("C3216X7R1V106KT000E", "C76666", "1206", "TDK"),
        "22uF25V": ("GRM32ER71E226KE15L", "C21397", "1210", "Murata"),
        "220pF": ("0603CG221J500NT", "C156398", "0603", "FH"),
        "10nF": ("CC0603KRX7R9BB103", "C100042", "0603", "YAGEO"),
    }
    mpn, code, size, manufacturer = choices[value]
    metrics = {"0603": "1608", "1206": "3216", "1210": "3225"}
    part(sheet, reference, "Device:C", value, mpn, code, f"Capacitor_SMD:C_{size}_{metrics[size]}Metric", {1: net1, 2: net2}, position, manufacturer)


def resistor(reference, value, net1, net2, position, sheet="audio"):
    choices = {"0R": ("0603WAF0000T5E", "C21189"), "100R": ("0603WAF1000T5E", "C22775"), "1k": ("0603WAF1001T5E", "C21190"), "2.2k": ("0603WAF2201T5E", "C4190"), "10k": ("0603WAF1002T5E", "C25804"), "100k": ("0603WAF1003T5E", "C25803")}
    mpn, code = choices[value]
    part(sheet, reference, "Device:R", value, mpn, code, "Resistor_SMD:R_0603_1608Metric", {1: net1, 2: net2}, position, "UNI-ROYAL")


def custom_symbol(name, pin_table, prefix="U"):
    count = len(pin_table)
    half = (count + 1) // 2
    height = max(5.08, (half + 1) * 1.27)
    body = ["symbol", quoted(name), ["pin_names", ["offset", 0.508]], ["in_bom", "yes"], ["on_board", "yes"], schematic.prop("Reference", prefix, 0, height + 2.54), schematic.prop("Value", name, 0, -height - 2.54), ["symbol", quoted(name + "_0_1"), ["rectangle", ["start", -10.16, height], ["end", 10.16, -height], ["stroke", ["width", 0.254], ["type", "default"]], ["fill", ["type", "background"]]]]]
    unit = ["symbol", quoted(name + "_1_1")]
    for index, (number, pin_name, pin_type) in enumerate(pin_table):
        left = index < half
        offset = index if left else index - half
        position = (-12.7 if left else 12.7, height - 2.54 - offset * 2.54, 0 if left else 180)
        unit.append(["pin", pin_type, "line", ["at", *position], ["length", 2.54], ["name", quoted(pin_name), schematic.effects(0.9)], ["number", quoted(number), schematic.effects(0.9)]])
    body.append(unit)
    return body


library = schematic.parse((project / "duck.kicad_sym").read_text(encoding="utf-8"))
for name, table, prefix in (
    ("AP63205_B", [(1,"FB","input"),(2,"EN","input"),(3,"VIN","power_in"),(4,"GND","power_in"),(5,"SW","power_out"),(6,"BST","passive")], "U"),
    ("LM5050_1_B", [(1,"VS","power_in"),(2,"GND","power_in"),(3,"OFF","input"),(4,"IN","input"),(5,"GATE","output"),(6,"OUT","input")], "U"),
    ("XC6206_18_B", [(1,"GND","power_in"),(2,"VIN","power_in"),(3,"VOUT","power_out")], "U"),
    ("AO3404A_B", [(1,"G","input"),(2,"S","passive"),(3,"D","passive")], "Q"),
    ("LMA2718_B", [(1,"OUT","output"),(2,"GND","power_in"),(3,"GND","power_in"),(4,"VDD","power_in")], "MK"),
    ("OSC2520_B", [(1,"OE","input"),(2,"GND","power_in"),(3,"OUT","output"),(4,"VDD","power_in")], "Y"),
    ("QWIIC4_B", [(1,"GND","passive"),(2,"3V3","passive"),(3,"SDA","passive"),(4,"SCL","passive"),("MP","MOUNT_GND","passive")], "J"),
):
    library[:] = [node for node in library if not (isinstance(node,list) and node and node[0]=="symbol" and node[1]==name)]
    library.append(custom_symbol(name, table, prefix))
(project / "duck.kicad_sym").write_text(schematic.dump(library) + "\n", encoding="utf-8")

contract = json.loads((base / "rev_a/net-contract.json").read_text(encoding="utf-8"))
header_pins = {row["pin"]: row["net"] for row in contract["pins"] if row["reference"] == "J101"}
header_pins["13"] = None
part("radxa_40p", "J101", "Connector_Generic:Conn_02x20_Odd_Even", "RADXA_ZERO_3W", "2.54-2*20", "C2977589", "duck:Radxa40P_Zhouri_B", header_pins, [108.32,104.59,0], "ZHOURI", "https://atta.szlcsc.com/upload/public/pdf/source/20251121/B609B00D0B3EB92686A2D2733E4211A9.pdf", "2x20 PTH 8.5mm socket; physical pin coordinates retained", "B")
part("power", "U301", "duck:AP63205_B", "AP63205WU-7", "AP63205WU-7", "C2071056", "Package_TO_SOT_SMD:TSOT-23-6", {1:"+5V_PRE_IDEAL",2:"VBATT_2S_IN",3:"VBATT_2S_IN",4:"POWER_GND",5:"BUCK_SW",6:"BUCK_BST"}, [115,120,90], "Diodes", "https://www.diodes.com/datasheet/download/AP63200-AP63201-AP63203-AP63205.pdf")
part("power", "L301", "Device:L", "6.8uH", "SWPA6045S6R8MT", "C57254", "Inductor_SMD:L_Sunlord_SWPA6045S", {1:"BUCK_SW",2:"+5V_PRE_IDEAL"}, [122,122,0], "Sunlord")
capacitor("C301","10uF35V","VBATT_2S_IN","POWER_GND",[112,122,90],"power")
capacitor("C302","100nF","BUCK_BST","BUCK_SW",[115,116.5,0],"power")
capacitor("C303","22uF25V","+5V_PRE_IDEAL","POWER_GND",[127.5,121,90],"power")
capacitor("C304","22uF25V","+5V_PRE_IDEAL","POWER_GND",[131,121,90],"power")
part("power","U302","duck:LM5050_1_B","LM5050-1","LM5050MKX-1/NOPB","C473393","Package_TO_SOT_SMD:TSOT-23-6",{1:"IDEAL_VS",2:"POWER_GND",3:"POWER_GND",4:"+5V_PRE_IDEAL",5:"IDEAL_GATE",6:"+5V"},[133,115,0],"Texas Instruments","https://www.ti.com/lit/ds/symlink/lm5050-1.pdf")
part("power","Q301","duck:AO3404A_B","AO3404A","AO3404A","C30010","Package_TO_SOT_SMD:SOT-23",{1:"IDEAL_GATE",2:"+5V_PRE_IDEAL",3:"+5V"},[134,121.5,180],"AOS","https://www.aosmd.com/sites/default/files/res/datasheets/AO3404A.pdf")
resistor("R301","100R","VBATT_2S_IN","IDEAL_VS",[129,114.5,0],"power")
capacitor("C305","100nF","IDEAL_VS","POWER_GND",[129,112.5,0],"power")
part("power","D301","Device:D_Zener","SMBJ12A","SMBJ12A-E3/52","C1973121","Diode_SMD:D_SMB",{1:"VBATT_2S_IN",2:"POWER_GND"},[107.5,120,180],"Vishay","https://www.vishay.com/docs/88392/smbj.pdf")

for reference,position in (("J401",[106.5,110.5,90]),("J402",[113.8,110.5,90])):
    part("servo_ttl",reference,"Connector_Generic:Conn_01x03","SERVO_AMP2","CNJM A2007WV-3P","C5151076","duck:AMP2007_3P_B",{1:"POWER_GND",2:"VBATT_2S_IN",3:"DXL_DATA"},position,"CNJM","https://atta.szlcsc.com/upload/public/pdf/source/20220909/93F02259E7146615AAD747544D994A1F.pdf")
part("servo_ttl","U801","74xGxx:74LVC1G126","SN74LVC1G126DBVR","SN74LVC1G126DBVR","C7834","Package_TO_SOT_SMD:SOT-23-5",{1:"DXL_DIR",2:"UART2_TX",3:"POWER_GND",4:"DXL_DATA_INT",5:"+3V3"},[121,110,0],"Texas Instruments")
part("servo_ttl","U802","74xGxx:74LVC1G125","SN74LVC1G125DBVR","SN74LVC1G125DBVR","C23654","Package_TO_SOT_SMD:SOT-23-5",{1:"DXL_DIR",2:"DXL_DATA_INT",3:"POWER_GND",4:"UART2_RX",5:"+3V3"},[126,110,180],"Texas Instruments")
resistor("R401","100k","DXL_DIR","POWER_GND",[123.5,106.5,0],"servo_ttl")
resistor("R402","10k","UART2_TX","+3V3",[119.5,106.5,0],"servo_ttl")
resistor("R403","10k","DXL_DATA_INT","+3V3",[120,114,0],"servo_ttl")
resistor("R404","0R","DXL_DATA_INT","DXL_DATA",[117,110,90],"servo_ttl")
part("servo_ttl","D401","Device:D_Zener","5.1V","BZT52C5V1S-7-F","C151348","Diode_SMD:D_SOD-323",{1:"DXL_DATA",2:"POWER_GND"},[117.2,113.5,0],"Diodes")
capacitor("C401","100nF","+3V3","POWER_GND",[121,112.8,0],"servo_ttl")
capacitor("C402","100nF","+3V3","POWER_GND",[126,112.8,0],"servo_ttl")
part("i2c_expansion","J502","duck:QWIIC4_B","QWIIC_3V3","BM04B-SRSS-TB(LF)(SN)","C160390","Connector_JST:JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical",{1:"POWER_GND",2:"+3V3",3:"I2C5_SDA",4:"I2C5_SCL","MP":"POWER_GND"},[160,112,90],"JST")
resistor("R501","10k","+3V3","I2C5_SDA",[156,108.5,0],"i2c_expansion")
resistor("R502","10k","+3V3","I2C5_SCL",[156,110.5,0],"i2c_expansion")

codec = {1:"AUDIO_MCLK",2:"I2S_BCLK",3:"I2S_LRCK",4:"I2S_SDO",5:"I2S_SDI",6:"POWER_GND",7:"+3V3",8:"I2C5_SCL",9:"I2C5_SDA",10:"MIC_EXT_L_AC",11:"POWER_GND",12:"MIC_EXT_R_AC",13:"POWER_GND",14:"POWER_GND",15:"MICBIAS",16:"MIC_ONBOARD_AC",17:"POWER_GND",18:"+3V3",19:None,20:None,21:"POWER_GND",22:None,23:None,24:"+3V3",25:"+3V3",26:"POWER_GND",27:"CODEC_LEFT_LOP",28:None,29:"CODEC_RIGHT_LOP",30:None,31:"CODEC_RST",32:"+1V8_CODEC",33:"POWER_GND"}
part("audio_codec","U701","duck:TLV320AIC3104","TLV320AIC3104","TLV320AIC3104IRHBR","C181753","duck:TI_RHB0032E_AIC3104_EP345",codec,[143,115,0],"Texas Instruments","https://www.ti.com/lit/ds/symlink/tlv320aic3104.pdf")
part("audio_codec","U702","duck:XC6206_18_B","XC6206P182MR","XC6206P182MR","C347373","duck:UMW_XC6206_SOT23_B",{1:"POWER_GND",2:"+3V3",3:"+1V8_CODEC"},[136,109,180],"UMW","https://atta.szlcsc.com/upload/public/pdf/source/20260423/ACBED32A813F1E5C9C286FBFCFC9B7FD.pdf")
part("audio_codec","Y701","duck:OSC2520_B","12MHz","OT3EL89CJI-111YLC-12M","C7425459","duck:YXC_2520_YSO110TR_B",{1:"+3V3",2:"POWER_GND",3:"AUDIO_MCLK",4:"+3V3"},[141,108,0],"YXC","https://atta.szlcsc.com/upload/public/pdf/source/20260116/277ADDA9FE6BD42D3AF503786E6466E2.pdf")
resistor("R701","10k","+3V3","CODEC_RST",[147,108,0],"audio_codec")
capacitor("C701","100nF","CODEC_RST","POWER_GND",[149.5,108,0],"audio_codec")
capacitor("C702","1uF","+3V3","POWER_GND",[133.5,108,90],"audio_codec")
capacitor("C703","10uF","+1V8_CODEC","POWER_GND",[136,112,90],"audio_codec")
capacitor("C704","100nF","+1V8_CODEC","POWER_GND",[139,111,0],"audio_codec")
capacitor("C705","100nF","+3V3","POWER_GND",[147.5,112,90],"audio_codec")
capacitor("C706","1uF","+3V3","POWER_GND",[149.5,112,90],"audio_codec")
capacitor("C707","100nF","+3V3","POWER_GND",[143,119.2,0],"audio_codec")
capacitor("C708","1uF","+3V3","POWER_GND",[143,121.3,0],"audio_codec")
capacitor("C709","100nF","+3V3","POWER_GND",[139,115,90],"audio_codec")
capacitor("C710","1uF","+3V3","POWER_GND",[136.8,115,90],"audio_codec")
capacitor("C711","100nF","+3V3","POWER_GND",[145.5,110,0],"audio_codec")
capacitor("C712","1uF","+3V3","POWER_GND",[145.5,108,0],"audio_codec")
capacitor("C713","100nF","+3V3","POWER_GND",[140,105.8,0],"audio_codec")

part("audio_io","MK701","duck:LMA2718_B","MEMS_MIC","LMA2718T421-OA5-2","C7587901","duck:LMA2718_B",{1:"MIC_ONBOARD_OUT",2:"POWER_GND",3:"POWER_GND",4:"+3V3"},[137.5,123,0],"LinkMems","https://atta.szlcsc.com/upload/public/pdf/source/20230901/7575319F733F22ECE149FBB07CD99356.pdf")
capacitor("C721","100nF","+3V3","POWER_GND",[137.5,120.4,0],"audio_io")
capacitor("C722","1uF","MIC_ONBOARD_OUT","MIC_ONBOARD_AC",[140,123,90],"audio_io")
for reference,net,position in (("J505","MIC_EXT_L",[144,127,0]),("J507","MIC_EXT_R",[151,127,0])):
    part("audio_io",reference,"Connector_Generic:Conn_01x02",reference+"_MIC","A1251WV-2P","C5333427","duck:A1251_2P_B",{1:"POWER_GND",2:net},position,"CJT","https://atta.szlcsc.com/upload/public/pdf/source/20180913/C273009_2E94D2EE16A658F8B593BE6904D224FC.pdf")
resistor("R721","2.2k","MICBIAS","MIC_EXT_L",[142,125,0],"audio_io")
resistor("R722","2.2k","MICBIAS","MIC_EXT_R",[148.5,125,0],"audio_io")
capacitor("C723","1uF","MIC_EXT_L","MIC_EXT_L_AC",[144.5,123,0],"audio_io")
capacitor("C724","1uF","MIC_EXT_R","MIC_EXT_R_AC",[147,123,0],"audio_io")
capacitor("C725","100nF","MICBIAS","POWER_GND",[146,120.5,0],"audio_io")
amp = {1:None,2:"POWER_GND",3:None,4:"+5V",5:"+3V3",6:"AMP_VDD_FILT",7:"AMP_LEFT_INPUT",8:"AMP_VREF",9:"+3V3",10:"AMP_RIGHT_INPUT",11:"POWER_GND",12:"AUDIO_AMP_EN",13:"+5V",14:"AMP_R_N_RAW",15:"POWER_GND",16:"AMP_R_P_RAW"}
part("audio_amp","U803","Amplifier_Audio:PAM8406D","PAM8406DR","PAM8406DR","C86270","Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",amp,[155,118,180],"Diodes","https://www.diodes.com/assets/Datasheets/PAM8406.pdf")
capacitor("C731","1uF","CODEC_LEFT_LOP","AMP_LEFT_INPUT",[150,115,0],"audio_amp")
capacitor("C732","1uF","CODEC_RIGHT_LOP","AMP_RIGHT_INPUT",[150,117,0],"audio_amp")
capacitor("C733","1uF","AMP_VREF","POWER_GND",[150,119,0],"audio_amp")
capacitor("C734","10uF","+5V","POWER_GND",[152,112,0],"audio_amp")
capacitor("C735","100nF","+5V","POWER_GND",[155,111.5,0],"audio_amp")
capacitor("C736","10uF","+5V","POWER_GND",[158,124,0],"audio_amp")
capacitor("C737","100nF","+5V","POWER_GND",[156,124,0],"audio_amp")
capacitor("C738","1uF","AMP_VDD_FILT","POWER_GND",[151,110,0],"audio_amp")
part("audio_amp","FB701","Device:FerriteBead","600R@100MHz","BLM18KG601SN1D","C85833","Inductor_SMD:L_0603_1608Metric",{1:"+5V",2:"AMP_VDD_FILT"},[153.5,108,0],"Murata")
resistor("R731","100k","+3V3","AUDIO_AMP_EN",[150,121,0],"audio_amp")
for reference,raw,output,position in (("FB702","AMP_R_N_RAW","SPK_N",[160,118,90]),("FB703","AMP_R_P_RAW","SPK_P",[160,121,90])):
    part("audio_amp",reference,"Device:FerriteBead","120R@100MHz","PE-0603PFB121ST","C2661472","Inductor_SMD:L_0603_1608Metric",{1:raw,2:output},position,"Power Ever")
capacitor("C739","220pF","SPK_N","POWER_GND",[162.5,118,90],"audio_amp")
capacitor("C740","220pF","SPK_P","POWER_GND",[162.5,121,90],"audio_amp")
part("audio_amp","J506","Connector_Generic:Conn_01x02","SPEAKER","A1251WV-2P","C5333427","duck:A1251_2P_B",{1:"SPK_P",2:"SPK_N"},[158,127,0],"CJT","https://atta.szlcsc.com/upload/public/pdf/source/20180913/C273009_2E94D2EE16A658F8B593BE6904D224FC.pdf")
for reference,net,position in (("TP801","VBATT_2S_IN",[104,116,0]),("TP802","+5V",[131,124.5,0]),("TP803","+3V3",[149,106,0])):
    part("testpoints",reference,"Connector:TestPoint",net,"","","TestPoint:TestPoint_Pad_D1.0mm",{1:net},position,"",description="bare test pad; not a purchased component")

sheet_names = list(dict.fromkeys(part["sheet"] for part in parts))
sheets = []
for sheet_name in sheet_names:
    sheet = schematic.Sheet(sheet_name, "自主HAT B.0 / " + sheet_name)
    first(sheet.tree,"paper")[1]=quoted("A2")
    title = first(sheet.tree,"title_block")
    first(title,"date")[1]=quoted("2026-11-04")
    first(title,"rev")[1]=quoted("B.0 CANDIDATE - NOT FOR FAB")
    sheet.text("B.0 开发候选；脚位已建立，制造/成本和首板验收尚未完成。",25.4,20.32)
    for index, component in enumerate(part for part in parts if part["sheet"]==sheet_name):
        column=index%4
        row=index//4
        xpos=65+column*140
        ypos=80+row*75
        try:
            sheet.component(component["symbol"],component["ref"],component["value"],xpos,ypos,component["pins"],component["footprint"])
        except Exception as error:
            raise RuntimeError(f"Cannot create {component['ref']} using {component['symbol']}") from error
        instance=children(sheet.tree,"symbol")[-1]
        for key,value in (("MPN",component["mpn"]),("LCSC",component["code"]),("Manufacturer",component["manufacturer"]),("Datasheet",component["datasheet"]),("Description",component["description"])):
            instance.append(schematic.prop(key,value,xpos,ypos,True))
        if component["ref"].startswith("TP"):
            first(instance,"in_bom")[1]="no"
        component["uuid"]=str(first(instance,"uuid")[1])
        component["sheet_uuid"]=str(sheet.id)
    if sheet_name=="power":
        for index,net in enumerate(("VBATT_2S_IN","POWER_GND","+3V3","+5V","+5V_PRE_IDEAL","IDEAL_VS","AMP_VDD_FILT")):
            sheet.component("power:PWR_FLAG",f"#FLG{index+1:02d}","PWR_FLAG",50+index*75,370,{"1":net},"")
    sheet.save()
    sheets.append(sheet)
root=schematic.Sheet(stem,"自主HAT Rev B.0 / 成本约束开发")
first(root.tree,"uuid")[1]=schematic.uid("root")
first(root.tree,"paper")[1]=quoted("A2")
first(first(root.tree,"title_block"),"rev")[1]=quoted("B.0 CANDIDATE - NOT FOR FAB")
root.text("5片目标总价 <= 750元；两层/单面SMT；无板载BMI088；当前不是生产放行。",25,25)
for index,sheet in enumerate(sheets):
    xpos,ypos=35+(index%3)*150,60+(index//3)*55
    root.tree.append(["sheet",["at",xpos,ypos],["size",110,25],["stroke",["width",0.1524],["type","solid"]],["fill",["color",0,0,0,0]],["uuid",sheet.id],schematic.prop("Sheetname",sheet.name,xpos+55,ypos-2),schematic.prop("Sheetfile",sheet.name+".kicad_sch",xpos+55,ypos+28),["instances",["project",quoted(stem),["path",quoted("/"+str(schematic.uid("root"))),["page",quoted(index+2)]]]]])
root.tree.append(["sheet_instances",["path",quoted("/"),["page",quoted("1")]]])
root.save()
net_contract={"date":"2026-11-04","revision":"B.0","production_ready":False,"pins":[pin for sheet in sheets for pin in sheet.contract if not pin["reference"].startswith("#")],"radxa_physical_pins":header_pins,"hardware_tested":False,"bmi088":"removed; I2C expansion retained","lm5050_supply":"VBATT via 100ohm; output 5V sensing; AO3404A +/-20V gate"}
(project/"net-contract.json").write_text(json.dumps(net_contract,ensure_ascii=False,indent=2),encoding="utf-8")
(project/"design-components.json").write_text(json.dumps(parts,ensure_ascii=False,indent=2),encoding="utf-8")
with (project/"bom-candidate.csv").open("w",encoding="utf-8-sig",newline="") as stream:
    writer=csv.DictWriter(stream,fieldnames=["Reference","Value","MPN","LCSC","Footprint","Manufacturer"])
    writer.writeheader()
    for component in parts:
        if component["mpn"]:
            writer.writerow(dict(zip(writer.fieldnames,[component["ref"],component["value"],component["mpn"],component["code"],component["footprint"],component["manufacturer"]])))
print(json.dumps({"parts":len(parts),"fitted":sum(bool(part["mpn"]) for part in parts),"sheets":sheet_names,"status":"schematic_candidate_unverified"},ensure_ascii=False))
