"""Generate the project symbol library (duck.kicad_sym).

Two symbols, both built from datasheet pin tables rather than from memory:
- TLV320AIC3104: 32 pins + EP, names/numbers from the TI IBIS model
- AP64350: 8 pins + EP9, functions from DS41976 page 3 (pin description table)
"""
from pathlib import Path

TLV_PINS = [
    ("1", "MCLK", "input", "L"),
    ("2", "BCLK", "input", "L"),
    ("3", "WCLK", "input", "L"),
    ("4", "DIN", "input", "L"),
    ("5", "DOUT", "output", "L"),
    ("6", "DVSS", "power_in", "L"),
    ("7", "IOVDD", "power_in", "L"),
    ("8", "SCL", "bidirectional", "L"),
    ("9", "SDA", "bidirectional", "L"),
    ("10", "MIC1LP/LINE1LP", "input", "L"),
    ("11", "MIC1LM/LINE1LM", "input", "L"),
    ("12", "MIC1RP/LINE1RP", "input", "L"),
    ("13", "MIC1RM/LINE1RM", "input", "L"),
    ("14", "MIC2L/LINE2L/MICDET", "input", "L"),
    ("15", "MICBIAS", "output", "L"),
    ("16", "MIC2R/LINE2R", "input", "L"),
    ("17", "AVSS1", "power_in", "R"),
    ("18", "DRVDD", "power_in", "R"),
    ("19", "HPLOUT", "output", "R"),
    ("20", "HPLCOM", "output", "R"),
    ("21", "DRVSS", "power_in", "R"),
    ("22", "HPRCOM", "output", "R"),
    ("23", "HPROUT", "output", "R"),
    ("24", "DRVDD", "power_in", "R"),
    ("25", "AVDD", "power_in", "R"),
    ("26", "AVSS2", "power_in", "R"),
    ("27", "LEFT_LOP", "output", "R"),
    ("28", "LEFT_LOM", "output", "R"),
    ("29", "RIGHT_LOP", "output", "R"),
    ("30", "RIGHT_LOM", "output", "R"),
    ("31", "~{RESET}", "input", "R"),
    ("32", "DVDD", "power_in", "R"),
]

AP_PINS = [
    ("1", "BST", "input", "L"),
    ("2", "VIN", "power_in", "L"),
    ("3", "EN", "input", "L"),
    ("4", "RT/CLK", "input", "L"),
    ("5", "FB", "input", "R"),
    ("6", "COMP", "output", "R"),
    ("7", "GND", "power_in", "R"),
    ("8", "SW", "output", "R"),
]

PITCH = 3.81  # wide enough that adjacent global labels do not touch
TOP = 30.48


def pin_sexpr(number, name, etype, side, index):
    y = TOP - index * PITCH
    x, angle = (-17.78, 0) if side == "L" else (17.78, 180)
    return (
        f'      (pin {etype} line (at {x} {y:.2f} {angle}) (length 2.54)\n'
        f'        (name "{name}" (effects (font (size 1.27 1.27))))\n'
        f'        (number "{number}" (effects (font (size 1.27 1.27))))\n'
        f'      )'
    )


def pin_rows(pins, ep_number, ep_y, ep_len):
    left = [p for p in pins if p[3] == "L"]
    right = [p for p in pins if p[3] == "R"]
    rows = [pin_sexpr(*p, i) for i, p in enumerate(left)]
    rows += [pin_sexpr(*p, i) for i, p in enumerate(right)]
    rows.append(
        f'      (pin power_in line (at 0 {ep_y} 90) (length {ep_len})\n'
        f'        (name "EP" (effects (font (size 1.27 1.27))))\n'
        f'        (number "{ep_number}" (effects (font (size 1.27 1.27))))\n'
        f'      )'
    )
    return "\n".join(rows)


def make_symbol(name, pins, half_w, top, bottom, ep_number, ep_y, ep_len,
                ref_at, val_at, footprint, datasheet, description):
    rows = pin_rows(pins, ep_number, ep_y, ep_len)
    return f'''  (symbol "{name}"
    (pin_names (offset 1.016))
    (exclude_from_sim no)
    (in_bom yes)
    (on_board yes)
    (property "Reference" "U" (at {ref_at[0]} {ref_at[1]} 0)
      (effects (font (size 1.27 1.27)) (justify left))
    )
    (property "Value" "{name}" (at {val_at[0]} {val_at[1]} 0)
      (effects (font (size 1.27 1.27)) (justify left))
    )
    (property "Footprint" "{footprint}" (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Datasheet" "{datasheet}" (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Description" "{description}" (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (symbol "{name}_0_1"
      (rectangle (start {-half_w} {top}) (end {half_w} {bottom})
        (stroke (width 0.254) (type default))
        (fill (type background))
      )
    )
    (symbol "{name}_1_1"
{rows}
    )
  )
'''


def build():
    tlv = make_symbol(
        "TLV320AIC3104", TLV_PINS, 15.24, 33.02, -33.02, "33", -35.56, 2.54,
        (-17.78, 34.29), (-17.78, -36.83),
        "Package_DFN_QFN:VQFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm",
        "https://www.ti.com/lit/ds/symlink/tlv320aic3104.pdf",
        "Stereo audio codec, I2S + I2C, 3.3V IO, 1.8V core",
    )
    ap = make_symbol(
        "AP64350", AP_PINS, 7.62, 12.7, -17.78, "9", -20.32, 2.54,
        (-10.16, 15.24), (-10.16, -21.59),
        "duck:SO-8EP_AP64350",
        "https://www.diodes.com/assets/Datasheets/AP64350.pdf",
        "3.5A synchronous buck 3.8-40V in, SO-8EP, EP(pin9) must connect to GND",
    )
    out = Path("hardware/custom_hat/rev_a/duck.kicad_sym")
    out.write_text(
        '(kicad_symbol_lib (version 20231120) (generator "duck_hw")\n' + tlv + ap + ")\n",
        encoding="utf-8", newline="\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    build()
