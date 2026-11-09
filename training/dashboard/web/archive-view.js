import { h } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import htm from 'htm';
import { api, mutate } from './api.js';

const html = htm.bind(h);
const valueText = value => value == null ? '未记录' : typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value);
const labels = { complete: '完整', partial: '部分归档', incomplete: '归档不完整', missing: '缺失', pending: '待验证', verified: '已验证', passed: '通过', confirmed: '已确认', reused: '复用已有证据', in_progress: '进行中', completed: '已完成', interrupted: '已中断', failed: '失败', unavailable: '不可用', not_applicable: '不适用', syncing: '同步中', collecting: '持续归档中', sync_failed: '同步失败', error: '归档错误', recorded: '已记录' };
const capabilityLabels = { browse: '浏览档案', replay: '仿真回放', scratch: '从零复训', warm: '接策略权重', resume: '原状态续训' };
const binaryArtifact = item => /checkpoint|binary/.test(item.kind || '') || /\.(pt|onnx|npz|npy|zip|gz)$/i.test(item.path || '');

function DataBlock({ title, value, open = false }) {
  return html`<details class="panel archive-block" open=${open}><summary>${title}</summary><pre>${valueText(value)}</pre></details>`;
}

export function ArchiveView({ run, checkpoints = [], onDraft, notify }) {
  const [archive, setArchive] = useState(null), [error, setError] = useState(null), [busy, setBusy] = useState(false);
  const [checkpointId, setCheckpointId] = useState(''), [artifact, setArtifact] = useState(null), [content, setContent] = useState(null), [contentError, setContentError] = useState(null);
  const [catalog, setCatalog] = useState(null);
  const artifactRequest = useRef(0);
  useEffect(() => {
    let active = true;
    setArchive(null); setArtifact(null); setContent(null); setError(null); artifactRequest.current += 1;
    const load = async () => { try { const result = await api(`/api/runs/${encodeURIComponent(run.run_id)}/archive`); if (active) { setArchive(result); setError(null); } } catch (failure) { if (active) setError(failure); } };
    load(); const timer = setInterval(load, 15000);
    return () => { active = false; artifactRequest.current += 1; clearInterval(timer); };
  }, [run.run_id]);
  useEffect(() => { let active = true; api('/api/catalog').then(result => { if (active) setCatalog(result); }).catch(() => {}); return () => { active = false; }; }, []);
  useEffect(() => { setCheckpointId(''); }, [run.run_id]);
  const capabilities = archive?.capabilities || run.capabilities || {};
  const derive = async mode => {
    setBusy(true);
    try {
      const response = await mutate(`/api/runs/${encodeURIComponent(run.run_id)}/derive`, { mode, ...(mode === 'warm' ? { checkpoint_id: checkpointId } : {}) });
      onDraft(response.draft || response);
    } catch (failure) { notify(failure); } finally { setBusy(false); }
  };
  const openArtifact = item => {
    const request = ++artifactRequest.current;
    setArtifact(item); setContent(null); setContentError(null);
    if (!item.available || binaryArtifact(item) || /video|image/.test(item.kind || '') || /\.(mp4|webm|png|jpg|jpeg)$/i.test(item.path || '')) return;
    const url = item.url || `/api/runs/${encodeURIComponent(run.run_id)}/artifacts/${encodeURIComponent(item.artifact_id)}`;
    fetch(url, { credentials: 'same-origin' }).then(async response => {
      if (!response.ok) throw new Error(`读取失败（${response.status}）`);
      const reader = response.body.getReader(), decoder = new TextDecoder();
      let text = '', truncated = false;
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        text += decoder.decode(value, { stream: true });
        if (text.length > 200000) { text = text.slice(0, 200000); truncated = true; await reader.cancel(); break; }
      }
      if (request === artifactRequest.current) setContent(text + (truncated ? '\n\n[预览已截断，可下载完整文件]' : ''));
    }).catch(failure => { if (request === artifactRequest.current) setContentError(failure); });
  };
  const workflow = Array.isArray(archive?.workflow) ? archive.workflow : archive?.workflow?.steps || [];
  const rewardDesign = archive?.reward_design;
  const terms = rewardDesign?.catalog?.reward_terms || (Array.isArray(rewardDesign?.catalog) ? rewardDesign.catalog : null);
  const rewardDocuments = rewardDesign?.documents || [];
  const missing = archive?.integrity?.missing || [];
  return html`<div class="archive-view"><div class="section-heading"><div><span class="eyebrow">EXPERIMENT ARCHIVE</span><h2>实验档案与复训</h2></div><span class="badge">${labels[archive?.integrity?.state] || archive?.integrity?.state || '正在读取'}</span></div>
    ${error && html`<p class="notice error">${error.message}；已取得的档案保留显示。</p>`}
    <section class="panel archive-block"><h3>可用能力</h3><div class="capability-grid">${Object.entries(capabilityLabels).map(([key, label]) => html`<div class=${`capability ${capabilities[key]?.allowed ? 'enabled' : ''}`}><strong>${label} · ${capabilities[key]?.allowed ? '可用' : '不可用'}</strong><p>${capabilities[key]?.reasons?.join('；') || (capabilities[key]?.allowed ? '所需材料可用' : '尚无可验证的完整材料')}</p></div>`)}</div><div class="derive-controls"><button class="button secondary" disabled=${busy || !capabilities.scratch?.allowed} onClick=${() => derive('scratch')}>复制配置从零重训</button><label class="field"><span>接权重来源检查点（rank0）</span><select value=${checkpointId} onChange=${event => setCheckpointId(event.target.value)}><option value="">选择检查点</option>${checkpoints.map(item => html`<option value=${item.checkpoint_id}>第 ${item.model_iteration ?? '—'} 轮 · ${item.checkpoint_id}</option>`)}</select></label><button class="button secondary" disabled=${busy || !checkpointId || !capabilities.warm?.allowed} onClick=${() => derive('warm')}>接策略权重建立新实验</button></div><p class="muted compact">以上操作只创建配置草稿，校验后才能启动新实验。原状态续训在“检查点与回放”中操作，沿用原预算。</p></section>
    ${(missing.length > 0 || archive?.integrity?.errors?.length > 0) && html`<section class="notice"><strong>档案缺口与核验结果</strong>${[...missing, ...(archive?.integrity?.errors || [])].map(item => html`<p>${valueText(item)}</p>`)}</section>`}
    <section class="panel archive-block"><h3>训练流程</h3>${workflow.length ? html`<div class="workflow-grid">${workflow.map(step => html`<details class="workflow-step"><summary><b>${step.number} · ${step.name}</b><span>${labels[step.status] || step.status || '未记录'}</span></summary><dl>${[['输入', step.inputs], ['输出', step.outputs], ['证据', step.evidence]].map(([label, value]) => html`<div><dt>${label}</dt><dd><pre>${valueText(value)}</pre></dd></div>`)}</dl></details>`)}</div>` : html`<p class="muted compact">此记录未保存逐步流程证据，不以训练文件存在补记通过。</p>`}</section>
    <${DataBlock} title="任务、版本与来源" value=${{ run_id: run.run_id, experiment_id: run.experiment_id, task_id: run.task_id, task_version: run.task_version, parent_run_id: run.parent_run_id, parent_checkpoint_id: run.parent_checkpoint_id, initialization: archive?.initialization || run.initialization, source: archive?.provenance || archive?.source || run.source, execution: run.execution }}/>
    <section class="panel archive-block"><h3>与来源配置的差异</h3>${archive?.config_diff?.length ? html`<div class="table-scroll"><table class="archive-table"><thead><tr><th>字段</th><th>来源值</th><th>本次值</th></tr></thead><tbody>${archive.config_diff.map(item => html`<tr><td>${item.path}</td><td>${valueText(item.before)}</td><td>${valueText(item.after)}</td></tr>`)}</tbody></table></div>` : html`<p class="muted compact">${run.parent_run_id ? '未记录差异或配置相同；以冻结配置为准。' : '无父运行配置可比较。'}</p>`}</section>
    <${DataBlock} title="实际训练配置（冻结快照）" value=${archive?.config || run.config}/>
    ${rewardDocuments.length > 0 && html`<section class="panel archive-block"><h3>奖励设计的历史文档与冻结实现</h3><p class="muted compact">以下材料来自该运行的存档，用于核对当时配方和实现。</p><div class="reward-documents">${rewardDocuments.map(item => html`<a class="button secondary small" href=${item.url || `/api/runs/${encodeURIComponent(run.run_id)}/artifacts/${encodeURIComponent(item.artifact_id)}`} target="_blank" rel="noopener noreferrer">${item.label || item.path}</a>`)}</div></section>`}
    <section class="panel archive-block"><h3>奖励设计 · ${rewardDesign?.version || '版本未记录'}</h3><p class="muted compact">不同奖励版本的总回报不直接排名；行为结论依据各自预设评估标准。</p>${terms?.length ? html`<div class="table-scroll"><table class="archive-table"><thead><tr><th>奖励项</th><th>公式与符号</th><th>启用条件</th><th>单位</th></tr></thead><tbody>${terms.map(term => html`<tr><td>${term.label || term.key}</td><td>${term.formula || '未记录'}${term.sign != null ? `（符号 ${term.sign}）` : ''}</td><td>${term.gate || '未记录'}</td><td>${term.unit || '未记录'}</td></tr>`)}</tbody></table></div>` : html`<p class="notice compact">此历史记录未保存结构化奖励说明，不能用当前奖励目录冒充当时设计。请查看来源代码和研究文档。</p>`}<details><summary>奖励配置与阶段配方原始记录</summary><pre>${valueText(rewardDesign?.config || archive?.config?.reward_config)}</pre></details></section>
    <section class="panel archive-block"><h3>日志、评估、视频与文件</h3><p class="muted compact">归档文件可离线读取；未采集的指标和轨迹不补零。</p><div class="table-scroll"><table class="archive-table"><thead><tr><th>文件</th><th>类型</th><th>大小</th><th>状态</th><th>操作</th></tr></thead><tbody>${(archive?.artifacts || []).map(item => html`<tr><td><span class="artifact-path">${item.path}</span><small>${item.sha256 ? `SHA256 ${item.sha256}` : '哈希未记录'}</small></td><td>${item.kind}</td><td>${item.size == null ? '未记录' : `${(item.size / 1024).toFixed(1)} KiB`}</td><td>${item.available ? '可读' : '缺失'}</td><td><button class="button secondary small" disabled=${!item.available} onClick=${() => openArtifact(item)}>查看</button></td></tr>`)}</tbody></table></div>${!archive?.artifacts?.length && html`<p class="muted compact">暂无已登记产物。</p>`}
    ${artifact && html`<div class="artifact-preview"><div class="card-heading"><h3>${artifact.path}</h3><a class="button secondary small" href=${artifact.url || `/api/runs/${encodeURIComponent(run.run_id)}/artifacts/${encodeURIComponent(artifact.artifact_id)}`} download>下载完整文件</a></div>${/\.(mp4|webm)$/i.test(artifact.path) ? html`<video controls preload="metadata" src=${artifact.url}/>` : /\.(png|jpg|jpeg)$/i.test(artifact.path) ? html`<img alt=${artifact.path} src=${artifact.url}/>` : html`<pre>${contentError?.message || content || (binaryArtifact(artifact) ? '二进制产物，请下载查看。' : '正在读取…')}</pre>`}</div>`}</section>
    <${DataBlock} title="当前平台可调字段目录（不代表历史配置）" value=${catalog?.fields || '尚未取得字段目录'}/>
  </div>`;
}
