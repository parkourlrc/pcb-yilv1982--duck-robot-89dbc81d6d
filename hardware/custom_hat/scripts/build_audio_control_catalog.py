"""Extract AIC3104 control metadata from the exact codec source used for the modules."""
import hashlib
import json
from pathlib import Path
import re

from collect_audio_routing_sources import EVIDENCE, ROOT


SOURCE = EVIDENCE.parent / "driver-compatibility-20261031/sources/exact-sound__soc__codecs__tlv320aic3x.c"
OUTPUT = ROOT / "hardware/custom_hat/software/codec/control-catalog.json"


def calls(text, expression):
    for match in re.finditer(expression + r"\s*\(", text):
        cursor, level, quoted, escaped = match.end(), 1, False, False
        while level:
            character = text[cursor]
            if quoted:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    quoted = False
            elif character == '"':
                quoted = True
            elif character == "(":
                level += 1
            elif character == ")":
                level -= 1
            cursor += 1
        yield match.group(1), [value.strip() for value in text[match.end():cursor-1].split(",")]


def main():
    if OUTPUT.exists():
        raise FileExistsError("Review the existing control catalog before replacing it")
    raw = SOURCE.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    binary_manifest = json.loads((OUTPUT.parent / "6.1.84-10-rk2410-nocsf/manifest.json").read_text(encoding="utf-8"))
    if source_hash != binary_manifest["source_hashes"]["tlv320aic3x.c"]:
        raise RuntimeError("Codec source no longer matches the built modules")
    text = re.sub(r"/\*.*?\*/", lambda match: "\n" * match[0].count("\n"), raw, flags=re.S)
    def array(name):
        match = re.search(r"\b" + re.escape(name) + r"\s*\[\]\s*=\s*\{(.*?)\};", text, re.S)
        if not match:
            raise RuntimeError("Missing source array: " + name)
        return match[1]
    enums = {}
    for kind, values in calls(text, r"(SOC_ENUM_(?:SINGLE|DOUBLE)_DECL)"):
        enums[values[0]] = {"type": "ENUMERATED", "count": 2 if "DOUBLE" in kind else 1,
                            "items": re.findall(r'"([^\"]+)"', array(values[-1])), "source_enum": values[0]}
    controls = {}
    for kind, values in calls(array("aic3x_snd_controls"), r"(SOC_(?:DOUBLE_R_TLV|DOUBLE_R|DOUBLE|SINGLE_TLV|SINGLE|ENUM))"):
        name = json.loads(values[0])
        if kind == "SOC_ENUM":
            entry = dict(enums[values[1]])
        else:
            double = "DOUBLE" in kind
            maximum = int(values[4 if double else 3], 0)
            entry = {"type": "BOOLEAN" if maximum == 1 and " Volume" not in name else "INTEGER",
                     "count": 2 if double else 1, "minimum": 0, "maximum": maximum}
        controls[name] = {**entry, "source_array": "aic3x_snd_controls", "source_macro": kind}
    for kind, values in calls(array("aic3x_dapm_widgets"), r"(SND_SOC_DAPM_MUX)"):
        name, variable = json.loads(values[0]), values[4].lstrip("&")
        declaration = re.search(r"\b" + variable + r'\s*=\s*SOC_DAPM_ENUM\("Route",\s*(\w+)\)', text)
        if not declaration:
            raise RuntimeError("Mux declaration missing: " + variable)
        controls[name] = {**enums[declaration[1]], "source_array": "aic3x_dapm_widgets", "source_control": variable,
                          "naming_basis": "soc-dapm.c mux names use the widget name"}
    for side in ("Left", "Right"):
        for section in ("Line", "HP", "HPCOM", "PGA"):
            identifier = "aic3104_" + side.lower() + "_pga_mixer_controls" if section == "PGA" else "aic3x_" + side.lower() + "_" + section.lower() + "_mixer_controls"
            entries = list(calls(array(identifier), r"(SOC_DAPM_SINGLE(?:_AIC3X)?)"))
            if section != "PGA":
                if len(entries) != 6 or f"ARRAY_SIZE({identifier}) - 2" not in array("aic3104_extra_dapm_widgets"):
                    raise RuntimeError("Unexpected AIC3104 output mixer registration")
                entries = entries[:-2]
            if len(entries) != 4:
                raise RuntimeError("Unexpected AIC3104 input mixer registration")
            for kind, values in entries:
                short_name = json.loads(values[0])
                name = side + " " + section + " Mixer " + short_name
                controls[name] = {"type": "BOOLEAN", "count": 1, "minimum": 0, "maximum": int(values[3], 0),
                                  "source_array": identifier, "source_macro": kind,
                                  "naming_basis": "soc-dapm.c mixer names join widget and control names"}
    result = {"schema_version": 1, "codec": "TLV320AIC3104", "card_id": "DuckHAT",
              "kernel_source_commit": "e6d12a77c8bc0ea6decbd3e4604ec131d4032c30", "codec_source_sha256": source_hash,
              "controls": controls, "runtime_verified": False,
              "limit": "Expected controls derived from exact source; the real card must match before any write"}
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (EVIDENCE / "control-catalog-audit.json").write_text(json.dumps({"control_count": len(controls), "codec_source_sha256": source_hash,
        "catalog_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(), "driver_binary_source_matches": True,
        "adc_hpf": controls["ADC HPF Cut-off"], "runtime_verified": False}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"controls": len(controls), "adc_hpf": controls["ADC HPF Cut-off"]}))


if __name__ == "__main__":
    main()
