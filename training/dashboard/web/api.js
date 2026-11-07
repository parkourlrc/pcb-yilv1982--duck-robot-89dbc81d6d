let token;
let socket;
let reconnectTimer;
let retry = 0;
const listeners = new Map();
const connectionListeners = new Set();
const cursors = new Map();
const eventPages = new Map();
const pendingOperations = new Map();

export const requestId = () => crypto.randomUUID();

export async function api(path, options = {}) {
  if (!token && options.method && options.method !== 'GET') {
    const session = await fetch('/api/session', { credentials: 'same-origin' });
    if (!session.ok) throw new Error('无法建立本机会话');
    token = (await session.json()).csrf_token;
  }
  const response = await fetch(path, { credentials: 'same-origin', ...options, headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { 'X-CSRF-Token': token } : {}), ...options.headers }, body: options.body == null ? undefined : JSON.stringify(options.body) });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error?.message || data.detail?.message || (typeof data.detail === 'string' ? data.detail : `请求失败（${response.status}）`));
    error.details = data.error?.details || data.detail; throw error;
  }
  if (path === '/api/session') token = data.csrf_token;
  return data;
}

export async function readRunEvents(runId) {
  if (!eventPages.has(runId)) eventPages.set(runId, { cursor: 0, items: [], pending: null });
  const state = eventPages.get(runId);
  if (state.pending) return state.pending;
  state.pending = (async () => {
    while (true) {
      const page = await api(`/api/runs/${encodeURIComponent(runId)}/events?after=${state.cursor}&limit=1000`);
      const items = (page.items || []).filter(item => item.seq > state.cursor);
      if (!items.length) return state.items;
      state.items = [...state.items, ...items].slice(-1000);
      state.cursor = Math.max(state.cursor, ...items.map(item => item.seq));
      if (items.length < 1000) return state.items;
    }
  })();
  try { return await state.pending; } finally { state.pending = null; }
}

export async function mutate(path, body = {}) {
  const identity = JSON.stringify([path, body]);
  if (!pendingOperations.has(identity)) pendingOperations.set(identity, { request_id: requestId(), promise: null });
  const operation = pendingOperations.get(identity);
  if (operation.promise) return operation.promise;
  operation.promise = api(path, { method: 'POST', body: { ...body, request_id: operation.request_id } });
  try {
    const result = await operation.promise;
    pendingOperations.delete(identity);
    return result;
  } finally { operation.promise = null; }
}

function subscriptions() {
  return [...listeners.keys()].map(key => {
    const [topic, ...ids] = key.split(':');
    return { topic, id: ids.join(':'), after_cursor: cursors.get(key) || 0 };
  });
}

function updateSubscriptions() {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'subscribe', subscriptions: subscriptions() }));
}

export function connect() {
  if (socket && socket.readyState < 2) return;
  socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
  socket.onopen = () => { retry = 0; connectionListeners.forEach(callback => callback('connected')); updateSubscriptions(); };
  socket.onmessage = event => {
    let message;
    try { message = JSON.parse(event.data); } catch { return; }
    const key = `${message.topic}:${message.id}`;
    if (message.cursor != null) cursors.set(key, message.cursor);
    listeners.get(key)?.forEach(callback => callback(message));
  };
  socket.onclose = () => {
    connectionListeners.forEach(callback => callback('disconnected'));
    clearTimeout(reconnectTimer); reconnectTimer = setTimeout(connect, Math.min(10000, 700 * 2 ** retry++));
  };
  socket.onerror = () => socket.close();
}

export function subscribe(topic, id, callback) {
  const key = `${topic}:${id}`;
  if (!listeners.has(key)) listeners.set(key, new Set());
  listeners.get(key).add(callback); connect(); updateSubscriptions();
  return () => { listeners.get(key)?.delete(callback); if (!listeners.get(key)?.size) listeners.delete(key); updateSubscriptions(); };
}

export function onConnection(callback) {
  connectionListeners.add(callback); return () => connectionListeners.delete(callback);
}
