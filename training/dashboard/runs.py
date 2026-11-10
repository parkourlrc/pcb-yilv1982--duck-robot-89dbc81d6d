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

from .archive import Archive, config_diff, workflow_for
from .executors import Executor
from .history import checkpoint_info, metrics
from .registry import Registry, digest, file_hash
from .store import Store, atomic_json, read_json, read_jsonl, utcnow


ACTIVE = {'preparing', 'initializing', 'training', 'evaluating', 'saving', 'stopping', 'running'}
LEGACY_EDITABLE = ['num_envs', 'num_steps_per_env', 'max_updates', 'save_interval', 'diagnostic_interval', 'seed', 'learning_rate', 'gamma', 'lam', 'desired_kl', 'num_learning_epochs', 'num_mini_batches', 'entropy_coef', 'value_loss_coef', 'clip_param', 'max_grad_norm', 'init_std']


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
        self.archive = Archive(root, config.get('artifact_dir', self.data / 'artifacts'))
        self.archive.export_records = config.get('export_records', True)
        self.artifacts = self.archive.directory
        self.registry = Registry(root, self.artifacts / 'tasks')
        self.lock = threading.RLock()
        self.heartbeat_observations = {}
        self.archive_retry_times = {}
        self.recovered_runs = set()
        self.executors = {name: Executor(name, node) for name, node in config['nodes'].items()}
        from .environment_probe import ensure_scripts
        self.probe_scripts = ensure_scripts(self.data, config['nodes'])
        from .identity import detect_host, match_environment
        self.host = detect_host()
        self.self_id, self.identity_report = match_environment(config['nodes'], self.host)
        if not any(isinstance(node, dict) and node.get('identity') for node in config['nodes'].values()):
            self.self_id = 'local'
            self.identity_report = {**self.identity_report, 'state': 'unconfigured', 'detail': '旧配置未登记环境身份，按 local 继续'}
            self.identity_report['matches'] = ['local']
        for path in (self.data / 'runs').glob('*/dashboard-run.json'):
            run = read_json(path)
            if run and not (self.archive.run_root(run['run_id']) / 'dashboard-run.json').exists():
                self.archive.migrate(run, path.parent)
        self.archive.restore(self.store)
        canonical_ids = {path.stem for path in (self.root / 'training/records').glob('*.json')
                         if read_json(path, {}).get('record_kind') == 'training-run'}
        for run in self.store.all('run'):
            if run['run_id'] not in canonical_ids:
                self.store.delete('run', run['run_id'])
        for path in (self.artifacts / 'runs').glob('*/dashboard-run.json'):
            run = read_json(path)
            canonical = self.archive.record_path(run.get('run_id')) if run and run.get('run_id') else None
            document = read_json(canonical, {}) if canonical else {}
            if run and document.get('record_kind') == 'training-run':
                self.store.put('run', run['run_id'], run)
                safe_directory = self.archive.source_directory(run)
                if safe_directory and not self.store.events(run['run_id']):
                    events, _ = read_jsonl(safe_directory / 'events.jsonl')
                    for event in events:
                        self.store.event(run['run_id'], event)
                for manifest in safe_directory.rglob('manifest.json') if safe_directory else []:
                    checkpoint = checkpoint_info(manifest, run['run_id'], run['run_id'] + '-' + manifest.parent.name)
                    if checkpoint:
                        self.store.put('checkpoint', checkpoint['checkpoint_id'], checkpoint)
                request_record = run.get('_request_record')
                if request_record and not self.store.request(request_record['request_id']):
                    self.store.remember(request_record['request_id'], request_record['fingerprint'], 'run', run['run_id'])
        # Do not scan docs/specs, docs/references or training/logs here.  The
        # canonical training/records documents are the only dashboard input.
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
            if run.get('workflow'):
                for step in run['workflow']['steps']:
                    if step['number'] == 5:
                        step.update(status='completed' if run['state'] == 'completed' else 'interrupted' if run['state'] in ('failed', 'stopped') else 'in_progress',
                                    outputs=['run.json', 'updates.jsonl', 'checkpoints', 'result.json'], evidence=['dashboard-run.json'])
            self.store.put('run', run['run_id'], run)
            self.archive.save(run)
            if run.get('managed') and run['state'] in ('completed', 'stopped', 'failed') and not run.get('_archive_pending'):
                self.archive.seal(run)
        return run

    def get(self, identifier):
        run = self.store.get('run', identifier)
        if not run:
            raise DashboardError('运行不存在', 'not_found', 404)
        return run

    def catalog(self):
        from mjlab_duck.experiment_config import parameter_catalog
        result = parameter_catalog()
        result.update(default_rewards=result['defaults']['reward_config'], presets=result['reward_presets'], locked_fields=result.get('locked', []))
        return result

    def import_history(self):
        """Rebuild the SQLite index from canonical process-produced documents."""
        report = {'schema': 1, 'source': 'training/records', 'imported': self.archive.restore(self.store)}
        return report

    def archive_detail(self, identifier):
        run = self.get(identifier)
        checkpoints = [item for item in self.store.all('checkpoint') if item['run_id'] == identifier]
        from mjlab_duck.experiment_config import transfer_contract
        expected_transfer = transfer_contract(self.root)
        run['_warm_compatible'] = any(read_json(item['_manifest'], {}).get('transfer_contract') == expected_transfer and item.get('replayable') for item in checkpoints)
        integrity, capabilities, entries = self.archive.inspect(run, checkpoints)
        parent = self.store.get('run', run.get('parent_run_id', '')) or {}
        workflow = run.get('workflow') or {'steps': [], 'current_step': None, 'missing': '历史流程证据未完整登记'}
        result = {'run_id': identifier, 'workflow': workflow, 'config': run.get('config', {}),
                  'config_diff': config_diff(parent.get('config', {}), run.get('config', {})) if parent else [],
                  'reward_design': {'config': run.get('config', {}).get('reward_config'),
                                    'documents': [{'label': Path(item['path']).name, **{key: item[key] for key in ('path', 'artifact_id', 'url')}} for item in entries if '/record-documents/' in item['path'] or item['path'].endswith(('/locomotion_env.py', '/reward_runtime.py'))],
                                    'catalog': self.catalog()['reward_terms'] if run.get('task_version') == 'v3' else [],
                                    'version': 'rewards-v1' if run.get('task_version') == 'v3' else '历史实现；结构化设计待补充'},
                  'artifacts': entries, 'integrity': integrity, 'capabilities': capabilities,
                  'provenance': run.get('provenance', {}), 'initialization': run.get('initialization'),
                  'parent_run_id': run.get('parent_run_id'), 'parent_checkpoint_id': run.get('parent_checkpoint_id')}
        return self.public(result)

    def record_resource(self, node_id, sample):
        for run in self.store.all('run'):
            if run.get('managed') and run['state'] in ACTIVE and node_id in run.get('execution', {}).get('node_ids', []):
                path = self.archive.run_root(run['run_id']) / 'resources.jsonl'
                with path.open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps({'node_id': node_id, **sample}, allow_nan=False) + '\n')

    def artifact_path(self, identifier, artifact_id):
        for item in self.archive.entries(self.get(identifier)):
            if item['artifact_id'] == artifact_id:
                return Path(item['_path'])
        raise DashboardError('归档文件不存在', 'artifact_not_found', 404)

    def derive(self, identifier, request):
        run = self.get(identifier)
        detail = self.archive_detail(identifier)
        capability = detail['capabilities'][request.mode]
        if not capability['allowed']:
            raise DashboardError('；'.join(capability['reasons']), 'derivation_unavailable', 409)
        checkpoint_id = request.checkpoint_id
        if request.mode == 'warm':
            checkpoint = self.store.get('checkpoint', checkpoint_id or '')
            if not checkpoint or checkpoint['run_id'] != identifier or not checkpoint.get('replayable'):
                raise DashboardError('请选择该运行完整rank0检查点', 'checkpoint_incomplete', 409)
        return {'task_id': run['task_id'], 'task_version': run['task_version'], 'source_run_id': identifier,
                'initialization': request.mode, 'checkpoint_id': checkpoint_id if request.mode == 'warm' else None,
                'parameters': run['config'], 'execution': {key: value for key, value in run['execution'].items() if key in ('mode', 'node_ids')} if run['execution'].get('mode') in ('local', 'single_spark', 'dual_spark') else {'mode': 'local', 'node_ids': ['local']},
                'name': run['name'] + (' · 接权重新实验' if request.mode == 'warm' else ' · 从零重训')}

    def validate(self, request):
        source = self.get(request.source_run_id) if request.source_run_id else None
        task = source.get('_task') if source and request.initialization == 'scratch' else self.registry.get(request.task_id, request.task_version)
        if not task:
            raise DashboardError('任务或版本不存在', 'task_not_found', 404)
        if task.get('legacy_adapter') and not source:
            raise DashboardError('旧版本必须从原运行档案派生，不能使用当前源码启动', 'legacy_source_required', 409)
        from mjlab_duck.experiment_config import resolve_config
        defaults = task.get('default_execution', {})
        errors = []
        if source:
            detail = self.archive_detail(source['run_id'])
            if request.task_id != source['task_id'] or (request.initialization == 'scratch' and request.task_version != source['task_version']):
                errors.append({'field': 'task_version', 'message': '来源任务版本与请求不一致'})
            if not detail['capabilities'][request.initialization]['allowed']:
                errors.append({'field': 'source_run_id', 'message': '来源冻结档案不完整或合同尚不兼容'})
            if request.initialization == 'scratch' and source.get('task_version') != task['task_version']:
                errors.append({'field': 'task_version', 'message': '从零复训必须保留来源任务及冻结运行时版本'})
            if source.get('task_id') != task['task_id']:
                errors.append({'field': 'task_id', 'message': '来源任务不匹配'})
            defaults = source.get('config') or defaults
        try:
            if task.get('legacy_adapter'):
                if set(request.parameters) - set(defaults):
                    raise ValueError('旧运行时不支持新增配置字段')
                changed = {key for key, value in request.parameters.items() if value != defaults.get(key)}
                if changed - set(LEGACY_EDITABLE):
                    raise ValueError('旧奖励/课程合同锁定；请使用原版本允许的训练字段')
                parameters = {**defaults, **request.parameters}
                resolve_config(parameters)
            else:
                parameters = resolve_config(request.parameters, base=defaults)
        except (ValueError, TypeError, KeyError) as error:
            errors.append({'field': 'parameters', 'message': str(error)})
            parameters = resolve_config()
        if request.initialization == 'warm':
            checkpoint = self.store.get('checkpoint', request.checkpoint_id or '')
            if not source or not checkpoint or checkpoint['run_id'] != source['run_id'] or not checkpoint.get('replayable'):
                errors.append({'field': 'checkpoint_id', 'message': '接权重训练需要来源运行的完整rank0检查点'})
            elif read_json(checkpoint['_manifest'], {}).get('transfer_contract') != __import__('mjlab_duck.experiment_config', fromlist=['transfer_contract']).transfer_contract(self.root):
                errors.append({'field': 'checkpoint_id', 'message': '来源物理、接口与网络合同尚未核验兼容'})
        execution = request.execution.model_dump()
        nodes = execution['node_ids']
        if execution['mode'] == 'local':
            nodes = ['local']
        elif execution['mode'] == 'dual_spark':
            nodes = ['spark1', 'spark2']
        elif len(nodes) != 1 or nodes[0] not in ('spark1', 'spark2'):
            errors.append({'field': 'node_ids', 'message': '单Spark必须选择spark1或spark2'})
        world_size = len(nodes)
        if 'local' in nodes and self.self_id != 'local':
            errors.append({'field': 'execution', 'message': '本机训练环境未登记：' + str((self.identity_report or {}).get('detail', '未匹配到本机环境')) + '；请先登记并搭建本机环境'})
        execution.update(node_ids=nodes, world_size=world_size)
        if task.get('legacy_adapter') and world_size != 2:
            errors.append({'field': 'execution', 'message': '旧v1正式入口要求双Spark，原运行时合同不变'})
        if world_size and parameters['num_envs'] % world_size:
            errors.append({'field': 'num_envs', 'message': '环境数必须可按节点均分'})
        if world_size and (parameters['num_envs'] // world_size * parameters['num_steps_per_env']) % parameters['num_mini_batches']:
            errors.append({'field': 'num_envs', 'message': '每rank样本数必须整除mini-batch数'})
        if (not source or request.initialization == 'warm') and task.get('availability', {}).get('state') != 'ready':
            errors.append({'field': 'task', 'message': '任务依赖尚未准备好'})
        budget = {'transitions_per_update': parameters['num_envs'] * parameters['num_steps_per_env'],
                  'max_transitions': parameters['num_envs'] * parameters['num_steps_per_env'] * parameters['max_updates']}
        workflow = workflow_for(task, parameters, budget, request.source_run_id)
        from experiment_archive import validate_workflow
        try:
            validate_workflow(workflow, parameters)
        except ValueError as error:
            errors.append({'field': 'workflow', 'message': str(error)})
        identity = {'config': parameters, 'task': task, 'execution': execution, 'source_run_id': request.source_run_id,
                    'initialization': request.initialization, 'checkpoint_id': request.checkpoint_id}
        result = {'valid': not errors, 'validation_id': uuid.uuid4().hex, 'config_hash': digest(identity),
                  'resolved_config': parameters, 'execution': execution, 'allocation': [{'node_id': name, 'rank': rank, 'num_envs': parameters['num_envs'] // max(1, world_size)} for rank, name in enumerate(nodes)],
                  'budget': budget, 'workflow': workflow, 'source_run_id': request.source_run_id,
                  'initialization': request.initialization, 'checkpoint_id': request.checkpoint_id,
                  'explicit_parameters': request.parameters if not errors else {},
                  'errors': errors, 'warnings': [], '_task': task, '_created': time.time()}
        self.store.put('validation', result['validation_id'], result)
        return self.public(result)

    def duplicate(self, request_id, fingerprint):
        previous = self.store.request(request_id)
        if previous:
            if previous[0] != fingerprint:
                raise DashboardError('request_id已用于其他请求', 'idempotency_conflict', 409)
            return self.store.get(previous[1], previous[2])
        return None

    def start(self, request, *, background=True):
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
            directory = self.artifacts / 'runs' / identifier
            run = {'run_id': identifier, 'experiment_id': uuid.uuid4().hex, 'name': request.name,
                   'task_id': validation['_task']['task_id'], 'task_version': validation['_task']['task_version'],
                   'parent_run_id': validation.get('source_run_id'), 'parent_checkpoint_id': validation.get('checkpoint_id'), 'managed': True, 'read_only': False,
                   'state': 'preparing', 'connection': {'state': 'connected', 'last_seen_utc': utcnow()}, 'stage': 1,
                   'model_iteration': 0, 'budget': {**validation['budget'], 'consumed_transitions': 0, 'remaining_transitions': validation['budget']['max_transitions']},
                   'execution': validation['execution'], 'config': validation['resolved_config'], 'created_utc': utcnow(),
                   'initialization': validation.get('initialization', 'scratch'), 'workflow': validation['workflow'],
                   'explicit_parameters': validation.get('explicit_parameters', {}), '_warm_compatible': True,
                   'elapsed_s': None, 'eta_s': None, 'latest_checkpoint_id': None, 'failure': None,
                   'capabilities': {'stop': {'allowed': True, 'reasons': []}, 'resume': {'allowed': False, 'reasons': ['运行尚未结束']}},
                   '_directory': str(directory / 'cache' / 'rank0' / 'run'), '_task': validation['_task'],
                   '_request_record': {'request_id': request.request_id, 'fingerprint': fingerprint}}
            self.save(run)
            self.store.remember(request.request_id, fingerprint, 'run', identifier)
            if background:
                threading.Thread(target=self._prepare_launch, args=(identifier,), daemon=True).start()
            return run

    def _snapshot(self, run):
        snapshot = self.artifacts / 'runs' / run['run_id'] / 'project'
        if run.get('_resume_manifest') or (run.get('parent_run_id') and run.get('initialization') == 'scratch'):
            parent = self.get(run['parent_run_id'])
            source = Path(parent.get('_runtime_root') or self.artifacts / 'runs' / run['parent_run_id'] / 'project')
            hashes = read_json(source / 'source-manifest.json') or read_json(source / 'manifest.json', {}).get('files', {})
            if not hashes or any(not (source / name).resolve().is_relative_to(source.resolve()) or not (source / name).is_file() or file_hash(source / name) != expected for name, expected in hashes.items()):
                raise DashboardError('来源冻结源码完整性校验失败', 'source_changed', 409)
            shutil.copytree(source, snapshot)
            for name in ('config.json', 'workflow.json'):
                if name in hashes:
                    shutil.copy2(snapshot / name, snapshot / ('parent-' + name))
            atomic_json(snapshot / 'config.json', run['config'])
            atomic_json(snapshot / 'workflow.json', run['workflow'])
            atomic_json(snapshot / 'parent-source-manifest.json', hashes)
            atomic_json(snapshot / 'source-manifest.json', {name: file_hash(snapshot / name) for name in hashes})
            if run['_task'].get('legacy_adapter'):
                for relative in ('training/experiment_archive.py', 'training/dashboard/legacy_runner.py', 'training/dashboard/executors/supervisor.py'):
                    destination = snapshot / relative
                    if not destination.exists():
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(self.root / relative, destination)
                atomic_json(snapshot / 'adapter-manifest.json', {relative: file_hash(snapshot / relative) for relative in ('training/experiment_archive.py', 'training/dashboard/legacy_runner.py', 'training/dashboard/executors/supervisor.py')})
                child_hashes = read_json(snapshot / 'source-manifest.json')
                child_hashes.update(read_json(snapshot / 'adapter-manifest.json'))
                atomic_json(snapshot / 'source-manifest.json', child_hashes)
            return snapshot
        for name, expected in run['_task'].get('source_hashes', {}).items():
            if file_hash(self.root / name) != expected:
                raise DashboardError('任务来源已改变，请重新确认任务版本', 'source_changed', 409)
        paths = list((self.root / 'training/mjlab_duck').glob('*.py')) + list((self.root / 'training/dashboard').glob('*.py')) + list((self.root / 'training/dashboard/executors').glob('*.py'))
        paths += list((self.root / 'training/models').glob('*.xml')) + list((self.root / 'training/params').glob('*.json'))
        paths += [self.root / 'training/experiment_archive.py']
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
        atomic_json(snapshot / 'workflow.json', run['workflow'])
        if run.get('initialization') == 'warm':
            checkpoint = self.store.get('checkpoint', run['parent_checkpoint_id'])
            manifest = read_json(checkpoint['_manifest'])
            source = Path(checkpoint['_manifest']).parent
            shutil.copytree(source, snapshot / 'initialization')
        return snapshot

    def _prepare_launch(self, identifier):
        run = self.get(identifier)
        if 'local' in run['execution']['node_ids'] and self.self_id != 'local':
            raise DashboardError('本机训练环境未登记：' + str((self.identity_report or {}).get('detail', '未匹配到本机环境')), 'local_environment_unregistered', 409)
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
                if run['_task'].get('legacy_adapter'):
                    module_index = arguments.index('mjlab_duck.train_locomotion')
                    arguments[module_index] = 'dashboard.legacy_runner'
                    arguments += ['--workflow-record', base + '/project/workflow.json']
                if run['task_version'] == 'v3':
                    arguments += ['--workflow-record', base + '/project/workflow.json']
                if run.get('initialization') == 'warm' and not run.get('_resume_manifest'):
                    arguments += ['--warm-start-manifest', base + '/project/initialization/manifest.json']
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
                atomic_json(self.archive.run_root(identifier) / f'launch.rank{rank}.json', job)
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

    def resume(self, identifier, request, *, background=True):
        with self.lock:
            fingerprint = digest({'parent': identifier, **request.model_dump()})
            previous = self.duplicate(request.request_id, fingerprint)
            if previous:
                return previous
            original = self.get(identifier)
            if not self.archive_detail(identifier)['capabilities']['resume']['allowed']:
                raise DashboardError('原运行档案完整性或续训条件未通过', 'resume_unavailable', 409)
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
                       initialization='resume',
                       name=original['name'] + ' · 续训', state='preparing', created_utc=utcnow(), failure=None,
                       _directory=str(self.artifacts / 'runs' / new_id / 'cache/rank0/run'), _event_count=0,
                       _request_record={'request_id': request.request_id, 'fingerprint': fingerprint},
                       _stop_requested=False, _resume_manifest=checkpoint['_manifest'],
                       _resume_remote_manifest=original['_locations'][original['execution']['node_ids'][0]] + '/run/checkpoints/' + Path(checkpoint['_manifest']).parent.name + '/manifest.json')
            run.pop('_locations', None)
            run.pop('_cached_manifest_count', None)
            run.pop('_last_cache_error', None)
            run.pop('_launch_failed', None)
            self.save(run)
            self.store.remember(request.request_id, fingerprint, 'run', new_id)
            if background:
                threading.Thread(target=self._prepare_launch, args=(new_id,), daemon=True).start()
            return run

    def refresh(self, identifier):
        run = self.get(identifier)
        if not run['managed'] or (run['state'] not in ACTIVE and not run.get('_archive_pending')):
            return run
        if run['state'] not in ACTIVE and run.get('_archive_pending'):
            if time.monotonic() < self.archive_retry_times.get(identifier, 0):
                return run
            self.archive_retry_times[identifier] = time.monotonic() + 30
        if run.get('_stop_requested'):
            run = self.stop(identifier)
        states, disconnected, stale = {}, [], []
        locations = run.get('_locations', {})
        def synchronize(rank, name, remote):
            cache = self.artifacts / 'runs' / identifier / 'cache' / f'rank{rank}'
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
                except Exception as error:
                    disconnected.append(name)
                    run.setdefault('_sync_errors', {})[name] = str(error)
                else:
                    run.get('_sync_errors', {}).pop(name, None)
        run['_archive_pending'] = bool(disconnected)
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
                atomic_json(directory.parent / 'experiment/experiment.json', {'id': run['experiment_id']})
                ledger_path = directory.parent / 'experiment/budget.jsonl'
                ledger_path.write_text(''.join(json.dumps(item) + '\n' for item in ledger), encoding='utf-8')
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
                run['_archive_pending'] = True
        if cache_missing:
            run['_archive_pending'] = True
        if not run.get('_archive_pending') and run.get('failure') == '等待完整checkpoint缓存校验':
            run['failure'] = None
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
            run.update(_archive_pending=True, failure='等待完整checkpoint缓存校验')
        resumable = run['state'] not in ACTIVE and run['budget']['remaining_transitions'] > 0 and any(item['resumable'] for item in self.store.all('checkpoint') if item['run_id'] == identifier)
        run['capabilities']['resume'] = {'allowed': resumable, 'reasons': [] if resumable else ['需剩余预算、终态及完整rank缓存']}
        return self.save(run)

    def metric_series(self, identifier, max_points=1000, keys=None):
        return metrics(self.get(identifier), max_points, keys)
