// Runs the real RecoveryCard with fake hooks/timers and RPC, without a browser or network.
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';

const source = readFileSync(new URL('../.work/studio/web/pad.js', import.meta.url), 'utf8');
const card = source.slice(source.indexOf('function RecoveryCard('), source.indexOf('\nfunction Remote(', source.indexOf('function RecoveryCard(')));

function fixture(reply) {
  const calls = [], timers = [], cleanups = [], events = new Map();
  const status = { ok: true, active: false, phase: 'idle' };
  const context = {
    useRef: current => ({ current }), useState: value => [value, () => {}],
    useEffect: run => cleanups.push(run()), html: (strings, ...values) => ({ strings, values }),
    setInterval: fn => { timers.push(fn); return timers.length; }, clearInterval: () => {},
    ACT: { active: true }, SEND_MS: 100, document: { visibilityState: 'visible' },
    window: { addEventListener: (key, fn) => events.set(key, fn), removeEventListener: key => events.delete(key) },
    padActivity: { subscribe: fn => { events.set('activity', fn); return () => {}; } },
  };
  const link = { cmd: async (name, args, timeout) => {
    calls.push({ name, args, timeout });
    return reply ? reply(args) : { ok: true, data: { request_id: 71 } };
  } };
  vm.createContext(context);
  vm.runInContext(`${card}\nthis.makeCard = RecoveryCard;`, context);
  const tree = context.makeCard({ recovery: status, link });
  return { calls, status, context, events, start: tree.values.find(v => typeof v === 'function'),
    tick: () => timers[0](), cleanup: () => cleanups.forEach(fn => fn()) };
}

test('heartbeats require an explicit start and carry increasing sequence', async () => {
  const f = fixture(); await f.tick(); assert.equal(f.calls.length, 0);
  await f.start(); await f.tick(); await f.tick();
  assert.deepEqual(f.calls.map(c => c.args.op), ['recover', 'recover_keepalive', 'recover_keepalive']);
  assert.deepEqual(f.calls.slice(1).map(c => [c.args.request_id, c.args.sequence, c.timeout]), [[71, 1, 500], [71, 2, 500]]);
});
test('window blur cancels this request and cannot silently resume', async () => {
  const f = fixture(); await f.start(); f.events.get('blur')(); await f.tick();
  assert.equal(f.calls.at(-1).args.op, 'recover_cancel');
  assert.equal(f.calls.at(-1).args.request_id, 71);
  assert.equal(f.calls.length, 2);
});
test('hidden page cancels without another heartbeat', async () => {
  const f = fixture(); await f.start(); f.context.document.visibilityState = 'hidden';
  await f.tick(); await f.tick(); assert.equal(f.calls.length, 2);
  assert.equal(f.calls.at(-1).args.op, 'recover_cancel');
});
test('a start reply after unmount cancels instead of renewing', async () => {
  let resolve;
  const f = fixture(args => args.op === 'recover' ? new Promise(r => { resolve = r; }) : { ok: true });
  const pending = f.start(); f.cleanup(); resolve({ ok: true, data: { request_id: 71 } });
  await pending; await f.tick(); assert.equal(f.calls.length, 2);
  assert.equal(f.calls.at(-1).args.request_id, 71);
  assert.equal(f.calls.at(-1).args.op, 'recover_cancel');
});
test('failed heartbeat stops all later renewals', async () => {
  const f = fixture(args => args.op === 'recover' ? { ok: true, data: { request_id: 71 } } : { ok: false });
  await f.start(); await f.tick(); await f.tick(); assert.equal(f.calls.length, 2);
});
test('handoff status ends the lease without stopping ordinary driving', async () => {
  const f = fixture(); await f.start(); Object.assign(f.status, { request_id: 71, active: false, phase: 'idle' });
  await f.tick(); f.cleanup(); assert.equal(f.calls.length, 1);
});
test('Escape can cancel even when this page did not start the recovery', async () => {
  const f = fixture(); f.status.active = true; f.events.get('keydown')({ code: 'Escape' });
  assert.equal(f.calls.length, 1); assert.equal(f.calls[0].args.op, 'recover_cancel');
  assert.equal(f.calls[0].args.request_id, undefined);
});
