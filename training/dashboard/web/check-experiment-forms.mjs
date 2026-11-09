import assert from 'node:assert/strict';
import { configurationChanges, finiteConfiguration, mergeConfig, readPath, rewardFields, taskConfiguration, taskFields, writePath } from './experiment-forms.js';

const source = { stage2: { probabilities: [.2, .3, .3, .15, .05] }, reward_config: { terms: { smooth: { enabled: true, weight: .05 } } } };
const changed = writePath(source, 'stage2.probabilities.0', .1);
assert.ok(Array.isArray(changed.stage2.probabilities));
assert.equal(readPath(changed, 'stage2.probabilities.0'), .1);
assert.equal(source.stage2.probabilities[0], .2);
assert.deepEqual(configurationChanges(source, changed), [{ path: 'stage2.probabilities', before: source.stage2.probabilities, after: changed.stage2.probabilities }]);
const merged = mergeConfig(source, { reward_config: { terms: { smooth: { weight: .4 } } } });
assert.equal(merged.reward_config.terms.smooth.enabled, true);
assert.equal(source.reward_config.terms.smooth.weight, .05);
assert.equal(finiteConfiguration({ config: { values: [1, NaN] } }), false);
assert.equal(finiteConfiguration({ config: { value: Infinity } }), false);
assert.equal(finiteConfiguration(merged), true);
assert.deepEqual(rewardFields({ fields: [
  { key: 'reward_config.terms.smooth.weight' },
  { key: 'reward_config.terms.failure.enabled', locked: true },
  { key: 'reward_config.schedule' },
  { key: 'stage2.probabilities.0' },
] }), [{ key: 'reward_config.terms.smooth.weight' }]);
const catalog = { runtime_version: 'locomotion-v3', defaults: { learning_rate: .001, reward_config: source.reward_config }, fields: [{ key: 'learning_rate' }, { key: 'stage2.probabilities.0' }, { key: 'reward_config.terms.smooth.weight' }] };
const legacyTask = { runtime_version: 'locomotion-v1', legacy_adapter: true, default_execution: { learning_rate: .0003 }, editable_execution: ['learning_rate'] };
assert.deepEqual(taskConfiguration(catalog, legacyTask), { learning_rate: .0003 });
assert.deepEqual(taskFields(catalog, legacyTask, legacyTask.default_execution), [{ key: 'learning_rate' }]);
assert.deepEqual(taskConfiguration(catalog, { runtime_version: 'locomotion-v3' }), catalog.defaults);
assert.deepEqual(taskConfiguration(catalog, legacyTask, { parameters: source }), source);
console.log('训练表单：嵌套数组、不可变编辑、配置差异、非有限值和可调字段检查通过。');

if (process.argv[2]) {
  const origin = new URL(process.argv[2]);
  const get = async path => {
    const response = await fetch(new URL(path, origin));
    assert.equal(response.ok, true, `${path}: ${response.status}`);
    return response.json();
  };
  const [actualCatalog, taskResponse, runResponse] = await Promise.all([get('/api/catalog'), get('/api/tasks'), get('/api/runs')]);
  const tasks = taskResponse.items || taskResponse;
  const runs = runResponse.items || runResponse;
  assert.equal(new Set(tasks.map(task => JSON.stringify([task.task_id, task.task_version]))).size, tasks.length, '任务版本目录不得重复');
  let inspectedTasks = 0, inspectedArchives = 0, inspectedRewardDocuments = 0;
  for (const task of tasks) {
    const parameters = taskConfiguration(actualCatalog, task);
    const fields = taskFields(actualCatalog, task, parameters);
    assert.equal(finiteConfiguration(parameters), true);
    assert.ok(fields.every(field => readPath(parameters, field.key) !== undefined), `${task.task_version}: 可见字段需要已记录值`);
    assert.ok(fields.every(field => !field.locked));
    if (task.runtime_version !== actualCatalog.runtime_version) {
      assert.ok(fields.every(field => !field.key.startsWith('reward_config.')));
      assert.deepEqual(parameters, task.default_execution?.parameters || task.default_execution || {});
    } else {
      assert.ok(rewardFields(actualCatalog).length > 0);
      assert.deepEqual(parameters.stage1.probabilities, [0, 1, 0, 0, 0]);
    }
    inspectedTasks += 1;
  }
  const selectedRuns = [...new Map([...runs.filter(item => item.config).slice(0, 8), ...runs.filter(item => item.run_id === 'legacy-run-001')].map(item => [item.run_id, item])).values()];
  for (const run of selectedRuns) {
    const archive = await get(`/api/runs/${encodeURIComponent(run.run_id)}/archive`);
    const sourceConfig = structuredClone(archive.config);
    const draftConfig = taskConfiguration(actualCatalog, {}, { parameters: sourceConfig });
    assert.deepEqual(draftConfig, sourceConfig);
    assert.deepEqual(configurationChanges(sourceConfig, draftConfig), []);
    for (const capability of ['browse', 'replay', 'scratch', 'warm', 'resume']) {
      assert.equal(typeof archive.capabilities[capability]?.allowed, 'boolean');
      assert.ok(Array.isArray(archive.capabilities[capability]?.reasons));
    }
    const workflow = Array.isArray(archive.workflow) ? archive.workflow : archive.workflow?.steps;
    assert.ok(Array.isArray(workflow));
    assert.ok(Array.isArray(archive.config_diff));
    assert.ok(archive.artifacts.every(item => typeof item.artifact_id === 'string' && typeof item.available === 'boolean'));
    for (const document of archive.reward_design?.documents || []) {
      assert.ok(document.label && document.path && document.artifact_id && document.url);
      assert.ok(archive.artifacts.some(item => item.artifact_id === document.artifact_id), '奖励来源文档必须属于该运行档案');
      if (inspectedRewardDocuments === 0) {
        const response = await fetch(new URL(document.url, origin));
        assert.equal(response.ok, true, '奖励来源文档可直接读取');
        assert.ok((await response.text()).length > 0);
      }
      inspectedRewardDocuments += 1;
    }
    inspectedArchives += 1;
  }
  console.log(JSON.stringify({ source: origin.origin, catalogFields: actualCatalog.fields.length, inspectedTasks, inspectedArchives, inspectedRewardDocuments, checks: '真实 API 字段显隐、旧版配置隔离、阶段约束、配置差异及档案结构', browserRendered: false }));
}
