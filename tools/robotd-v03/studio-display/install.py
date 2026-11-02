"""备份并安装本次 Studio 显示文件；不重启服务、不访问串口。"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = Path(__file__).resolve().parent
    target = Path('/home/radxa/studio-dev').resolve()
    manifest = json.loads((source / 'source-manifest.json').read_text(encoding='utf-8'))
    names = ('studio/state.py', 'studio/servo.py', 'studio/robotd.py',
             'studio/imu.py', 'studio/commissioning_display.py')
    if set(manifest['files']) != set(names):
        raise RuntimeError('Unexpected deployment file set')
    for name in names:
        old, new = target / name, source / 'overlay' / name
        expected = manifest['files'][name]
        if digest(new) != expected['installed_sha256']:
            raise RuntimeError(f'Payload SHA mismatch: {name}')
        compile(new.read_text(encoding='utf-8'), name, 'exec')
        if expected.get('upstream_sha256') is None:
            if old.exists():
                raise RuntimeError(f'New module already exists: {name}')
        elif not old.is_file() or digest(old) != expected['upstream_sha256']:
            raise RuntimeError(f'Installed source changed; no files written: {name}')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = Path('/home/radxa/studio-display-backups') / stamp
    backup.mkdir(parents=True, exist_ok=False)
    report = {'installed_at_utc': stamp, 'target': str(target), 'backup': str(backup),
              'service_restart_performed': False, 'files': {}}
    # 先备齐所有原件，再逐文件原子替换；失败时恢复本次已替换文件。
    for name in names:
        old = target / name
        if old.exists():
            saved = backup / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old, saved)
    changed = []
    try:
        for name in names:
            dest = target / name
            temp = dest.with_name(dest.name + '.duck-display-new')
            shutil.copyfile(source / 'overlay' / name, temp)
            temp.chmod(0o644)
            os.replace(temp, dest)
            changed.append(name)
            report['files'][name] = {'sha256': digest(dest),
                                     'before_sha256': manifest['files'][name].get('upstream_sha256')}
    except Exception:
        for name in reversed(changed):
            saved, dest = backup / name, target / name
            if saved.exists():
                shutil.copy2(saved, dest)
            else:
                dest.unlink()
        raise
    (backup / 'installation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
