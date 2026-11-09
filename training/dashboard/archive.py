from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

from .registry import file_hash
from .store import atomic_json, read_json, utcnow


STEP_NAMES = ('策略需求', '任务定义与验收标准', '训练环境组装', '训练方案', '执行训练', '独立评估与回放', '策略交付')


def public_record(value):
    if isinstance(value, dict):
        return {key: public_record(item) for key, item in value.items() if not key.startswith('_') and key not in ('command', 'environment', 'node_ids')}
    if isinstance(value, list):
        return [public_record(item) for item in value]
    if isinstance(value, str):
        value = re.sub(r'[A-Za-z]:[\\/][^\s\"\']+', '[local-path]', value)
        value = re.sub(r'/(?:home|mnt|Users|tmp)/[^\s\"\']+', '[local-path]', value)
        return re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[host]', value)
    return value


def workflow_for(task, config, budget, source=None):
    from experiment_archive import canonical_hash
    evidence = task.get('workflow_evidence', {})
    steps = []
    for number, name in enumerate(STEP_NAMES, 1):
        reference = evidence.get(str(number))
        steps.append({'number': number, 'name': name, 'status': 'reused' if reference and number < 5 else 'pending',
                      'inputs': [{'task_id': task['task_id'], 'task_version': task['task_version']}] if number == 1 else [],
                      'outputs': [], 'evidence': reference or []})
    steps[0]['outputs'] = [{'task': task.get('title'), 'description': task.get('description')}]
    steps[1]['inputs'] = [{'evaluation_suites': task.get('evaluation_suites', [])}]
    steps[1]['outputs'] = [{'acceptance': '沿用已确认任务验收版本，未放宽'}]
    steps[2]['inputs'] = [{'physics_model': task.get('physics_model'), 'contract': task.get('observation_action_contract')}]
    steps[2]['outputs'] = [{'source_hashes': task.get('source_hashes', {}), 'runtime_version': task.get('runtime_version')}]
    steps[3]['inputs'] = [{'resolved_config': config, 'budget': budget}]
    steps[3]['outputs'] = [{'config_hash': canonical_hash(config), 'validation': '配置类型/范围、任务约束及预算计算；节点可用性在启动准备时核验'}]
    steps[3]['status'] = 'passed'
    return {'task_id': task['task_id'], 'task_version': task['task_version'], 'current_step': 5,
            'steps': steps, 'budget': budget, 'config_hash': canonical_hash(config), 'source_run_id': source}


def config_diff(previous, current, prefix=''):
    result = []
    if isinstance(previous, dict) and isinstance(current, dict):
        for key in sorted(set(previous) | set(current)):
            path = prefix + '.' + key if prefix else key
            result.extend(config_diff(previous.get(key), current.get(key), path))
    elif previous != current:
        result.append({'path': prefix, 'before': previous, 'after': current})
    return result


class Archive:
    def __init__(self, root, directory):
        self.root, self.directory = Path(root), Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.hash_cache = {}
        self.export_records = True

    def run_root(self, identifier):
        if not identifier or any(value in identifier for value in ('/', '\\', '..')):
            raise ValueError('invalid run identifier')
        target = self.directory / 'runs' / identifier
        if not target.resolve().is_relative_to(self.directory.resolve()):
            raise ValueError('run directory escaped archive root')
        return target

    def source_directory(self, run):
        value = run.get('_directory')
        if not value:
            return None
        path = Path(value).resolve()
        allowed = (self.directory, self.root / 'training/logs', self.root / 'docs/specs', self.root / 'docs/references/自主训练平台')
        if not any(path.is_relative_to(base.resolve()) for base in allowed):
            return None
        return path if path.is_dir() else None

    def save(self, run):
        target = self.run_root(run['run_id'])
        atomic_json(target / 'dashboard-run.json', run)
        if run.get('workflow'):
            atomic_json(target / 'workflow.json', run['workflow'])
        if run.get('config'):
            atomic_json(target / 'resolved-config.json', run['config'])
        if run.get('managed') and self.export_records:
            summary = {key: run.get(key) for key in ('run_id', 'experiment_id', 'task_id', 'task_version', 'name', 'state',
                       'parent_run_id', 'parent_checkpoint_id', 'initialization', 'created_utc', 'model_iteration', 'stage', 'budget')}
            summary['config'] = run.get('config', {})
            summary['artifact_reference'] = 'training/artifacts/runs/' + run['run_id']
            summary['workflow'] = run.get('workflow', {})
            summary['task'] = {key: value for key, value in run.get('_task', {}).items() if key in ('task_id', 'task_version', 'title', 'description', 'physics_model', 'observation_action_contract', 'evaluation_suites', 'workflow_evidence')}
            summary['result'] = {key: run.get(key) for key in ('completion_reason', 'failure', 'elapsed_s', 'model_iteration', 'stage')}
            summary['behavior_acceptance'] = 'not_inferred_from_training_completion'
            atomic_json(self.root / 'training/records' / (run['run_id'] + '.json'), public_record(summary))

    def seal(self, run):
        path = self.run_root(run['run_id']) / 'artifact-manifest.json'
        if path.exists():
            return
        excluded = {'dashboard-run.json', 'workflow.json', 'artifact-manifest.json'}
        entries = [item for item in self.entries(run) if Path(item['path']).name not in excluded]
        atomic_json(path, {'schema': 1, 'sealed_utc': utcnow(), 'files': [{key: value for key, value in item.items() if key in ('artifact_id', 'path', 'size', 'sha256')} for item in entries]})

    def restore(self, store):
        count = 0
        for path in (self.directory / 'runs').glob('*/dashboard-run.json'):
            record = read_json(path)
            if isinstance(record, dict) and record.get('run_id'):
                store.put('run', record['run_id'], record)
                count += 1
        return count

    def migrate(self, run, old_root):
        destination = self.run_root(run['run_id'])
        source = Path(old_root)
        if source.resolve() != destination.resolve() and source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
            for key in ('_directory', '_runtime_root'):
                value = run.get(key)
                if value and Path(value).is_relative_to(source):
                    run[key] = str(destination / Path(value).relative_to(source))
        self.save(run)
        return run

    def entries(self, run):
        roots = [('archive', self.run_root(run['run_id']))]
        original = self.source_directory(run)
        if original and not original.is_relative_to(roots[0][1].resolve()):
            roots.append(('source', original))
        entries, seen = [], set()
        for label, root in roots:
            for path in sorted(root.rglob('*')):
                if not path.is_file() or path.is_symlink() or '__pycache__' in path.parts or path.suffix in ('.pyc', '.tmp'):
                    continue
                resolved = path.resolve()
                if not resolved.is_relative_to(root.resolve()) or resolved in seen:
                    continue
                seen.add(resolved)
                relative = label + '/' + path.relative_to(root).as_posix()
                identifier = hashlib.sha256(relative.encode()).hexdigest()[:24]
                suffix = path.suffix.lower()
                kind = 'video' if suffix in ('.mp4', '.webm') else 'image' if suffix in ('.png', '.jpg', '.jpeg') else 'checkpoint' if suffix in ('.pt', '.onnx', '.zip') else 'trajectory' if suffix in ('.npz', '.npy') else 'log' if suffix in ('.log', '.jsonl', '.txt') else 'document'
                if 'evaluation-traces' in path.parts:
                    kind = 'trajectory'
                stat = path.stat()
                fingerprint = (str(resolved), stat.st_size, stat.st_mtime_ns)
                if fingerprint not in self.hash_cache:
                    self.hash_cache[fingerprint] = file_hash(path)
                entries.append({'artifact_id': identifier, 'path': relative, 'kind': kind, 'size': stat.st_size, 'sha256': self.hash_cache[fingerprint],
                                'available': True, 'url': f"/api/runs/{run['run_id']}/artifacts/{identifier}", '_path': str(path)})
        return entries

    def inspect(self, run, checkpoints):
        entries = self.entries(run)
        missing = []
        if not run.get('config'):
            missing.append('完整训练配置')
        if not run.get('workflow'):
            missing.append('训练流程输入输出及验证证据')
        runtime = Path(run.get('_runtime_root') or self.run_root(run['run_id']) / 'project')
        sources = read_json(runtime / 'source-manifest.json') or read_json(runtime / 'manifest.json', {}).get('files', {})
        if not sources:
            missing.append('冻结源码及哈希清单')
        bad_sources = [name for name, expected in sources.items() if not (runtime / name).resolve().is_relative_to(runtime.resolve()) or not (runtime / name).is_file() or file_hash(runtime / name) != expected]
        if bad_sources:
            missing.append('冻结源码完整性')
        directory = self.source_directory(run)
        if not directory or not (directory / 'updates.jsonl').is_file():
            missing.append('逐轮日志')
        if run.get('config'):
            required = ['run.json', 'result.json', 'events.jsonl']
            missing.extend(name for name in required if not directory or not (directory / name).is_file())
            if not directory or not (directory.parent / 'experiment/budget.jsonl').is_file():
                missing.append('预算账本')
            if not list(self.run_root(run['run_id']).glob('cache/rank*/process.log')):
                missing.append('stdout/stderr合并日志')
            if not directory or not list(directory.glob('episodes.rank*.jsonl')):
                missing.append('完整回合日志')
            if not any('environment' in item['path'] or 'dependencies' in item['path'] for item in entries):
                missing.append('依赖与运行环境清单')
            if not any(item['path'].endswith('resources.jsonl') for item in entries):
                missing.append('运行资源采样')
            interval = run['config'].get('eval_interval', run['config'].get('save_interval'))
            iteration = run.get('model_iteration')
            if interval and iteration is not None and iteration >= interval:
                if not directory or not list(directory.glob('evaluation_*.json')):
                    missing.append('计划内独立评估报告')
                if not directory or not list((directory / 'evaluation-traces').rglob('*.pt')):
                    missing.append('指定评估轨迹')
        if not checkpoints:
            missing.append('检查点')
        elif any(item.get('integrity') != 'complete' for item in checkpoints):
            missing.append('完整检查点文件')
        if not run.get('config', {}).get('reward_config'):
            missing.append('结构化奖励配置（历史记录不补造）')
        errors = list(run.get('_archive_errors', []))
        sealed = read_json(self.run_root(run['run_id']) / 'artifact-manifest.json')
        if sealed:
            current = {item['path']: item for item in entries}
            for expected in sealed.get('files', []):
                actual = current.get(expected['path'])
                if not actual:
                    errors.append('已归档文件丢失: ' + expected['path'])
                elif file_hash(actual['_path']) != expected['sha256']:
                    errors.append('已归档文件哈希改变: ' + expected['path'])
        elif run.get('state') not in ('preparing', 'initializing', 'training', 'evaluating', 'saving', 'running', 'stopping'):
            missing.append('固定产物哈希清单')
        if run.get('_last_cache_error'):
            errors.append(run['_last_cache_error'])
        errors.extend('节点同步失败: ' + name + ': ' + error for name, error in run.get('_sync_errors', {}).items())
        source_ok = bool(sources) and not bad_sources and not errors
        rank0_ok = any(item.get('replayable') for item in checkpoints)
        replay_ok = source_ok and rank0_ok
        scratch_ok = source_ok and bool(run.get('config')) and bool(run.get('_task'))
        warm_ok = replay_ok and bool(run.get('_warm_compatible'))
        capabilities = dict(run.get('capabilities', {}))
        capabilities.update(browse={'allowed': True, 'reasons': []},
                            replay={'allowed': replay_ok, 'reasons': [] if replay_ok else ['需要原冻结运行时及完整rank0策略']},
                            scratch={'allowed': scratch_ok, 'reasons': [] if scratch_ok else ['缺少已校验冻结源码、任务或完整配置']},
                            warm={'allowed': warm_ok, 'reasons': [] if warm_ok else ['需完整rank0策略及已核验物理/接口/网络合同']})
        resume_ok = source_ok and run.get('managed') and run.get('state') in ('completed', 'stopped', 'failed') and (run.get('budget', {}).get('remaining_transitions') or 0) > 0 and any(item.get('resumable') for item in checkpoints)
        capabilities['resume'] = {'allowed': bool(resume_ok), 'reasons': [] if resume_ok else ['需终态、剩余原预算、完整检查点及冻结档案']}
        state = 'sync_failed' if errors else 'partial' if missing else 'complete'
        if run.get('state') in ('preparing', 'initializing', 'training', 'evaluating', 'saving', 'running', 'stopping'):
            state = 'collecting'
        return {'state': state, 'missing': missing, 'errors': errors, 'checked_utc': utcnow()}, capabilities, entries
