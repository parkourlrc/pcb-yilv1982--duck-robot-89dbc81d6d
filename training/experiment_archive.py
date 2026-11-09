from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def write_record(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def validate_workflow(workflow, config):
    if not isinstance(workflow, dict) or not workflow.get('task_id'):
        raise ValueError('训练必须关联已登记任务和流程记录')
    steps = workflow.get('steps', [])
    for number in range(1, 5):
        step = next((item for item in steps if item.get('number') == number), {})
        if step.get('status') not in ('passed', 'confirmed', 'reused') or not step.get('evidence'):
            raise ValueError(f'训练流程第{number}步缺少有效输入验证及证据')
    expected = config['num_envs'] * config['num_steps_per_env'] * config['max_updates']
    if workflow.get('budget', {}).get('max_transitions') != expected:
        raise ValueError('流程登记预算与实际训练配置不一致')
    if workflow.get('config_hash') != canonical_hash(config):
        raise ValueError('流程登记配置与实际训练配置不一致')
    return workflow


def register_runtime(output, workflow, config, *, run_id=None, source_root=None, initialization='scratch'):
    validate_workflow(workflow, config)
    output = Path(output)
    record = {'schema': 1, 'run_id': run_id or output.name, 'created_utc': datetime.now(timezone.utc).isoformat(),
              'workflow': workflow, 'config': config, 'config_hash': canonical_hash(config),
              'initialization': initialization, 'output': str(output), 'source_root': str(source_root) if source_root else None,
              'command': sys.argv, 'environment': {'python': sys.version, 'platform': platform.platform()}, 'state': 'registered'}
    write_record(output.parent / (output.name + '-startup') / 'archive-registration.json', record)
    return record
