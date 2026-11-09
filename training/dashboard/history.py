from __future__ import annotations

from pathlib import Path
import hashlib
import shutil

from .registry import file_hash
from .store import atomic_json, read_json, read_jsonl, utcnow


LEGACY_ID = 'legacy-run-001'


def import_all_history(root, store, archive):
    root = Path(root)
    search_roots = [root / 'training/logs', root / 'training/checkpoints',
                    root / 'docs/references/自主训练平台', root / 'docs/references/本机训练环境']
    search_roots += [root / 'training/artifacts/implementation-checks']
    search_roots += [path for path in (root / 'docs/specs').glob('*') if any(word in path.name for word in ('训练', '转圈', '步幅'))]
    candidates = {}
    evidence_files = []
    for directory in search_roots:
        if not directory.is_dir():
            continue
        for path in directory.rglob('run.json'):
            data = read_json(path)
            if isinstance(data, dict) and isinstance(data.get('config'), dict):
                candidates[str(path.parent.resolve())] = path.parent
            elif isinstance(data, dict) and ('source_sha256' in data or 'command' in data):
                evidence_files.append(path)
        for path in directory.rglob('benchmark*.json'):
            data = read_json(path, {})
            if isinstance(data, dict) and ('rank_records' in data or 'global_envs' in data or 'num_envs' in data):
                evidence_files.append(path)
        for path in directory.rglob('archive-registration.json'):
            candidates.setdefault(str(path.parent.resolve()), path.parent)
        for path in directory.rglob('result.json'):
            data = read_json(path, {})
            if isinstance(data, dict) and ('consumed_transitions' in data or 'model_iteration' in data):
                candidates.setdefault(str(path.parent.resolve()), path.parent)
        for path in directory.rglob('updates.jsonl'):
            candidates.setdefault(str(path.parent.resolve()), path.parent)
        for path in directory.rglob('model_*.pt'):
            candidates.setdefault(str(path.parent.resolve()), path.parent)
    items, warnings = [], []
    legacy = root / 'docs/specs/20261105-原地转圈策略/checks/step5-run-001'
    for source in sorted(candidates.values()):
        if source == legacy:
            continue
        relative = source.relative_to(root).as_posix()
        identifier = 'history-' + hashlib.sha256(relative.encode()).hexdigest()[:20]
        original, result = read_json(source / 'run.json') or read_json(source / 'archive-registration.json', {}), read_json(source / 'result.json', {})
        original = original if isinstance(original, dict) else {}
        result = result if isinstance(result, dict) else {}
        config = original.get('config') or read_json(source / 'config.json') or read_json(source.parent / 'config.json', {})
        config = config if isinstance(config, dict) else {}
        rows, row_errors = read_jsonl(source / 'updates.jsonl')
        last = rows[-1] if rows else {}
        maximum = result.get('max_transitions')
        if maximum is None and all(type(config.get(key)) is int for key in ('num_envs', 'num_steps_per_env', 'max_updates')):
            maximum = config['num_envs'] * config['num_steps_per_env'] * config['max_updates']
        consumed = result.get('consumed_transitions', last.get('consumed_transitions'))
        status = result.get('status')
        state = 'stopped' if status == 'interrupted_at_update_boundary' else 'completed' if status in ('budget_exhausted', 'check_limit', 'accepted') else 'failed' if status in ('failed', 'error') else 'unknown'
        error_record = read_json(source / 'failure.json', {})
        if error_record:
            state = 'failed'
        runtime = next((path for path in (source.parent / 'frozen', source.parent / 'project', source / 'sources') if (path / 'training/mjlab_duck/train_locomotion.py').is_file() and (path / 'training/mjlab_duck/__init__.py').is_file()), None)
        destination = archive.run_root(identifier) / 'history'
        for entry in source.rglob('*'):
            if not entry.is_file() or entry.is_symlink() or '__pycache__' in entry.parts:
                continue
            target = destination / entry.relative_to(source)
            if not target.exists() or target.stat().st_size != entry.stat().st_size or target.stat().st_mtime_ns != entry.stat().st_mtime_ns:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry, target)
        if runtime:
            frozen = archive.run_root(identifier) / 'project'
            if not frozen.exists():
                shutil.copytree(runtime, frozen, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            runtime = frozen
        documents = archive.run_root(identifier) / 'record-documents'
        for parent in (source, source.parent, source.parent.parent):
            if not parent.is_relative_to(root / 'docs/specs'):
                continue
            for document in parent.glob('*.md'):
                documents.mkdir(parents=True, exist_ok=True)
                target = documents / (hashlib.sha256(str(document.relative_to(root)).encode()).hexdigest()[:8] + '-' + document.name)
                if not target.exists():
                    shutil.copy2(document, target)
        run = {'run_id': identifier, 'experiment_id': original.get('experiment_id') or identifier,
               'parent_run_id': None, 'parent_checkpoint_id': None, 'task_id': 'locomotion' if original.get('config') else 'historical',
               'task_version': 'historical', 'name': relative, 'managed': False, 'read_only': True,
               'state': state, 'completion_reason': status, 'connection': {'state': 'offline_archive', 'last_seen_utc': None},
               'stage': result.get('stage', last.get('stage')), 'model_iteration': result.get('model_iteration', last.get('model_iteration')),
               'budget': {'consumed_transitions': consumed, 'remaining_transitions': max(0, maximum-consumed) if maximum is not None and consumed is not None else None,
                          'max_transitions': maximum, 'transitions_per_update': config.get('num_envs', 0)*config.get('num_steps_per_env', 0) or None},
               'execution': {'mode': original.get('mode', 'historical'), 'node_ids': [], 'world_size': original.get('world_size')},
               'config': config, 'created_utc': original.get('created_utc'), 'elapsed_s': result.get('wall_seconds_including_evaluation_and_checkpoint'),
               'eta_s': None, 'latest_checkpoint_id': None, 'failure': error_record or None,
               'capabilities': {'stop': {'allowed': False, 'reasons': ['历史归档']}, 'resume': {'allowed': False, 'reasons': ['未登记可恢复的原节点与预算账本']}},
               'provenance': {'kind': 'local_history', 'source': relative, 'imported_utc': utcnow()}, '_directory': str(destination),
               '_archive_errors': row_errors, '_warm_compatible': False}
        registration = read_json(source.parent / (source.name + '-startup') / 'archive-registration.json', {})
        if original.get('workflow') or registration.get('workflow'):
            run['workflow'] = original.get('workflow') or registration['workflow']
        if runtime:
            run['_runtime_root'] = str(runtime)
            task = read_json(runtime / 'task.json')
            if not task and run.get('workflow', {}).get('task_version') == 'v3':
                task = read_json(root / 'training/tasks/locomotion-v3.json')
                if task and original.get('source_sha256'):
                    atomic_json(runtime / 'source-manifest.json', original['source_sha256'])
                    task = {**task, 'source_hashes': original['source_sha256']}
                    atomic_json(runtime / 'task.json', task)
            if task and config:
                task = {**task, 'source_files': [], 'source_hashes': {}, 'source_policy': '派生时验证此运行冻结source-manifest，不读取当前源码'}
                run.update(task_id=task['task_id'], task_version=task['task_version'], _task=task)
                if not (root / 'training/tasks' / (task['task_id'] + '-' + task['task_version'] + '.json')).exists():
                    atomic_json(archive.directory / 'tasks' / (task['task_id'] + '-' + task['task_version'] + '.json'), task)
        for manifest in destination.rglob('manifest.json'):
            checkpoint = checkpoint_info(manifest, identifier, identifier + '-' + manifest.parent.name)
            if checkpoint:
                checkpoint['resumable'] = False
                store.put('checkpoint', checkpoint['checkpoint_id'], checkpoint)
                if checkpoint.get('model_iteration') is not None:
                    run['latest_checkpoint_id'] = checkpoint['checkpoint_id']
        archive.save(run)
        store.put('run', identifier, run)
        items.append({'run_id': identifier, 'source': relative, 'state': state, 'has_config': bool(config), 'has_runtime': bool(runtime)})
        warnings.extend(row_errors)
    for source in sorted(set(evidence_files)):
        if str(source.parent.resolve()) in candidates:
            continue
        relative = source.relative_to(root).as_posix()
        identifier = 'evidence-' + hashlib.sha256(relative.encode()).hexdigest()[:20]
        destination = archive.run_root(identifier) / 'history'
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination / source.name)
        data = read_json(source, {})
        rows = data.get('rank_records', [data])
        first = rows[0] if rows and isinstance(rows[0], dict) else {}
        run = {'run_id': identifier, 'experiment_id': identifier, 'parent_run_id': None, 'parent_checkpoint_id': None,
               'task_id': 'historical', 'task_version': 'evidence', 'name': relative, 'managed': False, 'read_only': True,
               'state': 'unknown', 'connection': {'state': 'offline_archive', 'last_seen_utc': None},
               'stage': None, 'model_iteration': None, 'config': {}, 'created_utc': first.get('utc_time'),
               'budget': {'consumed_transitions': None, 'remaining_transitions': None, 'max_transitions': None, 'transitions_per_update': first.get('global_samples_per_iteration')},
               'execution': {'mode': 'historical', 'node_ids': [], 'world_size': first.get('world_size')},
               'elapsed_s': None, 'eta_s': None, 'latest_checkpoint_id': None, 'failure': None,
               'capabilities': {'stop': {'allowed': False, 'reasons': ['历史证据']}, 'resume': {'allowed': False, 'reasons': ['仅短跑/测速证据，缺可恢复运行档案']}},
               '_directory': str(destination), 'provenance': {'kind': 'benchmark_or_profile', 'source': relative, 'imported_utc': utcnow()}}
        archive.save(run)
        store.put('run', identifier, run)
        items.append({'run_id': identifier, 'source': relative, 'state': 'unknown', 'has_config': False, 'has_runtime': False})
    identities = {}
    for item in items:
        run = store.get('run', item['run_id'])
        data = read_json(Path(run['_directory']) / 'run.json', {})
        identity = data.get('run_id') or ((data.get('created_utc'), tuple(data.get('command', []))) if data.get('command') else None)
        if identity:
            token = repr(identity)
            if token in identities:
                run['mirror_of'] = identities[token]
                run['experiment_id'] = store.get('run', identities[token])['experiment_id']
                archive.save(run)
                store.put('run', run['run_id'], run)
                item['mirror_of'] = identities[token]
            else:
                identities[token] = run['run_id']
    report = {'schema': 1, 'imported_utc': utcnow(), 'count': len(items), 'items': items, 'warnings': warnings,
              'scope': 'local training roots; remote-only artifacts are not claimed present'}
    atomic_json(archive.directory / 'history-inventory.json', report)
    return report


def import_history(root, store):
    directory = Path(root) / 'docs/specs/20261105-原地转圈策略/checks/step5-run-001'
    result = read_json(directory / 'result.json')
    original = read_json(directory / 'run.json')
    if not result or not original:
        return
    config = original['config']
    store.put('run', LEGACY_ID, {
        'run_id': LEGACY_ID, 'experiment_id': read_json(directory / 'manifest.json', {}).get('experiment_id'),
        'parent_run_id': None, 'parent_checkpoint_id': None, 'task_id': 'locomotion', 'task_version': 'v1',
        'name': '首轮双 Spark · 1000 更新（历史）', 'managed': False, 'read_only': True,
        'state': 'completed', 'completion_reason': result['status'], 'connection': {'state': 'offline_archive', 'last_seen_utc': None},
        'stage': result['stage'], 'model_iteration': result['model_iteration'],
        'budget': {'consumed_transitions': result['consumed_transitions'], 'remaining_transitions': 0,
                   'max_transitions': result['max_transitions'], 'transitions_per_update': config['num_envs'] * config['num_steps_per_env']},
        'execution': {'mode': 'dual_spark', 'node_ids': ['spark1', 'spark2'], 'world_size': 2},
        'config': config, 'created_utc': original['created_utc'],
        'elapsed_s': result['wall_seconds_including_evaluation_and_checkpoint'], 'eta_s': None,
        'latest_checkpoint_id': 'legacy-1000', 'capabilities': {'stop': {'allowed': False, 'reasons': ['只读历史运行']},
        'resume': {'allowed': False, 'reasons': ['原实验预算已耗尽']}}, 'failure': None,
        '_directory': str(directory), '_runtime_root': str(Path(root) / 'training/runtime_versions/locomotion-v1'),
        '_evaluation_paths': [str(path) for path in directory.parent.glob('step5-evaluation-*.json')],
    })
    for iteration in (100, 1000):
        directory = Path(root) / f'training/logs/step5-diagnosis/checkpoint{iteration}'
        checkpoint = checkpoint_info(directory / 'manifest.json', LEGACY_ID, f'legacy-{iteration}')
        if checkpoint:
            report = read_json(Path(root) / f'docs/specs/20261105-原地转圈策略/checks/step5-evaluation-{iteration:06d}.json')
            if report:
                checkpoint['evaluations'] = [report]
            store.put('checkpoint', checkpoint['checkpoint_id'], checkpoint)


def checkpoint_info(path, run_id, identifier):
    manifest = read_json(path)
    if not manifest:
        return None
    world_size = manifest.get('world_size')
    entries = manifest.get('rank_files')
    valid_manifest = (manifest.get('schema') == 1 and manifest.get('complete') is True
                      and type(world_size) is int and world_size in (1, 2) and isinstance(entries, dict)
                      and set(entries) == {str(rank) for rank in range(world_size)})
    parent = Path(path).parent.resolve()
    rank_files = []
    for rank, record in (entries.items() if isinstance(entries, dict) else []):
        if not isinstance(record, dict) or not str(rank).isdigit() or not isinstance(record.get('path'), str):
            valid_manifest = False
            continue
        candidate = (parent / record['path']).resolve()
        safe = candidate.parent == parent and not Path(record['path']).is_absolute() and '..' not in Path(record['path']).parts
        if not safe:
            valid_manifest = False
        valid = safe and candidate.is_file() and file_hash(candidate) == record.get('sha256')
        rank_files.append({'rank': int(rank), 'present': safe and candidate.is_file(), 'valid': valid, 'sha256': record.get('sha256')})
    replayable = valid_manifest and any(item['rank'] == 0 and item['valid'] for item in rank_files)
    complete = valid_manifest and bool(rank_files) and all(item['valid'] for item in rank_files)
    return {'checkpoint_id': identifier, 'run_id': run_id, 'model_iteration': manifest.get('iter'), 'stage': manifest.get('stage'),
            'world_size': manifest.get('world_size'), 'integrity': 'complete' if complete else 'partial',
            'cache_state': 'ready' if replayable else 'missing', 'replayable': replayable,
            'resumable': complete and manifest.get('resumable', True) and run_id != LEGACY_ID,
            'reasons': ([] if complete else ['本地尚缺完整各rank文件或manifest验证失败']) + ([manifest.get('resume_reason', '课程决策尚未应用，请选择最终或阶段切换检查点')] if manifest.get('resumable') is False else []),
            'evaluations': [], 'rank_files': rank_files, 'consumed_transitions': manifest.get('consumed_transitions'),
            '_manifest': str(path)}


METRICS = {
    'reward_mean': ('每转换奖励', '', 'global'), 'episode_return': ('完整回合奖励', '', 'global'),
    'episode_length': ('完整回合长度', 'steps', 'global'), 'value_loss': ('Value loss', '', 'rank0'),
    'surrogate_loss': ('Policy loss', '', 'rank0'), 'entropy': ('Entropy', '', 'rank0'),
    'action_std': ('Action std', '', 'rank0'), 'learning_rate': ('Learning rate', '', 'rank0'),
    'action_clip_fraction': ('动作裁剪比例', 'fraction', 'global'), 'transitions_per_s': ('采样及更新吞吐', 'transitions/s', 'global'),
    'sampling_transitions_per_s': ('纯采样吞吐', 'transitions/s', 'global'), 'overall_transitions_per_s': ('全程平均吞吐', 'transitions/s', 'global'),
    'kl': ('KL', '', 'rank0'), 'collect_s': ('采样耗时', 's', 'global'), 'update_s': ('更新耗时', 's', 'rank0'),
}


def metrics(run, max_points=1000, keys=None):
    records, warnings = read_jsonl(Path(run['_directory']) / 'updates.jsonl')
    series = {key: {'key': key, 'label': label, 'unit': unit, 'scope': scope, 'availability': 'missing', 'points': []}
              for key, (label, unit, scope) in METRICS.items() if not keys or key in keys}
    seen = set()
    for row in records:
        identity = (row.get('run_id', run['run_id']), row.get('rank', 0), row.get('seq', row.get('model_iteration')))
        if identity in seen:
            continue
        seen.add(identity)
        statistics = row.get('statistics', {})
        losses = row.get('losses_rank0', {})
        episode = statistics.get('episodes', row.get('episodes', {}))
        values = {'reward_mean': statistics['reward_sum'] / statistics['transitions'] if statistics.get('transitions') and statistics.get('reward_sum') is not None else None,
                  'episode_return': episode.get('return_mean', statistics.get('episode_return_mean')),
                  'episode_length': episode.get('length_mean', statistics.get('episode_length_mean')),
                  'value_loss': losses.get('value'), 'surrogate_loss': losses.get('surrogate'), 'entropy': losses.get('entropy'),
                  'action_std': row.get('action_std_rank0'), 'learning_rate': row.get('learning_rate'),
                  'action_clip_fraction': statistics.get('raw_action_clip_fraction'), 'transitions_per_s': row.get('transitions_per_s'),
                  'sampling_transitions_per_s': row.get('sampling_transitions_per_s'), 'overall_transitions_per_s': row.get('overall_transitions_per_s'),
                  'kl': row.get('kl'), 'collect_s': row.get('collect_s'), 'update_s': row.get('update_s')}
        for term, value in statistics.get('reward_terms_sum', {}).items():
            key = 'reward/' + term
            if not keys or key in keys:
                series.setdefault(key, {'key': key, 'label': term, 'unit': 'reward/transition', 'scope': 'global', 'availability': 'ok', 'points': []})
                values[key] = value / statistics['transitions'] if statistics.get('transitions') else None
        for term, detail in statistics.get('reward_details', {}).items():
            for field in ('raw_mean', 'signed_weight_mean', 'contribution_mean', 'reward_per_transition'):
                key = 'reward_detail/' + term + '/' + field
                if not keys or key in keys:
                    series.setdefault(key, {'key': key, 'label': term + ' · ' + field, 'unit': 'reward/transition' if field == 'reward_per_transition' else detail.get('unit', ''), 'scope': 'global', 'availability': 'missing', 'points': []})
                    values[key] = detail.get(field)
        for key, entry in series.items():
            value = values.get(key)
            if value is not None:
                entry['availability'] = 'ok'
            entry['points'].append({'iteration': row.get('model_iteration'), 'transitions': row.get('consumed_transitions'),
                                    'elapsed_s': row.get('elapsed_s'), 'time_utc': row.get('time_utc', row.get('utc')),
                                    'value': value, 'sample_count': episode.get('samples', episode.get('count'))})
    for entry in series.values():
        points = entry['points']
        if len(points) > max_points:
            width = max(1, len(points) // max(1, max_points // 2))
            reduced = []
            for start in range(0, len(points), width):
                batch = points[start:start + width]
                valid = [(index, point) for index, point in enumerate(batch) if point['value'] is not None]
                selected = {min(valid, key=lambda item: item[1]['value'])[0], max(valid, key=lambda item: item[1]['value'])[0]} if valid else {0}
                reduced.extend(batch[index] for index in sorted(selected))
            entry['points'] = reduced
    evaluation_paths = list(Path(run['_directory']).glob('evaluation_*.json')) + [Path(path) for path in run.get('_evaluation_paths', [])]
    for path in evaluation_paths:
        report = read_json(path, {})
        if not report.get('total'):
            continue
        suite = report.get('suite', 'dev' + str(report['total']))
        key = 'evaluation/' + suite
        if keys and key not in keys:
            continue
        entry = series.setdefault(key, {'key': key, 'label': suite + ' 开发通过率', 'unit': 'fraction', 'scope': 'suite', 'kind': 'sparse', 'availability': 'ok', 'points': []})
        checkpoint_name = Path(report.get('checkpoint', '')).parent.name
        iteration = report.get('model_iteration')
        if iteration is None and run['run_id'] == LEGACY_ID:
            iteration = int(path.stem.rsplit('-', 1)[-1])
        linked_manifest = read_json(Path(run['_directory']) / 'checkpoints' / checkpoint_name / 'manifest.json', {})
        matching_update = next((row for row in reversed(records) if row.get('model_iteration') == iteration), {})
        consumed = linked_manifest.get('consumed_transitions', matching_update.get('consumed_transitions'))
        entry['points'].append({'iteration': iteration, 'transitions': consumed, 'elapsed_s': matching_update.get('elapsed_s'),
                                'time_utc': report.get('utc'), 'value': report['passed_count'] / report['total'],
                                'sample_count': report['total'], 'passed_count': report['passed_count'],
                                'checkpoint_id': 'legacy-' + str(iteration) if run['run_id'] == LEGACY_ID else run['run_id'] + '-' + checkpoint_name})
    return {'series': list(series.values()), 'warnings': warnings}
