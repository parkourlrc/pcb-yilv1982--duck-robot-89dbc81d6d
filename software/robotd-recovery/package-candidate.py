"""打包本地候选和固定基线回退材料；没有部署或服务操作。"""
import io
import json
import tarfile
from source_inputs import HERE, PREP, baseline, sha


def pack(path, files):
    with tarfile.open(path, "w:gz") as archive:
        for name, content in sorted(files.items()):
            item = tarfile.TarInfo(name)
            item.size, item.mode, item.mtime = len(content), 0o755 if name == "bin/robotd" else 0o644, 0
            archive.addfile(item, io.BytesIO(content))


def main():
    source = json.loads((HERE / "source-manifest.json").read_text(encoding="utf-8"))
    binary = (HERE / "artifacts/robotd").read_bytes()
    if binary[:4] != b"\x7fELF" or int.from_bytes(binary[18:20], "little") != 183:
        raise ValueError("候选不是 AArch64 ELF")
    if b"0791fcd-feetech-qinmo-control.47+duck-recovery.1" not in binary:
        raise ValueError("候选缺少本项目构建标识")
    original_binary = (PREP / "software-runtime/studio/deploy/native/robotd").read_bytes()
    if sha(original_binary) != "725b74cd93660a312970a44879abe5b75e8becf108499a1b8798961e48ca5f00":
        raise ValueError("回退二进制与只读核对基线不同")
    original_studio = baseline("studio")
    candidate, rollback = {"bin/robotd": binary}, {"bin/robotd": original_binary}
    remove_on_rollback = []
    for item in source["components"]["studio"]["files"]:
        path = item["path"]
        content = (HERE / ".work/studio" / path).read_bytes()
        if sha(content) != item["candidate_sha256"]:
            raise ValueError(f"候选源码哈希变化，先重新导出并验证：{path}")
        candidate["studio/" + path] = content
        if path in original_studio:
            rollback["studio/" + path] = original_studio[path]
        else:
            remove_on_rollback.append("studio/" + path)
    metadata = {"date": "2026-11-01", "build": source["build"], "target": "aarch64-unknown-linux-gnu.2.31",
        "api_version": 43, "deployed": False, "robot_motion_tested": False,
        "robotd_sha256": sha(binary), "robotd_bytes": len(binary),
        "required_runtime": {"onnxruntime": "existing compatible ARM64 shared runtime (dlopen)", "studio_python": "3.13"},
        "source_manifest_sha256": sha((HERE / "source-manifest.json").read_bytes()),
        "baseline_robotd_sha256": sha(original_binary),
        "baseline_is_live_backup": False,
        "rollback_remove_only_if_candidate_hash_matches": remove_on_rollback,
        "candidate_files": {p: sha(b) for p, b in candidate.items()},
        "baseline_files": {p: sha(b) for p, b in rollback.items()},
        "not_included": ["models", "calibration", "robotd.toml", "systemd services", "installer"]}
    for kind, files in (("candidate", candidate), ("baseline-rollback", rollback)):
        files["MANIFEST.json"] = (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        path = HERE / "artifacts" / f"duck-recovery.1-{kind}.tar.gz"
        pack(path, files)
        metadata[kind + "_archive"] = {"path": str(path.relative_to(HERE)).replace("\\", "/"), "sha256": sha(path.read_bytes()), "bytes": path.stat().st_size}
    (HERE / "candidate-manifest.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"robotd_sha256": metadata["robotd_sha256"], "robotd_bytes": len(binary), "candidate_archive": metadata["candidate_archive"], "baseline-rollback_archive": metadata["baseline-rollback_archive"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
