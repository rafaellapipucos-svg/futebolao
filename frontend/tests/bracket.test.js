import assert from 'node:assert/strict';
import { test } from 'node:test';
import { fmtMatchDate } from '../js/views/bracket.js';
import { fmtTime } from '../js/format.js';

// fmtMatchDate é puro (sem DOM). Para não depender do fuso da máquina de CI,
// derivamos o esperado dos mesmos primitivos locais (Date + fmtTime).
function expected(iso) {
  const dt = new Date(iso);
  const dd = String(dt.getDate()).padStart(2, '0');
  const mm = String(dt.getMonth() + 1).padStart(2, '0');
  return `${dd}/${mm} ${fmtTime(iso)}`;
}

test('fmtMatchDate: formato "DD/MM HH:MM" consistente com Date/fmtTime', () => {
  for (const iso of ['2026-06-28T16:00:00Z', '2026-07-19T19:00:00Z', '2026-12-01T03:30:00Z']) {
    const out = fmtMatchDate(iso);
    assert.equal(out, expected(iso));
    assert.match(out, /^\d{2}\/\d{2} \d{2}:\d{2}$/);
  }
});

test('fmtMatchDate: dia e mês com zero à esquerda', () => {
  // 5 de janeiro -> "05/01" (independe do fuso porque é meio-dia UTC,
  // longe da virada de dia em qualquer offset realista).
  const out = fmtMatchDate('2026-01-05T12:00:00Z');
  assert.ok(out.startsWith('05/01'), `esperado começar com 05/01, veio ${out}`);
});

test('fmtMatchDate: data inválida retorna string vazia', () => {
  assert.equal(fmtMatchDate('não-é-data'), '');
  assert.equal(fmtMatchDate(undefined), '');
  assert.equal(fmtMatchDate(''), '');
});
