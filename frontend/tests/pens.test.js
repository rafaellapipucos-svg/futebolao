// Rodada 16 (feature B): parser do mini-placar de pênaltis.
import assert from 'node:assert/strict';
import { test } from 'node:test';

// Stub DOM mínimo: live.js importa ui.js (usa document em flagContent/avatarEl).
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

const { parsePensLog } = await import('../js/views/live.js');

test('parsePensLog: JSON válido vira lista de cobranças', () => {
  assert.deepEqual(parsePensLog('[["home",true],["away",false]]'),
    [['home', true], ['away', false]]);
});

test('parsePensLog: vazio/ inválido/ não-array ⇒ []', () => {
  assert.deepEqual(parsePensLog(''), []);
  assert.deepEqual(parsePensLog(null), []);
  assert.deepEqual(parsePensLog('lixo{'), []);
  assert.deepEqual(parsePensLog('{"a":1}'), []);
});
