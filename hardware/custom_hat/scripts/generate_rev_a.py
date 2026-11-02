import copy
import hashlib
import json
import math
import re
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "rev_a"
LIB = Path("C:/Users/yilv/AppData/Local/Programs/KiCad/10.0/share/kicad/symbols")
PROJECT = "custom_hat_rev_a"
NS = uuid.UUID("fe057346-2587-4c77-803f-d354cdb50eed")


class Quoted(str):
    pass


def parse(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack = [[]]
    for token in tokens:
        if token == "(":
            node = []
            stack[-1].append(node)
            stack.append(node)
        elif token == ")":
            stack.pop()
        elif token.startswith('"'):
            stack[-1].append(Quoted(json.loads(token)))
        else:
            stack[-1].append(token)
    return stack[0][0]


def dump(node, depth=0):
    if isinstance(node, Quoted):
        return json.dumps(str(node), ensure_ascii=False)
    if not isinstance(node, list):
        return str(node)
    if all(not isinstance(child, list) for child in node):
        return "(" + " ".join(dump(child) for child in node) + ")"
    return "(" + " ".join(dump(child) if not isinstance(child, list) else "\n" + "  " * (depth + 1) + dump(child, depth + 1) for child in node) + ")"


def q(value):
    return Quoted(str(value))


def uid(value):
    return q(uuid.uuid5(NS, value))


def children(node, key):
    return [child for child in node if isinstance(child, list) and child and child[0] == key]


def first(node, key):
    return next(iter(children(node, key)), None)


def effects(size=1.0, justify=None, hidden=False):
    value = ["effects", ["font", ["size", size, size]]]
    if justify:
        value.append(["justify", justify])
    if hidden:
        value.append(["hide", "yes"])
    return value


def prop(name, value, x, y, hidden=False):
    return ["property", q(name), q(value), ["at", x, y, 0], effects(hidden=hidden)]


LIB_CACHE = {}


def library_symbol(lib_id):
    library, name = lib_id.split(":", 1)
    if library not in LIB_CACHE:
        project_lib = OUT / (library + ".kicad_sym")
        path = project_lib if project_lib.exists() else (LIB / (library + ".kicad_sym"))
        LIB_CACHE[library] = parse(path.read_text(encoding="utf-8"))
    original = next(node for node in children(LIB_CACHE[library], "symbol") if node[1] == name)
    symbol = copy.deepcopy(original)
    extension = first(symbol, "extends")
    if extension:
        parent = library_symbol(library + ":" + extension[1])
        symbol.remove(extension)
        own_properties = {node[1] for node in children(symbol, "property")}
        for node in parent[2:]:
            if isinstance(node, list) and (node[0] != "property" or node[1] not in own_properties):
                symbol.append(copy.deepcopy(node))
    symbol[1] = q(lib_id)
    return symbol


class Sheet:
    def __init__(self, name, title):
        self.name = name
        self.id = uid("sheet:" + name)
        self.lib = ["lib_symbols"]
        self.tree = ["kicad_sch", ["version", "20250114"], ["generator", q("eeschema")], ["uuid", self.id], ["paper", q("A3")], ["title_block", ["title", q(title)], ["date", q("2026-10-28")], ["rev", q("A schematic draft")], ["company", q("duck-robot")]], self.lib]
        self.contract = []
        self.counter = 0

    def identity(self):
        self.counter += 1
        return uid(self.name + ":" + str(self.counter))

    def text(self, value, x, y, size=1.3):
        self.tree.append(["text", q(value), ["at", x, y, 0], effects(size, "left"), ["uuid", self.identity()]])

    def label(self, name, x, y, angle=0):
        self.tree.append(["global_label", q(name), ["shape", "bidirectional"], ["at", x, y, angle], effects(0.85, "left" if angle == 0 else "right"), ["uuid", self.identity()], prop("Intersheetrefs", "${INTERSHEET_REFS}", x, y, True)])

    def wire(self, start, end):
        self.tree.append(["wire", ["pts", ["xy", *start], ["xy", *end]], ["stroke", ["width", 0], ["type", "default"]], ["uuid", self.identity()]])

    def component(self, lib_id, reference, value, x, y, nets, footprint=None, dnp=False):
        # snap to the 1.27 mm connection grid so ERC does not flag off-grid pins
        x = round(x / 1.27) * 1.27
        y = round(y / 1.27) * 1.27
        symbol = library_symbol(lib_id)
        if not any(node[1] == lib_id for node in self.lib[1:]):
            self.lib.append(symbol)
        symbol_id = uid(self.name + ":" + reference)
        footprint_prop = next((node[2] for node in children(symbol, "property") if node[1] == "Footprint"), "")
        reference_position = (x + 5.08, y - 1.27) if lib_id in {"Device:C", "Device:R", "Device:L"} else (x, y - 5.08)
        value_position = (x + 5.08, y + 1.27) if lib_id in {"Device:C", "Device:R", "Device:L"} else (x, y - 2.54)
        instance = ["symbol", ["lib_id", q(lib_id)], ["at", x, y, 0], ["unit", 1], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "yes" if dnp else "no"], ["uuid", symbol_id], prop("Reference", reference, *reference_position), prop("Value", value, *value_position), prop("Footprint", footprint if footprint is not None else footprint_prop, x, y, True)]
        for sub in children(symbol, "symbol"):
            for pin in children(sub, "pin"):
                number = str(first(pin, "number")[1])
                pin_at = first(pin, "at")
                px, py = round(x + float(pin_at[1]), 4), round(y - float(pin_at[2]), 4)
                angle = float(pin_at[3])
                net = nets.get(number)
                instance.append(["pin", q(number), ["uuid", uid(self.name + ":" + reference + ":" + number)]])
                if net is None:
                    self.tree.append(["no_connect", ["at", px, py], ["uuid", self.identity()]])
                else:
                    end = (round(px - 7.62 * math.cos(math.radians(angle)), 4), round(py + 7.62 * math.sin(math.radians(angle)), 4))
                    self.wire((px, py), end)
                    self.label(net, *end, 0 if angle == 180 else 180)
                self.contract.append({"reference": reference, "pin": number, "net": net, "electrical_type": pin[1], "lib_id": lib_id})
        instance.append(["instances", ["project", q(PROJECT), ["path", q("/" + str(uid("root")) + "/" + str(self.id)), ["reference", q(reference)], ["unit", 1]]]])
        self.tree.append(instance)

    def save(self):
        self.tree.append(["embedded_fonts", "no"])
        (OUT / (self.name + ".kicad_sch")).write_text(dump(self.tree) + "\n", encoding="utf-8")


def interfaces():
    radxa = Sheet("radxa_40p", "Radxa ZERO 3W - 40-pin interface / 3.3V logic")
    nets = {1:"+3V3",2:"+5V",4:"+5V",6:"POWER_GND",8:"UART2_TX",9:"POWER_GND",10:"UART2_RX",11:"DXL_DIR",12:"I2S_BCLK",13:"I2S_MCLK",14:"POWER_GND",17:"+3V3",20:"POWER_GND",25:"POWER_GND",29:"I2C5_SCL",30:"POWER_GND",31:"I2C5_SDA",34:"POWER_GND",35:"I2S_LRCK",38:"I2S_SDI",39:"POWER_GND",40:"I2S_SDO"}
    radxa.component("Connector_Generic:Conn_02x20_Odd_Even", "J101", "RADXA_ZERO_3W_40P", 127, 90, {str(pin):net for pin,net in nets.items()}, "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical")
    radxa.text("3.3V GPIO only. Pin 8/10 UART2 also used by boot console: disable console before servo bus operation.", 35, 35)
    radxa.text("I2C5: pins 29/31. I2S3: 12/13/35/38/40. SPI3: 19/21/23/24. No EEPROM.", 35, 145)
    power = Sheet("power", "Power input and AP64350 5V buck - values from DS41976 and EVM BOM")
    power.component("Connector_Generic:Conn_01x08", "J301", "POWER_AND_RAILS", 127, 90, {"1":"VBATT_2S_IN", "2":"POWER_GND", "3":"+5V", "4":"+3V3", "5":None, "6":"+1V8_CODEC", "7":"SERVO_VBAT", "8":"POWER_GND"}, "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical")
    power.component("duck:AP64350", "U301", "AP64350", 190, 90, {"1":"BUCK_BST", "2":"VBATT_2S_IN", "3":"BUCK_EN", "4":"BUCK_RT", "5":"+5V_FB", "6":"BUCK_COMP", "7":"POWER_GND", "8":"BUCK_SW", "9":"POWER_GND"}, "duck:SO-8EP_AP64350")
    power.component("Device:D_TVS", "D301", "SMBJ12A (fitted)", 38.1, 60.96, {"1":"VBATT_2S_IN", "2":"POWER_GND"}, "Diode_SMD:D_SMB")
    power.component("Device:R", "R303", "200k", 72.39, 60.96, {"1":"BUCK_RT", "2":"POWER_GND"}, "Resistor_SMD:R_0805_2012Metric")
    power.component("Device:R", "R305", "100k", 106.68, 60.96, {"1":"VBATT_2S_IN", "2":"BUCK_EN"}, "Resistor_SMD:R_0805_2012Metric")
    power.component("Device:C", "C303", "10uF", 140.97, 60.96, {"1":"VBATT_2S_IN", "2":"POWER_GND"}, "Capacitor_SMD:C_1206_3216Metric")
    power.component("Device:C", "C304", "10uF", 175.26, 60.96, {"1":"VBATT_2S_IN", "2":"POWER_GND"}, "Capacitor_SMD:C_1206_3216Metric")
    power.component("Device:L", "L301", "5.5uH", 209.55, 60.96, {"1":"BUCK_SW", "2":"+5V"}, "Inductor_SMD:L_12x12mm_H8mm")
    power.component("Device:C", "C302", "100nF", 243.84, 60.96, {"1":"BUCK_BST", "2":"BUCK_SW"}, "Capacitor_SMD:C_0805_2012Metric")
    power.component("Device:C", "C305", "22uF", 278.13, 60.96, {"1":"+5V", "2":"POWER_GND"}, "Capacitor_SMD:C_1206_3216Metric")
    power.component("Device:C", "C306", "22uF", 312.42, 60.96, {"1":"+5V", "2":"POWER_GND"}, "Capacitor_SMD:C_1206_3216Metric")
    power.component("Device:C", "C307", "22uF reserve", 346.71, 60.96, {"1":"+5V", "2":"POWER_GND"}, "Capacitor_SMD:C_1206_3216Metric", dnp=True)
    power.component("Device:R", "R301", "52.3k", 106.68, 120.65, {"1":"+5V", "2":"+5V_FB"}, "Resistor_SMD:R_0805_2012Metric")
    power.component("Device:R", "R302", "10k", 140.97, 120.65, {"1":"+5V_FB", "2":"POWER_GND"}, "Resistor_SMD:R_0805_2012Metric")
    power.component("Device:R", "R304", "14k", 175.26, 120.65, {"1":"BUCK_COMP", "2":"COMP_RC"}, "Resistor_SMD:R_0805_2012Metric")
    power.component("Device:C", "C301", "3.3nF", 209.55, 120.65, {"1":"COMP_RC", "2":"POWER_GND"}, "Capacitor_SMD:C_0805_2012Metric")
    for idx, rail in enumerate(["+5V", "+3V3", "VBATT_2S_IN", "POWER_GND"], start=1):
        power.component("power:PWR_FLAG", f"FLG{idx}", rail, 40 + idx * 20, 160, {"1": rail})
    power.component("Regulator_Linear:LP38693DT-1.8", "U702", "LP38693DT-1.8 codec 1V8", 240, 60, {"1":"+1V8_CODEC", "2":"POWER_GND", "3":"+3V3"}, "Package_TO_SOT_SMD:TO-252-3_TabPin2")
    power.component("Device:C", "C308", "1uF", 250, 80, {"1":"+3V3", "2":"POWER_GND"}, "Capacitor_SMD:C_0805_2012Metric")
    power.component("Device:C", "C309", "1uF", 260, 80, {"1":"+1V8_CODEC", "2":"POWER_GND"}, "Capacitor_SMD:C_0805_2012Metric")
    power.text("AP64350 pin map: 1 BST, 2 VIN, 3 EN, 4 RT/CLK, 5 FB, 6 COMP, 7 GND, 8 SW; EP is pin 9 and must go to GND (DS41976 p3).", 35, 35)
    power.text("Vout=0.8V*(1+52.3k/10k)=4.98V; fsw=500kHz via RT=200k; C305+C306 fitted (44uF), C307 22uF reserved DNP.", 35, 145)
    power.text("U702 LP38693DT-1.8 makes +1V8_CODEC from +3V3 (codec DVDD); C308/C309 are its 1uF caps.", 35, 128)
    power.text("SMBJ12A fitted: hot-plug sweep peaks 14-16V over 1-10uH cable, below the 35V abs-max; TVS is defensive.", 35, 152)
    power.text("Pin 4 is RT/CLK here but SS on AP64501: symbols and PCB must not be reused across the two parts.", 35, 159)
    ttl = Sheet("servo_ttl", "Half-duplex TTL servo bus - two 3P outlets")
    # EH sockets follow the project's documented order: 1=GND, 2=VBAT, 3=DATA
    ttl.component("Connector_Generic:Conn_01x03", "J401", "DYNAMIXEL_TTL_1", 100, 75, {"1":"POWER_GND", "2":"SERVO_VBAT", "3":"DXL_DATA"}, "Connector_JST:JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical")
    ttl.component("Connector_Generic:Conn_01x03", "J402", "DYNAMIXEL_TTL_2", 100, 115, {"1":"POWER_GND", "2":"SERVO_VBAT", "3":"DXL_DATA"}, "Connector_JST:JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical")
    # half-duplex interface: 1G126 transmits (OE high), 1G125 receives (/OE low).
    # One DIR net drives both because their enables are complementary.
    ttl.component("74xGxx:74LVC1G126", "U801", "SN74LVC1G126", 190, 60, {"1":"DXL_DIR", "2":"UART2_TX", "3":"POWER_GND", "4":"DXL_DATA", "5":"+3V3"}, "Package_TO_SOT_SMD:SOT-23-5")
    ttl.component("74xGxx:74LVC1G125", "U802", "SN74LVC1G125", 240, 60, {"1":"DXL_DIR", "2":"DXL_DATA", "3":"POWER_GND", "4":"UART2_RX", "5":"+3V3"}, "Package_TO_SOT_SMD:SOT-23-5")
    # default to receive when the GPIO is high-Z at boot
    ttl.component("Device:R", "R310", "100k", 240, 90, {"1":"DXL_DIR", "2":"POWER_GND"}, "Resistor_SMD:R_0402_1005Metric")
    # single battery input with an explicit branch to the servo rail
    ttl.component("Device:R", "R309", "0R", 60, 60, {"1":"VBATT_2S_IN", "2":"SERVO_VBAT"}, "Resistor_SMD:R_1206_3216Metric")
    ttl.component("Connector_Generic:Conn_01x03", "J403", "HOST_UART2", 190, 95, {"1":"UART2_TX", "2":"UART2_RX", "3":"POWER_GND"}, "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical")
    ttl.text("Half-duplex TTL: 1G126 drives DATA from UART2_TX (OE=DXL_DIR high), 1G125 reads DATA into UART2_RX (/OE=DXL_DIR low). R310 pulls DXL_DIR low at boot so the board listens. One bus, two EH sockets, no RS485.", 35, 35)
    ttl.text("EH pin order: 1=GND, 2=VBAT, 3=DATA. R309 (0R) is the battery-to-servo branch. UART2 is the boot console until disabled in software.", 35, 145)
    imu = Sheet("imu_tof", "BMI088 + ToF on shared I2C5")
    imu.component("Connector_Generic:Conn_01x16", "U501", "BMI088", 127, 101.6, {"1":None, "2":"POWER_GND", "3":"+3V3", "4":"POWER_GND", "5":None, "6":"POWER_GND", "7":"+3V3", "8":"I2C5_SCL", "9":"I2C5_SDA", "10":"POWER_GND", "11":"+3V3", "12":"BMI_INT3_TP", "13":None, "14":"+3V3", "15":"+3V3", "16":"BMI_INT1_TP"}, "Package_LGA:Bosch_LGA-16_4.5x3mm_P0.5mm_LayoutBorder7x1y_ClockwisePinNumbering")
    imu.component("Device:C", "C319", "100nF", 60, 120, {"1":"+3V3", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    imu.component("Device:C", "C320", "100nF", 100, 120, {"1":"+3V3", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    imu.component("Connector_Generic:Conn_01x04", "J502", "TOF_I2C5", 190, 95, {"1":"+3V3", "2":"POWER_GND", "3":"I2C5_SCL", "4":"I2C5_SDA"}, "Connector_JST:JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical")
    imu.text("BMI088 Rev1.9 p52/53: accel SDO1=3V3 (0x19), gyro SDO2=GND (0x68), PS=3V3 selects I2C, CSB2 pin5 is DNC in I2C mode, CSB1 pin14=3V3. Pin 2 is GND despite its NC name. C319/C320 are the local 100nF for VDD/VDDIO.", 35, 35)
    imu.text("INT3/INT1 are testpoint/candidate GPIO nets; exact host GPIO assignment remains pending.", 35, 145)
    audio = Sheet("audio", "I2S codec interface - I2C5 and 1V8 codec rail")
    codec_nets = {
        "1": "I2S_MCLK", "2": "I2S_BCLK", "3": "I2S_LRCK", "4": "I2S_SDO", "5": "I2S_SDI",
        "6": "POWER_GND", "7": "+3V3", "8": "I2C5_SCL", "9": "I2C5_SDA",
        "10": "AUDIO_MIC_AC", "11": "AUDIO_MIC_REF", "12": None, "13": None, "14": None, "15": "AUDIO_MIC_BIAS", "16": None,
        "17": "POWER_GND", "18": "+3V3", "19": "AUDIO_HP_L", "20": None,
        "21": "POWER_GND", "22": None, "23": "AUDIO_HP_R", "24": "+3V3",
        "25": "+3V3", "26": "POWER_GND",
        "27": "AUDIO_LINE_L", "28": None, "29": None, "30": None,
        "31": "CODEC_RST", "32": "+1V8_CODEC", "33": "POWER_GND",
    }
    audio.component("duck:TLV320AIC3104", "U701", "TLV320AIC3104", 150, 210, codec_nets, "Package_DFN_QFN:VQFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm")
    audio.component("Device:R", "R308", "10k", 50, 60, {"1":"CODEC_RST", "2":"+3V3"}, "Resistor_SMD:R_0402_1005Metric")
    audio.component("Device:C", "C310", "100nF", 90, 60, {"1":"CODEC_RST", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C311", "1uF", 130, 60, {"1":"+1V8_CODEC", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C312", "100nF", 170, 60, {"1":"+3V3", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C313", "1uF", 50, 110, {"1":"+3V3", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C315", "1uF", 130, 110, {"1":"+3V3", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    # --- microphone: single-ended electret, biased from MICBIAS ---
    audio.component("Connector_Generic:Conn_01x02", "J505", "MIC_IN", 60, 160, {"1":"AUDIO_MIC", "2":"POWER_GND"}, "Connector_JST:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical")
    audio.component("Device:R", "R312", "2.2k", 100, 160, {"1":"AUDIO_MIC_BIAS", "2":"AUDIO_MIC"}, "Resistor_SMD:R_0402_1005Metric")
    audio.component("Device:C", "C325", "1uF", 140, 160, {"1":"AUDIO_MIC", "2":"AUDIO_MIC_AC"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C326", "1uF", 180, 160, {"1":"POWER_GND", "2":"AUDIO_MIC_REF"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C327", "100nF", 220, 160, {"1":"AUDIO_MIC_BIAS", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    # --- speaker: mono class-D from LEFT_LOP ---
    audio.component("Amplifier_Audio:PAM8302AAD", "U803", "PAM8302A", 280, 210, {"1":"AUDIO_AMP_EN", "2":None, "3":"AUDIO_AMP_INP", "4":"AUDIO_AMP_INN", "5":"SPK_P", "6":"+5V", "7":"POWER_GND", "8":"SPK_N"}, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")
    audio.component("Device:R", "R311", "100k", 280, 250, {"1":"AUDIO_AMP_EN", "2":"+3V3"}, "Resistor_SMD:R_0402_1005Metric")
    audio.component("Device:C", "C321", "1uF", 320, 210, {"1":"AUDIO_LINE_L", "2":"AUDIO_AMP_INP"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C322", "1uF", 360, 210, {"1":"AUDIO_AMP_INN", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C323", "10uF", 320, 250, {"1":"+5V", "2":"POWER_GND"}, "Capacitor_SMD:C_0805_2012Metric")
    audio.component("Connector_Generic:Conn_01x02", "J506", "SPEAKER", 360, 250, {"1":"SPK_P", "2":"SPK_N"}, "Connector_JST:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical")
    audio.component("Device:C", "C317", "10uF", 210, 110, {"1":"AUDIO_HP_L", "2":"AUDIO_L"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C318", "10uF", 250, 110, {"1":"AUDIO_HP_R", "2":"AUDIO_R"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Connector_Generic:Conn_01x03", "J504", "AUDIO_OUT_SH", 300, 110, {"1":"AUDIO_L", "2":"AUDIO_R", "3":"POWER_GND"}, "Connector_JST:JST_SH_BM03B-SRSS-TB_1x03-1MP_P1.00mm_Vertical")
    audio.text("Mic: electret biased from MICBIAS via R312 2.2k, AC-coupled by C325 into MIC1LP; MIC1LM is AC-coupled to GND by C326. Speaker: PAM8302A from LEFT_LOP through C321, /SD pulled up by R311, 2-pin speaker on J506.", 35, 250)
    audio.text("TLV320AIC3104, pinout from the TI IBIS model. I2C 0x18. DVDD(32)=1.8V, IOVDD(7)=3.3V, AVDD(25)=3.3V, DRVDD(18/24)=3.3V. Unused analog inputs left open (see research note).", 35, 35)
    audio.text("This page is a pin contract pending full C1 audio schematic re-implementation; no fabricated analog values are implied.", 35, 145)
    test = Sheet("testpoints", "Bring-up test points")
    test.component("Connector_Generic:Conn_01x02", "J802", "IMU_INT_TP", 190, 95, {"1":"BMI_INT1_TP", "2":"BMI_INT3_TP"}, "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical")
    # three rails only: the servo rail and the I2C pair are measurable at J301/J502
    # and the extra pads cost board space that the audio output needs
    for idx, net in enumerate(["VBATT_2S_IN", "+5V", "+3V3"], start=1):
        test.component("Connector:TestPoint", f"TP80{idx}", net, 60 + idx * 18, 95, {"1": net}, "TestPoint:TestPoint_Pad_D1.5mm")
    test.text("Six rails only (VBATT, SERVO_VBAT, +5V, +3V3, I2C5 SCL/SDA). Measurement access only; no load or protection function.", 35, 35)
    return [radxa, power, ttl, imu, audio, test]


def legacy_generate_unchecked():
    OUT.mkdir(parents=True, exist_ok=True)
    sheets = interfaces()
    root = Sheet(PROJECT, "Custom HAT Rev A - functional schematic")
    first(root.tree, "uuid")[1] = uid("root")
    root.text("2S servo power / Radxa ZERO 3W / BMI088 + ToF / audio", 25, 25)
    root.text("Excluded: RS485, identification EEPROM, charging, UPS, camera and display. Not released for fabrication.", 25, 33)
    for index, sheet in enumerate(sheets):
        posx, posy = 35 + (index % 3) * 115, 65 + (index // 3) * 50
        root.tree.append(["sheet", ["at", posx, posy], ["size", 90, 25], ["stroke", ["width", 0.1524], ["type", "solid"]], ["fill", ["color", 0,0,0,0]], ["uuid", sheet.id], prop("Sheetname", sheet.name, posx + 45, posy - 2), prop("Sheetfile", sheet.name + ".kicad_sch", posx + 45, posy + 28), ["instances", ["project", q(PROJECT), ["path", q("/" + str(uid("root"))), ["page", q(index + 2)]]]]])
        sheet.save()
    root.tree.append(["sheet_instances", ["path", q("/"), ["page", q("1")]]])
    root.save()
    (OUT / (PROJECT + ".kicad_pro")).write_text(json.dumps({"meta":{"filename":PROJECT + ".kicad_pro","version":1},"net_settings":{"classes":[{"name":"Default","clearance":0.2,"track_width":0.25,"via_diameter":0.6,"via_drill":0.3}]},"schematic":{}}, indent=2), encoding="utf-8")
    (OUT / "net-contract.json").write_text(json.dumps({"date":"2026-10-28","pins":[pin for sheet in sheets for pin in sheet.contract]}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {len(sheets)} functional sheets in {OUT}")


def main():
    raise SystemExit("Deprecated: full regeneration would overwrite the reviewed HAT. Use an isolated pipeline workspace and scoped edits.")


if __name__ == "__main__":
    main()
