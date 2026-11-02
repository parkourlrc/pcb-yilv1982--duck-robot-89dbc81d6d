"""Exercise route planning and fail-safe control handling without an ALSA device."""
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid

from collect_audio_routing_sources import EVIDENCE, ROOT


TOOL = ROOT / "hardware/custom_hat/software/codec/hat_audio.py"
loader = importlib.util.spec_from_file_location("hat_audio", TOOL)
audio = importlib.util.module_from_spec(loader)
loader.loader.exec_module(audio)


class Fixture:
    label = "simulated ALSA text/control backend, no device access"

    def __init__(self, catalog, card="DuckHAT", fail_at=None, corrupt_at=None, always_fail=False, interrupt_at=None):
        self.card, self.fail_at, self.corrupt_at, self.always_fail = card, fail_at, corrupt_at, always_fail
        self.interrupt_at = interrupt_at
        self.controls = copy.deepcopy(catalog["controls"])
        self.values = {name: [0] * entry["count"] for name, entry in self.controls.items()}
        for name in audio.MUTE_CONTROLS:
            self.values[name] = [1, 1]
        self.writes = []

    def info(self):
        return f"Card hw:CARD=DuckHAT '{self.card}'/'Fixture card'\n"

    def block(self, name, values=None):
        entry = self.controls[name]
        values = self.values[name] if values is None else values
        lines = [f"numid=1,iface=MIXER,name='{name}'", f"  ; type={entry['type']},access=rw------,values={entry['count']}"]
        if entry["type"] == "INTEGER":
            lines[-1] += f",min={entry['minimum']},max={entry['maximum']},step=0"
        elif entry["type"] == "ENUMERATED":
            lines[-1] += f",items={len(entry['items'])}"
            lines += [f"  ; Item #{index} '{item}'" for index, item in enumerate(entry["items"])]
        rendered = ["on" if value else "off" for value in values] if entry["type"] == "BOOLEAN" else list(map(str, values))
        lines.append("  : values=" + ",".join(rendered))
        return "\n".join(lines) + "\n"

    def contents(self):
        extra = "numid=999,iface=MIXER,name='Unrelated write-only bytes'\n  ; type=BYTES,access=-w------,values=16\n"
        return "".join(self.block(name) for name in self.controls) + extra

    def set(self, name, values):
        self.writes.append((name, list(values)))
        if len(self.writes) == self.interrupt_at:
            raise KeyboardInterrupt()
        if self.always_fail or len(self.writes) == self.fail_at:
            raise RuntimeError("Simulated control write failure")
        self.values[name] = list(values)
        if len(self.writes) == self.corrupt_at:
            corrupted = list(values)
            corrupted[0] = 0 if corrupted[0] else 1
            return self.block(name, corrupted)
        return self.block(name)


def main():
    catalog = json.loads(audio.CATALOG_PATH.read_text(encoding="utf-8"))
    plan = audio.make_plan(catalog, "both", True)
    run_dir = EVIDENCE / "fixtures" / (datetime.now(timezone.utc).strftime("%H%M%S") + "-" + uuid.uuid4().hex[:8])
    run_dir.mkdir(parents=True)
    results = []
    successful = Fixture(catalog)
    report = audio.apply_plan(successful, plan, catalog, run_dir / "both-mic.json")
    first_mute = successful.writes[:4] == [(name, [0, 0]) for name in audio.MUTE_CONTROLS]
    final_enables = successful.writes[-4:] == [("Line Playback Switch", [1, 0]), ("HP Playback Switch", [1, 1]),
                                             ("HPCOM Playback Switch", [0, 0]), ("PGA Capture Switch", [1, 0])]
    stereo_and_sum = successful.values["Line DAC Playback Volume"] == [105, 0] and successful.values["Left Line Mixer DACR1 Playback Volume"] == [105]
    stereo_and_sum = stereo_and_sum and successful.values["HP DAC Playback Volume"] == [118, 118]
    no_bypass = all(not any(values) for name, values in successful.values.items() if "Bypass Switch" in name)
    results.append({"case": "both-speaker-aux-and-mic", "accepted": first_mute and final_enables and stereo_and_sum and no_bypass and report["status"] == "controls_applied_and_read_back"})
    preflight_cases = {}
    preflight_cases["wrong-card"] = Fixture(catalog, card="USB")
    missing = Fixture(catalog)
    del missing.controls["Left DAC Mux"]
    preflight_cases["missing-control"] = missing
    drift = Fixture(catalog)
    drift.controls["PCM Playback Volume"]["maximum"] = 120
    preflight_cases["changed-range"] = drift
    enum = Fixture(catalog)
    enum.controls["Left Line1L Mux"]["items"].reverse()
    preflight_cases["changed-enum-order"] = enum
    for name, backend in preflight_cases.items():
        refused = False
        target = run_dir / (name + ".json")
        try:
            audio.apply_plan(backend, plan, catalog, target)
        except ValueError:
            refused = True
        results.append({"case": name, "accepted": refused and not backend.writes and not target.exists(), "write_count": len(backend.writes)})
    for name, backend in (("mid-write-failure", Fixture(catalog, fail_at=9)),
                          ("readback-mismatch", Fixture(catalog, corrupt_at=5)),
                          ("interrupted", Fixture(catalog, interrupt_at=8)),
                          ("mute-failure-visible", Fixture(catalog, always_fail=True))):
        target = run_dir / (name + ".json")
        refused = False
        try:
            audio.apply_plan(backend, plan, catalog, target)
        except RuntimeError:
            refused = True
        report = json.loads(target.read_text(encoding="utf-8"))
        should_mute = name != "mute-failure-visible"
        accepted = refused and report["status"] == "failed" and report["mute_controls_read_back_zero"] == should_mute
        accepted = accepted and len(report["failover_mute"]) == 4 and not any(record["phase"] == "enable" for record in report["writes"])
        accepted = accepted and report["interrupted"] == (name == "interrupted")
        results.append({"case": name, "accepted": accepted, "mute_readbacks_zero": report["mute_controls_read_back_zero"]})
    occupied = run_dir / "existing-report.json"
    occupied.write_text("preserved previous report", encoding="utf-8")
    backend = Fixture(catalog)
    refused = False
    try:
        audio.apply_plan(backend, plan, catalog, occupied)
    except FileExistsError:
        refused = True
    results.append({"case": "existing-report-preserved", "accepted": refused and not backend.writes and occupied.read_text(encoding="utf-8") == "preserved previous report"})
    profile_checks = []
    for output in ("none", "speaker", "aux", "both"):
        for microphone in (False, True):
            candidate = audio.make_plan(catalog, output, microphone)
            settings = {row["control"]: row["values"] for row in candidate["operations"]}
            profile_checks.append({"output": output, "mic": microphone, "control_count": len(settings),
                "accepted": settings["Line Playback Switch"] == [int(output in {"speaker", "both"}), 0]
                and settings["HP Playback Switch"] == [int(output in {"aux", "both"})] * 2
                and settings["PGA Capture Switch"] == [int(microphone), 0]})
    result = {"source_sha256": hashlib.sha256(TOOL.read_bytes()).hexdigest(), "catalog_sha256": hashlib.sha256(audio.CATALOG_PATH.read_bytes()).hexdigest(),
              "scenarios": results, "profiles": profile_checks, "fixture_reports": str(run_dir),
              "accepted_offline": all(row["accepted"] for row in results + profile_checks),
              "real_alsa_accessed": False, "hardware_tested": False,
              "limits": "Simulated amixer text and state only. No actual driver control enumeration, ALSA PCM, I2S or acoustic test."}
    (EVIDENCE / "routing-tool-audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    if not result["accepted_offline"]:
        raise RuntimeError("Audio routing verification failed")


if __name__ == "__main__":
    main()
