import assert from 'node:assert/strict';
import { test } from 'node:test';

// DOM stub mínimo: betbox.js e mybets.js importam ui.js (usa document em h()).
// As funções puras testadas aqui (clampScore/kickoffProgress/tallyBets) não
// tocam no DOM — o stub só permite o import dos módulos.
class Node {}
class El extends Node {
  constructor(tag) { super(); this.tag = tag; this.className = ''; this.dataset = {}; this.children = []; this.attrs = {}; }
  setAttribute(k, v) { this.attrs[k] = v; }
  appendChild(c) { this.children.push(c); return c; }
  addEventListener() {}
}
class Txt extends Node { constructor(t) { super(); this.text = String(t); } }
globalThis.Node = Node;
globalThis.document = {
  createElement: (t) => new El(t),
  createTextNode: (t) => new Txt(t),
  createElementNS: (_ns, t) => new El(t),
};

const { clampScore, kickoffProgress } = await import('../js/betbox.js');
const { tallyBets } = await import('../js/views/mybets.js');

test('clampScore: inteiro 0–20, entrada inválida/vazia vira 0', () => {
  assert.equal(clampScore('3'), 3);
  assert.equal(clampScore(0), 0);
  assert.equal(clampScore('07'), 7);
  assert.equal(clampScore(20), 20);
  assert.equal(clampScore('21'), 20);   // clamp no teto
  assert.equal(clampScore(99), 20);
  assert.equal(clampScore('-4'), 0);    // clamp no piso
  assert.equal(clampScore(''), 0);
  assert.equal(clampScore('abc'), 0);
  assert.equal(clampScore('2x'), 2);    // parseInt pega o prefixo numérico
});

test('kickoffProgress: 0 longe do apito, 1 no apito, cresce na janela de 24h', () => {
  const base = Date.parse('2026-06-15T12:00:00Z');
  const H = 3600 * 1000;
  assert.equal(kickoffProgress('2026-06-15T12:00:00Z', base), 1);   // no apito
  assert.equal(kickoffProgress('2026-06-15T11:59:00Z', base), 1);   // já passou
  assert.equal(kickoffProgress('2026-06-16T12:00:00Z', base), 0);   // exatamente 24h
  assert.equal(kickoffProgress('2026-06-17T12:00:00Z', base), 0);   // além da janela
  assert.equal(kickoffProgress('2026-06-15T18:00:00Z', base), 0.75); // faltam 6h → 75%
  assert.equal(kickoffProgress('2026-06-16T00:00:00Z', base), 0.5);  // faltam 12h → 50%
  assert.equal(kickoffProgress('lixo', base), 0);                    // data inválida
});

test('kickoffProgress: janela customizável', () => {
  const base = Date.parse('2026-06-15T12:00:00Z');
  const oneHour = 3600 * 1000;
  // faltam 30min numa janela de 1h → 50%
  assert.equal(kickoffProgress('2026-06-15T12:30:00Z', base, oneHour), 0.5);
});

test('tallyBets: soma pontos, conta cravadas e resultados (ignora sem my_points)', () => {
  const out = tallyBets([
    { my_points: { total: 3, hit_exact: true, hit_result: true } },  // cravada
    { my_points: { total: 1, hit_exact: false, hit_result: true } }, // resultado
    { my_points: { total: 0, hit_exact: false, hit_result: false } },// erro
    { my_bet: { home_goals: 1, away_goals: 0 } },                    // sem my_points
  ]);
  assert.deepEqual(out, { total: 4, exact: 1, results: 1 });
});

test('tallyBets: lista vazia zera tudo; cravada não conta como resultado', () => {
  assert.deepEqual(tallyBets([]), { total: 0, exact: 0, results: 0 });
  const out = tallyBets([
    { my_points: { total: 6, hit_exact: true, hit_result: true } },
    { my_points: { total: 6, hit_exact: true, hit_result: true } },
  ]);
  assert.deepEqual(out, { total: 12, exact: 2, results: 0 });
});
