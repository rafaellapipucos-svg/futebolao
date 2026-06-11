import assert from 'node:assert/strict';
import { test } from 'node:test';

import { parseHash, resolveRoute } from '../js/router.js';

const USER = { id: 1, is_admin: false };
const ADMIN = { id: 2, is_admin: true };

test('parseHash extrai nome e params', () => {
  assert.deepEqual(parseHash('#/jogos'), { name: 'jogos', params: {} });
  assert.deepEqual(parseHash('#/login?error=oauth'), {
    name: 'login', params: { error: 'oauth' },
  });
  assert.equal(parseHash('').name, 'dashboard');
  assert.equal(parseHash('#/').name, 'dashboard');
});

test('guard: sem user vai para login', () => {
  assert.equal(resolveRoute('#/jogos', null).name, 'login');
  assert.equal(resolveRoute('#/jogos', null).params.next, 'jogos');
});

test('guard: logado não volta para login', () => {
  assert.equal(resolveRoute('#/login', USER).name, 'dashboard');
});

test('guard: admin só para admins', () => {
  assert.equal(resolveRoute('#/admin', USER).name, 'dashboard');
  assert.equal(resolveRoute('#/admin', ADMIN).name, 'admin');
});

test('rota desconhecida cai no padrão', () => {
  assert.equal(resolveRoute('#/nao-existe', USER).name, 'dashboard');
  assert.equal(resolveRoute('#/nao-existe', null).name, 'login');
});
