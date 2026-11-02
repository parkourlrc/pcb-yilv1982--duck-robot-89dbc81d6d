"""Prepare the exact official headers and codec sources for an offline module build."""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import urllib.request

from collect_radxa_driver_sources import EVIDENCE, ROOT, SOURCES
from inspect_radxa_runtime_package import deb_members, KERNEL, TAG


def main():
    audit = json.loads((EVIDENCE / "runtime-package-audit.json").read_text(encoding="utf-8"))
    release = json.loads((SOURCES / ("nocsf-release-" + TAG + ".json")).read_text(encoding="utf-8"))
    asset = next(row for row in release["assets"] if row["name"].startswith("linux-headers-" + KERNEL + "_") and row["name"].endswith("_arm64.deb"))
    cache = Path(os.environ["LOCALAPPDATA"]) / "duck-robot-tools/radxa-kernel" / TAG
    archive = cache / asset["name"]
    if not archive.is_file():
        request = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "duck-robot-hat-review"})
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
        if len(data) != asset["size"] or "sha256:" + hashlib.sha256(data).hexdigest() != asset["digest"]:
            raise ValueError("Headers package authentication failed")
        archive.write_bytes(data)
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if asset["digest"] != "sha256:" + digest:
        raise ValueError("Cached headers differ from official release")
    headers = cache / "headers"
    headers.mkdir(exist_ok=True)
    prefix = "usr/src/linux-headers-" + KERNEL + "/"
    regular_count, skipped_links = 0, []
    for name, content in deb_members(archive):
        if not name.startswith("data.tar"):
            continue
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:*") as document:
            for member in document:
                member_name = member.name.removeprefix("./")
                if not member_name.startswith(prefix):
                    continue
                relative = PurePosixPath(member_name[len(prefix):])
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("Unsafe header member")
                if member.issym() or member.islnk():
                    skipped_links.append({"name": str(relative), "link": member.linkname})
                    continue
                if not member.isfile():
                    continue
                target = headers.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with document.extractfile(member) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                regular_count += 1
    if not (headers / "Module.symvers").is_file() or not (headers / ".config").is_file():
        raise RuntimeError("Headers lack configuration or symbol CRC data")
    build = cache / "codec-module"
    build.mkdir(exist_ok=True)
    source_hashes = {}
    for filename in ("tlv320aic3x.c", "tlv320aic3x.h", "tlv320aic3x-i2c.c"):
        source = SOURCES / ("exact-sound__soc__codecs__" + filename)
        shutil.copy2(source, build / filename)
        source_hashes[filename] = hashlib.sha256(source.read_bytes()).hexdigest()
    template = ROOT / "hardware/custom_hat/software/codec/Kbuild"
    shutil.copy2(template, build / "Kbuild")
    result = {"kernel": KERNEL, "headers_archive": str(archive), "headers_sha256": digest, "headers_upstream_digest_verified": True,
              "headers_directory": str(headers), "regular_headers_files": regular_count, "skipped_links": skipped_links,
              "module_build_directory": str(build), "kernel_source_commit": audit["kernel_source_commit"],
              "source_hashes": source_hashes, "Kbuild_sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
              "built": False, "installed": False, "hardware_tested": False}
    (EVIDENCE / "module-build-preparation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
