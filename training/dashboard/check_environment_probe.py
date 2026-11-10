"""Offline contract checks for environment identity and readiness probes.

No network, no training. The live probes are exercised separately against the
registered machines; this file only guards generation/parsing/matching logic.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard.environment_probe import build_script, ensure_scripts, parse_output
from dashboard.identity import match_environment, normalize


WSL_NODE = {
    'kind': 'wsl',
    'python': '/mnt/e/Projects/duck-robot/training/.venv-wsl/bin/python',
    'work_root': '/home/yilv/duck-dashboard',
    'identity': {'hostname': 'DESKTOP-TEST', 'gpu_name': 'NVIDIA GeForce RTX 4080', 'wsl_distro': 'Ubuntu'},
    'probe': {'gpu': 'torch', 'docker': False, 'env_keys': []},
}

SSH_NODE = {
    'kind': 'ssh',
    'ssh_target': 'spark-test',
    'work_root': '/home/test/dashboard',
    'benchmark_root': '/home/test/benchmark',
    'env_file': '/home/test/env.sh',
    'probe': {'gpu': 'nvidia-smi', 'docker': True, 'image': 'nvcr.io/nvidia/pytorch:25.10-py3',
              'env_keys': ['NCCL_NET', 'NCCL_SOCKET_IFNAME'], 'benchmark': True},
}


def test_scripts():
    wsl = build_script('local', WSL_NODE)
    assert 'DUCK_PROBE_READY' in wsl and 'CHECK %s ok' in wsl
    assert "torch.cuda.is_available()" in wsl
    assert 'work_root' in wsl
    assert 'nvidia-smi' not in wsl
    ssh = build_script('spark1', SSH_NODE)
    assert 'nvidia-smi --query-gpu=name' in ssh
    assert 'sudo -n docker info' in ssh
    assert 'image inspect' in ssh
    assert 'NCCL_NET' in ssh and 'NCCL_SOCKET_IFNAME' in ssh
    assert 'venv/pyvenv.cfg' in ssh
    with tempfile.TemporaryDirectory() as directory:
        paths = ensure_scripts(directory, {'local': WSL_NODE, 'spark1': SSH_NODE})
        assert paths['local'].read_text(encoding='utf-8') == wsl
        assert paths['spark1'].read_text(encoding='utf-8') == ssh
    return {'wsl_lines': len(wsl.splitlines()), 'ssh_lines': len(ssh.splitlines())}


def test_parse():
    ready = parse_output('CHECK gpu ok RTX 4080\nCHECK docker ok 29.2.1\nDUCK_PROBE_READY 1\n')
    assert ready['ready'] and len(ready['checks']) == 2 and ready['detail'] == '就绪'
    failed = parse_output('CHECK gpu ok RTX 4080\nCHECK docker fail daemon 不可用\nDUCK_PROBE_READY 0\n')
    assert not failed['ready'] and 'docker' in failed['detail']
    missing = parse_output('CHECK gpu ok RTX 4080\n')
    assert not missing['ready'] and 'READY' in missing['detail']
    return {'ready': ready['ready'], 'failed_detail': failed['detail']}


def test_matching():
    host = {'hostname': 'DESKTOP-TEST', 'gpu_names': ['NVIDIA GeForce RTX 4080'], 'wsl_distros': ['Ubuntu']}
    matched, report = match_environment({'local': WSL_NODE, 'spark1': SSH_NODE}, host)
    assert matched == 'local' and report['state'] == 'matched', report
    wrong_host = {**host, 'hostname': 'DESKTOP-OTHER'}
    matched, report = match_environment({'local': WSL_NODE, 'spark1': SSH_NODE}, wrong_host)
    assert matched is None and report['state'] == 'unregistered'
    wrong_gpu = {**host, 'gpu_names': ['NVIDIA GeForce RTX 5090']}
    matched, report = match_environment({'local': WSL_NODE}, wrong_gpu)
    assert matched is None and report['state'] == 'unregistered'
    duplicate = {'local': WSL_NODE, 'local2': {**WSL_NODE}}
    matched, report = match_environment(duplicate, host)
    assert matched is None and report['state'] == 'duplicate'
    assert normalize('  NVIDIA   GeForce RTX 4080 ') == 'nvidia geforce rtx 4080'
    return {'matched': matched, 'duplicate': report['state']}


def main():
    result = {
        'schema': 1,
        'scripts': test_scripts(),
        'parse': test_parse(),
        'matching': test_matching(),
        'status': 'passed',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
