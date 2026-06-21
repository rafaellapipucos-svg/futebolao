import assert from 'node:assert/strict';
import { test } from 'node:test';

import { countdown, dayKey, groupByDay, liveClock, statusLabel, teamFlag, flagIsAbbr, flagSrc } from '../js/format.js';

test('countdown formata dias/horas/minutos/segundos', () => {
  const base = Date.parse('2026-06-11T12:00:00Z');
  assert.equal(countdown('2026-06-13T15:00:00Z', base), '2d 3h');
  assert.equal(countdown('2026-06-11T14:13:00Z', base), '2h 13m');
  assert.equal(countdown('2026-06-11T12:13:05Z', base), '13m 05s');
  assert.equal(countdown('2026-06-11T12:00:42Z', base), '42s');
  assert.equal(countdown('2026-06-11T11:59:59Z', base), null);
  assert.equal(countdown('2026-06-11T12:00:00Z', base), null); // no apito = fechado
});

test('groupByDay agrupa preservando ordem', () => {
  const items = [
    { kickoff_utc: '2026-06-11T19:00:00Z', id: 1 },
    { kickoff_utc: '2026-06-11T23:00:00Z', id: 2 },
    { kickoff_utc: '2026-06-13T01:00:00Z', id: 3 },
  ];
  const groups = groupByDay(items);
  assert.ok(groups.length >= 2);
  assert.deepEqual(groups[0].items.map((i) => i.id).slice(0, 1), [1]);
  const total = groups.reduce((acc, g) => acc + g.items.length, 0);
  assert.equal(total, 3);
  for (const g of groups) {
    assert.match(g.key, /^\d{4}-\d{2}-\d{2}$/);
    assert.ok(g.label.length > 5);
  }
});

test('dayKey é estável para o mesmo instante', () => {
  assert.equal(dayKey('2026-06-11T19:00:00Z'), dayKey('2026-06-11T19:00:00Z'));
});

test('statusLabel', () => {
  assert.equal(statusLabel('finished'), 'Encerrado');
  assert.equal(statusLabel('live'), 'Ao vivo');
  assert.equal(statusLabel('scheduled'), 'Agendado');
});

test('liveClock: dirigido pelo status/period do servidor (M4)', () => {
  const lc = (m) => liveClock({ status: 'live', ...m });
  assert.equal(liveClock({ status: 'finished', period: '2H' }), ''); // não-live
  assert.equal(lc({ period: '1H', minute: 30 }), "30'");
  assert.equal(lc({ period: '1H', minute: 47 }), "45+2'");      // acréscimo 1º tempo
  assert.equal(lc({ period: '2H', minute: 93 }), "90+3'");      // acréscimo 2º tempo
  assert.equal(lc({ period: 'HT' }), 'Intervalo');
  assert.equal(lc({ period: 'ET_HT' }), 'Intervalo da prorrogação');
  assert.equal(lc({ period: 'ET2', minute: 124 }), "120+4'");   // acréscimo prorrog.
  assert.equal(lc({ period: 'PENS' }), 'Pênaltis');
});

const ENG = '\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}';
const SCO = '\u{1F3F4}\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}';

test('flagSrc: emoji → caminho do SVG Twemoji local (codepoints hex com hífen)', () => {
  assert.equal(flagSrc({ flag: '\u{1F1E7}\u{1F1F7}', code: 'BRA', name: 'Brasil' }),
    '/assets/flags/1f1e7-1f1f7.svg');
  assert.equal(flagSrc({ flag: '\u{1F1E6}\u{1F1F7}', code: 'ARG', name: 'Argentina' }),
    '/assets/flags/1f1e6-1f1f7.svg');
});

test('flagSrc: Inglaterra e Escócia (tag sequences) têm asset Twemoji próprio', () => {
  assert.equal(flagSrc({ flag: ENG, code: 'ENG', name: 'Inglaterra' }),
    '/assets/flags/1f3f4-e0067-e0062-e0065-e006e-e0067-e007f.svg');
  assert.equal(flagSrc({ flag: SCO, code: 'SCO', name: 'Escócia' }),
    '/assets/flags/1f3f4-e0067-e0062-e0073-e0063-e0074-e007f.svg');
});

test('flagSrc: sem flag → caminho vazio (fallback fica com a sigla)', () => {
  assert.equal(flagSrc({ flag: '', code: 'XYZ' }), '');
  assert.equal(flagSrc(null), '');
  assert.equal(flagSrc(undefined), '');
});

test('teamFlag/flagIsAbbr (fallback textual): sigla p/ sub-divisão, emoji p/ resto', () => {
  assert.equal(teamFlag({ flag: ENG, code: 'ENG', name: 'Inglaterra' }), 'IN');
  assert.equal(teamFlag({ flag: SCO, code: 'SCO', name: 'Escócia' }), 'SC');
  assert.equal(teamFlag({ flag: '\u{1F1E7}\u{1F1F7}', code: 'BRA', name: 'Brasil' }), '\u{1F1E7}\u{1F1F7}');
  assert.equal(teamFlag({ flag: '', code: 'XYZ', name: 'X' }), 'XY');
  assert.equal(teamFlag(null), '');
  assert.equal(flagIsAbbr({ flag: ENG, code: 'ENG' }), true);
  assert.equal(flagIsAbbr({ flag: '\u{1F1E7}\u{1F1F7}', code: 'BRA' }), false);
});
