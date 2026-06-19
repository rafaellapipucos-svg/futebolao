// Rodada 16 (feature I): aba Jogos unificada — fundo do cartão encerrado + tally.
import assert from 'node:assert/strict';
import { test } from 'node:test';

// Stub DOM mínimo: jogos.js importa ui/matches/live (usam document).
class Node {}
class El extends Node {
  constructor(t) { super(); this.tag = t; this.className = ''; this.dataset = {}; this.children = []; this.attrs = {}; }
  setAttribute(k, v) { this.attrs[k] = v; }
  appendChild(c) { this.children.push(c); return c; }
  addEventListener() {}
}
class Txt extends Node { constructor(t) { super(); this.text = String(t); } }
globalThis.Node = Node;
globalThis.document = {
  createElement: (t) => new El(t),
  createTextNode: (t) => new Txt(t),
  createElementNS: (_n, t) => new El(t),
};

const { closedCardClass, tallyBets } = await import('../js/views/jogos.js');

test('closedCardClass: cravou=ouro, acertou=verde, errou=vermelho, não apostou=neutro', () => {
  assert.equal(closedCardClass({ hit_exact: true }, true), 'is-exact');
  assert.equal(closedCardClass({ hit_result: true }, true), 'is-right');
  assert.equal(closedCardClass({ hit_exact: false, hit_result: false }, true), 'is-wrong');
  assert.equal(closedCardClass(null, false), 'is-nobet');
  assert.equal(closedCardClass(null, true), 'is-nobet');
});

test('tallyBets soma pontos, cravadas e resultados', () => {
  const r = tallyBets([
    { my_points: { total: 3, hit_exact: true } },
    { my_points: { total: 1, hit_result: true } },
    { my_points: { total: 0, hit_exact: false, hit_result: false } },
    {},
  ]);
  assert.deepEqual(r, { total: 4, exact: 1, results: 1 });
});
