"""从固定来源重建候选；只创建新目录，拒绝覆盖已有工作副本。"""
import argparse
import json
import subprocess
from pathlib import Path
from source_inputs import HERE, baseline, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=HERE / ".work")
    args = parser.parse_args()
    dest = args.dest.resolve()
    if dest.exists():
        raise SystemExit(f"目标已存在，请指定新目录：{dest}")
    manifest = json.loads((HERE / "source-manifest.json").read_text(encoding="utf-8"))
    originals = {name: baseline(name) for name in manifest["components"]}
    for component, entry in manifest["components"].items():
        patch = HERE / "patches" / f"{component}.patch"
        if sha(patch.read_bytes()) != entry["patch_sha256"]:
            raise ValueError(f"补丁哈希不符：{component}")
        for item in entry["files"]:
            content = originals[component].get(item["path"])
            actual = None if content is None else sha(content)
            if actual != item["original_sha256"]:
                raise ValueError(f"基线文件哈希不符：{component}/{item['path']}")
    dest.mkdir(parents=True)
    for component, entry in manifest["components"].items():
        folder = dest / component
        for name, content in originals[component].items():
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        patch = HERE / "patches" / f"{component}.patch"
        # git apply from an unrelated empty working directory could inherit this repo's prefix.
        # A tiny temporary local repository makes the application root explicit; no commits.
        subprocess.run(["git", "init", "--quiet", str(folder)], check=True)
        git = ["git", "-c", "core.autocrlf=false", "-C", str(folder)]
        subprocess.run([*git, "apply", "--check", str(patch)], check=True)
        subprocess.run([*git, "apply", str(patch)], check=True)
        for item in entry["files"]:
            if sha((folder / item["path"]).read_bytes()) != item["candidate_sha256"]:
                raise ValueError(f"重放后哈希不符：{component}/{item['path']}")
        if component == "firmware":
            for path, expected in manifest["unchanged_control_sources"].items():
                if sha((folder / path).read_bytes()) != expected:
                    raise ValueError(f"原版通信或依赖锁文件变化：{path}")
        print(f"{component}: 补丁应用及逐文件 SHA256 通过")
    print(f"候选源码已生成：{dest}；未构建、未连接设备")


if __name__ == "__main__":
    main()
