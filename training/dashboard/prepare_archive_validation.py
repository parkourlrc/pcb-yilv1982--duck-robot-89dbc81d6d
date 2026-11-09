from pathlib import Path
import json

from dashboard.archive import workflow_for
from dashboard.registry import Registry
from experiment_archive import write_record
from mjlab_duck.experiment_config import resolve_config


def main():
    root = Path(__file__).resolve().parents[2]
    directory = root / 'docs/specs/20261109-训练档案与复训/checks'
    task = Registry(root).get('locomotion', 'v3')
    common = {'num_envs': 4, 'num_steps_per_env': 8, 'num_mini_batches': 4,
              'num_learning_epochs': 1, 'save_interval': 1, 'eval_interval': 100,
              'diagnostic_interval': 100, 'seed': 42}
    for name, updates in (('scratch', 2), ('warm', 1)):
        config = resolve_config({**common, 'max_updates': updates})
        budget = {'transitions_per_update': 32, 'max_transitions': 32 * updates}
        workflow = workflow_for(task, config, budget)
        workflow['purpose'] = '归档与复训最小验收，非正式策略优化；scratch一轮后原状态续训一轮，warm一轮，总96转换'
        workflow['steps'][2].update(status='passed', evidence=['training/artifacts/implementation-checks/runtime-fixed-input.json'])
        workflow['steps'][3].update(status='confirmed', evidence=['docs/specs/20261109-训练档案与复训/spec.md', 'docs/specs/20261109-训练档案与复训/checks/' + name + '-config.json'])
        write_record(directory / (name + '-config.json'), config)
        write_record(directory / (name + '-workflow.json'), workflow)
    write_record(directory / 'validation-budget.json', {'registered_before_training': True,
                 'scratch_updates': 1, 'resume_updates': 1, 'warm_updates': 1, 'num_envs': 4,
                 'steps_per_update': 8, 'total_training_transitions': 96, 'formal_policy_training': False})
    print(json.dumps({'directory': str(directory), 'max_transitions': 96}))


if __name__ == '__main__':
    main()
