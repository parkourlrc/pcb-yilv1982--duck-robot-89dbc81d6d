from __future__ import annotations

import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


class Registry:
    def __init__(self, root, archive_tasks=None):
        self.root = Path(root)
        self.archive_tasks = Path(archive_tasks) if archive_tasks else None

    def tasks(self):
        result = []
        paths = list((self.root / 'training/tasks').glob('*.json'))
        if self.archive_tasks:
            paths += list(self.archive_tasks.glob('*.json'))
        identities = set()
        for path in paths:
            try:
                task = json.loads(path.read_text(encoding='utf-8-sig'))
                identity = (task['task_id'], task['task_version'])
                if identity in identities:
                    continue
                identities.add(identity)
                task.setdefault('availability', {'state': 'ready', 'missing': []})
                missing = [name for name in task.get('source_files', []) if not (self.root / name).is_file()]
                missing += [name + ': SHA256 mismatch' for name, expected in task.get('source_hashes', {}).items() if (self.root / name).is_file() and file_hash(self.root / name) != expected]
                if missing:
                    task['availability'] = {'state': 'missing_dependencies', 'missing': missing}
                result.append(task)
            except (ValueError, OSError):
                continue
        return result

    def get(self, identifier, version):
        return next((task for task in self.tasks() if task['task_id'] == identifier and task['task_version'] == version), None)
