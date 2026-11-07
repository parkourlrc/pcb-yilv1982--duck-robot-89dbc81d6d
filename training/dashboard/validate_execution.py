from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

from dashboard.config import ROOT, load_config
from dashboard.runs import ACTIVE, Runs
from dashboard.schemas import Execution, ResumeRequest, StartRequest, ValidationRequest
from dashboard.store import atomic_json, read_json, utcnow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['local', 'single_spark', 'dual_spark'])
    parser.add_argument('--run-id')
    args = parser.parse_args()
    config = load_config()
    config['data_dir'] = str(ROOT / 'training/.dashboard-validation' / args.mode)
    manager = Runs(ROOT, config)
    task = next(task for task in manager.registry.tasks() if task['task_id'] == 'locomotion' and task['task_version'] == 'v2')
    request = ValidationRequest(task_id=task['task_id'], task_version=task['task_version'], execution=Execution(mode=args.mode, node_ids=['spark1'] if args.mode == 'single_spark' else []),
                                parameters={'num_envs': 16, 'num_steps_per_env': 4, 'max_updates': 3, 'save_interval': 1, 'eval_interval': 2 if args.mode == 'local' else 100, 'seed': 42})
    validation = manager.validate(request)
    if not validation['valid']:
        raise ValueError(validation['errors'])
    record = {'mode': args.mode, 'started_utc': utcnow(), 'budget_transitions': 192, 'runs': []}
    output = ROOT / f'docs/specs/20261106-训练可视化工具/checks/backend-e2e-{args.mode}.json'
    for executor in manager.executors.values():
        original_launch = executor.launch
        def launch(job, directory, original=original_launch):
            if '--resume-manifest' not in job['argv']:
                job['argv'] += ['--max-new-updates', '2']
            return original(job, directory)
        executor.launch = launch
    initial = manager.get(args.run_id) if args.run_id else manager.start(StartRequest(request_id='validation-' + uuid.uuid4().hex, validation_id=validation['validation_id'], config_hash=validation['config_hash'], name='工具验收 ' + args.mode))

    def wait(run):
        deadline = time.monotonic() + 900
        last = None
        while run['state'] in ACTIVE and time.monotonic() < deadline:
            time.sleep(3)
            try:
                run = manager.refresh(run['run_id'])
            except Exception as error:
                print(json.dumps({'refresh_error': str(error)}), flush=True)
                continue
            status = (run['state'], run['model_iteration'], run['connection']['state'])
            if status != last:
                print(json.dumps({'run_id': run['run_id'], 'status': status, 'failure': run.get('failure')}), flush=True)
                last = status
        record['runs'].append(manager.public(run))
        atomic_json(output, record)
        if run['state'] in ACTIVE:
            manager.stop(run['run_id'])
            raise TimeoutError('验收达到15分钟观察上限，已请求停止')
        if run['state'] == 'failed':
            raise RuntimeError(run.get('failure'))
        return run

    initial = wait(initial)
    assert initial['budget']['consumed_transitions'] == 128
    checkpoints = [item for item in manager.store.all('checkpoint') if item['run_id'] == initial['run_id'] and item['resumable'] and 'final_' in item['checkpoint_id']]
    selected = max(checkpoints, key=lambda item: item['model_iteration'])
    resumed = manager.resume(initial['run_id'], ResumeRequest(request_id='resume-' + uuid.uuid4().hex, checkpoint_id=selected['checkpoint_id']))
    resumed = wait(resumed)
    assert resumed['budget']['consumed_transitions'] == 192 and resumed['budget']['remaining_transitions'] == 0
    record.update(completed_utc=utcnow(), passed=True, consumed_transitions=192)
    atomic_json(output, record)
    print(json.dumps({'mode': args.mode, 'passed': True, 'consumed_transitions': 192}), flush=True)


if __name__ == '__main__':
    main()
