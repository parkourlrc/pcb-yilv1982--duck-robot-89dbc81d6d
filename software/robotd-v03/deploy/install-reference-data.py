#!/usr/bin/env python3
"""安装已准备的参考配置；备份原文件，不启动 robotd，不访问电机。"""
import datetime
import grp
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib

STAGE = Path('/home/radxa/duck-reference-data-20261031')
TARGET = Path('/etc/robot/feetech-ft5')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status(*args):
    result = subprocess.run(['systemctl', *args], capture_output=True, text=True, check=False)
    return result.stdout.strip()


def atomic_install(source, target):
    fd, name = tempfile.mkstemp(prefix='.reference-', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(source.read_bytes())
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, 0o644)
        os.chown(name, 0, grp.getgrnam('radxa').gr_gid)
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    assert os.geteuid() == 0
    report = json.loads((STAGE / 'import-result.json').read_text())
    assert report.get('configuration_prepared') and not report.get('error')
    assert len(report['models']) == 6
    assert all(row['native_preflight']['valid'] for row in report['models'])
    assert sha(STAGE / 'robotd.toml') == report['configuration_sha256']
    assert sha(STAGE / 'hd1910-calibration.toml') == report['calibration_sha256']
    assert status('is-active', 'robotd.service') == 'inactive'
    assert status('is-enabled', 'robotd.service') == 'disabled'
    assert '--read-only' in status('show', 'robotd.service', '-p', 'ExecStart', '--value')
    configuration = tomllib.loads((STAGE / 'robotd.toml').read_text())
    calibration = tomllib.loads((STAGE / 'hd1910-calibration.toml').read_text())
    assert configuration['policy']['enabled'] is False
    assert calibration['motion_enabled'] is False and calibration['imu_mount_verified'] is False
    assert len(calibration['joints']) == 15 and all(not j['calibrated'] for j in calibration['joints'])
    for model in report['models']:
        assert configuration['policy'][model['slot']] == model['path']
        assert sha(Path(model['path'])) == model['sha256']
    existing = TARGET / 'hd1910-calibration.toml'
    if existing.exists():
        assert sha(existing) == report['calibration_sha256'], 'An independent local calibration exists'
    current = tomllib.loads((TARGET / 'robotd.toml').read_text())
    assert current.get('policy', {}).get('enabled') is False
    backup = TARGET / ('backup-before-reference-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    backup.mkdir(mode=0o750)
    for name in ('robotd.toml', 'hd1910-calibration.toml'):
        if (TARGET / name).exists():
            shutil.copy2(TARGET / name, backup / name)
    # Install the guarded calibration before making the config refer to it.
    atomic_install(STAGE / 'hd1910-calibration.toml', TARGET / 'hd1910-calibration.toml')
    atomic_install(STAGE / 'robotd.toml', TARGET / 'robotd.toml')
    for name in ('robotd.toml', 'hd1910-calibration.toml'):
        assert sha(TARGET / name) == sha(STAGE / name)
    result = {'date': '2026-10-31', 'backup': str(backup), 'configuration_installed': True,
        'configuration': configuration, 'configuration_sha256': sha(TARGET / 'robotd.toml'),
        'calibration': calibration, 'calibration_sha256': sha(TARGET / 'hd1910-calibration.toml'),
        'reference_robot': 'duck-10e4', 'local_calibration_verified': False,
        'robotd_active': status('is-active', 'robotd.service'),
        'robotd_enabled': status('is-enabled', 'robotd.service'),
        'studio_active': status('is-active', 'microduck-studio.service'),
        'motor_access': False}
    path = STAGE / 'install-result.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.chmod(path, 0o644)
    print(json.dumps({k:v for k,v in result.items() if k not in ('configuration', 'calibration')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
