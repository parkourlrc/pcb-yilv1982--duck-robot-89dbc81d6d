import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    output = Path(__file__).resolve().parent
    root = output.parents[3]
    scripts = root / "hardware/custom_hat/scripts"
    spec = importlib.util.spec_from_file_location("hat_pipeline", scripts / "pipeline.py")
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    before = pipeline.fingerprints(pipeline.PRIMARY)
    result = {"checks": {}}
    work = pipeline.prepare(pipeline.PRIMARY)
    reports, checked = pipeline.check(work)
    assert checked["status"] == "design_blocked"
    assert [checked["drc"][key]["count"] for key in ("violations", "unconnected_items", "schematic_parity")] == [29, 23, 101]
    assert not checked["netlist_check"]["mismatches"]
    assert not checked["netlist_check"]["contract_differences"]
    assert len(checked["netlist_check"]["nc_empty"]) == 32
    assert checked["source_unchanged"] and checked["workspace_unchanged"]
    result["checks"]["complete_project_baseline"] = True
    for name in ("summary.json", "netlist.xml", "erc.json", "drc.json"):
        shutil.copy2(reports / name, output / ("workflow-" + name))
    cli = os.environ.get("KICAD_CLI")
    try:
        os.environ["KICAD_CLI"] = str(work / "missing-cli.exe")
        try:
            pipeline.check(work)
        except FileNotFoundError:
            failures = [json.loads(path.read_text(encoding="utf-8")) for path in work.parent.glob("reports/*/summary.json")]
            assert any(item["status"] == "tool_failed" for item in failures)
            result["checks"]["missing_cli_fails"] = True
        else:
            raise AssertionError("Missing CLI accepted")
    finally:
        if cli is None:
            os.environ.pop("KICAD_CLI", None)
        else:
            os.environ["KICAD_CLI"] = cli
    for name, arguments in [
        ("primary_route_rejected", [str(scripts / "autoroute.py"), "--project", str(pipeline.PRIMARY)]),
        ("legacy_builder_rejected", [str(scripts / "build_pcb_rev_a.py")]),
        ("legacy_dsn_rejected", [str(scripts / "dsn_power_class.py")]),
        ("current_design_route_blocked", [str(scripts / "autoroute.py"), "--project", str(work)]),
    ]:
        process = subprocess.run([sys.executable, *arguments], capture_output=True, encoding="utf-8", errors="replace", timeout=90)
        (output / (name + ".log")).write_text(process.stdout + process.stderr, encoding="utf-8")
        assert process.returncode == (2 if name == "current_design_route_blocked" else 1), name
        result["checks"][name] = True
    with tempfile.TemporaryDirectory(prefix="hat-failure-check-") as temporary:
        folder = Path(temporary)
        stale = folder / "old.ses"
        stale.write_text("old", encoding="utf-8")
        commands = []
        try:
            pipeline.run_command([sys.executable, "-c", "print('unexpected')"], folder, "stale", commands, stale)
        except FileExistsError:
            assert commands == []
            result["checks"]["stale_result_rejected"] = True
        else:
            raise AssertionError("Stale result accepted")
        try:
            pipeline.run_command([sys.executable, "-c", "raise SystemExit(7)"], folder, "failed", commands, folder / "new.ses")
        except RuntimeError:
            assert commands[-1]["returncode"] == 7
            result["checks"]["failed_process_rejected"] = True
        else:
            raise AssertionError("Failed process accepted")
        try:
            pipeline.run_command([sys.executable, "-c", "pass"], folder, "empty", commands, folder / "absent.ses")
        except RuntimeError:
            result["checks"]["missing_output_rejected"] = True
        else:
            raise AssertionError("Missing output accepted")
    result["source_unchanged"] = before == pipeline.fingerprints(pipeline.PRIMARY)
    assert result["source_unchanged"]
    result["workspace"] = str(work)
    result["unverified"] = ["Successful Java routing and SES import", "Manufacturing readiness", "Hardware behavior"]
    pipeline.write_json(output / "workflow-verification.json", result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
