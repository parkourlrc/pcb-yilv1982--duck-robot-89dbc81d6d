"""Read-only incident collection on Radxa; JSON to stdout, no RPC or actions."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


def command(argv, timeout=15):
    try:
        p = subprocess.run(argv, capture_output=True, timeout=timeout)
        return {"argv": argv, "rc": p.returncode,
                "stdout": p.stdout.decode("utf-8", "replace"),
                "stderr": p.stderr.decode("utf-8", "replace")}
    except Exception as e:
        return {"argv": argv, "error": str(e)}


def read(path, limit=2_000_000):
    try:
        p = Path(path)
        with p.open("rb") as f:
            size = p.stat().st_size
            if size > limit:
                f.seek(size - limit)
            data = f.read(limit)
        return {"size": size, "tail_only": size > limit,
                "text": data.decode("utf-8", "replace")}
    except Exception as e:
        return {"error": str(e)}


out = {"utc": datetime.now(timezone.utc).isoformat(), "commands": {}, "files": {}}
commands = {
    "clock": ["date", "-Iseconds"],
    "uptime": ["uptime"],
    "boots": ["journalctl", "--list-boots", "--no-pager"],
    "services": ["systemctl", "show", "robotd.service", "microduck-studio.service",
                 "-p", "MainPID", "-p", "ActiveState", "-p", "UnitFileState", "-p", "NRestarts",
                 "-p", "Result", "-p", "ExecMainStatus", "-p", "ExecMainCode",
                 "-p", "ExecMainStartTimestamp", "-p", "ExecStart", "-p", "WorkingDirectory"],
    "incident": ["journalctl", "--since", "2026-11-01 15:49:00 UTC", "--no-pager", "-o", "short-iso-precise", "-n", "7000"],
    "previous_kernel": ["journalctl", "-b", "-1", "-k", "--no-pager", "-o", "short-iso-precise", "-n", "1800"],
    "current_kernel": ["journalctl", "-b", "0", "-k", "--no-pager", "-o", "short-iso-precise", "-n", "1000"],
    "core_list": ["coredumpctl", "--no-pager", "list", "--since", "2026-11-01 15:49:00 UTC"],
    "last": ["last", "-x", "-n", "15"],
    "memory": ["free", "-m"],
    "storage": ["df", "-h", "/", "/var/log", "/home/radxa/studio-dev/logs"],
    "journal_config": ["systemd-analyze", "cat-config", "systemd/journald.conf"],
}
for key, argv in commands.items():
    out["commands"][key] = command(argv)
for name in ["/proc/sys/kernel/random/boot_id", "/proc/uptime", "/etc/robot/feetech-ft5/robotd.toml"]:
    out["files"][name] = read(name)
for directory, pattern in [
    ("/home/radxa/studio-dev/logs", "studio-2026-11-0[12].log"),
    ("/sys/fs/pstore", "*"), ("/var/lib/systemd/pstore", "*"),
    ("/sys/class/thermal", "thermal_zone*/temp"),
    ("/sys/class/thermal", "thermal_zone*/trip_point_*_temp"),
    ("/sys/class/thermal", "thermal_zone*/trip_point_*_type"),
    ("/sys/devices/system/cpu/cpufreq", "policy*/scaling_cur_freq"),
]:
    try:
        paths = sorted(Path(directory).glob(pattern))
        out.setdefault("listings", {})[directory + "/" + pattern] = [str(p) for p in paths]
        for p in paths:
            if p.is_file():
                out["files"][str(p)] = read(p)
    except Exception as e:
        out.setdefault("listing_errors", {})[directory] = str(e)
binary = Path("/opt/robot/daemon/current/bin/robotd")
try:
    out["binary"] = {"path": str(binary.resolve()), "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}
except Exception as e:
    out["binary"] = {"error": str(e)}
print(json.dumps(out, ensure_ascii=False, indent=2))
