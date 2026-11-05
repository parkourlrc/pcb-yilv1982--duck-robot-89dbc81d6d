import hashlib
import json
import re
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path


base = Path(__file__).resolve().parent
checkout = Path(sys.argv[1]).resolve()


def git(*arguments):
    return subprocess.check_output(["git", "-C", str(checkout), *arguments]).decode("utf-8").strip()


paths = [path for path in git("ls-files", "-z").split("\x00") if path]
inventory = []
lfs_pointers = []
for relative_path in paths:
    source = checkout / relative_path
    content = source.read_bytes()
    inventory.append({"path": relative_path, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    if content.startswith(b"version https://git-lfs.github.com/spec/v1"):
        lfs_pointers.append(relative_path)
(base / "checkout-file-manifest.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")

branch_refs = git("for-each-ref", "--format=%(refname)", "refs/remotes/origin").splitlines()
branches = [branch.removeprefix("refs/remotes/") for branch in branch_refs if not branch.endswith("/HEAD")]
driver_path = "microduck-hd1910/firmware/tof/src/imu.rs"
hardware_profiles = {}
for branch in branches:
    entries = git("ls-tree", "-r", branch, "hardware").splitlines()
    hardware_profiles[branch] = [entry for entry in entries if entry.endswith(".epro2") or "BOM.json" in entry]

archives = []
for relative_path in paths:
    source = checkout / relative_path
    members = None
    if relative_path.endswith(".zip"):
        with zipfile.ZipFile(source) as archive:
            members = archive.namelist()
    elif relative_path.endswith((".tar.gz", ".tgz")):
        with tarfile.open(source) as archive:
            members = archive.getnames()
    if members is not None:
        archives.append({"path": relative_path, "member_count": len(members), "electrical_cad_members": [name for name in members if name.lower().endswith((".epro2", ".kicad_pcb", ".kicad_sch", ".pcbdoc", ".schdoc"))], "head_imu_source_members": [name for name in members if name.endswith(("tof/src/imu.rs", "deploy/robotd.toml"))]})

evidence = {}
for relative_path in (
    driver_path,
    "microduck-hd1910/firmware/tof/Cargo.toml",
    "microduck-hd1910/firmware/tof/src/main.rs",
    "microduck-hd1910/firmware/robotd-params/src/lib.rs",
    "microduck-hd1910/firmware/deploy/robotd.toml",
    "microduck-hd1910/firmware/duck-control/src/imu.rs",
    "microduck-hd1910/firmware/docs/project/tof-on-demand.md",
    "microduck-hd1910/firmware/deploy/audio/i2c3-pihat.dts",
    "hardware/README.md",
    "microduck-hd1910/README.md",
):
    lines = (checkout / relative_path).read_text(encoding="utf-8").splitlines()
    evidence[relative_path] = [{"line": number, "text": line} for number, line in enumerate(lines, 1) if re.search(r"BMI088|Bmi088::new|0x19|0x68|head_imu|HeadImuParams|LSM6DSV16X|bmi088-rs|官方.*0.15.1|Nothing subscribes", line)]

summary = {
    "observed_at": datetime.now().astimezone().isoformat(),
    "repository": "https://github.com/kissqy/Microduck-kissqy",
    "checkout": checkout.as_posix(),
    "head": git("rev-parse", "HEAD"),
    "head_time": git("show", "-s", "--format=%cI", "HEAD"),
    "is_shallow": git("rev-parse", "--is-shallow-repository") == "true",
    "reachable_commit_count": int(git("rev-list", "--all", "--count")),
    "remote_branches": branches,
    "tracked_files": len(paths),
    "tracked_bytes": sum(item["bytes"] for item in inventory),
    "lfs_pointer_files": lfs_pointers,
    "submodule_entries": [line for line in git("ls-tree", "-r", "HEAD").splitlines() if line.startswith("160000")],
    "git_status": git("status", "--short"),
    "fsck_full_exit_code_observed": 0,
    "driver_history": git("log", "--all", "--follow", "--format=%H %aI %s", "--", driver_path).splitlines(),
    "driver_blob_per_branch": {branch: git("rev-parse", branch + ":" + driver_path) for branch in branches},
    "hardware_profiles": hardware_profiles,
    "hardware_file_history": git("log", "--all", "--format=%H %aI %s", "--", "hardware/ProPrj_HAT_REVA_SCH_2026-10-15.epro2").splitlines(),
    "all_history_cad_paths": sorted(set(git("log", "--all", "--format=", "--name-only", "--", "*.epro2", "*.kicad_pcb", "*.kicad_sch", "*.SchDoc", "*.PcbDoc").splitlines()) - {""}),
    "archive_inventory": archives,
    "separate_release_asset": {"name": "microduck-zero3w-0.15.1-R1.img.xz", "bytes": 767412924, "downloaded": False, "reason": "separate bootable system-image asset, not part of Git repository or PCB-source evidence; not needed for this hardware-source question"},
}
(base / "repository-audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
(base / "source-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({key: value for key, value in summary.items() if key not in {"hardware_profiles", "archive_inventory"}}, ensure_ascii=False, indent=2))
print(json.dumps({"archives_scanned": len(archives), "archives_with_electrical_cad": [archive for archive in archives if archive["electrical_cad_members"]]}, ensure_ascii=False))
