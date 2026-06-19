// Rodada 16 (feature A): tema escuro padrão + reset único da preferência.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { resolveTheme } from '../js/theme.js';

function fakeStore(init) {
  const m = new Map(Object.entries(init || {}));
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: (k) => m.delete(k),
    has: (k) => m.has(k),
  };
}

test('sem nada salvo → escuro (e marca o reset)', () => {
  const s = fakeStore({});
  assert.equal(resolveTheme(s), 'dark');
  assert.equal(s.getItem('theme_reset'), 'r16-dark-default');
});

test('preferência ANTIGA "light" é zerada no reset → escuro', () => {
  const s = fakeStore({ theme: 'light' });
  assert.equal(resolveTheme(s), 'dark');
  assert.equal(s.has('theme'), false);
});

test('"light" escolhido DEPOIS do reset persiste', () => {
  const s = fakeStore({ theme: 'light', theme_reset: 'r16-dark-default' });
  assert.equal(resolveTheme(s), 'light');
});

test('"dark" pós-reset segue escuro', () => {
  const s = fakeStore({ theme: 'dark', theme_reset: 'r16-dark-default' });
  assert.equal(resolveTheme(s), 'dark');
});
