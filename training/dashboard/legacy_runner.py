from __future__ import annotations

import argparse
import json
import signal
import threading
from dataclasses import fields
from pathlib import Path

from experiment_archive import register_runtime


def main():
    parser = argparse.ArgumentParser(description='原冻结运行时的外置训练登记适配器')
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--workflow-record', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--experiment-dir', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--stop-file', type=Path)
    parser.add_argument('--resume-manifest', type=Path)
    args = parser.parse_args()
    values = json.loads(args.config.read_text(encoding='utf-8'))
    workflow = json.loads(args.workflow_record.read_text(encoding='utf-8'))
    register_runtime(args.output, workflow, values, run_id=args.run_id, source_root=Path.cwd().parent)
    from mjlab_duck import train_locomotion as runtime
    from mjlab_duck.locomotion_train_cfg import LocomotionTrainConfig, CurriculumConfig
    expected = {field.name for field in fields(LocomotionTrainConfig)}
    if set(values) - expected:
        raise ValueError('旧运行时配置字段不兼容')
    for name in ('stage1', 'stage2'):
        if isinstance(values.get(name), dict):
            values[name] = CurriculumConfig(**values[name])
    config = LocomotionTrainConfig(**values)
    signal.signal(signal.SIGINT, runtime.request_stop)
    signal.signal(signal.SIGTERM, runtime.request_stop)
    finished = threading.Event()
    def watch_stop():
        while not finished.wait(.25):
            if args.stop_file and args.stop_file.exists():
                runtime.request_stop(None, None)
                return
    threading.Thread(target=watch_stop, daemon=True).start()
    runner, env, coordinator = runtime.build_runtime(config)
    try:
        runtime.train_loop(runner, env, config, output_dir=args.output, experiment_dir=args.experiment_dir,
                           resume_manifest=args.resume_manifest, coordinator=coordinator)
    finally:
        finished.set()
        env.close()
        if runtime.distributed.is_initialized():
            runtime.distributed.destroy_process_group()


if __name__ == '__main__':
    main()
