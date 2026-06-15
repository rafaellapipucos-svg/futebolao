import assert from 'node:assert/strict';
import { test } from 'node:test';

// DOM stub mínimo: live.js importa ui.js (usa document em flagContent/avatarEl).
// As funções puras testadas aqui (sortBettors/shortName) não tocam no DOM.
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

const { sortBettors, shortName } = await import('../js/views/live.js');

test('shortName: <=2 palavras mantém; 3+ vira primeiro + último sobrenome', () => {
  assert.equal(shortName('Ana'), 'Ana');
  assert.equal(shortName('Ana Souza'), 'Ana Souza');
  assert.equal(shortName('Ana Maria Souza'), 'Ana Souza');
  assert.equal(shortName('  João  da  Silva  Pereira '), 'João Pereira');
  assert.equal(shortName(''), '');
  assert.equal(shortName(null), '');
});

test('sortBettors: pontuando no topo, depois alfabético acento-insensível, estável', () => {
  const bets = [
    { display_name: 'Zeca', points: { total: 0 } },
    { display_name: 'Ávila', points: { total: 3 } },
    { display_name: 'Bruno', points: { total: 1 } },
    { display_name: 'Ana', points: { total: 0 } },
    { display_name: 'Bea', points: { total: 3 } },
  ];
  const out = sortBettors(bets).map((b) => b.display_name);
  // 3pts (Ávila, Bea) -> 1pt (Bruno) -> 0pts (Ana, Zeca em ordem alfabética)
  assert.deepEqual(out, ['Ávila', 'Bea', 'Bruno', 'Ana', 'Zeca']);
});

test('sortBettors: não muta o array original e trata points ausente como 0', () => {
  const bets = [
    { display_name: 'Caio' },
    { display_name: 'Bia', points: { total: 2 } },
  ];
  const copy = [...bets];
  const out = sortBettors(bets);
  assert.deepEqual(out.map((b) => b.display_name), ['Bia', 'Caio']);
  assert.deepEqual(bets, copy); // original intacto (função pura)
});
