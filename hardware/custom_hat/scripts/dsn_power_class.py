"""Give the power nets a wider routing class in a Specctra DSN.

KiCad keeps netclasses in the project file and pcbnew's standalone export does
not carry them, so every net arrives at 0.25 mm - too thin for the 5 V rail.
This rebuilds the class section with two classes: kicad_power (800 um) and
kicad_default (250 um).
"""
import re
import sys
from pathlib import Path

POWER_NETS = ["+5V", "+3V3", "VBATT_2S_IN", "SERVO_VBAT", "BUCK_SW", "POWER_GND"]
POWER_WIDTH_UM = 400
DEFAULT_WIDTH_UM = 250


def main():
    dsn = Path(sys.argv[1])
    text = dsn.read_text(encoding="utf-8", errors="replace")

    start = text.index("(class ")
    end = text.index("(wiring", start)
    block = text[start:end]

    m = re.search(r"\(class\s+(\S+)(.*?)\(circuit", block, re.S)
    if not m:
        raise SystemExit("class block not understood")
    class_name, nets_blob = m.group(1), m.group(2)
    nets = re.findall(r"[^\s()]+", nets_blob)

    moved = [n for n in nets if n in POWER_NETS]
    rest = [n for n in nets if n not in POWER_NETS]
    if not moved:
        print("no power nets in the class block; nothing changed")
        return

    def class_block(name, net_list, width_um):
        lines = [f"(class {name}"]
        chunk = " ".join(net_list)
        for i in range(0, len(chunk), 90):
            lines.append("      " + chunk[i:i + 90])
        lines += [
            "      (circuit",
            '        (use_via "Via[0-3]_600:300_um")',
            "      )",
            "      (rule",
            f"        (width {width_um})",
            "        (clearance 200)",
            "      )",
            "    )",
        ]
        return "\n".join(lines)

    new_block = class_block("kicad_power", moved, POWER_WIDTH_UM) + "\n    " + \
        class_block("kicad_default", rest, DEFAULT_WIDTH_UM) + "\n  "
    dsn.write_text(text[:start] + new_block + text[end:], encoding="utf-8")
    print(f"power class written ({POWER_WIDTH_UM} um): {' '.join(moved)}")


if __name__ == "__main__":
    raise SystemExit("Legacy DSN rewrite disabled: hard-coded classes and token truncation are unsafe. Keep project rules and inspect exported DSN before routing.")






