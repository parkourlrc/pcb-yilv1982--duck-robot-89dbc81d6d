from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT, load_config
from .replays import Replays
from .runs import ACTIVE, DashboardError, Runs
from .schemas import DeriveRequest, ReplayControl, ReplayRequest, ResumeRequest, StartRequest, StopRequest, ValidationRequest
from .store import atomic_json, utcnow
from .telemetry import collect, rates


def create_app(config=None):
    config = config or load_config()
    runs = Runs(ROOT, config)
    replays = Replays(runs)
    secret_path = runs.data / 'session-secret'
    if not secret_path.exists():
        secret_path.write_text(secrets.token_hex(32))
    secret = secret_path.read_bytes()
    resources = {}
    stop_background = threading.Event()

    def sample_remote(identifier):
        previous = None
        node = config['nodes'][identifier]
        resource = resources.setdefault(identifier, {'node_id': identifier, 'label': node['label'], 'execution_kind': node['kind'], 'samples': [], 'active_run_ids': [], 'active_replay_ids': []})
        while not stop_background.is_set():
            try:
                sample = rates(runs.executors[identifier].sample(), previous)
                previous = sample
                received_utc = utcnow()
                sample['received_utc'] = received_utc
                runs.record_resource(identifier, sample)
                resource.update(connection={'state': 'connected', 'last_seen_utc': received_utc}, active_run_ids=[run['run_id'] for run in runs.store.all('run') if run['state'] in ACTIVE and identifier in run['execution']['node_ids']])
                resource['samples'] = (resource['samples'] + [sample])[-900:]
                with (runs.data / ('resources.' + identifier + '.jsonl')).open('a', encoding='utf-8') as handle:
                    handle.write(json.dumps({'node_id': identifier, **sample}) + '\n')
            except Exception as error:
                resource.update(connection={'state': 'stale' if previous else 'unavailable', 'last_seen_utc': previous.get('received_utc') if previous else None}, detail=str(error))
            stop_background.wait(2)

    def sample_resources():
        previous = None
        while not stop_background.is_set():
            try:
                sample = rates(collect(), previous)
                previous = sample
                received_utc = utcnow()
                sample['received_utc'] = received_utc
                resource = resources.setdefault('local', {'node_id': 'local', 'label': '本地 Windows / WSL', 'execution_kind': 'wsl', 'samples': []})
                runs.record_resource('local', sample)
                resource.update(connection={'state': 'connected', 'last_seen_utc': received_utc}, active_run_ids=[run['run_id'] for run in runs.store.all('run') if run['state'] in ACTIVE and 'local' in run['execution']['node_ids']], active_replay_ids=[item['replay_id'] for item in runs.store.all('replay') if replays.get(item['replay_id'])['state'] not in ('closed', 'failed')])
                resource['samples'] = (resource['samples'] + [sample])[-900:]
                with (runs.data / 'resources.jsonl').open('a', encoding='utf-8') as handle:
                    handle.write(json.dumps({'node_id': 'local', **sample}) + '\n')
            except Exception:
                resource = resources.get('local')
                if resource:
                    resource['connection'] = {'state': 'stale', 'last_seen_utc': previous.get('received_utc') if previous else None}
            stop_background.wait(2)

    def sample_wsl():
        previous = None
        while not stop_background.is_set():
            try:
                sample = rates(runs.executors['local'].sample_wsl(), previous)
                previous = sample
                sample['scope'] = 'wsl_virtual_machine'
                received_utc = utcnow()
                sample['received_utc'] = received_utc
                resource = resources.setdefault('local', {'node_id': 'local', 'label': '本地 Windows / WSL', 'execution_kind': 'wsl', 'samples': []})
                wsl = resource.setdefault('wsl', {'samples': []})
                wsl.update(connection={'state': 'connected', 'last_seen_utc': received_utc}, sample=sample)
                wsl['samples'] = (wsl.get('samples', []) + [sample])[-900:]
                with (runs.data / 'resources.local-wsl.jsonl').open('a', encoding='utf-8') as handle:
                    handle.write(json.dumps({'node_id': 'local', **sample}) + '\n')
            except Exception as error:
                resource = resources.get('local')
                if resource:
                    resource['wsl'] = {'connection': {'state': 'stale' if previous else 'unavailable', 'last_seen_utc': previous.get('received_utc') if previous else None}, 'error': str(error), 'sample': previous, 'samples': resource.get('wsl', {}).get('samples', [])}
            stop_background.wait(2)

    def refresh_runs():
        while not stop_background.is_set():
            for run in runs.store.all('run'):
                if run['managed'] and (run['state'] in ACTIVE or run.get('_archive_pending')):
                    try:
                        runs.refresh(run['run_id'])
                    except Exception as error:
                        runs.store.event(run['run_id'], {'level': 'error', 'type': 'refresh_error', 'message': str(error)})
            stop_background.wait(3)

    @asynccontextmanager
    async def lifespan(application):
        threading.Thread(target=sample_resources, daemon=True).start()
        threading.Thread(target=refresh_runs, daemon=True).start()
        if config['nodes'].get('local', {}).get('python'):
            threading.Thread(target=sample_wsl, daemon=True).start()
        for identifier, node in config['nodes'].items():
            if node['kind'] == 'ssh' and node.get('work_root'):
                threading.Thread(target=sample_remote, args=(identifier,), daemon=True).start()
        yield
        stop_background.set()
        for item in runs.store.all('replay'):
            try:
                replay = replays.get(item['replay_id'])
                if replay['state'] not in ('closed', 'failed'):
                    atomic_json(Path(replay['_directory']) / 'STOP', {'reason': 'dashboard_shutdown'})
            except Exception:
                pass

    app = FastAPI(title='Duck 训练工作台', lifespan=lifespan)
    app.state.runs, app.state.replays = runs, replays

    def token(session):
        return hmac.new(secret, session.encode(), hashlib.sha256).hexdigest()

    def valid_origin(origin, host):
        return origin in (f'http://{host}', f'https://{host}')

    @app.middleware('http')
    async def security(request, next_call):
        host = request.headers.get('host', '')
        if host.split(':')[0] not in ('127.0.0.1', 'localhost', 'testserver'):
            return JSONResponse({'error': {'code': 'host_rejected', 'message': '仅允许本机访问'}}, status_code=403)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            session = request.cookies.get('duck_session', '')
            origin = request.headers.get('origin')
            if not session or not hmac.compare_digest(request.headers.get('x-csrf-token', ''), token(session)) or (origin and not valid_origin(origin, host)):
                return JSONResponse({'error': {'code': 'session_rejected', 'message': '本机会话已失效，请刷新页面'}}, status_code=403)
        elif request.url.path == '/api/session' and request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'error': {'code': 'origin_rejected', 'message': '会话仅允许同源创建'}}, status_code=403)
        response = await next_call(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        return response

    @app.exception_handler(DashboardError)
    async def dashboard_error(request, error):
        return JSONResponse({'error': {'code': error.code, 'message': str(error), 'details': None}}, status_code=error.status)

    @app.get('/api/session')
    def session(request: Request):
        identifier = request.cookies.get('duck_session') or secrets.token_hex(32)
        response = JSONResponse({'schema_version': 1, 'csrf_token': token(identifier)})
        response.set_cookie('duck_session', identifier, httponly=True, samesite='strict', max_age=86400 * 30)
        return response

    @app.get('/api/tasks')
    def tasks():
        return {'items': runs.registry.tasks()}

    @app.get('/api/catalog')
    def catalog():
        return runs.catalog()

    @app.post('/api/history/import')
    def import_history():
        return runs.import_history()

    @app.get('/api/runs/{identifier}/archive')
    def archive(identifier: str):
        return runs.archive_detail(identifier)

    @app.get('/api/runs/{identifier}/artifacts/{artifact_id}')
    def artifact(identifier: str, artifact_id: str):
        path = runs.artifact_path(identifier, artifact_id)
        return FileResponse(path, filename=path.name)

    @app.post('/api/runs/{identifier}/derive')
    def derive(identifier: str, request: DeriveRequest):
        return runs.public(runs.derive(identifier, request))

    @app.get('/api/runs')
    def list_runs():
        return {'items': runs.public(runs.store.all('run'))}

    @app.post('/api/runs/validate')
    def validate(request: ValidationRequest):
        return runs.validate(request)

    @app.post('/api/runs')
    def start(request: StartRequest):
        return runs.public(runs.start(request))

    @app.get('/api/runs/{identifier}')
    def get_run(identifier: str):
        return runs.public(runs.get(identifier))

    @app.post('/api/runs/{identifier}/stop')
    def stop_run(identifier: str, request: StopRequest):
        return runs.public(runs.stop(identifier))

    @app.post('/api/runs/{identifier}/resume')
    def resume_run(identifier: str, request: ResumeRequest):
        return runs.public(runs.resume(identifier, request))

    @app.get('/api/runs/{identifier}/metrics')
    def get_metrics(identifier: str, max_points: int = 1000, keys: str = '', axis: str = 'iteration'):
        return runs.metric_series(identifier, max(10, min(max_points, 20000)), keys.split(',') if keys else None)

    @app.get('/api/runs/{identifier}/events')
    def events(identifier: str, after: int = 0, limit: int = 200):
        items = runs.store.events(identifier, after, max(1, min(limit, 1000)))
        return {'items': items, 'next_cursor': items[-1]['seq'] if items else after}

    @app.get('/api/runs/{identifier}/checkpoints')
    def checkpoints(identifier: str):
        return {'items': runs.public(sorted([item for item in runs.store.all('checkpoint') if item['run_id'] == identifier], key=lambda item: item['model_iteration']))}

    @app.get('/api/resources')
    def list_resources():
        return {'items': [resources.get(name, {'node_id': name, 'label': node['label'], 'execution_kind': node['kind'], 'connection': {'state': 'unprobed', 'last_seen_utc': None}, 'active_run_ids': [], 'active_replay_ids': [], 'samples': []}) for name, node in config['nodes'].items()]}

    @app.post('/api/resources/{identifier}/probe')
    def probe(identifier: str):
        if identifier not in runs.executors:
            raise DashboardError('节点不存在', 'not_found', 404)
        try:
            detail = runs.executors[identifier].probe()
            state = 'connected'
        except Exception as error:
            detail, state = str(error), 'unavailable'
        resource = resources.setdefault(identifier, {'node_id': identifier, 'label': config['nodes'][identifier]['label'], 'execution_kind': config['nodes'][identifier]['kind'], 'samples': [], 'active_run_ids': [], 'active_replay_ids': []})
        resource.update(connection={'state': state, 'last_seen_utc': utcnow()}, detail=detail)
        return resource

    @app.get('/api/replays')
    def list_replays():
        return {'items': [runs.public(replays.get(item['replay_id'])) for item in runs.store.all('replay')]}

    @app.post('/api/replays')
    def create_replay(request: ReplayRequest):
        return runs.public(replays.create(request))

    @app.get('/api/replays/{identifier}')
    def get_replay(identifier: str):
        return runs.public(replays.get(identifier))

    @app.get('/api/replays/{identifier}/frames')
    def replay_frames(identifier: str, after_seq: int = 0, limit: int = 2500):
        return replays.frames(identifier, max(0, after_seq), limit)

    @app.post('/api/replays/{identifier}/control')
    def control_replay(identifier: str, request: ReplayControl):
        return runs.public(replays.control(identifier, request.action, request.speed, request.request_id))

    @app.delete('/api/replays/{identifier}')
    def delete_replay(identifier: str):
        return runs.public(replays.control(identifier, 'close'))

    @app.websocket('/ws')
    async def websocket(socket: WebSocket):
        host, origin = socket.headers.get('host', ''), socket.headers.get('origin', '')
        if host.split(':')[0] not in ('127.0.0.1', 'localhost', 'testserver') or not socket.cookies.get('duck_session') or not valid_origin(origin, host):
            await socket.close(code=1008)
            return
        await socket.accept()
        subscriptions, cursors, frames, snapshots = [], {}, {}, {}
        try:
            while True:
                try:
                    message = await asyncio.wait_for(socket.receive_json(), timeout=.04)
                    if message.get('type') == 'subscribe':
                        subscriptions = message.get('subscriptions', [])[:32]
                except asyncio.TimeoutError:
                    pass
                for subscription in subscriptions:
                    topic, identifier = subscription.get('topic'), subscription.get('id')
                    if topic == 'run':
                        data = runs.public(runs.get(identifier))
                        if time.monotonic() - snapshots.get((topic, identifier), 0) >= 1:
                            await socket.send_json({'type': 'snapshot', 'topic': topic, 'id': identifier, 'time_utc': utcnow(), 'data': data})
                            snapshots[(topic, identifier)] = time.monotonic()
                        items = runs.store.events(identifier, cursors.get(identifier, subscription.get('after_cursor', 0)))
                        for item in items:
                            await socket.send_json({'type': 'event', 'topic': topic, 'id': identifier, 'seq': item['seq'], 'cursor': item['seq'], 'data': item})
                            cursors[identifier] = item['seq']
                    elif topic == 'resource' and identifier in resources:
                        if time.monotonic() - snapshots.get((topic, identifier), 0) >= 2:
                            await socket.send_json({'type': 'snapshot', 'topic': topic, 'id': identifier, 'time_utc': utcnow(), 'data': resources[identifier]})
                            snapshots[(topic, identifier)] = time.monotonic()
                    elif topic == 'replay':
                        replay = replays.get(identifier)
                        frame = replay.get('latest_frame')
                        if frame and frame.get('seq') != frames.get(identifier):
                            await socket.send_json({'type': 'frame', 'topic': topic, 'id': identifier, 'seq': frame['seq'], 'data': frame})
                            frames[identifier] = frame['seq']
                await asyncio.sleep(.04)
        except (WebSocketDisconnect, DashboardError):
            return

    web = Path(__file__).parent / 'web'
    app.mount('/web', StaticFiles(directory=web), name='web')
    app.mount('/studio-model', StaticFiles(directory=ROOT / 'software/studio/model-source-2026103101/web'), name='studio-model')

    @app.get('/')
    def index():
        return FileResponse(web / 'index.html')

    return app


def main():
    import uvicorn
    config = load_config()
    uvicorn.run(create_app(config), host='127.0.0.1', port=config['port'])


if __name__ == '__main__':
    main()
