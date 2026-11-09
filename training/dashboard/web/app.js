import { h, render } from 'preact';
import { useCallback, useEffect, useRef, useState } from 'preact/hooks';
import htm from 'htm';
import { api, connect, mutate, onConnection, readRunEvents, subscribe } from './api.js';
import { Chart } from './charts.js';
import { StudioReplay } from './studio-model.js';
import { mergeReplayFrames, normalizeFrame } from './replay-frames.js';
import { TrainingForm } from './training-form.js';
import { ArchiveView } from './archive-view.js';

const html = htm.bind(h);
const integer = value => value == null ? '—' : Number(value).toLocaleString('zh-CN');
const decimal = (value, places = 2) => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toFixed(places);
const duration = value => value == null ? '—' : value >= 3600 ? `${Math.floor(value / 3600)}时 ${Math.floor(value % 3600 / 60)}分` : value >= 60 ? `${Math.floor(value / 60)}分 ${Math.floor(value % 60)}秒` : `${Math.floor(value)}秒`;
const bytes = value => value == null ? '—' : value >= 1024 ** 3 ? `${(value / 1024 ** 3).toFixed(1)} GiB` : value >= 1024 ** 2 ? `${(value / 1024 ** 2).toFixed(1)} MiB` : `${(value / 1024).toFixed(1)} KiB`;
const list = value => Array.isArray(value) ? value : value?.items || [];
const stateNames = { offline_archive: '历史归档', unavailable: '不可用', closing: '释放中', closed: '已释放', connecting: '连接中', preparing: '准备中', initializing: '初始化', starting: '启动中', running: '训练中', training: '训练中', evaluating: '评估中', saving: '保存中', stopping: '停止中', stopped: '已停止', completed: '已完成', finished: '已结束', budget_exhausted: '预算已用完', failed: '失败', error: '错误', unknown: '状态未知', connected: '已连接', online: '在线', disconnected: '连接中断', offline: '离线', stale: '数据过期', available: '可用', ready: '就绪', playing: '播放中', paused: '已暂停', ended: '回放结束', released: '已释放', loading: '加载中' };
const stateName = state => stateNames[state] || state || '未知';
const errorText = error => error?.message || String(error || '');
const allowed = capability => typeof capability === 'boolean' ? capability : Boolean(capability?.allowed);
const taskKey = task => task ? JSON.stringify([task.task_id, task.task_version]) : '';
const runState = run => run?.completion_reason === 'budget_exhausted' ? 'budget_exhausted' : run?.state;
const executionName = run => ({ dual_spark: '双 Spark · 环境平均分配', single_spark: '单 Spark', local: '本地 GPU / WSL' })[run?.execution?.mode] || '执行环境未记录';

function telemetryPoints(samples, key, divisor = 1) {
  const points = [];
  let previousTime;
  for (const sample of samples) {
    const timestamp = Date.parse(sample.received_utc || sample.sample_utc);
    if (!Number.isFinite(timestamp)) continue;
    if (previousTime != null && timestamp - previousTime > 10000) points.push({ timestamp: previousTime + 1, value: null });
    const metric = sample.metrics?.[key];
    points.push({ timestamp, value: metric?.status === 'ok' && Number.isFinite(metric.value) ? metric.value / divisor : null });
    previousTime = timestamp;
  }
  return points;
}

function Icon({ name, size = 18 }) {
  const paths = { grid: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z', chart: 'M3 3v18h18M6 15l4-5 4 3 7-8', replay: 'M9 6l10 6-10 6zM3 5v14', server: 'M3 3h18v7H3zM3 14h18v7H3zM7 6h.01M7 17h.01M11 6h6M11 17h6', config: 'M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M10 15v6', plus: 'M12 5v14M5 12h14', arrow: 'M7 5l7 7-7 7', external: 'M13 3h8v8M21 3L10 14M9 3H3v18h18v-6', close: 'M6 6l12 12M6 18L18 6', refresh: 'M20 7a8 8 0 1 0 1 8M20 3v5h-5', play: 'M7 4l14 8-14 8z', pause: 'M7 4v16M17 4v16', stop: 'M5 5h14v14H5z', check: 'M4 12l5 5L20 6' };
  return html`<svg width=${size} height=${size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d=${paths[name] || paths.grid}/></svg>`;
}

function Badge({ state }) { return html`<span class=${`badge status-${state || 'unknown'}`}><i></i>${stateName(state)}</span>`; }
function Empty({ title, children }) { return html`<div class="empty-state"><span class="empty-axis">⌁</span><h3>${title}</h3><p>${children}</p></div>`; }
function Metric({ label, value, unit, note, accent }) { return html`<div class=${`metric ${accent ? 'accent' : ''}`}><span class="eyebrow">${label}</span><strong>${value}<small>${unit}</small></strong><span class="metric-note">${note || ' '}</span></div>`; }

function usePoll(loader, dependencies, interval = 4000) {
  const [data, setData] = useState(null), [error, setError] = useState(null);
  const currentRequest = useRef(0);
  const callback = useRef(loader); callback.current = loader;
  const refresh = useCallback(async () => { const sequence = ++currentRequest.current; try { const value = await callback.current(); if (sequence === currentRequest.current) { setData(value); setError(null); } } catch (failure) { if (sequence === currentRequest.current) setError(failure); } }, dependencies);
  useEffect(() => { let disposed = false, timer; const poll = async () => { if (disposed) return; await refresh(); if (!disposed) timer = setTimeout(poll, interval); }; poll(); return () => { disposed = true; clearTimeout(timer); }; }, [refresh, interval]);
  return [data, error, refresh];
}


function Overview({ run, metricData, events }) {
  const [axis, setAxis] = useState('iteration'), [smoothing, setSmoothing] = useState(1);
  const series = metricData?.series || [];
  const select = expression => series.filter(item => expression.test(item.key));
  const reward = select(/reward.*mean|reward_mean|reward_per|episode.*return|return.*mean/).filter(item => !item.key.startsWith('reward_detail/'));
  const rewardDetails = select(/^reward_detail\//);
  const lengths = select(/episode.*length|length.*mean/);
  const evaluations = select(/eval|pass_rate|success_rate/);
  const diagnostics = select(/loss|entropy|std|learning_rate|^lr$|clip|^kl$|collect_s|update_s/);
  const seen = new Set([...reward, ...rewardDetails, ...lengths, ...evaluations, ...diagnostics].map(item => item.key));
  const rest = series.filter(item => !seen.has(item.key) && item.points?.some(point => point.value != null));
  return html`<div class="overview"><div class="section-heading"><div><span class="eyebrow">LEARNING CURVES</span><h2>训练效果</h2></div><div class="chart-tools"><label>横轴<select value=${axis} onChange=${event => setAxis(event.target.value)}><option value="iteration">更新轮次</option><option value="transitions">累计转换数</option><option value="elapsed_s">实际耗时</option></select></label><label>平滑<select value=${smoothing} onChange=${event => setSmoothing(Number(event.target.value))}><option value="1">原始采样</option><option value="10">最近 10 点</option><option value="30">最近 30 点</option><option value="100">最近 100 点</option></select></label></div></div>
    <div class="charts-grid"><${Chart} title="每转换奖励" subtitle="全局采样均值" series=${reward.filter(item => !/episode|return/.test(item.key))} axis=${axis} smoothing=${smoothing} empty="此运行尚无每转换奖励采样"/><${Chart} title="完整回合回报" subtitle="跨 rollout 累积 · 完整 episode" series=${reward.filter(item => /episode|return/.test(item.key))} axis=${axis} smoothing=${smoothing} empty="旧日志未采集完整回合回报；不补零"/><${Chart} title="完整回合长度" subtitle="完整 episode · steps" series=${lengths} axis=${axis} smoothing=${smoothing} empty="尚无完整回合长度采样；不补零"/><${Chart} title="开发评估" subtitle="真实评估点 · 绑定 checkpoint" series=${evaluations} axis=${axis} scatter=${true} empty="暂无对应 checkpoint 的开发评估"/><${Chart} title="训练吞吐" subtitle="每轮实测 · transitions / s" series=${rest.filter(item => /transition|throughput/.test(item.key))} axis=${axis} smoothing=${smoothing}/></div>
    ${(metricData?.warnings || []).map(warning => html`<p class="notice">${typeof warning === 'string' ? warning : warning.message}</p>`)}
    ${rewardDetails.length > 0 && html`<details class="diagnostics"><summary><span>分项奖励：原始项、实际权重与贡献</span><small>奖励率与终止事件代价分别展示</small></summary><div class="charts-grid">${rewardDetails.map(item => html`<${Chart} key=${item.key} title=${item.label || item.key} subtitle=${item.unit || '单位以原记录为准'} series=${[item]} axis=${axis} smoothing=${smoothing} height=${200}/>` )}</div></details>`}
    <details class="diagnostics" open><summary><span>PPO 诊断与奖励分项</span><small>loss、entropy、action std、learning rate</small></summary><div class="charts-grid">${diagnostics.map(item => html`<${Chart} key=${item.key} title=${item.label || item.key} subtitle=${item.scope === 'rank0' ? 'rank0 · 不是全局均值' : item.scope || '实际采样'} series=${[item]} axis=${axis} smoothing=${smoothing} height=${200}/>`)}${rest.filter(item => !/transition|collect|update_s|throughput|elapsed/.test(item.key)).map(item => html`<${Chart} key=${item.key} title=${item.label || item.key} series=${[item]} axis=${axis} smoothing=${smoothing} height=${200}/>` )}</div><p class="muted compact">KL 仅在训练库提供可靠采集源时展示；当前缺测不等于 0。自然完成率与开发行为通过率分别记录。</p></details>
    <${EventLog} events=${events}/>
  </div>`;
}

function EventLog({ events = [] }) {
  return html`<section class="panel event-panel"><div class="card-heading"><h3>运行事件</h3><span>持久日志 · ${events.length} 条</span></div><div class="event-list">${events.length ? events.slice(-80).reverse().map(event => html`<div class=${`event-row event-${event.level}`}><time>${event.time_utc ? new Date(event.time_utc).toLocaleTimeString() : '时间缺测'}</time><span>${event.type || event.level || '记录'}</span><p>${event.message || JSON.stringify(event.data)}</p></div>`) : html`<p class="muted">暂无运行事件</p>`}</div></section>`;
}

function ReplayPane({ session, checkpoint, onClose, standalone = false }) {
  const canvas = useRef(), model = useRef(), frames = useRef([]), lastFrame = useRef(), lastPaint = useRef(0), identity = useRef({ generation: -1, seq: -1 });
  const historyLoader = useRef();
  const [viewError, setViewError] = useState(null), [ready, setReady] = useState(false), [frame, setFrame] = useState(null), [history, setHistory] = useState([]), [metadata, setMetadata] = useState(session), [busy, setBusy] = useState(false), [controlError, setControlError] = useState(null), [historyError, setHistoryError] = useState(null), [follow, setFollow] = useState(true), [chartMode, setChartMode] = useState('velocity');
  const acceptFrames = (incoming, generation = -1, force = false) => {
    const previousGeneration = identity.current.generation;
    const merged = mergeReplayFrames(frames.current, incoming.map(normalizeFrame), session.replay_id, previousGeneration, generation);
    frames.current = merged.frames;
    const latest = merged.frames.at(-1);
    identity.current = { generation: merged.generation, seq: latest?.seq ?? -1 };
    lastFrame.current = latest;
    if (latest) model.current?.setFrame(latest);
    if (force || merged.generation !== previousGeneration || performance.now() - lastPaint.current > 200) {
      setFrame(latest || null); setHistory([...merged.frames]);
      if (latest) setMetadata(current => ({ ...current, actual_realtime_factor: latest.actual_realtime_factor ?? current.actual_realtime_factor }));
      lastPaint.current = performance.now();
    }
    return merged.generation > previousGeneration;
  };
  useEffect(() => {
    let active = true, pending = false, again = false;
    const restoreHistory = async () => {
      if (pending) { again = true; return; }
      pending = true;
      do {
        again = false;
        try {
          const response = await api(`/api/replays/${encodeURIComponent(session.replay_id)}/frames?after_seq=0&limit=2500`);
          if (active) { acceptFrames(response.items || [], response.generation ?? -1, true); setHistoryError(null); }
        } catch (error) { if (active) setHistoryError(error); }
      } while (active && again);
      pending = false;
    };
    historyLoader.current = restoreHistory;
    restoreHistory();
    const disconnect = onConnection(state => { if (state === 'connected') restoreHistory(); });
    return () => { active = false; historyLoader.current = null; disconnect(); };
  }, [session.replay_id]);
  useEffect(() => { let active = true; try { model.current = new StudioReplay(canvas.current); model.current.load().then(() => { if (active) { setReady(true); if (lastFrame.current) model.current.setFrame(lastFrame.current); } }).catch(error => { if (active) setViewError(error); }); } catch (error) { setViewError(error); } return () => { active = false; model.current?.dispose(); model.current = null; }; }, []);
  useEffect(() => subscribe('replay', session.replay_id, message => {
    if (message.type !== 'frame') { if (message.data?.state) setMetadata(current => ({ ...current, ...message.data })); return; }
    const next = { ...message.data, seq: message.data.seq ?? message.seq };
    if (acceptFrames([next])) historyLoader.current?.();
  }), [session.replay_id]);
  useEffect(() => { let active = true; const timer = setInterval(() => api(`/api/replays/${encodeURIComponent(session.replay_id)}`).then(value => { if (active) { setMetadata(value); if (value.generation > identity.current.generation) { acceptFrames([], value.generation, true); historyLoader.current?.(); } } }).catch(error => { if (active) setControlError(error); }), 2500); return () => { active = false; clearInterval(timer); }; }, [session.replay_id]);
  const control = async (action, speed) => { setBusy(true); setControlError(null); try { const value = await mutate(`/api/replays/${encodeURIComponent(session.replay_id)}/control`, { action, ...(speed ? { speed } : {}) }); setMetadata(value); if (action === 'reset') historyLoader.current?.(); } catch (error) { setControlError(error); } finally { setBusy(false); } };
  const chartSeries = chartMode === 'velocity' ? [['command.vx_m_s', '命令前进', 'm/s'], ['actual.vx_m_s', '实际前进', 'm/s']] : chartMode === 'yaw' ? [['command.yaw_rad_s', '命令角速度', 'rad/s'], ['actual.yaw_rad_s', '实际角速度', 'rad/s']] : chartMode === 'attitude' ? [['attitude_rad.roll', '横滚', 'rad'], ['attitude_rad.pitch', '俯仰', 'rad'], ['attitude_rad.yaw', '偏航', 'rad']] : [];
  const charts = chartMode === 'trajectory' ? [{ key: 'trajectory', label: '根位置轨迹', unit: 'm', points: history.map(item => ({ x: item.root_position_m?.[0], value: item.root_position_m?.[1] })) }] : chartSeries.map(([path, label, unit]) => ({ key: path, label, unit, points: history.map(item => ({ sim_time_s: item.sim_time_s, value: path.split('.').reduce((value, key) => value?.[key], item) })) }));
  const failure = metadata.error?.message || metadata.error;
  const terminal = ['failed', 'stopped', 'closed', 'released', 'ended', 'finished', 'completed'].includes(metadata.state);
  const controllable = !['failed', 'closed', 'released'].includes(metadata.state);
  return html`<article class=${`replay-pane ${standalone ? 'standalone' : ''}`}><header class="replay-header"><div><span class="eyebrow">CHECKPOINT ${checkpoint?.model_iteration ?? session.model_iteration ?? ''} · RANK 0</span><h3 title=${session.checkpoint_id}>${session.checkpoint_id}</h3></div><div class="replay-header-actions"><${Badge} state=${metadata.state}/>${!standalone && html`<button class="icon-button" aria-label="在独立窗口打开" title="连接同一回放会话，不重复占用 GPU" onClick=${() => window.open(`/?replay=${encodeURIComponent(session.replay_id)}`, `duck-replay-${session.replay_id}`, 'width=1000,height=850')}><${Icon} name="external"/></button>`}<button class="icon-button" aria-label="释放回放" title="停止此回放并释放 GPU 资源" onClick=${() => onClose(session.replay_id)}><${Icon} name="close"/></button></div></header>
    <div class="replay-stage"><canvas ref=${canvas} aria-label="Studio 真实外观模型回放"/><div class="stage-topline"><span>STUDIO · v2026.10.3101</span><span>${metadata.node_id || 'local-wsl'} · Z ↑</span></div><div class="stage-coordinates"><span>X ${decimal(frame?.root_position_m?.[0], 3)}</span><span>Y ${decimal(frame?.root_position_m?.[1], 3)}</span><span>Z ${decimal(frame?.root_position_m?.[2], 3)} m</span></div>${(!ready || !frame || viewError) && html`<div class="stage-message">${viewError ? html`<strong>模型加载失败</strong><p>${errorText(viewError)}</p>` : !ready ? html`<span class="spinner"></span><p>解码 Studio 网格…</p>` : html`${terminal ? html`<strong>${failure ? '回放失败' : stateName(metadata.state)}</strong>` : html`<span class="spinner"></span>`}<p>${failure || (terminal ? '此会话已结束，可重置或关闭窗口。' : '等待真实仿真姿态…')}</p>`}</div>`}<div class="stage-view"><select aria-label="相机视角" onChange=${event => model.current?.setView(event.target.value)}><option value="perspective">自由视角</option><option value="front">正视</option><option value="side">侧视</option><option value="top">俯视</option></select><label><input type="checkbox" checked=${follow} onChange=${event => { setFollow(event.target.checked); if (model.current) model.current.follow = event.target.checked; }}/>跟随</label></div></div>
    <div class="replay-controls"><button class="button small secondary" disabled=${busy || !controllable} onClick=${() => control(metadata.state === 'paused' ? 'play' : 'pause')}><${Icon} name=${metadata.state === 'paused' ? 'play' : 'pause'} size=${14}/>${metadata.state === 'paused' ? '播放' : '暂停'}</button><button class="icon-button" disabled=${busy || !controllable} onClick=${() => control('reset')} title="以相同场景和 seed 重置"><${Icon} name="refresh" size=${16}/></button><select aria-label="回放倍率" disabled=${busy || !controllable} value=${metadata.speed || 1} onChange=${event => control('set_speed', Number(event.target.value))}><option value="0.5">0.5×</option><option value="1">1×</option><option value="2">2×</option></select><span class="replay-time">${decimal(frame?.sim_time_s, 2)} s</span><span class="realtime-factor">实际 ${decimal(frame?.actual_realtime_factor ?? metadata.actual_realtime_factor)}×</span></div>
    <div class="replay-condition">${session.scenario_id} · seed ${session.seed} · ${frame?.task_version || metadata.task_version || '冻结任务版本'} · 速度坐标 ${frame?.velocity_frame || metadata.velocity_frame || 'body'}<br/>${standalone ? '独立窗口未加载评估记录；可回主页面查看' : checkpoint?.evaluations?.length ? `已有 ${checkpoint.evaluations.length} 份开发评估` : '此 checkpoint 未提供开发评估'} · 画面帧 seq ${frame?.seq ?? '—'}</div>
    ${historyError && html`<div class="notice error compact">历史帧暂未恢复：${errorText(historyError)} <button class="button secondary small" onClick=${() => historyLoader.current?.()}>重试加载历史</button></div>`}
    ${(controlError || failure) && html`<div class="notice error compact">${controlError ? errorText(controlError) : typeof failure === 'string' ? failure : JSON.stringify(failure)}</div>`}
    <div class="replay-chart-tabs">${[['velocity', '速度跟踪'], ['yaw', '角速度'], ['attitude', '姿态'], ['trajectory', '轨迹']].map(([key, title]) => html`<button class=${chartMode === key ? 'active' : ''} onClick=${() => setChartMode(key)}>${title}</button>`)}</div><${Chart} title="本次真实回放" subtitle=${frame?.failed ? `终止原因 ${frame.reason}` : frame?.completed ? '轨迹已完成' : '独立仿真时间轴'} series=${charts} axis="sim_time_s" height=${185} xy=${chartMode === 'trajectory'} empty="等待此会话的采样帧"/>
    ${frame?.events?.length > 0 && html`<div class="notice compact">${frame.events.map(event => typeof event === 'string' ? event : event.message || JSON.stringify(event)).join(' · ')}</div>`}
  </article>`;
}

function Checkpoints({ run, checkpoints, task, sessions, refreshSessions, notify }) {
  const [selected, setSelected] = useState(''), [scenario, setScenario] = useState('straight_0.06_101'), [seed, setSeed] = useState(101), [layout, setLayout] = useState(2), [busy, setBusy] = useState(false), [filter, setFilter] = useState('');
  const available = checkpoints.filter(item => String(item.model_iteration).includes(filter));
  const checkpoint = checkpoints.find(item => item.checkpoint_id === selected) || checkpoints[checkpoints.length - 1];
  const rawScenarios = task?.replay_scenarios || task?.evaluation_suites?.scenarios || [];
  const scenarios = Array.isArray(rawScenarios) && rawScenarios.length ? rawScenarios.map(item => typeof item === 'string' ? { id: item, label: item } : { id: item.scenario_id || item.name || item.id, label: item.title || item.name || item.scenario_id }) : [{ id: 'straight_0.06_101', label: '直行 0.06 m/s' }, { id: 'straight_0.03_101', label: '直行 0.03 m/s' }, { id: 'straight_0.1_101', label: '直行 0.10 m/s' }, { id: 'inplace_30', label: '原地转向 +30°/s' }, { id: 'inplace_-30', label: '原地转向 −30°/s' }, { id: 'arc_15', label: '弧线 +15°/s' }, { id: 'stand', label: '站立' }];
  const create = async () => { if (!checkpoint || busy) return; setBusy(true); try { await mutate('/api/replays', { checkpoint_id: checkpoint.checkpoint_id, scenario_id: scenario, seed }); await refreshSessions(); } catch (error) { notify(error); } finally { setBusy(false); } };
  const close = async id => { try { await api(`/api/replays/${encodeURIComponent(id)}`, { method: 'DELETE' }); await refreshSessions(); } catch (error) { notify(error); } };
  const replayPanes = sessions.map(session => html`<${ReplayPane} key=${session.replay_id} session=${session} checkpoint=${checkpoints.find(item => item.checkpoint_id === session.checkpoint_id)} onClose=${close}/>`);
return html`<div class="checkpoint-layout"><aside class="checkpoint-browser"><div class="card-heading"><h3>Checkpoints</h3><span>${checkpoints.length} 个</span></div><input class="search-input" value=${filter} placeholder="按更新轮次筛选…" onInput=${event => setFilter(event.target.value)} aria-label="筛选 checkpoint"/><div class="checkpoint-list">${available.length ? [...available].reverse().map(item => html`<button class=${`checkpoint-item ${checkpoint?.checkpoint_id === item.checkpoint_id ? 'active' : ''}`} onClick=${() => setSelected(item.checkpoint_id)}><div><strong>第 ${integer(item.model_iteration)} 轮</strong><span class=${item.replayable ? 'status-dot good' : 'status-dot'}></span></div><span>阶段 ${item.stage ?? '—'} · ${item.world_size ?? '—'} rank</span><small>${item.evaluations?.length ? `${item.evaluations.length} 份开发评估` : '未评估'} · ${item.replayable ? '可回放' : '不可回放'}</small></button>`) : html`<p class="muted compact">暂无完整 checkpoint</p>`}</div><div class="replay-config"><label class="field"><span>回放场景</span><select value=${scenario} onChange=${event => setScenario(event.target.value)}>${scenarios.map(item => html`<option value=${item.id}>${item.label}</option>`)}</select></label><label class="field"><span>Seed</span><input type="number" min="0" value=${seed} onInput=${event => setSeed(Number(event.target.value))}/></label><button class="button primary" disabled=${busy || !checkpoint?.replayable || sessions.filter(item => !['failed', 'closing'].includes(item.state)).length >= 4} onClick=${create}><${Icon} name="plus" size=${16}/>${busy ? '创建中…' : '添加回放窗口'}</button><small class="muted">最多 4 路，共享本地 GPU。刷新会重新接入已有会话。</small>${checkpoint?.reasons?.length ? html`<div class="notice compact">${checkpoint.reasons.join('；')}</div>` : null}<button class="button secondary small" disabled=${!checkpoint?.resumable || !allowed(run.capabilities?.resume)} title=${run.capabilities?.resume?.reasons?.join('；')} onClick=${async () => { try { await mutate(`/api/runs/${run.run_id}/resume`, { checkpoint_id: checkpoint.checkpoint_id }); notify('续训已创建；预算沿用原实验'); } catch (error) { notify(error); } }}>从此检查点续训</button></div></aside><div class="replay-workspace"><div class="section-heading"><div><span class="eyebrow">POLICY REPLAY</span><h2>策略回放对比</h2></div><div class="segmented">${[1, 2, 4].map(count => html`<button class=${layout === count ? 'active' : ''} onClick=${() => setLayout(count)}>${count === 1 ? '单窗' : count === 2 ? '双窗' : '四宫格'}</button>`)}</div></div><p class="muted compact">Studio 原始网格 · 完整世界位姿 · actor 确定性推理。回放不推动训练课程。</p><div class=${`replay-grid columns-${layout === 1 ? 1 : 2}`}>${replayPanes}</div>${!sessions.length && html`<${Empty} title="选择 checkpoint，观察策略如何运动">从左侧添加两个 checkpoint，可在相同场景下并排比较真实仿真表现。</${Empty}>`}${checkpoint?.evaluations?.length > 0 && html`<details class="panel evaluation-details"><summary>所选 checkpoint 的开发评估原始记录</summary><pre>${JSON.stringify(checkpoint.evaluations, null, 2)}</pre></details>`}</div></div>`;
}

function Resources({ resources, notify }) {
  return html`<div><div class="section-heading"><div><span class="eyebrow">COMPUTE TELEMETRY</span><h2>计算环境负载</h2></div><span class="muted">2 秒采集 · 节点总负载</span></div><div class="resource-grid">${resources.map(resource => html`<${ResourceCard} key=${resource.node_id} resource=${resource} notify=${notify}/>` )}</div><p class="muted compact">Windows 主机、WSL 与 Spark 宿主机分开记录；设备内存与统一内存不重复累加。缺测和过期采样不会绘制为空载。</p></div>`;
}

function WslResources({ wsl }) {
  const sample = wsl.sample, samples = wsl.samples || (sample ? [sample] : []);
  const state = wsl.connection?.state;
  const unavailable = ['stale', 'disconnected', 'offline', 'error', 'unavailable', 'unprobed'].includes(state);
  const value = (key, formatter = decimal) => unavailable ? `${stateName(state)} · 旧数据` : sample?.metrics?.[key]?.status === 'ok' ? formatter(sample.metrics[key].value) : '缺测';
  const points = key => telemetryPoints(samples, key);
  const processes = sample?.processes || [];
  return html`<section class="wsl-resource"><div class="card-heading"><div><h3>WSL 虚拟机</h3><span class="muted">独立采集 · 不与 Windows 宿主内存累加</span></div><${Badge} state=${state}/></div><div class="resource-values"><div><span>CPU</span><strong>${value('cpu_percent')}<small>%</small></strong></div><div><span>已用内存</span><strong>${value('memory_used_bytes', bytes)}</strong></div><div><span>可用内存</span><strong>${value('memory_available_bytes', bytes)}</strong></div></div><div class="wsl-charts"><${Chart} title="WSL CPU" series=${[{ key: 'wsl_cpu', label: 'WSL CPU', unit: '%', points: points('cpu_percent') }]} axis="timestamp" height=${160}/><${Chart} title="WSL 内存" series=${[{ key: 'wsl_memory', label: 'WSL 已用内存', unit: 'GiB', points: points('memory_used_bytes').map(point => ({ ...point, value: point.value == null ? null : point.value / 1024 ** 3 })) }]} axis="timestamp" height=${160}/></div><div class="wsl-processes"><h3>训练与回放进程${unavailable ? '（旧采样）' : ''}</h3>${processes.length ? html`<table><thead><tr><th>PID / 类型</th><th>RSS</th><th>GPU 进程内存</th></tr></thead><tbody>${processes.map(process => html`<tr><td>${process.pid} · ${process.kind === 'training' ? '训练' : process.kind === 'replay' ? '回放' : '未分类'}</td><td>${bytes(process.memory_rss_bytes)}</td><td>${process.gpu_memory_status === 'unsupported' ? '不支持' : '缺测'}</td></tr>`)}</tbody></table>` : html`<p class="muted">${sample ? '本次采样未发现训练或回放进程' : '尚无进程采样'}</p>`}<p class="muted">采集时间 ${sample?.sample_utc ? new Date(sample.sample_utc).toLocaleString() : '缺测'} · 最后接收 ${wsl.connection?.last_seen_utc ? new Date(wsl.connection.last_seen_utc).toLocaleTimeString() : '缺测'}</p></div></section>`;
}

function ResourceCard({ resource, notify }) {
  const samples = resource.samples || [], latest = samples[samples.length - 1];
  const current = key => latest?.metrics?.[key];
  const metricValue = (key, formatter = decimal) => { if (['stale', 'disconnected', 'offline', 'error', 'unavailable', 'unprobed'].includes(resource.connection?.state)) return `${stateName(resource.connection.state)} · 旧数据`; const metric = current(key); return metric?.status === 'ok' && metric.value != null ? formatter(metric.value) : ({ unsupported: '不支持', error: '采集失败', stale: '数据过期' }[metric?.status] || '无数据'); };
  const [group, setGroup] = useState('utilization');
  const groups = { utilization: [['cpu_percent', 'CPU', '%', 1], ['gpu_util_percent', 'GPU', '%', 1]], memory: [['memory_used_bytes', '系统内存', 'GiB', 1024 ** 3], ['gpu_memory_used_bytes', '设备内存', 'GiB', 1024 ** 3]], thermal: [['temperature_c', '温度', '°C', 1]], power: [['power_w', '功耗', 'W', 1]], io: [['disk_read_bytes_s', '磁盘读', 'MiB/s', 1024 ** 2], ['disk_write_bytes_s', '磁盘写', 'MiB/s', 1024 ** 2], ['network_rx_bytes_s', '网络接收', 'MiB/s', 1024 ** 2], ['network_tx_bytes_s', '网络发送', 'MiB/s', 1024 ** 2]] };
  const series = groups[group].map(([key, label, unit, divisor]) => ({ key, label, unit, points: telemetryPoints(samples, key, divisor) }));
  return html`<section class="resource-card"><header><div class="resource-title"><span class="resource-icon"><${Icon} name="server" size=${23}/></span><div><h3>${resource.label || resource.node_id}</h3><span>${latest?.scope || resource.execution_kind || resource.node_id}</span></div></div><${Badge} state=${resource.connection?.state}/></header><div class="resource-values"><div><span>CPU</span><strong>${metricValue('cpu_percent')}<small>%</small></strong></div><div><span>GPU</span><strong>${metricValue('gpu_util_percent')}<small>%</small></strong></div><div><span>系统内存</span><strong>${metricValue('memory_used_bytes', bytes)}</strong></div><div><span>设备内存</span><strong>${metricValue('gpu_memory_used_bytes', bytes)}</strong></div></div><div class="resource-secondary"><span>温度 <b>${metricValue('temperature_c')} °C</b></span><span>功耗 <b>${metricValue('power_w')} W</b></span><span>可用内存 <b>${metricValue('memory_available_bytes', bytes)}</b></span></div><div class="replay-chart-tabs">${[['utilization', '利用率'], ['memory', '内存'], ['thermal', '温度'], ['power', '功耗'], ['io', '磁盘 / 网络']].map(([key, label]) => html`<button class=${key === group ? 'active' : ''} onClick=${() => setGroup(key)}>${label}</button>`)}</div><${Chart} title="真实负载时序" series=${series} axis="timestamp" height=${205}/>${resource.wsl && html`<${WslResources} wsl=${resource.wsl}/>`}<footer><div><span>采集 ${latest?.sample_utc ? new Date(latest.sample_utc).toLocaleTimeString() : '尚未取得'}</span><span>${resource.active_run_ids?.length || 0} 个训练 · ${resource.active_replay_ids?.length || 0} 个回放</span></div><button class="icon-button" title="刷新必要探测" onClick=${async () => { try { await api(`/api/resources/${resource.node_id}/probe`, { method: 'POST', body: {} }); } catch (error) { notify(error); } }}><${Icon} name="refresh"/></button></footer></section>`;
}

function Records({ run, task, events }) {
  return html`<div><div class="section-heading"><div><span class="eyebrow">REPRODUCIBILITY</span><h2>配置与运行记录</h2></div><span class="badge">不可变运行快照</span></div><div class="records-grid"><section class="panel"><h3>运行身份</h3><dl>${[['运行 ID', run.run_id], ['实验 ID', run.experiment_id], ['任务版本', `${run.task_id} / ${run.task_version}`], ['来源', run.read_only ? '只读历史记录' : '工具管理'], ['创建时间', run.created_utc], ['父运行', run.parent_run_id], ['父 checkpoint', run.parent_checkpoint_id], ['显示模型', task?.display_model_version || 'Studio v2026.10.3101']].map(([key, value]) => html`<div><dt>${key}</dt><dd>${value || '—'}</dd></div>`)}</dl></section><section class="panel"><h3>预算与恢复合同</h3><dl>${Object.entries(run.budget || {}).map(([key, value]) => html`<div><dt>${({ consumed_transitions: '累计已消费', remaining_transitions: '剩余预算', max_transitions: '总预算', transitions_per_update: '每轮转换数' })[key] || key}</dt><dd>${integer(value)}</dd></div>`)}</dl><p class="notice compact">${run.capabilities?.resume?.reasons?.join('；') || '续训锁定原任务、源码、配置与 world size，回退 checkpoint 不返还已消费预算。'}</p></section></div><details class="panel" open><summary>实际训练配置</summary><pre>${JSON.stringify(run.config || {}, null, 2)}</pre></details><details class="panel"><summary>执行环境与来源记录</summary><pre>${JSON.stringify({ execution: run.execution, source: run.source, runtime: run.runtime, failure: run.failure }, null, 2)}</pre></details><${EventLog} events=${events}/></div>`;
}

function App() {
  const standaloneId = new URLSearchParams(location.search).get('replay');
  const [tasksResult, tasksError] = usePoll(() => api('/api/tasks'), [], 30000);
  const [runsResult, runsError, refreshRuns] = usePoll(() => api('/api/runs'), [], 3000);
  const [resourcesResult] = usePoll(() => api('/api/resources'), [], 3000);
  const [sessionsResult, , refreshSessions] = usePoll(() => api('/api/replays'), [], 3000);
  const tasks = list(tasksResult), runs = list(runsResult), resources = list(resourcesResult), sessions = list(sessionsResult).filter(item => !['released', 'closed'].includes(item.state));
  const [selectedRun, setSelectedRun] = useState(localStorage.getItem('duck.selectedRun') || ''), [selectedTask, setSelectedTask] = useState(''), [selectedExperiment, setSelectedExperiment] = useState(''), [tab, setTab] = useState('overview'), [drawer, setDrawer] = useState(false), [draft, setDraft] = useState(null), [connection, setConnection] = useState('connecting'), [toast, setToast] = useState(null), [importing, setImporting] = useState(false);
  const toastTimeout = useRef();
  const notify = useCallback(value => { setToast({ message: typeof value === 'string' ? value : errorText(value), error: typeof value !== 'string' }); clearTimeout(toastTimeout.current); toastTimeout.current = setTimeout(() => setToast(null), 8000); }, []);
  const taskRuns = selectedTask ? runs.filter(run => taskKey(run) === selectedTask) : runs;
  const taskChoices = [...new Map([...runs.map(item => ({ task_id: item.task_id, task_version: item.task_version, title: `${item.task_id} · 历史任务` })), ...tasks].map(item => [taskKey(item), item])).values()];
  const experiments = [...new Map(taskRuns.map(item => [item.experiment_id || item.run_id, { id: item.experiment_id || item.run_id, name: item.name || item.experiment_id || item.run_id }])).values()];
  const visibleRuns = selectedExperiment ? taskRuns.filter(item => (item.experiment_id || item.run_id) === selectedExperiment) : taskRuns;
  const run = visibleRuns.find(item => item.run_id === selectedRun) || visibleRuns[0];
  const task = tasks.find(item => taskKey(item) === (run ? taskKey(run) : selectedTask)) || null;
  const [details, detailsError, refreshDetails] = usePoll(async () => {
    if (!run?.run_id) return null;
    const [metrics, checkpoints, events] = await Promise.all([api(`/api/runs/${run.run_id}/metrics?max_points=1200`), api(`/api/runs/${run.run_id}/checkpoints`), readRunEvents(run.run_id)]);
    return { run_id: run.run_id, metrics, checkpoints: list(checkpoints), events: list(events) };
  }, [run?.run_id], 5000);
  useEffect(() => { api('/api/session').then(connect).catch(notify); return onConnection(setConnection); }, []);
  useEffect(() => { if (run?.run_id) { localStorage.setItem('duck.selectedRun', run.run_id); return subscribe('run', run.run_id, message => { if (message.type === 'event') { refreshDetails(); refreshRuns(); } }); } }, [run?.run_id]);
  const stop = async () => { try { await mutate(`/api/runs/${run.run_id}/stop`); await refreshRuns(); notify('停止请求已送达，等待更新边界及完整 checkpoint 保存。'); } catch (error) { notify(error); } };
  const selectedDetails = details?.run_id === run?.run_id ? details : null;
  const importHistory = async () => { setImporting(true); try { const result = await mutate('/api/history/import'); await refreshRuns(); notify(`历史盘点完成：${result.count ?? result.items?.length ?? '—'} 条记录${result.warnings?.length ? `；${result.warnings.length} 项缺口，详见档案` : ''}`); } catch (error) { notify(error); } finally { setImporting(false); } };
  if (standaloneId) {
    const session = list(sessionsResult).find(item => item.replay_id === standaloneId);
    return html`<main class="standalone-page"><div class="standalone-heading"><a href="/">DUCK / TRAINING LAB</a><span>独立回放窗口 · 刷新保持同一会话</span></div>${session ? html`<${ReplayPane} session=${session} standalone=${true} onClose=${async id => { try { await api(`/api/replays/${id}`, { method: 'DELETE' }); await refreshSessions(); } catch (error) { notify(error); } }}/>` : html`<${Empty} title="回放会话不可用">会话可能尚未加载或已经释放。返回主页面选择 checkpoint。</${Empty}>`}${toast && html`<div class=${`toast ${toast.error ? 'error' : ''}`}>${toast.message}</div>`}</main>`;
  }
  const consumed = run?.budget?.consumed_transitions, maximum = run?.budget?.max_transitions;
  const latestEvaluation = (selectedDetails?.metrics?.series || []).filter(item => /^evaluation\//.test(item.key)).flatMap(item => item.points || []).filter(point => Number.isFinite(point.value)).sort((left, right) => (right.iteration || 0) - (left.iteration || 0))[0];
  const progress = maximum > 0 && Number.isFinite(consumed) ? Math.min(100, consumed / maximum * 100) : null;
  const latestThroughput = selectedDetails?.metrics?.series?.find(item => /transitions_per_s|throughput/.test(item.key))?.points?.filter(point => point.value != null).slice(-1)[0]?.value;
  return html`<div class="app-shell"><aside class="sidebar"><a class="brand" href="/"><span class="brand-mark">D<span></span></span><div><strong>DUCK<span> LAB</span></strong><small>强化学习训练控制台</small></div></a><div class="workflow-label"><span>REAL → SIM → REAL</span><b>05 / 训练</b></div><button class="button primary new-run" onClick=${() => { setDraft(null); setDrawer(true); }} disabled=${!tasks.length}><${Icon} name="plus"/>新建训练运行</button><div class="sidebar-section"><span class="eyebrow">TRAINING TASKS</span><select class="task-select" value=${selectedTask} onChange=${event => { setSelectedTask(event.target.value); setSelectedExperiment(''); setSelectedRun(''); }}><option value="">全部训练任务</option>${taskChoices.map(item => html`<option value=${taskKey(item)}>${item.title} · ${item.task_version}</option>`)}</select><label class="experiment-filter"><span>实验</span><select class="task-select" value=${selectedExperiment} onChange=${event => { setSelectedExperiment(event.target.value); setSelectedRun(''); }}><option value="">全部实验</option>${experiments.map(item => html`<option value=${item.id}>${item.name}</option>`)}</select></label><button class="button secondary small history-import" disabled=${importing} onClick=${importHistory}>${importing ? '盘点中…' : '盘点并导入历史训练'}</button></div><div class="sidebar-section runs-heading"><span class="eyebrow">运行记录</span><span>${visibleRuns.length}</span></div><nav class="run-list">${visibleRuns.map(item => html`<button class=${`run-item ${run?.run_id === item.run_id ? 'selected' : ''}`} onClick=${() => setSelectedRun(item.run_id)}><div><span class=${`run-state-dot status-${item.state}`}></span><strong>${item.name || item.run_id}</strong></div><small>${item.read_only ? '历史只读' : item.execution?.mode === 'dual_spark' ? '双 Spark' : item.execution?.mode === 'single_spark' ? '单 Spark' : '本地 GPU'}<span>${integer(item.model_iteration)} 轮</span></small></button>`) }${!visibleRuns.length && html`<p class="sidebar-empty">暂无运行记录</p>`}</nav><div class="sidebar-footer"><div><span class=${`connection-dot ${connection === 'connected' ? 'connected' : ''}`}></span>${connection === 'connected' ? '实时连接正常' : '正在重新连接…'}</div><small>仅仿真训练 · 不驱动实物</small></div></aside>
    <main class="main"><header class="topbar"><div class="breadcrumb">工作台 <span>/</span> 第⑤步 · 执行训练</div><div class="topbar-right"><span class="live-label"><i></i> LIVE TELEMETRY</span><span>本机控制服务</span></div></header><div class="page-content"><div class="page-heading"><div><span class="eyebrow">TRAINING WORKSPACE</span><h1>${run?.name || '训练工作台'}</h1><p>${task?.title || (run ? `${run.task_id} · 历史任务版本` : '选择前序已建立的任务')} <span>·</span> ${run?.task_version || task?.task_version || '等待任务数据'} ${run?.read_only ? html`<span class="read-only">只读历史</span>` : ''}</p></div><div class="page-actions">${run && html`<${Badge} state=${runState(run)}/><button class="button secondary" disabled=${!allowed(run.capabilities?.stop)} title=${run.capabilities?.stop?.reasons?.join('；') || '在更新边界停止并保存'} onClick=${stop}><${Icon} name="stop" size=${15}/>停止并保存</button>`}</div></div>
    ${(tasksError || runsError || detailsError) && html`<div class="notice error">${errorText(tasksError || runsError || detailsError)} · 保留已取得的数据，连接恢复后自动更新。</div>`}
    ${runState(run) === 'budget_exhausted' && html`<div class="notice"><strong>训练预算已耗尽</strong><p>本次运行已经结束，预算消耗完成不代表行为验收通过。${latestEvaluation ? latestEvaluation.value < 1 ? `最近开发评估 ${latestEvaluation.passed_count ?? '—'} / ${latestEvaluation.sample_count ?? '—'} 通过，行为仍未达标。` : `最近开发评估 ${latestEvaluation.passed_count} / ${latestEvaluation.sample_count} 通过；完整验收以对应评估套件为准。` : '尚未取得行为评估结果。'}${run?.read_only ? ' 此记录只读，原实验无剩余预算。' : ''}</p></div>`}
    ${run?.failure && html`<div class="notice error">${run.failure.message || JSON.stringify(run.failure)}</div>`}
    ${run && html`<section class="run-summary"><div class="metrics-strip"><${Metric} label="更新进度" value=${integer(run.model_iteration)} unit=${`/ ${integer(run.config?.max_updates ?? (maximum && run.budget?.transitions_per_update ? maximum / run.budget.transitions_per_update : null))}`} note=${`课程阶段 ${run.stage ?? '—'}`} accent=${true}/><${Metric} label="累计转换数" value=${integer(consumed)} note=${`剩余 ${integer(run.budget?.remaining_transitions)}`}/><${Metric} label="采样吞吐" value=${integer(latestThroughput == null ? null : Math.round(latestThroughput))} unit=" /s" note="全局 transitions / s"/><${Metric} label="运行耗时" value=${duration(run.elapsed_s)} note=${run.eta_s == null ? 'ETA：暂无可靠估计' : `预计剩余 ${duration(run.eta_s)}`}/></div><div class="progress-track"><span style=${{ width: `${progress ?? 0}%` }}></span></div><div class="progress-caption"><span>${executionName(run)}<b>${run.connection?.state && !['connected', 'online'].includes(run.connection.state) ? ` · ${stateName(run.connection.state)}` : ''}</b></span><span>${decimal(progress, 1)}% 预算已消费</span></div></section>`}
    <nav class="tabs">${[['overview', '训练概览', 'chart'], ['replay', '检查点与回放', 'replay'], ['resources', '计算资源', 'server'], ['records', '配置与记录', 'config'], ['archive', '实验档案与复训', 'config']].map(([key, title, icon]) => html`<button class=${tab === key ? 'active' : ''} onClick=${() => setTab(key)}><${Icon} name=${icon}/>${title}${key === 'replay' && sessions.length > 0 ? html`<span class="tab-count">${sessions.length}</span>` : null}</button>`)}</nav>
    <div class=${tab === 'overview' ? '' : 'hidden'}>${run ? html`<${Overview} run=${run} metricData=${selectedDetails?.metrics} events=${selectedDetails?.events}/>` : html`<${Empty} title="开始第一次训练">选择已建立的任务，配置执行资源与训练预算。</${Empty}>`}</div>
    <div class=${tab === 'replay' ? '' : 'hidden'}>${run && html`<${Checkpoints} run=${run} checkpoints=${selectedDetails?.checkpoints || []} task=${task} sessions=${sessions} refreshSessions=${refreshSessions} notify=${notify}/>`}</div>
    <div class=${tab === 'resources' ? '' : 'hidden'}><${Resources} resources=${resources} notify=${notify}/></div>
    <div class=${tab === 'records' ? '' : 'hidden'}>${run && html`<${Records} run=${run} task=${task} events=${selectedDetails?.events}/>`}</div>
    <div class=${tab === 'archive' ? '' : 'hidden'}>${run && tab === 'archive' && html`<${ArchiveView} key=${run.run_id} run=${run} checkpoints=${selectedDetails?.checkpoints || []} notify=${notify} onDraft=${value => { setDraft(value); setDrawer(true); }}/>`}</div><footer class="page-footer"><span>DUCK TRAINING LAB</span><span>真实日志 · 不可变配置 · 可追溯 checkpoint</span></footer></div></main>
    ${drawer && html`<${TrainingForm} tasks=${tasks} draft=${draft} selectedTask=${selectedTask || taskKey(task)} onClose=${() => setDrawer(false)} onCreated=${async created => { setDrawer(false); setDraft(null); setSelectedTask(''); setSelectedExperiment(''); setSelectedRun(created.run_id); setTab('overview'); await refreshRuns(); notify('训练运行已创建，正在准备执行环境。'); }}/>`}${toast && html`<div class=${`toast ${toast.error ? 'error' : ''}`}><span>${toast.message}</span><button class="icon-button" onClick=${() => setToast(null)} aria-label="关闭通知"><${Icon} name="close"/></button></div>`}
  </div>`;
}

const appRoot = document.getElementById('app');
appRoot.replaceChildren();
render(html`<${App}/>`, appRoot);
