import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import htm from 'htm';
import { api, mutate } from './api.js';
import { configurationChanges, finiteConfiguration, readPath, rewardFields, taskConfiguration, taskFields, writePath } from './experiment-forms.js';

const html = htm.bind(h);
const taskKey = task => JSON.stringify([task?.task_id, task?.task_version]);
const printable = value => value === undefined ? '未记录' : JSON.stringify(value);

function Field({ field, value, onChange, disabled = false }) {
  const choices = field.choices || field.enum;
  const isBoolean = field.type === 'boolean' || field.type === 'bool' || typeof value === 'boolean';
  const isInteger = field.type === 'integer' || field.type === 'int';
  const isArray = field.type === 'array' || Array.isArray(value);
  return html`<label class=${`field ${isBoolean ? 'checkbox-field' : ''}`}><span>${field.label || field.key}${field.unit ? ` · ${field.unit}` : ''}</span>
    ${choices ? html`<select value=${value} disabled=${disabled} onChange=${event => onChange(event.target.value)}>${choices.map(choice => html`<option value=${typeof choice === 'object' ? choice.value : choice}>${typeof choice === 'object' ? choice.label || choice.value : choice}</option>`)}</select>`
      : isBoolean ? html`<input type="checkbox" checked=${Boolean(value)} disabled=${disabled} onChange=${event => onChange(event.target.checked)}/>`
      : isArray ? html`<input type="text" value=${Array.isArray(value) ? value.join(', ') : ''} disabled=${disabled} onInput=${event => onChange(event.target.value.split(',').map(item => item.trim() ? Number(item) : NaN))}/>`
      : html`<input type="number" required step=${isInteger ? '1' : 'any'} min=${field.min ?? field.minimum} max=${field.max ?? field.maximum} value=${value ?? ''} disabled=${disabled} onInput=${event => onChange(event.target.value === '' ? NaN : Number(event.target.value))}/>`}
    <small>${field.description || field.help || field.key}${field.exclusive_min ? ` · 必须大于 ${field.min}` : ''}${field.exclusive_max ? ` · 必须小于 ${field.max}` : ''}${field.source ? ` · ${field.source}` : ''}</small></label>`;
}

function Overrides({ values, fields, onChange }) {
  const [selected, setSelected] = useState('');
  const available = fields.filter(field => readPath(values, field.key.replace(/^reward_config\./, '')) === undefined);
  const entries = fields.filter(field => readPath(values, field.key.replace(/^reward_config\./, '')) !== undefined);
  const remove = path => {
    const result = structuredClone(values), keys = path.split('.');
    let current = result;
    for (const key of keys.slice(0, -1)) current = current[key];
    delete current[keys.at(-1)];
    onChange(result);
  };
  return html`<div class="override-editor">${entries.map(field => {
    const path = field.key.replace(/^reward_config\./, '');
    return html`<div class="override-row"><${Field} field=${field} value=${readPath(values, path)} onChange=${value => onChange(writePath(values, path, value))}/><button type="button" class="button secondary small" onClick=${() => remove(path)}>移除</button></div>`;
  })}<div class="override-add"><select aria-label="选择奖励覆盖字段" value=${selected} onChange=${event => setSelected(event.target.value)}><option value="">选择要覆盖的奖励参数</option>${available.map(field => html`<option value=${field.key}>${field.label || field.key}</option>`)}</select><button type="button" class="button secondary small" disabled=${!selected || !available.some(field => field.key === selected)} onClick=${() => { const field = available.find(item => item.key === selected); onChange(writePath(values, selected.replace(/^reward_config\./, ''), field.default)); setSelected(''); }}>添加覆盖</button></div></div>`;
}

function RewardEditor({ config, catalog, onChange }) {
  const fields = rewardFields(catalog);
  const schedule = config.schedule || [];
  const presets = catalog.reward_presets || catalog.presets || {};
  return html`<div class="reward-editor"><p class="notice compact">奖励公式与门控按版本固定。基础配置先应用，再应用阶段覆盖，最后应用当前更新进度配方。修改将建立新实验。</p>
    <details class="form-section"><summary>查看各奖励项的公式与启用条件</summary><div class="table-scroll"><table class="archive-table"><thead><tr><th>奖励项</th><th>公式</th><th>符号与单位</th><th>条件</th></tr></thead><tbody>${(catalog.reward_terms || []).map(term => html`<tr><td>${term.label}</td><td>${term.formula}</td><td>${term.sign} · ${term.unit}</td><td>${term.gate}</td></tr>`)}</tbody></table></div></details>
    <label class="field"><span>已登记配方</span><select value="" onChange=${event => { if (event.target.value) onChange(structuredClone(presets[event.target.value]?.config || presets[event.target.value])); }}><option value="">选择配方替换当前奖励设置</option>${Object.keys(presets).map(key => html`<option value=${key}>${presets[key]?.label || key}</option>`)}</select></label>
    <div class="form-grid">${fields.map(field => html`<${Field} field=${field} value=${readPath({ reward_config: config }, field.key)} onChange=${value => onChange(writePath({ reward_config: config }, field.key, value).reward_config)}/>` )}</div>
    ${[1, 2].map(stage => html`<details class="form-section"><summary>阶段 ${stage} 奖励覆盖</summary><${Overrides} fields=${fields} values=${config.stage_overrides?.[stage] || {}} onChange=${values => onChange({ ...config, stage_overrides: { ...(config.stage_overrides || {}), [stage]: values } })}/></details>`)}
    <details class="form-section"><summary>按训练更新进度调整奖励 · ${schedule.length} 个节点</summary><p class="muted compact">更新数从本实验开始累计，续训不归零；每个节点在完整 PPO 更新边界生效。</p>
    ${schedule.map((entry, index) => html`<div class="schedule-entry"><div class="override-row"><label class="field"><span>生效更新数</span><input type="number" required min="0" step="1" value=${entry.update} onInput=${event => onChange({ ...config, schedule: schedule.map((item, position) => position === index ? { ...item, update: event.target.value === '' ? NaN : Number(event.target.value) } : item) })}/></label><button type="button" class="button secondary small" onClick=${() => onChange({ ...config, schedule: schedule.filter((_, position) => position !== index) })}>删除节点</button></div><${Overrides} fields=${fields} values=${entry.values || {}} onChange=${values => onChange({ ...config, schedule: schedule.map((item, position) => position === index ? { ...item, values } : item) })}/></div>`)}
    <button type="button" class="button secondary small" onClick=${() => onChange({ ...config, schedule: [...schedule, { update: schedule.length ? Math.max(...schedule.map(item => item.update)) + 1 : 0, values: {} }] })}>添加进度节点</button></details></div>`;
}

export function TrainingForm({ tasks, selectedTask, draft, onClose, onCreated }) {
  const canCreate = task => !task.legacy_adapter && task.availability?.state === 'ready';
  const preferredTask = tasks.find(task => taskKey(task) === selectedTask && canCreate(task)) || tasks.find(canCreate) || tasks[0];
  const initialTask = draft ? taskKey(draft) : taskKey(preferredTask);
  const [selectedKey, setSelectedKey] = useState(initialTask), [catalog, setCatalog] = useState(null);
  const task = tasks.find(item => taskKey(item) === selectedKey) || (draft ? { ...draft, title: `${draft.task_id} · ${draft.task_version}` } : null);
  const [parameters, setParameters] = useState({}), [base, setBase] = useState({}), [name, setName] = useState(draft?.name || '');
  const [mode, setMode] = useState(draft?.execution?.mode || 'local'), [spark, setSpark] = useState(draft?.execution?.node_ids?.[0] || 'spark1');
  const [validation, setValidation] = useState(null), [busy, setBusy] = useState(false), [error, setError] = useState(null);
  useEffect(() => { let active = true; api('/api/catalog').then(value => { if (active) setCatalog(value); }).catch(failure => { if (active) setError(failure); }); return () => { active = false; }; }, []);
  useEffect(() => {
    if (!catalog) return;
    const resolved = taskConfiguration(catalog, task, draft);
    setParameters(resolved); setBase(structuredClone(resolved)); setValidation(null);
  }, [catalog, selectedKey]);
  const change = (path, value) => { setParameters(writePath(parameters, path, value)); setValidation(null); };
  const supportedFields = taskFields(catalog, task, parameters);
  const fields = supportedFields.filter(field => !field.key.startsWith('reward_config.'));
  const rewardsEditable = supportedFields.some(field => field.key.startsWith('reward_config.'));
  const groups = [...new Set(fields.map(field => field.group || '训练参数'))];
  const changes = configurationChanges(base, parameters);
  const execution = { mode, node_ids: mode === 'local' ? ['local'] : mode === 'dual_spark' ? ['spark1', 'spark2'] : [spark] };
  const validate = async event => {
    event.preventDefault(); setBusy(true); setError(null);
    try {
      if (!finiteConfiguration(parameters)) throw new Error('参数含空值或非有限数字，请修正后校验。');
      const body = { task_id: task.task_id, task_version: task.task_version, execution, parameters };
      if (draft) Object.assign(body, { source_run_id: draft.source_run_id, initialization: draft.initialization || 'scratch', checkpoint_id: draft.checkpoint_id });
      setValidation(await api('/api/runs/validate', { method: 'POST', body }));
    } catch (failure) { setValidation(null); setError(failure); } finally { setBusy(false); }
  };
  const start = async () => {
    setBusy(true); setError(null);
    try { onCreated(await mutate('/api/runs', { validation_id: validation.validation_id, config_hash: validation.config_hash, name: name.trim() || undefined })); }
    catch (failure) { setError(failure); } finally { setBusy(false); }
  };
  return html`<div class="drawer-backdrop"><form class="drawer experiment-drawer" onSubmit=${validate}><header><div><span class="eyebrow">EXPERIMENT CONFIGURATION</span><h2>${draft?.initialization === 'warm' ? '接策略权重建立新实验' : draft ? '复制配置从零重训' : '新建训练实验'}</h2></div><button type="button" class="icon-button" aria-label="关闭配置" onClick=${onClose}>×</button></header><div class="drawer-body">
    <label class="field"><span>任务与版本</span><select value=${selectedKey} disabled=${Boolean(draft)} onChange=${event => setSelectedKey(event.target.value)}>${draft && !tasks.some(item => taskKey(item) === selectedKey) && html`<option value=${selectedKey}>${draft.task_id} · ${draft.task_version}</option>`}${tasks.map(item => html`<option value=${taskKey(item)}>${item.title} · ${item.task_version}</option>`)}</select><small>${task?.description}</small></label>
    <label class="field"><span>实验名称</span><input value=${name} maxLength="120" onInput=${event => setName(event.target.value)}/></label>
    ${draft && html`<p class="notice compact">来源运行：${draft.source_run_id}${draft.checkpoint_id ? `；来源检查点：${draft.checkpoint_id}` : ''}。${draft.initialization === 'warm' ? '只接入 actor 与观测归一化；critic、优化器、探索标准差、随机状态、课程和预算重新初始化。' : '保留来源配置与版本记录，策略从零训练，使用新预算。'}</p>`}
    <h3>计算资源</h3><div class="environment-options">${[['local', '本地 GPU'], ['single_spark', '单 Spark'], ['dual_spark', '双 Spark']].map(([key, label]) => html`<button type="button" class=${`env-option ${mode === key ? 'selected' : ''}`} onClick=${() => { setMode(key); setValidation(null); }}><strong>${label}</strong></button>`)}</div>
    ${mode === 'single_spark' && html`<label class="field"><span>Spark 节点</span><select value=${spark} onChange=${event => { setSpark(event.target.value); setValidation(null); }}><option value="spark1">Spark 1</option><option value="spark2">Spark 2</option></select></label>`}
    ${groups.map(group => html`<details class="form-section" open><summary>${group}</summary><div class="form-grid">${fields.filter(field => (field.group || '训练参数') === group).map(field => html`<${Field} field=${field} value=${readPath(parameters, field.key)} onChange=${value => change(field.key, value)}/>` )}</div></details>`)}
    ${catalog && rewardsEditable ? html`<details class="form-section"><summary>奖励设计与阶段配方</summary><${RewardEditor} config=${parameters.reward_config || catalog.default_rewards || catalog.defaults?.reward_config || {}} catalog=${catalog} onChange=${value => change('reward_config', value)}/></details>` : html`<p class="notice compact">此版本保留原奖励与课程合同，只开放该任务登记的训练字段。历史配置不补入当前版本的奖励默认值。</p>`}
    <details class="form-section"><summary>锁定项与参数来源</summary><p class="muted compact">物理、接口、网络、终止规则及验收标准按任务版本锁定。默认值来自历史采用配置，不代表最优值。</p><pre>${JSON.stringify(catalog?.locked_fields || (catalog?.fields || []).filter(field => field.locked), null, 2)}</pre></details>
    <details class="form-section" open=${changes.length > 0}><summary>本次配置改动 · ${changes.length} 项</summary>${changes.length ? html`<div class="table-scroll"><table class="archive-table"><thead><tr><th>字段</th><th>来源值</th><th>新值</th></tr></thead><tbody>${changes.map(item => html`<tr><td>${item.path}</td><td>${printable(item.before)}</td><td>${printable(item.after)}</td></tr>`)}</tbody></table></div>` : html`<p class="muted compact">当前与来源配置一致。</p>`}</details>
    <div class="budget-box"><div><span>每轮转换数</span><strong>${Number.isFinite(parameters.num_envs * parameters.num_steps_per_env) ? (parameters.num_envs * parameters.num_steps_per_env).toLocaleString('zh-CN') : '—'}</strong></div><div><span>本实验预算</span><strong>${Number.isFinite(parameters.num_envs * parameters.num_steps_per_env * parameters.max_updates) ? (parameters.num_envs * parameters.num_steps_per_env * parameters.max_updates).toLocaleString('zh-CN') : '—'}</strong></div></div>
    ${error && html`<div class="notice error" role="alert">${error.message}</div>`}${validation && html`<div class=${`notice ${validation.valid ? 'success' : 'error'}`}><strong>${validation.valid ? '配置与预算校验通过' : '配置需要修正'}</strong>${[...(validation.errors || []), ...(validation.warnings || [])].map(item => html`<p>${typeof item === 'string' ? item : `${item.field || ''} ${item.message}`}</p>`)}<p>${validation.allocation?.map(item => `${item.node_id}：${item.num_envs} 环境`).join('；')}</p></div>`}
    <p class="muted compact">启动后配置冻结；浏览器关闭不停止训练。归档和训练完成状态与行为验收结果分别记录。</p>
    </div><footer><button type="button" class="button secondary" onClick=${onClose}>取消</button>${validation?.valid ? html`<button type="button" class="button primary" disabled=${busy} onClick=${start}>${busy ? '正在创建…' : '启动新实验'}</button>` : html`<button class="button primary" disabled=${busy || !catalog || !task}>${busy ? '正在校验…' : '校验配置与预算'}</button>`}</footer></form></div>`;
}
