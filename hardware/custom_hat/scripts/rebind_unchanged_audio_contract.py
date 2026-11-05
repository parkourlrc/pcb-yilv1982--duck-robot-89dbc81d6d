"""Rebind offline software evidence after an exclusively manufacturing-contract revision."""
import hashlib
import json
from pathlib import Path
import shutil

import pipeline


def main():
    checkpoint=pipeline.current_checkpoint()
    root=pipeline.BASE.parents[1]
    evidence=root/'docs/references/归档扩展板音频芯片焊盘'
    old_path=evidence/'before-metadata/net-contract.json'
    new_path=pipeline.PRIMARY/'net-contract.json'
    old=json.loads(old_path.read_text(encoding='utf-8'));new=json.loads(new_path.read_text(encoding='utf-8'))
    changed=[key for key in set(old)|set(new) if old.get(key)!=new.get(key)]
    if changed!=['qualified_codec_pth']:
        raise RuntimeError('Electrical contract changed or unrelated metadata differs')
    package=pipeline.BASE/'software/codec/6.1.84-10-rk2410-nocsf'
    manifest_path=package/'overlay-manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['net_contract_sha256']!=pipeline.digest(old_path):
        raise RuntimeError('Previous overlay contract does not match the recorded source')
    if manifest['overlay_sha256']!=pipeline.digest(package/'duck-hat-audio.dtbo'):
        raise RuntimeError('Overlay binary changed')
    backup=evidence/'software-before-padstack';backup.mkdir(exist_ok=False)
    shutil.copy2(manifest_path,backup/manifest_path.name)
    manifest['net_contract_sha256']=pipeline.digest(new_path)
    manifest['manufacturing_only_rebind']={'old_contract_sha256':pipeline.digest(old_path),'changed_keys':changed,
        'electrical_contract_equal':True,'overlay_binary_recompiled':False,'retested_on_hardware':False,'source_pcb_sha256':checkpoint['pcb_sha256']}
    pipeline.write_json(manifest_path,manifest)
    source_reports={
        'driver-compatibility-20261031':'offline-package-final-audit.json',
        'bmi088-adapter-20261031':'final-audit.json',
        'audio-routing-20261031':'final-audit.json'}
    for folder,name in source_reports.items():
        source=root/'docs/references/扩展板电路仿真工具'/folder/name
        shutil.copy2(source,backup/(folder+'-'+name))
    pipeline.write_json(evidence/'software-contract-rebind.json',manifest['manufacturing_only_rebind'])
    print(json.dumps(manifest['manufacturing_only_rebind']))


if __name__=='__main__':main()
