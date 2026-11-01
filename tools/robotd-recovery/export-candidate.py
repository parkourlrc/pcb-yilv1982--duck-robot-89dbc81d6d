"""从隔离副本导出补丁与源码哈希；不构建、不安装。"""
import difflib
import json
from source_inputs import HERE, ARCHIVES, baseline, sha

EXPECTED = {
    "firmware": {
        "docs/design/robotd-design.md", "duck-ipc-proto/src/lib.rs", "robotd/src/control.rs",
        "robotd/src/feetech_commissioning.rs", "robotd/src/feetech_recovery_tests.rs",
        "robotd/src/intents.rs", "robotd/src/main.rs", "robotd/src/raw_stream.rs",
        "robotd/src/recovery.rs", "updater/src/ipc.rs",
    },
    "studio": {"studio/pad.py", "studio/pad_drive.py", "studio/pad_recovery.py", "studio/updates.py", "web/pad.js"},
}


def main():
    manifest = {"date": "2026-11-01", "build": "0791fcd-feetech-qinmo-control.47+duck-recovery.1", "api_version": 43,
                "deployed": False, "robot_motion_tested": False, "components": {}}
    (HERE / "patches").mkdir(exist_ok=True)
    for component in EXPECTED:
        original = baseline(component)
        workspace = HERE / ".work" / component
        # Firmware is a complete export: detect changes outside the approved surface too.
        names = (set(original) | {p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file() and not {".git", "target"}.intersection(p.relative_to(workspace).parts)}) if component == "firmware" else EXPECTED[component]
        records, diffs = [], []
        for path in sorted(names):
            before = original.get(path, b"")
            after = (workspace / path).read_bytes()
            if before == after:
                continue
            if path not in EXPECTED[component]:
                raise ValueError(f"发现范围外变更：{component}/{path}")
            records.append({"path": path, "original_sha256": sha(before) if path in original else None,
                            "candidate_sha256": sha(after), "candidate_bytes": len(after)})
            diffs.append("".join(difflib.unified_diff(before.decode("utf-8").splitlines(keepends=True),
                after.decode("utf-8").splitlines(keepends=True),
                fromfile=f"a/{path}" if path in original else "/dev/null", tofile=f"b/{path}")))
        patch = "".join(diffs).encode("utf-8")
        (HERE / "patches" / f"{component}.patch").write_bytes(patch)
        archive, checksum, prefix = ARCHIVES[component]
        manifest["components"][component] = {"archive": archive, "archive_sha256": checksum,
            "archive_prefix": prefix, "patch_sha256": sha(patch), "files": records}
        if component == "firmware":
            unchanged = ["Cargo.lock", "duck-control/src/feetech.rs", "duck-control/src/imu.rs", "duck-control/src/feetech_imu_observation.rs", "duck-control/src/feetech_observations.rs"]
            manifest["unchanged_control_sources"] = {path: sha(original[path]) for path in unchanged}
        print(f"{component}: {len(records)} files, patch {len(patch)} bytes")
    (HERE / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
