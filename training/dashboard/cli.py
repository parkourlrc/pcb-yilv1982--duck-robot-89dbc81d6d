from __future__ import annotations

import argparse
import json
import os
import uuid
import time
from pathlib import Path

from .config import ROOT, load_config
from .environment_probe import ensure_scripts
from .runs import ACTIVE, Runs
from .store import atomic_json
from .schemas import DeriveRequest, ResumeRequest, StartRequest, ValidationRequest


def monitor(manager, run):
    try:
        while run['state'] in ACTIVE or run.get('_archive_pending'):
            run = manager.refresh(run['run_id'])
            for node in run['execution']['node_ids']:
                try:
                    manager.record_resource(node, manager.executors[node].sample())
                except Exception as error:
                    manager.store.event(run['run_id'], {'type': 'resource_unavailable', 'message': str(error)})
            if run['state'] in ACTIVE or run.get('_archive_pending'):
                time.sleep(2)
    except KeyboardInterrupt:
        manager.store.event(run['run_id'], {'type': 'monitor_detached', 'message': 'CLI监视已退出；训练监督进程继续运行，重新打开平台继续同步归档'})
        print(json.dumps({'run_id': run['run_id'], 'monitor': 'detached', 'training': 'continues under supervisor'}, ensure_ascii=False))
    return manager.public(manager.get(run['run_id']))


def register_environment(args):
    path = Path(args.dashboard_config or os.environ.get('DUCK_DASHBOARD_CONFIG', ROOT / 'training/dashboard.local.json'))
    data = json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    nodes = data.setdefault('nodes', {})
    node = nodes.setdefault(args.environment, {})
    node['name'] = args.name
    if args.hardware:
        node['hardware'] = args.hardware
    if args.kind:
        node['kind'] = args.kind
    for key in ('distribution', 'python', 'work_root', 'ssh_target', 'benchmark_root', 'env_file', 'master_addr', 'image'):
        value = getattr(args, key, None)
        if value:
            node[key] = value
    identity = node.setdefault('identity', {})
    for key, value in (('hostname', args.hostname), ('gpu_name', args.gpu_name), ('wsl_distro', args.wsl_distro)):
        if value:
            identity[key] = value
    if not identity:
        node.pop('identity', None)
    probe = node.setdefault('probe', {})
    if args.gpu:
        probe['gpu'] = args.gpu
    if args.docker:
        probe['docker'] = True
    if args.image:
        probe['image'] = args.image
    if args.env_key:
        probe['env_keys'] = list(dict.fromkeys(args.env_key))
    if args.benchmark:
        probe['benchmark'] = True
    if args.timeout_s:
        probe['timeout_s'] = args.timeout_s
    if not probe:
        node.pop('probe', None)
    atomic_json(path, data)
    config = load_config(path)
    scripts = ensure_scripts(config['data_dir'], config['nodes'])
    return {
        'path': str(path),
        'environment': {key: node.get(key) for key in ('name', 'hardware', 'kind', 'identity', 'probe')},
        'probe_script': str(scripts[args.environment]),
    }

def main():
    parser = argparse.ArgumentParser(description='训练平台共用登记、校验、冻结与归档入口')
    parser.add_argument('--dashboard-config', type=Path)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('catalog')
    commands.add_parser('import-history')
    commands.add_parser('self')
    commands.add_parser('environments')
    probe_environment = commands.add_parser('probe-environment')
    probe_environment.add_argument('environment')
    register = commands.add_parser('register-environment')
    register.add_argument('environment')
    register.add_argument('--name', required=True)
    register.add_argument('--hardware')
    register.add_argument('--kind', choices=('wsl', 'ssh'))
    register.add_argument('--hostname')
    register.add_argument('--gpu-name')
    register.add_argument('--wsl-distro')
    register.add_argument('--distribution')
    register.add_argument('--python')
    register.add_argument('--work-root')
    register.add_argument('--ssh-target')
    register.add_argument('--benchmark-root')
    register.add_argument('--env-file')
    register.add_argument('--master-addr')
    register.add_argument('--image')
    register.add_argument('--gpu', choices=('torch', 'nvidia-smi'))
    register.add_argument('--docker', action='store_true')
    register.add_argument('--env-key', action='append', default=[])
    register.add_argument('--benchmark', action='store_true')
    register.add_argument('--timeout-s', type=int)
    inspect = commands.add_parser('archive')
    inspect.add_argument('run_id')
    derive = commands.add_parser('derive')
    derive.add_argument('run_id')
    derive.add_argument('--mode', choices=('scratch', 'warm'), default='scratch')
    derive.add_argument('--checkpoint-id')
    resume = commands.add_parser('resume')
    resume.add_argument('run_id')
    resume.add_argument('--checkpoint-id', required=True)
    for name in ('validate', 'start'):
        command = commands.add_parser(name)
        command.add_argument('request', type=Path)
        command.add_argument('--name', default='CLI训练运行')
    args = parser.parse_args()
    if args.command == 'register-environment':
        print(json.dumps(register_environment(args), ensure_ascii=False, indent=2))
        return
    manager = Runs(ROOT, load_config(args.dashboard_config))
    if args.command == 'catalog':
        result = manager.catalog()
    elif args.command == 'import-history':
        result = manager.import_history()
    elif args.command == 'self':
        result = {'host': manager.host, 'environment_id': manager.self_id, **(manager.identity_report or {})}
    elif args.command == 'environments':
        from .environment_probe import probe_directory
        scripts = probe_directory(manager.data)
        result = {'self': {'environment_id': manager.self_id, **(manager.identity_report or {})},
                  'items': [{'id': node_id, 'name': node.get('name') or node.get('label'), 'kind': node.get('kind'),
                             'hardware': node.get('hardware'), 'identity': node.get('identity'),
                             'probe_script': str(scripts / (str(node_id) + '.sh')), 'probe': node.get('probe')}
                            for node_id, node in manager.config['nodes'].items()]}
    elif args.command == 'probe-environment':
        if args.environment not in manager.executors:
            raise SystemExit('未知环境: ' + args.environment)
        try:
            result = manager.executors[args.environment].probe_result()
            result['state'] = 'ready' if result['ready'] else 'unavailable'
        except Exception as error:
            result = {'ready': False, 'state': 'offline', 'checks': [], 'detail': str(error)}
    elif args.command == 'archive':
        result = manager.archive_detail(args.run_id)
    elif args.command == 'derive':
        result = manager.derive(args.run_id, DeriveRequest(request_id=uuid.uuid4().hex, mode=args.mode, checkpoint_id=args.checkpoint_id))
    elif args.command == 'resume':
        run = manager.resume(args.run_id, ResumeRequest(request_id=uuid.uuid4().hex, checkpoint_id=args.checkpoint_id), background=False)
        manager._prepare_launch(run['run_id'])
        result = monitor(manager, manager.get(run['run_id']))
    else:
        data = json.loads(args.request.read_text(encoding='utf-8-sig'))
        data.pop('name', None)
        result = manager.validate(ValidationRequest(**data))
        if args.command == 'start' and result['valid']:
            run = manager.start(StartRequest(request_id=uuid.uuid4().hex, validation_id=result['validation_id'], config_hash=result['config_hash'], name=args.name), background=False)
            manager._prepare_launch(run['run_id'])
            result = monitor(manager, manager.get(run['run_id']))
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    if result.get('valid') is False or result.get('state') == 'failed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
