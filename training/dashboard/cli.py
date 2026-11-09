from __future__ import annotations

import argparse
import json
import uuid
import time
from pathlib import Path

from .config import ROOT, load_config
from .runs import ACTIVE, Runs
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


def main():
    parser = argparse.ArgumentParser(description='训练平台共用登记、校验、冻结与归档入口')
    parser.add_argument('--dashboard-config', type=Path)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('catalog')
    commands.add_parser('import-history')
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
    manager = Runs(ROOT, load_config(args.dashboard_config))
    if args.command == 'catalog':
        result = manager.catalog()
    elif args.command == 'import-history':
        result = manager.import_history()
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
