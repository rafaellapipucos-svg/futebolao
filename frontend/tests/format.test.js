import assert from 'node:assert/strict';
import { test } from 'node:test';

import { countdown, dayKey, groupByDay, minuteLabel, statusLabel, teamFlag, flagIsAbbr } from '../js/format.js';

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

test('minuteLabel e statusLabel', () => {
  assert.equal(minuteLabel('live', 20), '20′');
  assert.equal(minuteLabel('live', null), 'AO VIVO');
  assert.equal(minuteLabel('finished', 90), '');
  assert.equal(statusLabel('finished'), 'Encerrado');
});

test('teamFlag: sigla curta p/ bandeira de sub-divisão (quadrado preto), emoji p/ resto', () => {
  const eng = '\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}';
  const sco = '\u{1F3F4}\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}';
  assert.equal(teamFlag({ flag: eng, code: 'ENG', name: 'Inglaterra' }), 'IN');
  assert.equal(teamFlag({ flag: sco, code: 'SCO', name: 'Escócia' }), 'SC');
  assert.equal(teamFlag({ flag: '\u{1F1E7}\u{1F1F7}', code: 'BRA', name: 'Brasil' }), '\u{1F1E7}\u{1F1F7}');
  assert.equal(teamFlag({ flag: '', code: 'XYZ', name: 'X' }), 'XY');
  assert.equal(teamFlag(null), '');
  assert.equal(flagIsAbbr({ flag: eng, code: 'ENG' }), true);
  assert.equal(flagIsAbbr({ flag: '\u{1F1E7}\u{1F1F7}', code: 'BRA' }), false);
});
