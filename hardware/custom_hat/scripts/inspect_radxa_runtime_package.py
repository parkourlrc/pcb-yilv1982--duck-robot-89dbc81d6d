"""Inspect an official kernel package without installing or executing its contents."""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import urllib.request

from collect_radxa_driver_sources import EVIDENCE, SOURCES, fetch


TAG = "6.1.84-10"
KERNEL = TAG + "-rk2410-nocsf"


def deb_members(path):
    with path.open("rb") as stream:
        if stream.read(8) != b"!<arch>\n":
            raise ValueError("Not a Debian ar archive")
        while header := stream.read(60):
            if len(header) != 60 or header[58:] != b"`\n":
                raise ValueError("Invalid ar member")
            name = header[:16].decode("ascii").strip().rstrip("/")
            length = int(header[48:58])
            content = stream.read(length)
            if len(content) != length:
                raise ValueError("Truncated ar member")
            if length % 2:
                stream.read(1)
            yield name, content


def main():
    if (EVIDENCE / "runtime-package-audit.json").exists():
        raise FileExistsError("Review existing package audit before repeating")
    records = json.loads((EVIDENCE / "sources-manifest.json").read_text(encoding="utf-8"))["sources"]
    api = "https://api.github.com/repos/radxa-pkg/linux-rk2410-nocsf"
    release = json.loads(fetch("nocsf-release-" + TAG + ".json", api + "/releases/tags/" + TAG, records))
    commit = json.loads(fetch("nocsf-package-commit.json", api + "/commits/" + TAG, records))["sha"]
    tree = json.loads(fetch("nocsf-package-tree.json", api + "/git/trees/" + commit + "?recursive=1", records))
    kernel_commit = next(entry["sha"] for entry in tree["tree"] if entry["path"] == "src")
    raw = "https://raw.githubusercontent.com/radxa-pkg/linux-rk2410-nocsf/" + commit + "/"
    for entry in tree["tree"]:
        if entry["type"] == "blob" and (entry["path"] in {".github/local/Makefile.local", "debian/changelog", ".gitmodules"} or entry["path"].startswith("debian/patches/")):
            fetch("nocsf-" + entry["path"].replace("/", "__"), raw + entry["path"], records)
    asset = next(entry for entry in release["assets"] if entry["name"].startswith("linux-image-" + KERNEL + "_") and entry["name"].endswith("_arm64.deb"))
    cache = Path(os.environ["LOCALAPPDATA"]) / "duck-robot-tools/radxa-kernel" / TAG
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / asset["name"]
    if not archive.is_file():
        temporary = archive.with_suffix(".part")
        request = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "duck-robot-hat-review"})
        with urllib.request.urlopen(request, timeout=45) as response, temporary.open("wb") as stream:
            while block := response.read(1024 * 1024):
                stream.write(block)
        if temporary.stat().st_size != asset["size"]:
            raise ValueError("Kernel package size mismatch")
        temporary.replace(archive)
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    upstream_digest = asset.get("digest")
    if upstream_digest and upstream_digest != "sha256:" + digest:
        raise ValueError("Kernel package digest mismatch")
    extracted, modules = [], []
    for member_name, content in deb_members(archive):
        if not member_name.startswith("data.tar"):
            continue
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:*") as document:
            for member in document:
                if not member.isfile():
                    continue
                name = member.name.removeprefix("./")
                if ".ko" in name:
                    modules.append(name)
                selected = (name == "boot/config-" + KERNEL or name.endswith(("/modules.alias", "/modules.builtin", "/modules.dep"))
                            or ("radxa-zero" in name and name.endswith(".dtb")))
                if selected:
                    source = document.extractfile(member)
                    if source is None:
                        raise ValueError("Selected archive entry has no regular data")
                    data = source.read()
                    target = SOURCES / ("runtime-" + Path(name).name)
                    if target.exists():
                        raise FileExistsError(target)
                    target.write_bytes(data)
                    extracted.append({"member": name, "file": target.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    config_path = SOURCES / ("runtime-config-" + KERNEL)
    if not config_path.is_file():
        raise RuntimeError("Exact release configuration was not present")
    selected_config = {}
    for line in config_path.read_text(encoding="utf-8").splitlines():
        if any(key in line for key in ("TLV320AIC3X", "BMI088", "BMG160", "BMI160", "I2C_RK3X", "I2C_CHARDEV", "SND_SIMPLE_CARD", "SND_SOC_ROCKCHIP_I2S", "SND_SOC_ALL_CODECS")):
            selected_config[line.split("=")[0].removeprefix("# ").removesuffix(" is not set")] = line
    result = {"release_url": release["html_url"], "tag": TAG, "kernel": KERNEL, "package_commit": commit,
              "kernel_source_commit": kernel_commit, "asset_url": asset["browser_download_url"], "cached_package": str(archive),
              "package_size_bytes": archive.stat().st_size, "sha256": digest, "upstream_digest": upstream_digest,
              "upstream_digest_verified": bool(upstream_digest), "extracted": extracted, "selected_config": selected_config,
              "relevant_modules": [name for name in modules if any(key in name.lower() for key in ("aic3x", "bmi088", "bmg160", "i2s", "simple-card"))],
              "total_module_files": len(modules), "installed_or_executed": False, "current_runtime_verified": False,
              "recorded_runtime_date": "2026-10-24", "limit": "Official release artifact with the recorded kernel version; does not prove the board still runs it or uses unchanged DT/config"}
    (EVIDENCE / "runtime-package-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in {"extracted", "relevant_modules"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
