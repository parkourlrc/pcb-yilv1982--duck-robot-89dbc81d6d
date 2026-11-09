from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mjlab_duck import train_locomotion as runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    args = parser.parse_args()
    output = args.directory / "initialization-failure"
    startup = output.with_name(output.name + "-startup")
    if args.directory.exists():
        raise ValueError("verification directory already exists")
    args.directory.mkdir(parents=True)
    observed = {}

    def fail_initialization(*values, **keywords):
        snapshot = json.loads((startup / "runtime-environment.json").read_text())
        observed["snapshot_precedes_initialization"] = snapshot["status"] == "before_runtime_initialization"
        observed["dependency_count"] = len(snapshot["dependencies"])
        observed["source_count"] = len(snapshot["source_sha256"])
        observed["archive_helper_frozen"] = "training/experiment_archive.py" in snapshot["source_sha256"]
        for name, expected in snapshot["source_sha256"].items():
            assert runtime.sha_file(startup / "sources" / name) == expected
        assert snapshot["config"]["reward_config"]
        assert snapshot["workflow"]["config_hash"]
        assert observed["snapshot_precedes_initialization"] and observed["archive_helper_frozen"]
        print("mock initialization failure: zero training updates")
        raise RuntimeError("injected initialization failure")

    command = ["train_locomotion", "--output", str(output), "--config", str(args.config),
               "--workflow-record", str(args.workflow)]
    with patch.object(sys, "argv", command), patch.object(runtime, "build_runtime", side_effect=fail_initialization), \
            patch.object(runtime, "train_loop") as training:
        try:
            runtime.main()
        except RuntimeError as error:
            assert str(error) == "injected initialization failure"
        else:
            raise AssertionError("injected failure did not propagate")
        training.assert_not_called()
    console = (startup / "console.rank0.log").read_text()
    events = [json.loads(line) for line in (startup / "events.jsonl").read_text().splitlines()]
    assert "injected initialization failure" in console and "Traceback" in console
    assert any(event.get("phase") == "failed" for event in events)
    assert (startup / "archive-registration.json").is_file()
    observed.update(status="passed", training_updates=0, training_loop_called=False,
                    traceback_retained=True, failure_event_retained=True, registration_retained=True)
    (args.directory / "verification.json").write_text(json.dumps(observed, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(observed, indent=2))


if __name__ == "__main__":
    main()
