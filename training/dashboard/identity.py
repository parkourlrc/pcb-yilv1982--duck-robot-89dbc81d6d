from __future__ import annotations

import platform
import re
import subprocess


def normalize(value):
    """Case-insensitive, whitespace-collapsed form used for identity matching."""
    return re.sub(r'\s+', ' ', (value or '').strip()).casefold()


def detect_gpu():
    """Return the GPU names visible to the Windows host (nvidia-smi), if any."""
    try:
        process = subprocess.run(
            ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if process.returncode:
        return []
    return [line.strip() for line in process.stdout.decode(errors='replace').splitlines() if line.strip()]


def detect_wsl_distros():
    """Return WSL distribution names; empty when WSL or the query is unavailable."""
    try:
        process = subprocess.run(
            ['wsl.exe', '-l', '-q'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if process.returncode:
        return []
    raw = process.stdout
    text = raw.decode('utf-16-le', errors='ignore') if b'\x00' in raw else raw.decode('utf-8', errors='ignore')
    return [line.strip().strip('\x00') for line in text.splitlines() if line.strip().strip('\x00')]


def detect_host():
    """Describe the machine the dashboard is currently running on."""
    return {
        'hostname': platform.node(),
        'gpu_names': detect_gpu(),
        'wsl_distros': detect_wsl_distros(),
        'platform': platform.system(),
    }


def _matches(identity, hostname, gpu_names, distros):
    if not identity or not identity.get('hostname'):
        return False
    if normalize(identity.get('hostname')) != hostname:
        return False
    expected_gpu = normalize(identity.get('gpu_name'))
    if expected_gpu and gpu_names and expected_gpu not in gpu_names:
        return False
    expected_distro = normalize(identity.get('wsl_distro'))
    if expected_distro and distros and expected_distro not in distros:
        return False
    return True


def match_environment(nodes, host=None):
    """Match the current host to one registered environment.

    Only local-capable entries (kind != 'ssh') are considered. Returns
    (environment_id, report); environment_id is None when the host is
    unregistered or several entries share the same identity.
    """
    host = host or detect_host()
    hostname = normalize(host.get('hostname'))
    gpu_names = {normalize(name) for name in host.get('gpu_names', []) if name}
    distros = {normalize(name) for name in host.get('wsl_distros', []) if name}
    matches = [
        node_id for node_id, node in nodes.items()
        if isinstance(node, dict) and node.get('kind') != 'ssh'
        and _matches(node.get('identity'), hostname, gpu_names, distros)
    ]
    report = {
        'hostname': host.get('hostname'),
        'gpu_names': host.get('gpu_names', []),
        'wsl_distros': host.get('wsl_distros', []),
        'matches': sorted(matches),
    }
    if len(matches) == 1:
        report.update(state='matched', detail='已登记：' + matches[0])
        return matches[0], report
    if not matches:
        report.update(state='unregistered', detail='未找到与主机名/GPU 匹配的登记环境')
        return None, report
    report.update(state='duplicate', detail='多个登记环境匹配同一主机：' + ', '.join(sorted(matches)))
    return None, report
