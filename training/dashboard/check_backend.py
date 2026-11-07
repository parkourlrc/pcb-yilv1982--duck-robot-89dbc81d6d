from __future__ import annotations

import json
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from dashboard.config import ROOT, load_config
from dashboard.runs import Runs
from dashboard.history import checkpoint_info, metrics
from dashboard.registry import file_hash
from dashboard.schemas import ResumeRequest
from dashboard.store import atomic_json, utcnow
from dashboard.telemetry import collect


def main():
    config = load_config()
    config['data_dir'] = tempfile.mkdtemp(prefix='duck-backend-contract-')
    manager = Runs(ROOT, config)
    checks = []
    first = manager.store.event('event-run', {'seq': 100, 'phase': 'training'})
    second = manager.store.event('event-run', {'seq': 1, 'phase': 'failed'})
    assert second['seq'] > first['seq'] and second['source_seq'] == 1
    assert manager.store.events('event-run', first['seq'])[0]['seq'] == second['seq']
    checks.append('database_cursor_separate_from_source_seq')
    directory = Path(config['data_dir']) / 'runs/synthetic/cache/rank0/run'
    run = {'run_id': 'synthetic', 'experiment_id': 'experiment', 'managed': True, 'state': 'training',
           'execution': {'node_ids': ['spark1', 'spark2'], 'world_size': 2}, 'connection': {'state': 'connected', 'last_seen_utc': utcnow()},
           'budget': {'remaining_transitions': 128, 'max_transitions': 192, 'consumed_transitions': 64, 'transitions_per_update': 64},
           'capabilities': {'stop': {'allowed': True}, 'resume': {'allowed': False}}, 'model_iteration': 1, 'stage': 1,
           '_directory': str(directory), '_locations': {'spark1': '/fake/one', 'spark2': '/fake/two'}}
    actions = []

    class FakeExecutor:
        def __init__(self, name, state=None, offline=False):
            self.name, self.state, self.offline = name, state, offline
        def sync_run(self, remote, local):
            if self.offline:
                raise OSError('synthetic disconnect')
            atomic_json(Path(local) / 'supervisor.json', self.state)
        def write_json(self, path, value):
            actions.append((self.name, 'stop'))
        def terminate(self, directory, container_name=None):
            actions.append((self.name, 'terminate'))
        def read_json(self, path):
            return None
        def cache_checkpoints(self, remote, local):
            actions.append((self.name, 'cache'))
        def job_alive(self, directory):
            return True
    manager.executors = {'spark1': FakeExecutor('spark1', {'state': 'failed'}), 'spark2': FakeExecutor('spark2', offline=True)}
    manager.save(run)
    refreshed = manager.refresh('synthetic')
    assert refreshed['state'] == 'stopping' and ('spark2', 'stop') in actions and ('spark2', 'terminate') in actions
    checks.append('peer_failure_processed_during_disconnect')
    old = json.loads(json.dumps(run))
    old.update(state='training', _stop_requested=False)
    manager.save(old)
    assert manager.get('synthetic')['_stop_requested'] and manager.get('synthetic')['state'] == 'stopping'
    checks.append('stop_intent_survives_stale_snapshot')
    stale = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    manager.executors = {name: FakeExecutor(name, {'state': 'running', 'heartbeat_utc': stale}) for name in ('spark1', 'spark2')}
    assert manager.refresh('synthetic')['connection']['state'] == 'connected'
    manager.heartbeat_observations = {('synthetic', name): (stale, time.monotonic() - 20) for name in ('spark1', 'spark2')}
    assert manager.refresh('synthetic')['connection']['state'] == 'stale'
    checks.append('supervisor_heartbeat_staleness')
    current = manager.get('synthetic')
    current.update(state='stopped', _cached_manifest_count=2, _launch_failed=True, name='synthetic')
    manager.save(current)
    manifest = directory / 'checkpoints/final/manifest.json'
    atomic_json(manifest, {'world_size': 2})
    manager.store.put('checkpoint', 'synthetic-final', {'checkpoint_id': 'synthetic-final', 'run_id': 'synthetic', 'resumable': True, '_manifest': str(manifest)})
    with patch('dashboard.runs.threading.Thread'):
        child = manager.resume('synthetic', ResumeRequest(request_id='resume-synthetic', checkpoint_id='synthetic-final'))
    assert '_cached_manifest_count' not in child and '_launch_failed' not in child and not child['_stop_requested']
    checks.append('resume_clears_parent_runtime_counters')
    broken_directory = Path(config['data_dir']) / 'broken-checkpoint'
    broken_directory.mkdir()
    (broken_directory / 'rank0.pt').write_bytes(b'only rank0')
    broken = {'schema': 1, 'complete': True, 'world_size': 2, 'rank_files': {'0': {'path': 'rank0.pt', 'sha256': file_hash(broken_directory / 'rank0.pt')}}, 'iter': 2}
    atomic_json(broken_directory / 'manifest.json', broken)
    information = checkpoint_info(broken_directory / 'manifest.json', 'new', 'broken')
    assert information['integrity'] != 'complete' and not information['replayable'] and not information['resumable']
    broken['world_size'] = 1
    broken['rank_files']['0']['path'] = '../broken-checkpoint/rank0.pt'
    atomic_json(broken_directory / 'manifest.json', broken)
    information = checkpoint_info(broken_directory / 'manifest.json', 'new', 'broken')
    assert not information['resumable']
    checks.append('manifest_rank_set_and_path_validation')
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'updates.jsonl').write_text(json.dumps({'model_iteration': 2, 'consumed_transitions': 192, 'statistics': {'transitions': 64}, 'episodes': {'samples': 7, 'return_mean': 3, 'length_mean': 4}}) + '\n')
    atomic_json(directory / 'evaluation_000002.json', {'model_iteration': 2, 'checkpoint': '/remote/checkpoints/test/manifest.json', 'passed_count': 1, 'total': 9})
    curves = {item['key']: item for item in metrics(current)['series']}
    assert curves['episode_return']['points'][0]['sample_count'] == 7
    assert curves['evaluation/dev9']['points'][0]['transitions'] == 192
    assert curves['reward_mean']['points'][0]['value'] is None
    checks.append('episode_samples_and_actual_evaluation_budget')
    manager.save({**current, 'state': 'training'})
    def write_failure(*args):
        raise OSError('synthetic unavailable node')
    manager.executors['spark1'].write_json = write_failure
    actions.clear()
    manager.stop('synthetic')
    assert ('spark2', 'stop') in actions and 'spark1' in manager.get('synthetic')['_stop_delivery_errors']
    checks.append('stop_delivery_continues_after_node_error')
    orphan = {**current, 'run_id': 'orphan', 'state': 'preparing', '_directory': str(Path(config['data_dir']) / 'missing')}
    orphan.pop('_locations', None)
    manager.save(orphan)
    reloaded = Runs(ROOT, config)
    assert reloaded.get('orphan')['state'] == 'failed'
    checks.append('restarted_preparing_without_job_converges')
    with patch('dashboard.telemetry.subprocess.run', side_effect=subprocess.TimeoutExpired('nvidia-smi', 3)):
        sample = collect()
    assert sample['metrics']['gpu_util_percent']['status'] == 'error'
    assert sample['metrics']['gpu_util_percent']['reason'] == 'query_timeout'
    checks.append('gpu_query_timeout_is_error')
    result = {'date': utcnow(), 'synthetic': True, 'training_transitions': 0, 'passed': checks}
    output = ROOT / 'docs/specs/20261106-训练可视化工具/backend-checks.json'
    atomic_json(output, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
