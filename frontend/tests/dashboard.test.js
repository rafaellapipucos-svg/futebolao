// Rodada 16 (feature D): zona de classificação da tabela (3ºs que passam).
import assert from 'node:assert/strict';
import { test } from 'node:test';

// Stub DOM mínimo: dashboard.js importa ui.js (usa document).
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

const { zoneFor } = await import('../js/views/dashboard.js');

test('zoneFor: 1º–2º verde, 3º que passa amarelo, 3º fora + 4º vermelho', () => {
  assert.equal(zoneFor({ position: 1 }), 'row-q');
  assert.equal(zoneFor({ position: 2 }), 'row-q');
  assert.equal(zoneFor({ position: 3, third_qualifying: true }), 'row-t');
  assert.equal(zoneFor({ position: 3, third_qualifying: false }), 'row-out');
  assert.equal(zoneFor({ position: 4 }), 'row-out');
});
