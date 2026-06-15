import assert from 'node:assert/strict';
import { test } from 'node:test';

// DOM stub mínimo para h()/flagContent (Node real não existe no node:test).
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

const ENG = '\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}';
const { flagContent } = await import('../js/ui.js');

test('flagContent: bandeira vira <img.team-flag-img> Twemoji, alt vazio e aria-hidden', () => {
  const el = flagContent({ flag: '\u{1F1E7}\u{1F1F7}', code: 'BRA', name: 'Brasil' });
  assert.equal(el.tag, 'img');
  assert.equal(el.className, 'team-flag-img');
  assert.equal(el.attrs.src, '/assets/flags/1f1e7-1f1f7.svg');
  assert.equal(el.attrs.alt, '');
  assert.equal(el.attrs['aria-hidden'], 'true');
});

test('flagContent: Inglaterra também é imagem (não mais sigla por padrão)', () => {
  const el = flagContent({ flag: ENG, code: 'ENG', name: 'Inglaterra' });
  assert.equal(el.tag, 'img');
  assert.equal(el.attrs.src, '/assets/flags/1f3f4-e0067-e0062-e0065-e006e-e0067-e007f.svg');
});

test('flagContent: sem flag → fallback span .flag-abbr com a sigla', () => {
  const el = flagContent({ flag: '', code: 'XYZ', name: 'X' });
  assert.equal(el.tag, 'span');
  assert.equal(el.className, 'flag-abbr');
  assert.equal(el.children[0].text, 'XY');
});

const { outcomeClass } = await import('../js/views/profile.js');
test('outcomeClass: cravada=dourado, resultado=verde, erro=vermelho', () => {
  assert.equal(outcomeClass({ hit_exact: true, hit_result: true }), 'hist-gold');
  assert.equal(outcomeClass({ hit_exact: false, hit_result: true }), 'hist-green');
  assert.equal(outcomeClass({ hit_exact: false, hit_result: false }), 'hist-red');
  assert.equal(outcomeClass(null), '');
});
