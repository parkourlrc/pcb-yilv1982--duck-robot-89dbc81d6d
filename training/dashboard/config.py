from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_config(path=None):
    path = Path(path or os.environ.get('DUCK_DASHBOARD_CONFIG', ROOT / 'training/dashboard.local.json'))
    config = json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    config.setdefault('data_dir', str(ROOT / 'training/.dashboard'))
    config.setdefault('artifact_dir', str(ROOT / 'training/artifacts'))
    config.setdefault('port', 8765)
    # History migration is an explicit maintenance operation.  The dashboard
    # reads only process-produced documents under training/records.
    config.setdefault('auto_import_history', False)
    if os.environ.get('DUCK_DASHBOARD_PORT'):
        config['port'] = int(os.environ['DUCK_DASHBOARD_PORT'])
    config.setdefault('nodes', {
        'local': {'label': '本地 Windows / WSL', 'kind': 'wsl', 'project_root': '', 'python': '', 'work_root': '', 'distribution': ''},
        'spark1': {'label': 'Spark 1', 'kind': 'ssh', 'ssh_target': 'spark1', 'work_root': '', 'benchmark_root': '', 'env_file': '', 'master_addr': ''},
        'spark2': {'label': 'Spark 2', 'kind': 'ssh', 'ssh_target': 'spark2', 'work_root': '', 'benchmark_root': '', 'env_file': '', 'master_addr': ''},
    })
    config['data_dir'] = str(Path(config['data_dir']).resolve())
    return config
