import assert from 'node:assert/strict';
import { test } from 'node:test';

// Mocks mínimos (api.js usa document.cookie e fetch globais).
globalThis.document = { cookie: 'csrf_token=tok123' };
const calls = [];
let firstX = true;
function mkResp(status, body) {
  return {
    status, ok: status >= 200 && status < 300,
    clone() { return mkResp(status, body); },
    async json() { return body; },
  };
}
globalThis.fetch = async (url, opts = {}) => {
  calls.push({ url, method: opts.method || 'GET' });
  if (url === '/x' && firstX) { firstX = false; return mkResp(403, { detail: 'CSRF token inválido ou ausente' }); }
  if (url === '/api/meta/config') return mkResp(200, { ok: true });
  if (url === '/x') return mkResp(200, { done: true });
  return mkResp(200, {});
};

const { request } = await import('../js/api.js');

test('403-CSRF reemite o config e re-tenta a requisição mutante', async () => {
  const r = await request('/x', { method: 'POST' });
  assert.deepEqual(r, { done: true });
  assert.ok(calls.some((c) => c.url === '/api/meta/config'), 'buscou o config');
  assert.equal(calls.filter((c) => c.url === '/x').length, 2, 'tentou /x duas vezes');
});
