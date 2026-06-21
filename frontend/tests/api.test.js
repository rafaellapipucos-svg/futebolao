import assert from 'node:assert/strict';
import { test } from 'node:test';

// Mocks mínimos (api.js usa document.cookie e fetch globais).
globalThis.document = { cookie: 'csrf_token=tok123' };
const calls = [];
const once = { '/x': true, '/p': true };
function mkResp(status, body) {
  return {
    status, ok: status >= 200 && status < 300,
    clone() { return mkResp(status, body); },
    async json() { return body; },
  };
}
globalThis.fetch = async (url, opts = {}) => {
  calls.push({ url, method: opts.method || 'GET' });
  if (url === '/x' && once['/x']) { once['/x'] = false; return mkResp(403, { detail: 'CSRF token inválido ou ausente' }); }
  if (url === '/p' && once['/p']) { once['/p'] = false; return mkResp(401, { detail: 'sessão expirada' }); }
  if (url === '/api/meta/config') return mkResp(200, { ok: true });
  if (url === '/api/auth/refresh') return mkResp(200, { ok: true });
  if (url === '/x') return mkResp(200, { done: true });
  if (url === '/p') return mkResp(200, { ok: true });
  return mkResp(200, {});
};

const { request } = await import('../js/api.js');

test('403-CSRF reemite o config e re-tenta a requisição mutante', async () => {
  const r = await request('/x', { method: 'POST' });
  assert.deepEqual(r, { done: true });
  assert.ok(calls.some((c) => c.url === '/api/meta/config'), 'buscou o config');
  assert.equal(calls.filter((c) => c.url === '/x').length, 2, 'tentou /x duas vezes');
});

test('401 renova a sessão (refresh) e re-tenta a requisição', async () => {
  const r = await request('/p');
  assert.deepEqual(r, { ok: true });
  assert.ok(calls.some((c) => c.url === '/api/auth/refresh'), 'chamou o refresh');
  assert.equal(calls.filter((c) => c.url === '/p').length, 2, 'tentou /p duas vezes');
});
