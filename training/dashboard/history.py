from __future__ import annotations

from pathlib import Path

from .registry import file_hash
from .store import read_json, read_jsonl


LEGACY_ID = 'legacy-run-001'


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
