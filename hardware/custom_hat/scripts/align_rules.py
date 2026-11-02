"""Historical rule-rewriting experiment; its command-line entry is disabled."""
import json
from pathlib import Path

PRO = Path("hardware/custom_hat/rev_a/custom_hat_rev_a.kicad_pro")
DRU = Path("hardware/custom_hat/rev_a/custom_hat_rev_a.kicad_dru")

POWER_NETS = ["+5V", "+3V3", "VBATT_2S_IN", "SERVO_VBAT", "BUCK_SW", "POWER_GND"]


def legacy_align_rules_unchecked():
    d = json.loads(PRO.read_text(encoding="utf-8"))

    rules = d["board"]["design_settings"]["rules"]
    rules["min_track_width"] = 0.1  # FreeRouting emits 0.1 mm on dense escapes
    rules["min_clearance"] = 0.0
    rules["min_copper_edge_clearance"] = 0.2

    ns = d["net_settings"]
    for cls in ns["classes"]:
        if cls["name"] == "Default":
            cls["clearance"] = 0.15
            cls["track_width"] = 0.25
    ns["classes"] = [c for c in ns["classes"] if c["name"] != "Power"]
    ns["classes"].append({
        "name": "Power",
        "clearance": 0.2,
        "track_width": 0.6,
        "via_diameter": 0.6,
        "via_drill": 0.3,
        "priority": -1,
        "pcb_color": "rgba(0, 0, 0, 0.000)",
        "schematic_color": "rgba(0, 0, 0, 0.000)",
        "tuning_profile": "",
    })
    ns["netclass_patterns"] = [{"netclass": "Power", "pattern": n} for n in POWER_NETS]

    PRO.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")

    DRU.write_text(
        "(version 1)\n"
        "(rule \"BMI088 fine pitch\"\n"
        "  (condition \"A.insideCourtyard('U501')\")\n"
        "  (constraint clearance (min 0.12mm))\n"
        "  (constraint annular_width (min 0.09mm))\n"
        "  (constraint hole_clearance (min 0.15mm))\n"
        ")\n",
        encoding="utf-8",
    )
    print("project rules: Default clearance 0.15, track min 0.15, Power class 0.6")
    print("custom rule written for U501")


def main():
    raise SystemExit("Deprecated: do not rewrite manufacturing rules to fit router output. Use an isolated pipeline workspace and an explicitly reviewed process-rule change.")


if __name__ == "__main__":
    main()
