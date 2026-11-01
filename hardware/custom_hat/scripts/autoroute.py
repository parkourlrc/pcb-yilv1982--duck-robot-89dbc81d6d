"""Route an explicit workspace into a new candidate; never overwrite its source."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

import pcbnew

import pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--passes", type=int, default=20)
    arguments = parser.parse_args()
    if arguments.passes < 1:
        raise ValueError("passes must be positive")
    source = pipeline.managed(arguments.project)
    baseline_dir, baseline = pipeline.check(source)
    geometry_errors = baseline["drc"]["violations"]["severities"].get("error", 0)
    if geometry_errors or baseline["drc"]["schematic_parity"]["count"] or baseline["erc"]["count"] or baseline["netlist_check"]["mismatches"] or baseline["netlist_check"]["contract_differences"]:
        print(f"Routing blocked by existing design/consistency errors: {baseline_dir}")
        return 2
    project = pipeline.prepare(source)
    route_dir = project.parent / "route"
    route_dir.mkdir()
    commands = []
    record = {"status": "running", "source": str(source), "production_ready": False, "commands": commands}
    try:
        tool_root = Path(os.environ["LOCALAPPDATA"]) / "duck-robot-tools"
        router = Path(os.environ.get("FREEROUTING_JAR", str(tool_root / "freerouting/freerouting-2.5.0.jar")))
        java = Path(os.environ.get("JAVA_EXE", str(tool_root / "jre25/jdk-25.0.5+8-jre/bin/java.exe")))
        for tool in (router, java):
            if not tool.is_file():
                raise FileNotFoundError(tool)
        board_path = project / (pipeline.STEM + ".kicad_pcb")
        before = pipeline.fingerprints(source)
        board = pcbnew.LoadBoard(str(board_path))
        dsn = route_dir / (pipeline.STEM + ".dsn")
        session = route_dir / (pipeline.STEM + ".ses")
        if not pcbnew.ExportSpecctraDSN(board, str(dsn)) or not dsn.is_file() or not dsn.stat().st_size:
            raise RuntimeError("DSN export failed")
        record["dsn_sha256"] = pipeline.digest(dsn)
        pipeline.run_command(
            [java, "-jar", router, "-de", dsn, "-do", session, "-mp", arguments.passes],
            route_dir, "freerouting", commands, session,
        )
        if pipeline.digest(dsn) != record["dsn_sha256"] or pipeline.fingerprints(source) != before:
            raise RuntimeError("Routing inputs changed")
        record["ses_sha256"] = pipeline.digest(session)
        if not pcbnew.ImportSpecctraSES(board, str(session)):
            raise RuntimeError("SES import failed")
        pcbnew.SaveBoard(str(board_path), board)
        report_dir, checked = pipeline.check(project)
        record["status"] = checked["status"]
        record["reports"] = str(report_dir)
        record["candidate"] = str(project)
        print(f"Candidate: {project}\nStatus: {checked['status']}")
        return 2 if checked["status"] == "design_blocked" else 0
    except Exception as error:
        record["status"] = "tool_failed"
        record["error"] = str(error)
        raise
    finally:
        pipeline.write_json(route_dir / "result.json", record)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"FAILED: {error}", file=sys.stderr)
        sys.exit(1)
