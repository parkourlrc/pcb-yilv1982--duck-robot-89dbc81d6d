from __future__ import annotations

import subprocess
import json
from collections import deque
import threading
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path

from .registry import digest
from .runs import DashboardError
from .store import atomic_json, read_json, utcnow


class Replays:
    def __init__(self, runs):
        self.runs, self.lock = runs, threading.RLock()
        self.processes = {}
        self.frame_caches = {}

    def frames(self, identifier, after_seq=0, limit=2500):
        with self.lock:
            replay = self.get(identifier)
            path = Path(replay['_directory']) / 'frames.jsonl'
            generation = replay.get('generation', 0)
            cache = self.frame_caches.setdefault(identifier, {'offset': 0, 'generation': generation, 'items': deque(maxlen=2500)})
            if not path.exists():
                return {'items': [], 'generation': generation}
            if path.stat().st_size < cache['offset']:
                cache.update(offset=0, generation=generation, items=deque(maxlen=2500))
            with path.open('rb') as handle:
                handle.seek(cache['offset'])
                while True:
                    offset = handle.tell()
                    line = handle.readline()
                    if not line or not line.endswith(b'\n'):
                        cache['offset'] = offset
                        break
                    cache['offset'] = handle.tell()
                    try:
                        frame = json.loads(line)
                    except (ValueError, UnicodeDecodeError):
                        continue
                    if frame.get('replay_id') != identifier:
                        continue
                    frame_generation = frame.get('generation', 0)
                    if frame_generation > cache['generation']:
                        cache.update(generation=frame_generation, items=deque(maxlen=2500))
                    if frame_generation == cache['generation']:
                        cache['items'].append(frame)
            generation = max(generation, cache['generation'])
            if generation != cache['generation']:
                cache.update(generation=generation, items=deque(maxlen=2500))
            return {'items': [frame for frame in cache['items'] if frame.get('seq', 0) > after_seq][-max(1, min(limit, 2500)):], 'generation': generation}

    def _wsl_path(self, path):
        node = self.runs.config['nodes']['local']
        argv = ['wsl.exe'] + (['-d', node['distribution']] if node.get('distribution') else [])
        return subprocess.run(argv + ['--exec', 'wslpath', '-a', '-u', Path(path).resolve().as_posix()], capture_output=True, text=True, timeout=10, check=True).stdout.strip()

    def get(self, identifier):
        replay = self.runs.store.get('replay', identifier)
        if not replay:
            raise DashboardError('回放不存在', 'not_found', 404)
        status = read_json(Path(replay['_directory']) / 'status.json', {})
        if status:
            replay.update({key: value for key, value in status.items() if key not in ('replay_id', 'checkpoint_id')})
        heartbeat = status.get('utc', replay.get('created_utc'))
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(heartbeat)).total_seconds() if heartbeat else float('inf')
        replay['connection'] = {'state': 'stale' if age > 15 else 'connected', 'last_seen_utc': heartbeat}
        latest = read_json(Path(replay['_directory']) / 'latest-frame.json')
        if latest:
            replay['latest_frame'] = latest
        process = self.processes.get(identifier)
        if process and process.poll() is not None and replay['state'] not in ('closed', 'failed'):
            replay.update(state='failed' if process.returncode else 'closed', error=f'回放进程退出: {process.returncode}')
            atomic_json(Path(replay['_directory']) / 'status.json', replay)
            self.runs.store.put('replay', identifier, replay)
        elif process is None and age > 20 and replay['state'] not in ('closed', 'failed'):
            try:
                import psutil
                owner = psutil.Process(replay['_pid'])
                identity_matches = abs(owner.create_time() - replay.get('_pid_started', 0)) < .1
                alive = identity_matches and identifier in ' '.join(owner.cmdline())
            except (KeyError, psutil.Error):
                alive = False
            if not alive:
                replay.update(state='failed', error='回放监督进程已退出，且状态心跳过期')
                self.runs.store.put('replay', identifier, replay)
        return replay

    def create(self, request):
        with self.lock:
            fingerprint = digest(request.model_dump())
            previous = self.runs.duplicate(request.request_id, fingerprint)
            if previous:
                return self.get(previous['replay_id'])
            active = [item for item in self.runs.store.all('replay') if self.get(item['replay_id'])['state'] not in ('closed', 'failed')]
            if len(active) >= 4:
                raise DashboardError('最多同时四路回放，请先关闭一个窗口', 'replay_limit', 409)
            checkpoint = self.runs.store.get('checkpoint', request.checkpoint_id)
            if not checkpoint or not checkpoint['replayable']:
                raise DashboardError('checkpoint文件尚未完整缓存', 'checkpoint_unavailable', 409)
            node = self.runs.config['nodes']['local']
            if not node.get('python'):
                raise DashboardError('未配置本地WSL解释器', 'node_unconfigured', 503)
            identifier = uuid.uuid4().hex
            directory = self.runs.data / 'replays' / identifier
            directory.mkdir(parents=True, exist_ok=False)
            run = self.runs.get(checkpoint['run_id'])
            runtime = Path(run.get('_runtime_root') or self.runs.data / 'runs' / run['run_id'] / 'project')
            replay = {'replay_id': identifier, 'state': 'initializing', 'checkpoint_id': request.checkpoint_id,
                      'node_id': 'local', 'scenario_id': request.scenario_id, 'seed': request.seed, 'speed': 1,
                      'generation': 0, 'actual_realtime_factor': None, 'error': None, 'created_utc': utcnow(),
                      '_directory': str(directory), '_control_seq': 0}
            self.runs.store.put('replay', identifier, replay)
            self.runs.store.remember(request.request_id, fingerprint, 'replay', identifier)
            try:
                command = [node['python'], self._wsl_path(self.runs.root / 'training/dashboard/replay_worker.py'),
                           '--checkpoint', self._wsl_path(checkpoint['_manifest']), '--task-version', run['task_version'],
                           '--runtime-root', self._wsl_path(runtime), '--scenario', request.scenario_id, '--seed', str(request.seed),
                           '--output-dir', self._wsl_path(directory), '--replay-id', identifier]
                wsl = ['wsl.exe'] + (['-d', node['distribution']] if node.get('distribution') else []) + ['--exec']
                with (directory / 'process.log').open('ab') as log:
                    process = subprocess.Popen(wsl + command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                replay['_pid'] = process.pid
                import psutil
                replay['_pid_started'] = psutil.Process(process.pid).create_time()
                self.processes[identifier] = process
                self.runs.store.put('replay', identifier, replay)
            except Exception as error:
                replay.update(state='failed', error=str(error))
                self.runs.store.put('replay', identifier, replay)
                atomic_json(directory / 'status.json', {'state': 'failed', 'error': str(error)})
            return replay

    def control(self, identifier, action, speed=None, request_id=None):
        with self.lock:
            fingerprint = digest({'replay_id': identifier, 'action': action, 'speed': speed})
            if request_id:
                previous = self.runs.duplicate(request_id, fingerprint)
                if previous:
                    return self.get(identifier)
            replay = self.get(identifier)
            if replay['state'] == 'failed' and action == 'close':
                replay['state'] = 'closed'
                atomic_json(Path(replay['_directory']) / 'status.json', {'state': 'closed', 'utc': utcnow()})
                self.runs.store.put('replay', identifier, replay)
                return replay
            if replay['state'] == 'closed' and action == 'close':
                return replay
            if speed is not None and speed not in (.5, 1, 2):
                raise DashboardError('倍率只支持0.5、1、2')
            previous_control = read_json(Path(replay['_directory']) / 'controls.json', {})
            if previous_control and replay.get('control_seq', -1) < previous_control.get('seq', -1):
                raise DashboardError('上一条回放控制尚未确认，请稍候重试', 'control_pending', 409)
            replay['_control_seq'] = max(replay['_control_seq'], replay.get('control_seq', -1)) + 1
            control = {'seq': replay['_control_seq'], 'action': action}
            if speed is not None:
                control['speed'] = speed
                replay['speed'] = speed
            atomic_json(Path(replay['_directory']) / 'controls.json', control)
            if action == 'close':
                replay['state'] = 'closing'
            self.runs.store.put('replay', identifier, replay)
            if request_id:
                self.runs.store.remember(request_id, fingerprint, 'replay', identifier)
            return replay
