from __future__ import annotations

import json
import shutil
import shlex
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from .executors import Executor
from .history import checkpoint_info, import_history, metrics
from .registry import Registry, digest, file_hash
from .store import Store, atomic_json, read_json, read_jsonl, utcnow


ACTIVE = {'preparing', 'initializing', 'training', 'evaluating', 'saving', 'stopping', 'running'}


class DashboardError(Exception):
    def __init__(self, message, code='invalid_request', status=400):
        super().__init__(message)
        self.code, self.status = code, status


class Runs:
    def __init__(self, root, config):
        self.root, self.config = Path(root), config
        self.data = Path(config['data_dir'])
        self.data.mkdir(parents=True, exist_ok=True)
        self.store = Store(self.data / 'index.sqlite')
        self.registry = Registry(root)
        self.lock = threading.RLock()
        self.heartbeat_observations = {}
        self.recovered_runs = set()
        self.executors = {name: Executor(name, node) for name, node in config['nodes'].items()}
        for path in (self.data / 'runs').glob('*/dashboard-run.json'):
            run = read_json(path)
            if run:
                self.store.put('run', run['run_id'], run)
                if not self.store.events(run['run_id']):
                    events, _ = read_jsonl(Path(run['_directory']) / 'events.jsonl')
                    for event in events:
                        self.store.event(run['run_id'], event)
                for manifest in (Path(run['_directory']) / 'checkpoints').glob('*/manifest.json'):
                    checkpoint = checkpoint_info(manifest, run['run_id'], run['run_id'] + '-' + manifest.parent.name)
                    if checkpoint:
                        self.store.put('checkpoint', checkpoint['checkpoint_id'], checkpoint)
                request_record = run.get('_request_record')
                if request_record and not self.store.request(request_record['request_id']):
                    self.store.remember(request_record['request_id'], request_record['fingerprint'], 'run', run['run_id'])
        import_history(root, self.store)
        for run in self.store.all('run'):
            if run.get('managed') and run['state'] in ACTIVE:
                self.recovered_runs.add(run['run_id'])
            if run.get('managed') and run['state'] == 'preparing' and not run.get('_locations'):
                run.update(state='failed', failure='服务在提交远端作业前中断；未启动训练，请重新创建', _launch_failed=True)
                run['capabilities']['stop']['allowed'] = False
                self.save(run)
            elif run.get('managed') and run['state'] == 'stopping' and not run.get('_locations'):
                run.update(state='stopped', failure=None)
                run['capabilities']['stop']['allowed'] = False
                self.save(run)

    def public(self, value):
        if isinstance(value, dict):
            return {key: self.public(item) for key, item in value.items() if not key.startswith('_')}
        if isinstance(value, list):
            return [self.public(item) for item in value]
        return value

    def save(self, run):
        with self.lock:
            previous = self.store.get('run', run['run_id'])
            if previous and previous.get('_stop_requested'):
                run['_stop_requested'] = True
                if run['state'] in ACTIVE and not run.get('_launch_failed'):
                    run['state'] = 'stopping'
            self.store.put('run', run['run_id'], run)
            if run['managed']:
                atomic_json(self.data / 'runs' / run['run_id'] / 'dashboard-run.json', run)
        return run

    def get(self, identifier):
        run = self.store.get('run', identifier)
        if not run:
            raise DashboardError('运行不存在', 'not_found', 404)
        return run

    def validate(self, request):
        task = self.registry.get(request.task_id, request.task_version)
        if not task:
            raise DashboardError('任务或版本不存在', 'task_not_found', 404)
        from mjlab_duck.locomotion_train_cfg import LocomotionTrainConfig
        parameters = LocomotionTrainConfig().as_dict()
        defaults = task.get('default_execution', {})
        parameters.update({key: value for key, value in defaults.items() if key in parameters})
        editable = {'num_envs', 'num_steps_per_env', 'max_updates', 'save_interval', 'eval_interval', 'seed'}
        errors = []
        for name, value in request.parameters.items():
            if name not in editable:
                errors.append({'field': name, 'message': '此字段不可编辑'})
            elif isinstance(value, bool) or not isinstance(value, int) or (value < 1 and name != 'seed') or value < 0:
                errors.append({'field': name, 'message': '参数必须是有效非负/正整数'})
            else:
                parameters[name] = value
        execution = request.execution.model_dump()
        nodes = execution['node_ids']
        if execution['mode'] == 'local':
            nodes = ['local']
        elif execution['mode'] == 'dual_spark':
            nodes = ['spark1', 'spark2']
        elif len(nodes) != 1 or nodes[0] not in ('spark1', 'spark2'):
            errors.append({'field': 'node_ids', 'message': '单Spark必须选择spark1或spark2'})
        world_size = len(nodes)
        execution.update(node_ids=nodes, world_size=world_size)
        if world_size and parameters['num_envs'] % world_size:
            errors.append({'field': 'num_envs', 'message': '环境数必须可按节点均分'})
        if world_size and (parameters['num_envs'] // world_size * parameters['num_steps_per_env']) % parameters['num_mini_batches']:
            errors.append({'field': 'num_envs', 'message': '每rank样本数必须整除mini-batch数'})
        try:
            LocomotionTrainConfig.from_dict(parameters)
        except (ValueError, TypeError) as error:
            errors.append({'field': 'parameters', 'message': str(error)})
        if task.get('availability', {}).get('state') != 'ready':
            errors.append({'field': 'task', 'message': '任务依赖尚未准备好'})
        budget = {'transitions_per_update': parameters['num_envs'] * parameters['num_steps_per_env'],
                  'max_transitions': parameters['num_envs'] * parameters['num_steps_per_env'] * parameters['max_updates']}
        result = {'valid': not errors, 'validation_id': uuid.uuid4().hex, 'config_hash': digest(parameters),
                  'resolved_config': parameters, 'execution': execution, 'allocation': [{'node_id': name, 'rank': rank, 'num_envs': parameters['num_envs'] // max(1, world_size)} for rank, name in enumerate(nodes)],
                  'budget': budget, 'errors': errors, 'warnings': [], '_task': task, '_created': time.time()}
        self.store.put('validation', result['validation_id'], result)
        return self.public(result)

    def duplicate(self, request_id, fingerprint):
        previous = self.store.request(request_id)
        if previous:
            if previous[0] != fingerprint:
                raise DashboardError('request_id已用于其他请求', 'idempotency_conflict', 409)
            return self.store.get(previous[1], previous[2])
        return None

    def start(self, request):
        with self.lock:
            fingerprint = digest(request.model_dump())
            previous = self.duplicate(request.request_id, fingerprint)
            if previous:
                return previous
            validation = self.store.get('validation', request.validation_id)
            if not validation or not validation['valid'] or time.time() - validation['_created'] > 1800 or request.config_hash != validation['config_hash']:
                raise DashboardError('校验已失效，请重新校验', 'validation_expired', 409)
            if any(run['state'] in ACTIVE and run['managed'] for run in self.store.all('run')):
                raise DashboardError('已有活动训练作业', 'active_run', 409)
            identifier = uuid.uuid4().hex
            directory = self.data / 'runs' / identifier
            run = {'run_id': identifier, 'experiment_id': uuid.uuid4().hex, 'name': request.name,
                   'task_id': validation['_task']['task_id'], 'task_version': validation['_task']['task_version'],
                   'parent_run_id': None, 'parent_checkpoint_id': None, 'managed': True, 'read_only': False,
                   'state': 'preparing', 'connection': {'state': 'connected', 'last_seen_utc': utcnow()}, 'stage': 1,
                   'model_iteration': 0, 'budget': {**validation['budget'], 'consumed_transitions': 0, 'remaining_transitions': validation['budget']['max_transitions']},
                   'execution': validation['execution'], 'config': validation['resolved_config'], 'created_utc': utcnow(),
                   'elapsed_s': None, 'eta_s': None, 'latest_checkpoint_id': None, 'failure': None,
                   'capabilities': {'stop': {'allowed': True, 'reasons': []}, 'resume': {'allowed': False, 'reasons': ['运行尚未结束']}},
                   '_directory': str(directory / 'cache' / 'rank0' / 'run'), '_task': validation['_task'],
                   '_request_record': {'request_id': request.request_id, 'fingerprint': fingerprint}}
            self.save(run)
            self.store.remember(request.request_id, fingerprint, 'run', identifier)
            threading.Thread(target=self._prepare_launch, args=(identifier,), daemon=True).start()
            return run

    def _snapshot(self, run):
        snapshot = self.data / 'runs' / run['run_id'] / 'project'
        if run.get('parent_run_id'):
            source = self.data / 'runs' / run['parent_run_id'] / 'project'
            shutil.copytree(source, snapshot)
            return snapshot
        for name, expected in run['_task'].get('source_hashes', {}).items():
            if file_hash(self.root / name) != expected:
                raise DashboardError('任务来源已改变，请重新确认任务版本', 'source_changed', 409)
        paths = list((self.root / 'training/mjlab_duck').glob('*.py')) + list((self.root / 'training/dashboard').glob('*.py')) + list((self.root / 'training/dashboard/executors').glob('*.py'))
        paths += list((self.root / 'training/models').glob('*.xml')) + list((self.root / 'training/params').glob('*.json'))
        hashes = {}
        for source in paths:
            relative = source.relative_to(self.root)
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            hashes[str(relative).replace('\\', '/')] = file_hash(target)
        atomic_json(snapshot / 'source-manifest.json', hashes)
        atomic_json(snapshot / 'config.json', run['config'])
        atomic_json(snapshot / 'task.json', run['_task'])
        return snapshot

    def _prepare_launch(self, identifier):
        run = self.get(identifier)
        try:
            snapshot = self._snapshot(run)
            nodes = run['execution']['node_ids']
            locations = {}
            for name in nodes:
                self.executors[name].probe()
            if len(nodes) == 2 and not self.config['nodes'][nodes[0]].get('master_addr'):
                raise ValueError('双Spark缺master_addr配置')
            for name in nodes:
                node = self.config['nodes'][name]
                directory = node['work_root'].rstrip('/') + '/' + identifier
                self.executors[name].prepare(snapshot, directory)
                locations[name] = directory
            if self.get(identifier).get('_stop_requested'):
                run.update(state='stopped', _stop_requested=True)
                self.save(run)
                return
            run['_locations'] = locations
            run['_experiment_locations'] = run.get('_experiment_locations') or {name: directory + '/experiment' for name, directory in locations.items()}
            for name in nodes:
                self.executors[name].shell('mkdir -p ' + shlex.quote(run['_experiment_locations'][name]))
            run['state'] = 'initializing'
            self.save(run)
            port = 30000 + int(identifier[:4], 16) % 20000
            for rank, name in enumerate(nodes):
                node, directory = self.config['nodes'][name], locations[name]
                if node['kind'] == 'wsl':
                    base, python = directory, node['python']
                else:
                    base, python = '/work', '/bench/venv/bin/python'
                arguments = [python]
                if len(nodes) == 2:
                    master = self.config['nodes'][nodes[0]].get('master_addr')
                    if not master:
                        raise ValueError('双Spark缺master_addr配置')
                    arguments += ['-m', 'torch.distributed.run', '--nnodes=2', '--nproc-per-node=1', f'--node-rank={rank}', f'--master-addr={master}', f'--master-port={port}', '--max-restarts=0']
                arguments += ['-m', 'mjlab_duck.train_locomotion', '--config', base + '/project/config.json', '--run-id', identifier,
                              '--output', base + '/run', '--experiment-dir', '/experiment' if node['kind'] == 'ssh' else run['_experiment_locations'][name], '--stop-file', base + '/STOP']
                if run.get('_resume_manifest'):
                    arguments += ['--resume-manifest', '/resume/' + Path(run['_resume_manifest']).parent.name + '/manifest.json' if node['kind'] == 'ssh' else run['_resume_remote_manifest']]
                if node['kind'] == 'ssh':
                    arguments = ['sudo', '-n', 'docker', 'run', '--name', 'duck-dashboard-' + identifier + '-' + str(rank), '--gpus', 'all', '--network', 'host', '--ipc', 'host', '--device', '/dev/infiniband', '--ulimit', 'memlock=-1', '--ulimit', 'stack=67108864', '--env-file', node['env_file'], '--env', 'PYTHONUNBUFFERED=1', '-v', node['benchmark_root'] + ':/bench:ro', '-v', directory + ':/work', '--workdir', '/work/project/training', '--entrypoint', python, node.get('image', 'nvcr.io/nvidia/pytorch:25.10-py3')] + arguments[1:]
                    image_index = arguments.index(node.get('image', 'nvcr.io/nvidia/pytorch:25.10-py3'))
                    arguments[image_index:image_index] = ['-v', run['_experiment_locations'][name] + ':/experiment']
                    if run.get('_resume_manifest'):
                        arguments[image_index:image_index] = ['-v', str(Path(run['_resume_remote_manifest']).parent.parent).replace('\\', '/') + ':/resume:ro']
                if self.get(identifier).get('_stop_requested'):
                    raise RuntimeError('准备期间收到停止请求')
                job = {'job_id': identifier, 'directory': directory, 'cwd': directory + '/project/training', 'argv': arguments, 'env': {'PYTHONUNBUFFERED': '1'}}
                self.executors[name].launch(job, directory)
            self.store.event(identifier, {'type': 'started', 'message': '训练监督进程已启动'})
        except Exception as error:
            run = self.get(identifier)
            cleanup_ok = True
            for rank, (name, directory) in enumerate(run.get('_locations', {}).items()):
                try:
                    self.executors[name].write_json(directory + '/STOP', {'reason': 'launch_failed'})
                    self.executors[name].terminate(directory, 'duck-dashboard-' + identifier + '-' + str(rank) if self.config['nodes'][name]['kind'] == 'ssh' else None)
                except Exception:
                    cleanup_ok = False
            run.update(state='failed' if cleanup_ok else 'stopping', failure=str(error), _launch_failed=True)
            self.save(run)
            self.store.event(identifier, {'type': 'failed', 'level': 'error', 'message': str(error)})

    def stop(self, identifier):
        run = self.get(identifier)
        if not run['managed']:
            raise DashboardError('只读导入运行不能停止', 'read_only', 409)
        if run['state'] not in ACTIVE:
            return run
        run['state'] = 'stopping'
        run['_stop_requested'] = True
        self.save(run)
        errors = {}
        for name, directory in run.get('_locations', {}).items():
            try:
                self.executors[name].write_json(directory + '/STOP', {'run_id': identifier, 'requested_utc': utcnow()})
            except Exception as error:
                errors[name] = str(error)
        run['_stop_delivery_errors'] = errors
        return self.save(run)

    def resume(self, identifier, request):
        with self.lock:
            fingerprint = digest({'parent': identifier, **request.model_dump()})
            previous = self.duplicate(request.request_id, fingerprint)
            if previous:
                return previous
            original = self.get(identifier)
            if original['budget']['remaining_transitions'] <= 0:
                raise DashboardError('原实验预算已耗尽', 'budget_exhausted', 409)
            if not original['managed'] or original['state'] in ACTIVE:
                raise DashboardError('该运行当前不能续训', 'resume_unavailable', 409)
            if any(run['managed'] and run['state'] in ACTIVE for run in self.store.all('run')):
                raise DashboardError('已有活动训练作业', 'active_run', 409)
            checkpoint = self.store.get('checkpoint', request.checkpoint_id)
            if not checkpoint or checkpoint['run_id'] != identifier or not checkpoint['resumable']:
                raise DashboardError('必须选择本运行完整checkpoint', 'checkpoint_incomplete', 409)
            manifest = read_json(checkpoint['_manifest'])
            if manifest.get('resumable') is False:
                raise DashboardError(manifest.get('resume_reason', '检查点课程决策尚未应用'), 'checkpoint_not_resumable', 409)
            if manifest['world_size'] != original['execution']['world_size']:
                raise DashboardError('恢复节点拓扑不兼容', 'world_size_mismatch', 409)
            run = json.loads(json.dumps(original))
            new_id = uuid.uuid4().hex
            run.update(run_id=new_id, parent_run_id=identifier, parent_checkpoint_id=request.checkpoint_id,
                       name=original['name'] + ' · 续训', state='preparing', created_utc=utcnow(), failure=None,
                       _directory=str(self.data / 'runs' / new_id / 'cache/rank0/run'), _event_count=0,
                       _request_record={'request_id': request.request_id, 'fingerprint': fingerprint},
                       _stop_requested=False, _resume_manifest=checkpoint['_manifest'],
                       _resume_remote_manifest=original['_locations'][original['execution']['node_ids'][0]] + '/run/checkpoints/' + Path(checkpoint['_manifest']).parent.name + '/manifest.json')
            run.pop('_locations', None)
            run.pop('_cached_manifest_count', None)
            run.pop('_last_cache_error', None)
            run.pop('_launch_failed', None)
            self.save(run)
            self.store.remember(request.request_id, fingerprint, 'run', new_id)
            threading.Thread(target=self._prepare_launch, args=(new_id,), daemon=True).start()
            return run

    def refresh(self, identifier):
        run = self.get(identifier)
        if not run['managed'] or run['state'] not in ACTIVE:
            return run
        if run.get('_stop_requested'):
            run = self.stop(identifier)
        states, disconnected, stale = {}, [], []
        locations = run.get('_locations', {})
        def synchronize(rank, name, remote):
            cache = self.data / 'runs' / identifier / 'cache' / f'rank{rank}'
            self.executors[name].sync_run(remote, cache)
            state = read_json(cache / 'supervisor.json', {})
            if not state and (identifier in self.recovered_runs or run.get('_launch_failed')) and not self.executors[name].job_alive(remote):
                return {'state': 'failed', 'error': '服务重启后未发现监督或训练进程'}
            return state
        with ThreadPoolExecutor(max_workers=max(1, len(locations))) as pool:
            pending = {pool.submit(synchronize, rank, name, remote): name for rank, (name, remote) in enumerate(locations.items())}
            for future in as_completed(pending):
                name = pending[future]
                try:
                    state = future.result()
                    states[name] = state
                    if state.get('state') not in ('completed', 'failed'):
                        heartbeat = state.get('heartbeat_utc', state.get('started_utc'))
                        observation_key = (identifier, name)
                        observed = self.heartbeat_observations.get(observation_key)
                        if not observed or observed[0] != heartbeat:
                            observed = (heartbeat, time.monotonic())
                            self.heartbeat_observations[observation_key] = observed
                        age = time.monotonic() - observed[1] if observed else float('inf')
                        if age > 15:
                            if not self.executors[name].job_alive(locations[name]):
                                states[name] = {'state': 'failed', 'error': '监督心跳停止且未发现同作业进程'}
                            else:
                                stale.append(name)
                except Exception:
                    disconnected.append(name)
        if not states:
            if disconnected:
                run['connection'] = {'state': 'disconnected', 'nodes': disconnected, 'last_seen_utc': run['connection'].get('last_seen_utc')}
                return self.save(run)
            return run
        run['connection'] = {'state': 'disconnected' if disconnected else 'stale' if stale else 'connected', 'nodes': disconnected + stale, 'last_seen_utc': utcnow() if not disconnected and not stale else run['connection'].get('last_seen_utc')}
        failed_nodes = [name for name, state in states.items() if state.get('state') == 'failed']
        if failed_nodes:
            run.update(state='stopping', _stop_requested=True, failure='训练节点非零退出；正在停止同作业其余节点: ' + ', '.join(failed_nodes))
            self.save(run)
            for rank, (name, remote) in enumerate(locations.items()):
                if states.get(name, {}).get('state') not in ('completed', 'failed'):
                    try:
                        self.executors[name].write_json(remote + '/STOP', {'run_id': identifier})
                        self.executors[name].terminate(remote, 'duck-dashboard-' + identifier + '-' + str(rank) if self.config['nodes'][name]['kind'] == 'ssh' else None)
                    except Exception:
                        pass
            if len(states) == len(locations) and all(state.get('state') in ('completed', 'failed') for state in states.values()):
                run['state'] = 'failed'
        if disconnected:
            return self.save(run)
        directory = Path(run['_directory'])
        updates, _ = read_jsonl(directory / 'updates.jsonl')
        if updates:
            last = updates[-1]
            run.update(model_iteration=last['model_iteration'], stage=last['stage'], elapsed_s=last.get('elapsed_s'))
            run['budget'].update(consumed_transitions=last['consumed_transitions'], remaining_transitions=last['remaining_transitions'])
        events, _ = read_jsonl(directory / 'events.jsonl')
        for event in events[run.get('_event_count', 0):]:
            self.store.event(identifier, event)
        run['_event_count'] = len(events)
        ledger, ledger_warnings = read_jsonl(directory.parent / 'experiment/budget.jsonl')
        reservations = {item.get('reservation') for item in ledger if item.get('event') == 'begin'}
        if reservations and not ledger_warnings:
            consumed = len(reservations) * run['budget']['transitions_per_update']
            run['budget'].update(consumed_transitions=consumed, remaining_transitions=max(0, run['budget']['max_transitions'] - consumed))
        actual_experiment = read_json(directory.parent / 'experiment/experiment.json', {})
        if actual_experiment.get('id'):
            run['experiment_id'] = actual_experiment['id']
        elif run.get('_experiment_locations'):
            first = run['execution']['node_ids'][0]
            remote_experiment = self.executors[first].read_json(run['_experiment_locations'][first] + '/experiment.json')
            if remote_experiment:
                run['experiment_id'] = remote_experiment['id']
        first = run['execution']['node_ids'][0]
        if run.get('parent_run_id') and run.get('_experiment_locations'):
            ledger = self.executors[first].read_jsonl(run['_experiment_locations'][first] + '/budget.jsonl')
            if ledger is not None:
                reservations = {item.get('reservation') for item in ledger if item.get('event') == 'begin'}
                consumed = len(reservations) * run['budget']['transitions_per_update']
                run['budget'].update(consumed_transitions=max(consumed, run['budget']['consumed_transitions']), remaining_transitions=max(0, run['budget']['max_transitions'] - max(consumed, run['budget']['consumed_transitions'])))
        if events and run['state'] != 'stopping' and not failed_nodes:
            phase = events[-1].get('phase', 'training')
            run['state'] = {'collecting': 'training', 'updating': 'training', 'completed': 'saving', 'stopped': 'stopping', 'failed': 'stopping'}.get(phase, phase if phase in ACTIVE else 'training')
        if not failed_nodes and len(states) == len(locations) and all(state.get('state') == 'completed' for state in states.values()):
            result = read_json(directory / 'result.json')
            if result:
                run.update(state='stopped' if result['status'] == 'interrupted_at_update_boundary' else 'completed', completion_reason=result['status'], elapsed_s=result.get('wall_seconds_including_evaluation_and_checkpoint'))
                run['budget'].update(consumed_transitions=result['consumed_transitions'], remaining_transitions=max(0, run['budget']['max_transitions'] - result['consumed_transitions']))
            else:
                run.update(state='failed', failure='进程退出但缺少完成记录')
        manifests = list((directory / 'checkpoints').glob('*/manifest.json'))
        cache_missing = any((checkpoint_info(manifest, identifier, identifier + '-' + manifest.parent.name) or {}).get('integrity') != 'complete' for manifest in manifests)
        if manifests and (run.get('_cached_manifest_count') != len(manifests) or cache_missing):
            first = run['execution']['node_ids'][0]
            try:
                self.executors[first].cache_checkpoints(run['_locations'][first], directory / 'checkpoints')
                run['_cached_manifest_count'] = len(manifests)
                run.pop('_last_cache_error', None)
            except Exception as error:
                run['_last_cache_error'] = str(error)
        if len(updates) >= 3:
            measured = [row for row in updates if row.get('elapsed_s') is not None]
            if len(measured) >= 3 and measured[-1]['elapsed_s'] > measured[0]['elapsed_s']:
                speed = (measured[-1]['consumed_transitions'] - measured[0]['consumed_transitions']) / (measured[-1]['elapsed_s'] - measured[0]['elapsed_s'])
                if speed > 0 and run['state'] in ACTIVE:
                    run['eta_s'] = run['budget']['remaining_transitions'] / speed
                    run['eta_status'] = 'estimate_including_observed_overhead'
        for manifest in manifests:
            checkpoint_id = identifier + '-' + manifest.parent.name
            checkpoint = checkpoint_info(manifest, identifier, checkpoint_id)
            if checkpoint:
                report = read_json(directory / f"evaluation_{checkpoint['model_iteration']:06d}.json")
                if report and Path(report.get('checkpoint', '')).parent.name == manifest.parent.name:
                    checkpoint['evaluations'] = [report]
                self.store.put('checkpoint', checkpoint_id, checkpoint)
                if checkpoint['model_iteration'] == run['model_iteration']:
                    run['latest_checkpoint_id'] = checkpoint_id
        run['capabilities']['stop']['allowed'] = run['state'] in ACTIVE
        if run['state'] in ('completed', 'stopped') and (not manifests or not all(self.store.get('checkpoint', identifier + '-' + manifest.parent.name)['integrity'] == 'complete' for manifest in manifests)):
            run.update(state='saving', failure='等待完整checkpoint缓存校验')
        resumable = run['state'] not in ACTIVE and run['budget']['remaining_transitions'] > 0 and any(item['resumable'] for item in self.store.all('checkpoint') if item['run_id'] == identifier)
        run['capabilities']['resume'] = {'allowed': resumable, 'reasons': [] if resumable else ['需剩余预算、终态及完整rank缓存']}
        return self.save(run)

    def metric_series(self, identifier, max_points=1000, keys=None):
        return metrics(self.get(identifier), max_points, keys)
