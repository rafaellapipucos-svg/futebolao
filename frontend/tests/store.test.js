import assert from 'node:assert/strict';
import { test } from 'node:test';

import { createStore } from '../js/store.js';

test('set parcial preserva o resto do estado', () => {
  const s = createStore({ a: 1, b: 2 });
  s.set({ b: 3 });
  assert.deepEqual(s.get(), { a: 1, b: 3 });
});

test('subscribe notifica e unsubscribe para', () => {
  const s = createStore({ n: 0 });
  const seen = [];
  const unsub = s.subscribe((state) => seen.push(state.n));
  s.set({ n: 1 });
  s.set({ n: 2 });
  unsub();
  s.set({ n: 3 });
  assert.deepEqual(seen, [1, 2]);
});

test('múltiplos subscribers recebem o mesmo estado', () => {
  const s = createStore({});
  let a = null;
  let b = null;
  s.subscribe((st) => { a = st; });
  s.subscribe((st) => { b = st; });
  s.set({ x: 9 });
  assert.equal(a.x, 9);
  assert.equal(b, a);
});
