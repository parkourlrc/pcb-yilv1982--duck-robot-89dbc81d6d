"""Cross-build and audit codec modules locally without installing them on a board."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

from collect_radxa_driver_sources import EVIDENCE, ROOT


def wsl(*arguments):
    return ["wsl.exe", "-d", "Ubuntu", "--exec", *map(str, arguments)]


def linux_path(path):
    return subprocess.check_output(wsl("wslpath", "-u", str(Path(path).resolve())), text=True, encoding="utf-8").strip()


def run(name, command):
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (EVIDENCE / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(name + " failed; see saved log")
    return result.stdout.strip()


def symbol_versions(path):
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        columns = line.split()
        if len(columns) >= 2:
            result[columns[1]] = int(columns[0], 16)
    return result


def main():
    preparation = json.loads((EVIDENCE / "module-build-preparation.json").read_text(encoding="utf-8"))
    headers = Path(preparation["headers_directory"]).resolve()
    build = Path(preparation["module_build_directory"]).resolve()
    kernel = preparation["kernel"]
    output = ROOT / "hardware/custom_hat/software/codec" / kernel
    if output.exists():
        raise FileExistsError("Inspect the existing codec build before replacing it")
    if headers.parent != build.parent or headers.name != "headers" or build.name != "codec-module":
        raise RuntimeError("Unexpected private build paths")
    for filename, expected in preparation["source_hashes"].items():
        if hashlib.sha256((build / filename).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Codec source differs from the pinned archive")
    foreign_tools = []
    for path in (headers / "scripts").rglob("*"):
        if not path.is_file():
            continue
        with path.open("rb") as stream:
            prefix = stream.read(20)
        if len(prefix) >= 20 and prefix[:4] == b"\x7fELF" and struct.unpack("<H", prefix[18:20])[0] == 183:
            if not path.resolve().is_relative_to(headers / "scripts"):
                raise RuntimeError("Host-tool cleanup escaped the private headers tree")
            foreign_tools.append(path.relative_to(headers).as_posix())
            path.unlink()
    (EVIDENCE / "header-host-tools-rebuild.json").write_text(json.dumps({"removed_aarch64_generated_tools": foreign_tools,
        "original_headers_package_retained": preparation["headers_archive"]}, indent=2) + "\n", encoding="utf-8")
    header_linux, build_linux = linux_path(headers), linux_path(build)
    flags = ["-C", header_linux, "ARCH=arm64", "CROSS_COMPILE=aarch64-linux-gnu-", "HOSTCC=gcc", "-j2"]
    compiler = run("cross-compiler-version", wsl("aarch64-linux-gnu-gcc", "--version"))
    host_tools = {
        "basic/fixdep": ["basic/fixdep.c"],
        "mod/modpost": ["mod/modpost.c", "mod/file2alias.c", "mod/sumversion.c"],
        "genksyms/genksyms": ["genksyms/genksyms.c", "genksyms/parse.tab.c", "genksyms/lex.lex.c"],
    }
    for name, sources in host_tools.items():
        directory = header_linux + "/scripts/" + name.rsplit("/", 1)[0]
        run("codec-host-" + name.replace("/", "-"), wsl("gcc", "-O2", "-I" + directory, "-o", header_linux + "/scripts/" + name,
                                                       *[header_linux + "/scripts/" + source for source in sources]))
    run("codec-module-build", wsl("make", *flags, "M=" + build_linux, "modules"))
    symbols = symbol_versions(headers / "Module.symvers")
    symbols.update(symbol_versions(build / "Module.symvers"))
    checks = []
    for filename in ("snd-soc-tlv320aic3x.ko", "snd-soc-tlv320aic3x-i2c.ko"):
        path = build / filename
        prefix = path.read_bytes()[:20]
        elf_machine = struct.unpack("<H", prefix[18:20])[0]
        module_linux = build_linux + "/" + filename
        info = run(filename + "-modinfo", wsl("/usr/sbin/modinfo", module_linux))
        imports = run(filename + "-versions", wsl("/usr/sbin/modprobe", "--dump-modversions", module_linux))
        mismatches = []
        count = 0
        for line in imports.splitlines():
            crc, symbol = line.split()[:2]
            count += 1
            if symbols.get(symbol) != int(crc, 16):
                mismatches.append({"symbol": symbol, "module_crc": crc, "reference_crc": symbols.get(symbol)})
        vermagic = next(line.split(":", 1)[1].strip() for line in info.splitlines() if line.startswith("vermagic:"))
        checks.append({"file": filename, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size,
                       "elf_machine": elf_machine, "vermagic": vermagic, "imported_symbols": count,
                       "symbol_crc_mismatches": mismatches, "accepted": elf_machine == 183 and vermagic.split()[0] == kernel and not mismatches and count > 0})
    if not all(row["accepted"] for row in checks):
        raise RuntimeError("Module architecture, vermagic or symbol CRC check failed")
    output.mkdir(parents=True)
    for row in checks:
        shutil.copy2(build / row["file"], output / row["file"])
    result = {"built_at": datetime.now(timezone.utc).isoformat(), "kernel": kernel, "compiler": compiler.splitlines()[0],
              "kernel_source_commit": preparation["kernel_source_commit"], "headers_sha256": preparation["headers_sha256"],
              "source_hashes": preparation["source_hashes"], "modules": checks, "accepted_offline": True,
              "compiler_difference_limit": "Architecture, vermagic and symbol CRC checks do not replace loading and functional validation on the actual kernel",
              "installed": False, "loaded": False, "hardware_tested": False, "current_runtime_verified": False}
    (output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (EVIDENCE / "codec-module-audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
