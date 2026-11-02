"""Plan, inspect or apply AIC3104 routes on the explicitly named DuckHAT ALSA card."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


CATALOG_PATH = Path(__file__).with_name("control-catalog.json")
MUTE_CONTROLS = ("Line Playback Switch", "HP Playback Switch", "HPCOM Playback Switch", "PGA Capture Switch")


class RoutingInterrupted(RuntimeError):
    pass


def gain(value, minimum, maximum):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or not Decimal(str(minimum)) <= amount <= Decimal(str(maximum)) or amount * 2 != (amount * 2).to_integral_value():
            raise ValueError()
    except (InvalidOperation, ValueError):
        raise ValueError(f"Gain must be {minimum}..{maximum} dB in 0.5 dB steps") from None
    return amount


def validate_values(name, values, specification):
    if len(values) != specification["count"] or any(type(value) is not int for value in values):
        raise ValueError("Invalid value count/type: " + name)
    maximum = len(specification["items"]) - 1 if specification["type"] == "ENUMERATED" else specification["maximum"]
    if any(not 0 <= value <= maximum for value in values):
        raise ValueError("Out-of-range value: " + name)


def make_plan(catalog, output="none", microphone=False, pcm_db="-40", capture_db="0"):
    if output not in {"none", "speaker", "aux", "both"}:
        raise ValueError("Unknown output profile")
    playback_gain, capture_gain = gain(pcm_db, -63.5, 0), gain(capture_db, 0, 59.5)
    speaker, auxiliary = output in {"speaker", "both"}, output in {"aux", "both"}
    controls = catalog["controls"]
    setup = {}
    def setting(name, values):
        specification = controls[name]
        if specification["type"] == "ENUMERATED":
            values = [specification["items"].index(value) for value in values]
        values = [int(value) for value in values]
        validate_values(name, values, specification)
        setup[name] = values
    for name, specification in controls.items():
        if name not in MUTE_CONTROLS and specification["type"] != "ENUMERATED":
            if name.endswith(("Bypass Volume", "Bypass Switch", "Playback Volume")) or " Mixer " in name and name.endswith(" Switch"):
                setting(name, [0] * specification["count"])
    setting("PCM Playback Volume", [int(127 + playback_gain * 2)] * 2)
    setting("AGC Switch", [0, 0])
    setting("De-emphasis Switch", [0, 0])
    setting("PGA Capture Volume", [int(capture_gain * 2) if microphone else 0, 0])
    setting("ADC HPF Cut-off", ["Disabled", "Disabled"])
    setting("Output Driver Power-On time", ["100ms"])
    setting("Output Driver Ramp-up step", ["4ms"])
    setting("Left DAC Mux", ["DAC_L1"])
    setting("Right DAC Mux", ["DAC_R1"])
    for side in ("Left", "Right"):
        for line in ("Line1L", "Line1R"):
            setting(side + " " + line + " Mux", ["differential" if side == "Left" and line == "Line1L" and microphone else "single-ended"])
    setting("Line DAC Playback Volume", [105 if speaker else 0, 0])
    setting("Left Line Mixer DACR1 Playback Volume", [105 if speaker else 0])
    setting("Left Line Mixer DACL1 Switch", [speaker])
    setting("Left Line Mixer DACR1 Switch", [speaker])
    setting("HP DAC Playback Volume", [118 if auxiliary else 0] * 2)
    setting("Left HP Mixer DACL1 Switch", [auxiliary])
    setting("Right HP Mixer DACR1 Switch", [auxiliary])
    setting("Left PGA Mixer Line1L Switch", [microphone])
    enables = {"Line Playback Switch": [int(speaker), 0], "HP Playback Switch": [int(auxiliary)] * 2,
               "HPCOM Playback Switch": [0, 0], "PGA Capture Switch": [int(microphone), 0]}
    operations = [{"phase": "mute", "control": name, "values": [0, 0]} for name in MUTE_CONTROLS]
    operations += [{"phase": "configure", "control": name, "values": values} for name, values in setup.items()]
    operations += [{"phase": "enable", "control": name, "values": values} for name, values in enables.items()]
    for operation in operations:
        validate_values(operation["control"], operation["values"], controls[operation["control"]])
    return {"card_id": "DuckHAT", "codec": catalog["codec"], "codec_source_sha256": catalog["codec_source_sha256"],
            "output": output, "microphone": microphone, "pcm_gain_db": str(playback_gain), "capture_gain_db": str(capture_gain),
            "speaker_mix": "L+R, each output-stage route at nominal -6.5dB; J504 stays stereo", "operations": operations,
            "plan_only": True, "note": "Configuration plan only; no sample-rate, waveform, speaker load or microphone performance claim"}


def parse_controls(text, names=None):
    result = {}
    blocks = re.split(r"(?=^numid=)", text, flags=re.M)
    for block in blocks:
        if not block.startswith("numid="):
            continue
        header = block.splitlines()[0]
        fields = {match[0]: match[1] if match[1] else match[2] for match in re.findall(r"(\w+)=(?:'([^']*)'|([^,]*))", header)}
        if fields.get("iface") != "MIXER" or any(int(fields.get(key, "0")) for key in ("index", "device", "subdevice")):
            continue
        name = fields["name"]
        if names is not None and name not in names:
            continue
        metadata = re.search(r"^\s*;\s*type=([^,]+),access=([^,]+),values=(\d+)([^\n]*)", block, re.M)
        values = re.search(r"^\s*:\s*values=([^\n]*)", block, re.M)
        if not metadata or not values:
            raise ValueError("Unreadable control metadata/value: " + name)
        entry = {"type": metadata[1], "access": metadata[2], "count": int(metadata[3])}
        if entry["type"] == "INTEGER":
            bounds = dict(re.findall(r"(min|max)=(-?\d+)", metadata[4]))
            entry.update(minimum=int(bounds["min"]), maximum=int(bounds["max"]))
        elif entry["type"] == "BOOLEAN":
            entry.update(minimum=0, maximum=1)
        elif entry["type"] == "ENUMERATED":
            items = {int(index): name for index, name in re.findall(r"^\s*;\s*Item #(\d+) '([^']*)'", block, re.M)}
            if sorted(items) != list(range(len(items))):
                raise ValueError("Incomplete enum items: " + name)
            entry["items"] = [items[index] for index in range(len(items))]
        else:
            continue
        tokens = [value.strip() for value in values[1].split(",")]
        if entry["type"] == "BOOLEAN":
            boolean_values = {"on": 1, "off": 0, "1": 1, "0": 0}
            if any(value not in boolean_values for value in tokens):
                raise ValueError("Invalid boolean value: " + name)
            entry["values"] = [boolean_values[value] for value in tokens]
        else:
            entry["values"] = [int(value) for value in tokens]
        validate_values(name, entry["values"], entry)
        if name in result:
            raise ValueError("Ambiguous control identity: " + name)
        result[name] = entry
    return result


class Amixer:
    label = "amixer control interface"

    def __init__(self):
        self.executable = shutil.which("amixer")
        if not self.executable:
            raise RuntimeError("amixer is required for inspect/apply")

    def command(self, *arguments):
        result = subprocess.run([self.executable, "-D", "hw:CARD=DuckHAT", *arguments], capture_output=True, encoding="utf-8", errors="replace", timeout=15)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "amixer failed")
        return result.stdout

    def info(self):
        return self.command("info")

    def contents(self):
        return self.command("contents")

    def set(self, name, values):
        return self.command("cset", "iface=MIXER,name='" + name + "'", ",".join(map(str, values)))


def preflight(backend, plan, catalog):
    info = backend.info()
    identity = re.search(r"^Card\s+.+?\s+'([^']+)'/'([^']*)'", info, re.M)
    if not identity or identity[1] != "DuckHAT":
        raise ValueError("The selected ALSA card does not identify as DuckHAT")
    required = sorted({operation["control"] for operation in plan["operations"]})
    actual = parse_controls(backend.contents(), set(required))
    for name in required:
        expected = catalog["controls"][name]
        if name not in actual:
            raise ValueError("Missing expected control: " + name)
        observed = actual[name]
        keys = ("type", "count", "items") if expected["type"] == "ENUMERATED" else ("type", "count", "minimum", "maximum")
        if any(observed.get(key) != expected[key] for key in keys) or "r" not in observed["access"] or "w" not in observed["access"]:
            raise ValueError("Control schema differs from the reviewed driver: " + name)
    return {"card_info": info, "controls": {name: actual[name] for name in required}, "required_control_count": len(required)}


def apply_plan(backend, plan, catalog, report_path):
    before = preflight(backend, plan, catalog)
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "backend": backend.label, "plan": plan, "before": before, "status": "prepared", "writes": [],
              "failover_mute": [], "sound_tested": False, "physical_amplifier_power_controlled": False}
    with report_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    def save():
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    def set_verified(name, values):
        reply = parse_controls(backend.set(name, values), {name})
        if name not in reply or reply[name]["values"] != values:
            raise RuntimeError("Control readback differs after write: " + name)
        return {"control": name, "values": values, "readback": reply[name]["values"]}
    try:
        report["status"] = "applying"
        save()
        for operation in plan["operations"]:
            record = {"phase": operation["phase"], "control": operation["control"], "requested": operation["values"], "status": "attempting"}
            report["writes"].append(record)
            save()
            record.update(set_verified(operation["control"], operation["values"]))
            record["status"] = "read_back"
            save()
        expected_values = {operation["control"]: operation["values"] for operation in plan["operations"]}
        final = parse_controls(backend.contents(), set(expected_values))
        if any(name not in final or final[name]["values"] != values for name, values in expected_values.items()):
            raise RuntimeError("Final control snapshot differs; another client or driver may have changed it")
        report["status"] = "controls_applied_and_read_back"
        report["after"] = {name: final[name] for name in expected_values}
        save()
        return report
    except (Exception, KeyboardInterrupt) as error:
        report["status"] = "failed"
        report["interrupted"] = isinstance(error, KeyboardInterrupt)
        report["error"] = str(error) or type(error).__name__
        for name in MUTE_CONTROLS:
            try:
                report["failover_mute"].append({**set_verified(name, [0, 0]), "success": True})
            except Exception as mute_error:
                report["failover_mute"].append({"control": name, "success": False, "error": str(mute_error)})
        report["mute_controls_read_back_zero"] = all(row["success"] for row in report["failover_mute"])
        try:
            save()
        except OSError as report_error:
            print("Could not save final failure report: " + str(report_error), file=sys.stderr)
        failure = RoutingInterrupted if report["interrupted"] else RuntimeError
        raise failure("Audio configuration failed; inspect the report and mute results") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("plan", "inspect", "apply"), default="plan")
    parser.add_argument("--output", choices=("none", "speaker", "aux", "both"), default="none")
    parser.add_argument("--mic", action="store_true")
    parser.add_argument("--pcm-db", default="-40")
    parser.add_argument("--capture-db", default="0")
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        plan = make_plan(catalog, arguments.output, arguments.mic, arguments.pcm_db, arguments.capture_db)
        if arguments.action == "plan":
            result = plan
        elif arguments.action == "inspect":
            result = {"inspection": preflight(Amixer(), plan, catalog), "controls_changed": False}
        else:
            if arguments.report is None:
                parser.error("apply requires --report with a new report filename")
            result = apply_plan(Amixer(), plan, catalog, arguments.report)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (RoutingInterrupted, KeyboardInterrupt) as error:
        print(str(error) or "Audio operation interrupted", file=sys.stderr)
        raise SystemExit(130) from error
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
