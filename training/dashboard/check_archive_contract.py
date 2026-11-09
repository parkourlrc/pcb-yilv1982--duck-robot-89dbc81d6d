from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from dashboard.config import ROOT
from dashboard.runs import DashboardError, Runs
from dashboard.schemas import DeriveRequest, StartRequest, ValidationRequest
from dashboard.store import atomic_json
from experiment_archive import validate_workflow


def main():
    directory = Path(tempfile.mkdtemp(prefix='duck-archive-check-'))
    config = {'data_dir': str(directory / 'index'), 'artifact_dir': str(directory / 'artifacts'),
              'auto_import_history': False, 'export_records': False, 'nodes': {'local': {'kind': 'wsl', 'label': 'synthetic'}}}
    manager = Runs(ROOT, config)
    checks = []
    good = ValidationRequest(task_id='locomotion', task_version='v3', parameters={'num_envs': 4, 'num_steps_per_env': 8, 'max_updates': 2})
    validation = manager.validate(good)
    assert validation['valid'], validation['errors']
    validate_workflow(validation['workflow'], validation['resolved_config'])
    checks.append('resolved_config_and_workflow_budget_bound')
    for overrides in ({'Kd': 1}, {'learning_rate': float('nan')}, {'stage1': {'stage': 1, 'probabilities': [1, 0, 0, 0, 0]}}, {'num_envs': 3, 'num_steps_per_env': 3}):
        assert not manager.validate(ValidationRequest(task_id='locomotion', task_version='v3', parameters=overrides))['valid']
    checks.append('locked_nonfinite_curriculum_and_batch_invalid_rejected')
    with patch('dashboard.runs.threading.Thread'):
        original = manager.start(StartRequest(request_id='archive-contract-first', validation_id=validation['validation_id'], config_hash=validation['config_hash']))
    assert (manager.archive.run_root(original['run_id']) / 'dashboard-run.json').is_file()
    manager._snapshot(original)
    original.update(state='failed', failure='synthetic initialization failure')
    manager.save(original)
    assert manager.archive_detail(original['run_id'])['integrity']['state'] == 'partial'
    checks.append('registration_precedes_launch_and_failure_keeps_archive')
    draft = manager.derive(original['run_id'], DeriveRequest(request_id='archive-contract-derive', mode='scratch'))
    draft.pop('name')
    draft['parameters']['learning_rate'] = .0002
    validated = manager.validate(ValidationRequest(**draft))
    assert validated['valid'], validated['errors']
    with patch('dashboard.runs.threading.Thread'):
        derived = manager.start(StartRequest(request_id='archive-contract-second', validation_id=validated['validation_id'], config_hash=validated['config_hash']))
    assert derived['experiment_id'] != original['experiment_id'] and derived['parent_run_id'] == original['run_id']
    assert manager.get(original['run_id'])['config']['learning_rate'] != derived['config']['learning_rate']
    checks.append('scratch_derivation_new_budget_and_parent_immutable')
    original_source = manager.archive.run_root(original['run_id']) / 'project/training/experiment_archive.py'
    original_bytes = original_source.read_bytes()
    manager._snapshot(derived)
    assert (manager.archive.run_root(derived['run_id']) / 'project/training/experiment_archive.py').read_bytes() == original_bytes
    assert original_source.read_bytes() == original_bytes
    checks.append('scratch_freezes_parent_contract_without_overwrite')
    from mjlab_duck.experiment_config import transfer_contract
    checkpoint_root = manager.archive.run_root(original['run_id']) / 'cache/rank0/run/checkpoints/final'
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    (checkpoint_root / 'rank0.pt').write_bytes(b'synthetic checkpoint, not torch payload')
    from dashboard.registry import file_hash
    manifest = {'schema': 1, 'complete': True, 'world_size': 1, 'iter': 1, 'stage': 1,
                'rank_files': {'0': {'path': 'rank0.pt', 'sha256': file_hash(checkpoint_root / 'rank0.pt')}},
                'transfer_contract': transfer_contract(ROOT), 'consumed_transitions': 32}
    atomic_json(checkpoint_root / 'manifest.json', manifest)
    from dashboard.history import checkpoint_info
    checkpoint = checkpoint_info(checkpoint_root / 'manifest.json', original['run_id'], 'synthetic-warm')
    manager.store.put('checkpoint', checkpoint['checkpoint_id'], checkpoint)
    warm_draft = manager.derive(original['run_id'], DeriveRequest(request_id='archive-contract-warm', mode='warm', checkpoint_id=checkpoint['checkpoint_id']))
    warm_draft.pop('name')
    assert manager.validate(ValidationRequest(**warm_draft))['valid']
    manifest['transfer_contract']['action'] = 'incompatible'
    atomic_json(checkpoint_root / 'manifest.json', manifest)
    assert not manager.validate(ValidationRequest(**warm_draft))['valid']
    checks.append('warm_manifest_contract_checked_before_start')
    from dashboard.schemas import ResumeRequest
    parent = manager.get(original['run_id'])
    parent.update(state='stopped', initialization='warm', _locations={'local': '/synthetic/parent'},
                  _experiment_locations={'local': '/synthetic/experiment'})
    manager.save(parent)
    child = manager.get(derived['run_id'])
    child.update(state='failed')
    manager.save(child)
    with patch('dashboard.runs.threading.Thread'):
        resumed = manager.resume(original['run_id'], ResumeRequest(request_id='archive-contract-resume', checkpoint_id=checkpoint['checkpoint_id']))
    assert resumed['initialization'] == 'resume' and resumed['_resume_manifest']
    assert resumed['experiment_id'] == parent['experiment_id'] and resumed['budget'] == parent['budget']
    checks.append('warm_run_resume_keeps_ledger_without_warm_flag')
    detail = manager.archive_detail(original['run_id'])
    assert any(item['path'] == 'archive/project/config.json' for item in detail['artifacts'])
    try:
        manager.artifact_path(original['run_id'], '../session-secret')
        raise AssertionError('path traversal accepted')
    except DashboardError:
        pass
    malicious = {**original, 'run_id': 'malicious-path', '_directory': str(ROOT.parent)}
    manager.save(malicious)
    assert all(not item['path'].startswith('source/') for item in manager.archive_detail('malicious-path')['artifacts'])
    checks.append('artifact_allowlist_and_no_arbitrary_source_directory')
    artifact = manager.archive.run_root(original['run_id']) / 'project/config.json'
    artifact.write_text('{}', encoding='utf-8')
    assert manager.archive_detail(original['run_id'])['integrity']['errors']
    checks.append('sealed_artifact_tampering_detected')
    tampered = manager.archive_detail(original['run_id'])['capabilities']
    assert not any(tampered[key]['allowed'] for key in ('scratch', 'warm', 'resume', 'replay'))
    checks.append('tampering_disables_all_training_and_replay_capabilities')
    source_run = manager.get(derived['run_id'])
    pending_run = {**source_run, 'run_id': 'synthetic-sync-pending', '_archive_pending': True, 'state': 'failed'}
    manager.save(pending_run)
    assert not (manager.archive.run_root(pending_run['run_id']) / 'artifact-manifest.json').exists()
    from dashboard.cli import monitor
    with patch.object(manager, 'refresh', side_effect=lambda identifier: manager.save({**manager.get(identifier), '_archive_pending': False})), patch.object(manager, 'record_resource'), patch.object(manager.executors['local'], 'sample', return_value={}):
        monitor(manager, pending_run)
    assert not manager.get(pending_run['run_id'])['_archive_pending']
    checks.append('terminal_sync_pending_is_not_sealed_and_cli_retries')
    fresh = {**config, 'data_dir': str(directory / 'rebuilt-index')}
    reloaded = Runs(ROOT, fresh)
    assert reloaded.get(original['run_id'])['failure'] == 'synthetic initialization failure'
    assert reloaded.get(derived['run_id'])['state'] == 'failed'
    checks.append('sqlite_rebuilt_and_unlaunched_registration_converges')
    output = ROOT / 'docs/specs/20261109-训练档案与复训/checks/backend-contract.json'
    report = {'passed': checks, 'synthetic': True, 'training_updates': 0, 'training_transitions': 0}
    atomic_json(output, report)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
