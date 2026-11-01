"""Create isolated KiCad workspaces and reproducible checks without editing the source."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
PRIMARY = BASE / "rev_a"
RUNS = BASE / "runs"
STEM = "custom_hat_rev_a"
EXCLUDED_DIRS = {"production", "route", "simulation", ".history", "__pycache__"}
DESIGN_SUFFIXES = {".kicad_pro", ".kicad_dru", ".kicad_sch", ".kicad_pcb", ".kicad_sym", ".kicad_mod", ".step", ".stp", ".wrl"}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def design_files(project):
    files = []
    for path in project.rglob("*"):
        relative = path.relative_to(project)
        if not path.is_file() or any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.suffix in {".kicad_pcb", ".kicad_pro", ".kicad_dru"} and path.stem != STEM:
            continue
        if path.suffix in DESIGN_SUFFIXES or path.name in {"fp-lib-table", "sym-lib-table", "net-contract.json", "source-manifest.json"}:
            files.append(path)
    return sorted(files)


def fingerprints(project):
    return {path.relative_to(project).as_posix(): digest(path) for path in design_files(project)}


def find_cli():
    override = os.environ.get("KICAD_CLI")
    candidates = [Path(override)] if override else [
        Path(sys.base_prefix) / "kicad-cli.exe",
        Path(shutil.which("kicad-cli") or "__missing_cli__"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError("Set KICAD_CLI to an existing KiCad CLI executable")


def prepare(source):
    source = source.resolve()
    for suffix in (".kicad_pcb", ".kicad_pro", ".kicad_sch"):
        if not (source / (STEM + suffix)).is_file():
            raise FileNotFoundError(source / (STEM + suffix))
    before = fingerprints(source)
    run_dir = RUNS / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    work = run_dir / "work"
    work.mkdir(parents=True)
    for name in before:
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)
    if fingerprints(source) != before or fingerprints(work) != before:
        raise RuntimeError("Project changed during copy; discard this workspace")
    write_json(run_dir / "manifest.json", {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source), "source_hashes": before,
        "status": "prepared", "production_ready": False,
    })
    return work


def managed(project):
    project = project.resolve()
    if project == PRIMARY.resolve() or not project.is_relative_to(RUNS.resolve()):
        raise ValueError("Only a workspace under hardware/custom_hat/runs may be modified or checked")
    if project.name != "work" or not (project.parent / "manifest.json").is_file():
        raise ValueError("Missing workspace manifest")
    return project


def run_command(command, directory, name, commands, expected=None):
    if expected is not None and expected.exists():
        raise FileExistsError(f"Refusing to reuse report: {expected}")
    process = subprocess.run(list(map(str, command)), capture_output=True, encoding="utf-8", errors="replace", timeout=1800)
    (directory / (name + ".log")).write_text(process.stdout + process.stderr, encoding="utf-8")
    commands.append({"name": name, "argv": list(map(str, command)), "returncode": process.returncode})
    if process.returncode != 0:
        raise RuntimeError(f"{name} failed: exit {process.returncode}; see {directory}")
    if expected is not None and (not expected.is_file() or expected.stat().st_size == 0):
        raise RuntimeError(f"{name} produced no fresh output")
    return process.stdout.strip()


def counts(items):
    return {"count": len(items), "types": dict(Counter(item["type"] for item in items)),
            "severities": dict(Counter(item["severity"] for item in items))}


def compare_netlist(project, netlist):
    import pcbnew
    document = ET.parse(netlist).getroot()
    components = {item.get("ref"): item for item in document.findall("components/comp") if item.findtext("footprint")}
    expected = {}
    for net in document.findall("nets/net"):
        nodes = net.findall("node")
        for node in nodes:
            if node.get("ref") in components:
                expected[(node.get("ref"), node.get("pin"))] = {
                    "net": net.get("name"),
                    "nc": len(nodes) == 1 and net.get("name", "").startswith("unconnected-")
                    and "no_connect" in node.get("pintype", "").split("+"),
                }
    board = pcbnew.LoadBoard(str(project / (STEM + ".kicad_pcb")))
    actual = {}
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetNumber():
                actual.setdefault((footprint.GetReference(), pad.GetNumber()), set()).add(pad.GetNetname())
    mismatches = []
    nc_empty = []
    for key, value in expected.items():
        names = actual.get(key)
        if value["nc"] and names == {""}:
            nc_empty.append({"reference": key[0], "pin": key[1], "schematic_net": value["net"]})
        elif names != {value["net"]}:
            mismatches.append({"reference": key[0], "pin": key[1], "expected": value, "actual": sorted(names) if names is not None else None})
    for key, names in actual.items():
        if key[0] in components and key not in expected and names != {""}:
            mismatches.append({"reference": key[0], "pin": key[1], "expected": None, "actual": sorted(names)})
    contract_differences = []
    contract = project / "net-contract.json"
    if contract.exists():
        for pin in json.loads(contract.read_text(encoding="utf-8"))["pins"]:
            key = (pin["reference"], str(pin["pin"]))
            expected_pin = expected.get(key)
            if pin["reference"] not in components:
                continue
            if expected_pin is None:
                if pin["net"] is not None:
                    contract_differences.append({"reference": key[0], "pin": key[1], "contract": pin["net"], "netlist": None})
                continue
            expected_name = None if expected_pin["nc"] else expected_pin["net"]
            if pin["net"] != expected_name:
                contract_differences.append({"reference": key[0], "pin": key[1], "contract": pin["net"], "netlist": expected_name})
    tracks = board.GetTracks()
    return {
        "mismatches": mismatches, "nc_empty": nc_empty, "contract_differences": contract_differences,
        "footprints": len(board.GetFootprints()),
        "segments": sum(item.Type() != pcbnew.PCB_VIA_T for item in tracks),
        "vias": sum(item.Type() == pcbnew.PCB_VIA_T for item in tracks),
        "zones": [{"layer": board.GetLayerName(zone.GetLayer()), "net": zone.GetNetname()} for zone in board.Zones()],
    }


def check(project):
    project = managed(project)
    report_dir = project.parent / "reports" / uuid.uuid4().hex[:12]
    report_dir.mkdir(parents=True)
    commands = []
    before = fingerprints(project)
    result = {"status": "running", "production_ready": False, "source_hashes": before, "commands": commands}
    try:
        cli = find_cli()
        result["kicad_version"] = run_command([cli, "--version"], report_dir, "version", commands)
        for name, args in [
            ("netlist", ["sch", "export", "netlist", "--format", "kicadxml", "--output", report_dir / "netlist.xml", project / (STEM + ".kicad_sch")]),
            ("erc", ["sch", "erc", "--format", "json", "--severity-all", "--output", report_dir / "erc.json", project / (STEM + ".kicad_sch")]),
            ("drc", ["pcb", "drc", "--format", "json", "--severity-all", "--refill-zones", "--schematic-parity", "--output", report_dir / "drc.json", project / (STEM + ".kicad_pcb")]),
        ]:
            expected_output = report_dir / (name + (".xml" if name == "netlist" else ".json"))
            run_command([cli, *args], report_dir, name, commands, expected_output)
        drc = json.loads((report_dir / "drc.json").read_text(encoding="utf-8"))
        erc = json.loads((report_dir / "erc.json").read_text(encoding="utf-8"))
        result["drc"] = {name: counts(drc[name]) for name in ("violations", "unconnected_items", "schematic_parity")}
        result["erc"] = counts([violation for sheet in erc["sheets"] for violation in sheet["violations"]])
        result["netlist_check"] = compare_netlist(project, report_dir / "netlist.xml")
        manifest = json.loads((project.parent / "manifest.json").read_text(encoding="utf-8"))
        result["workspace_unchanged"] = before == fingerprints(project)
        result["source_unchanged"] = manifest["source_hashes"] == fingerprints(Path(manifest["source"]))
        if not result["workspace_unchanged"] or not result["source_unchanged"]:
            raise RuntimeError("Design changed while checking; report cannot be accepted")
        blocked = any(result["drc"][name]["count"] for name in result["drc"])
        blocked = blocked or result["erc"]["count"] or result["netlist_check"]["mismatches"] or result["netlist_check"]["contract_differences"]
        result["status"] = "design_blocked" if blocked else "checks_clean_not_manufacturing_release"
    except Exception as error:
        result["status"] = "tool_failed"
        result["error"] = str(error)
        raise
    finally:
        write_json(report_dir / "summary.json", result)
    return report_dir, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--source", type=Path, default=PRIMARY)
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--project", type=Path, required=True)
    arguments = parser.parse_args()
    project = prepare(arguments.source) if arguments.action == "prepare" else managed(arguments.project)
    print(f"Workspace: {project}", flush=True)
    reports, result = check(project)
    print(f"Status: {result['status']}\nReports: {reports}", flush=True)
    return 2 if result["status"] == "design_blocked" else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"FAILED: {error}", file=sys.stderr)
        sys.exit(1)
