#!/usr/bin/env python3
"""导入现成六模型并准备关闭动作的参考配置；不访问串口或启动服务。"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import tomllib
import zipfile

STUDIO = Path('/home/radxa/studio-dev')
BASE = Path('/home/radxa/duck-policies/hd1910-20261031')
STAGE = Path('/home/radxa/duck-reference-data-20261031')
REFERENCE = STAGE / 'reference-data'
sys.path[:0] = [str(STUDIO), str(STUDIO / 'deps')]

from studio.models import Models, _signature
from studio.model_package import REQUIRED, OPTIONAL, validate_policy
from studio.__main__ import default_state_dir


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_report(report):
    (STAGE / 'import-result.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    assert os.geteuid() != 0, 'Run as radxa so Studio owns its model library'
    STAGE.mkdir(exist_ok=True)
    provenance = json.loads((REFERENCE / 'source.json').read_text())
    for item in provenance['files']:
        assert digest(REFERENCE / item['file']) == item['sha256'], item['file']
    library = Models(None, None, default_state_dir())
    report = {'date': '2026-10-31', 'models': [], 'hardware_access': False,
              'local_calibration_verified': False, 'configuration_installed': False}
    active_result = {}

    def validator(path):
        result = validate_policy(path, '/opt/robot/feetech-ft5-r5/robotd',
                                 env=library._runtime_env())
        active_result.update(result)
        return result

    library.validator = validator
    catalog = json.loads((BASE / 'catalog.json').read_text())
    paths = {}
    signatures = []
    try:
        for model in catalog['models']:
            active_result.clear()
            _, existing, error = library._read_library()
            if error:
                raise RuntimeError(error)
            matching = [e for e in existing if e['sha256'] == model['sha256']
                        and e['slot'] == model['slot']]
            source = BASE / model['directory']
            assert digest(source / 'policy.onnx') == model['sha256']
            if not matching:
                with tempfile.TemporaryDirectory(prefix='reference-import-', dir=STAGE) as tmp:
                    archive = Path(tmp) / 'model.zip'
                    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_STORED) as bundle:
                        for name in sorted(REQUIRED | OPTIONAL):
                            if (source / name).is_file():
                                bundle.write(source / name, arcname=name)
                    library._install(archive, model['name'])
                _, entries, error = library._read_library()
                if error:
                    raise RuntimeError(error)
                matching = [e for e in entries if e['sha256'] == model['sha256']
                            and e['slot'] == model['slot']]
            else:
                validator(Path(matching[0]['path']))
            assert len(matching) == 1, 'Ambiguous imported model identity'
            item = matching[0]
            target = Path(item['path'])
            assert digest(target) == model['sha256']
            copied = []
            for name in sorted(REQUIRED | OPTIONAL):
                if (source / name).is_file():
                    assert digest(source / name) == digest(target.parent / name), name
                    copied.append({'name': name, 'sha256': digest(target.parent / name)})
            contract = json.loads((target.parent / 'deployment-contract.json').read_text())
            signatures.append(_signature(contract))
            assert signatures[-1] == signatures[0], 'Models disagree on HOME/P/joint order'
            paths[model['slot']] = str(target)
            report['models'].append({'slot': model['slot'], 'source': str(source),
                'path': str(target), 'studio_id': item['id'], 'sha256': model['sha256'],
                'native_preflight': dict(active_result), 'files': copied,
                'deployment_verified': False})
            save_report(report)
            print(json.dumps({'slot': model['slot'], 'valid': active_result.get('valid'),
                              'path': str(target)}, ensure_ascii=False), flush=True)

        config = (REFERENCE / 'robotd-profile.toml').read_text()
        config = config.split('# Operator-requested L3 test')[0].rstrip() + '\n'
        config = re.sub(r'\[safety\]\n.*?(?=\n\[)', '', config, count=1, flags=re.S)
        config = config.replace('enabled = true', 'enabled = false', 1)
        config = config.replace('protocol = "feetech"\n',
            'protocol = "feetech"\nimu_protocol = "feetech"\nimu_profile = "legacy"\n', 1)
        config = config.replace('gain = 5\n', 'gain = 5\nhead_lowpass = 1.0\nlegs_lowpass = 1.0\n', 1)
        for model in catalog['models']:
            original = '/opt/robot/feetech-ft5-r5/' + model['onnx']
            config = config.replace(original, paths[model['slot']])
        config += '\n[trunk_imu]\nsource = "bus"\n\n[audio]\nenabled = false\n'
        config = ('# Reference numeric settings; local motion remains disabled.\n'
                  '# Walk deployment-execution.json overrides global action_scale.\n' + config)
        parsed = tomllib.loads(config)
        assert parsed['policy']['enabled'] is False
        assert set(paths) == {'walk', 'sitstand', 'ground_pick', 'roulade', 'kick_left', 'kick_right'}
        assert all(parsed['policy'][slot] == path for slot, path in paths.items())
        assert {s['name'] for s in parsed['policy']['skill']} == {'roulade', 'kick_left', 'kick_right'}
        assert 'safety' not in parsed
        (STAGE / 'robotd.toml').write_text(config, encoding='utf-8')

        original = (REFERENCE / 'hd1910-calibration.robot.toml').read_text()
        calibration = original.replace('"motion_enabled" = true', '"motion_enabled" = false')
        calibration = calibration.replace('"imu_mount_verified" = true', '"imu_mount_verified" = false')
        calibration = calibration.replace('"calibrated" = true', '"calibrated" = false')
        calibration = ('# Numeric values borrowed from duck-10e4, NOT measured on radxa-zero3.\n'
                       '# Upstream verification flags are cleared for this local copy.\n' + calibration)
        source_cal = tomllib.loads(original)
        local_cal = tomllib.loads(calibration)
        assert not local_cal['motion_enabled'] and not local_cal['imu_mount_verified']
        assert len(local_cal['joints']) == 15
        for source_joint, local_joint in zip(source_cal['joints'], local_cal['joints']):
            assert not local_joint['calibrated']
            assert {k:v for k,v in source_joint.items() if k != 'calibrated'} == {
                k:v for k,v in local_joint.items() if k != 'calibrated'}
        assert source_cal['imu_mount_quat'] == local_cal['imu_mount_quat']
        (STAGE / 'hd1910-calibration.toml').write_text(calibration, encoding='utf-8')
        report.update({'configuration_prepared': True, 'home_p_joint_order_match': True,
            'configuration_sha256': digest(STAGE / 'robotd.toml'),
            'calibration_sha256': digest(STAGE / 'hd1910-calibration.toml'),
            'reference_calibration_sha256': digest(REFERENCE / 'hd1910-calibration.robot.toml'),
            'reference_robot': 'duck-10e4', 'policy_enabled': False, 'motion_enabled': False})
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
        save_report(report)
        raise
    save_report(report)
    print('Six models imported; guarded configuration prepared.', flush=True)


if __name__ == '__main__':
    main()
