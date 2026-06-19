// Rodada 16 (feature B): relógio ao vivo ciente da fase (45+X, 90+X, prorrogação, pênaltis).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { liveClock } from '../js/format.js';

test('1º tempo: minuto corrente e acréscimos (45+X)', () => {
  assert.equal(liveClock({ status: 'live', period: '1H', minute: 30 }), "30'");
  assert.equal(liveClock({ status: 'live', period: '1H', minute: 47 }), "45+2'");
  assert.equal(liveClock({ status: 'live', period: '1H', minute: 45, stoppage: 2 }), "45+2'");
});

test('2º tempo: minuto corrente e acréscimos (90+X)', () => {
  assert.equal(liveClock({ status: 'live', period: '2H', minute: 80 }), "80'");
  assert.equal(liveClock({ status: 'live', period: '2H', minute: 93 }), "90+3'");
});

test('prorrogação e pênaltis', () => {
  assert.equal(liveClock({ status: 'live', period: 'ET1', minute: 98 }), "98'");
  assert.equal(liveClock({ status: 'live', period: 'ET2', minute: 123 }), "120+3'");
  assert.equal(liveClock({ status: 'live', period: 'ET_HT' }), 'Intervalo da prorrogação');
  assert.equal(liveClock({ status: 'live', period: 'PENS' }), 'Pênaltis');
  assert.equal(liveClock({ status: 'live', period: 'HT' }), 'Intervalo');
});

test('fora de "live" não mostra relógio', () => {
  assert.equal(liveClock({ status: 'finished', period: 'FT' }), '');
  assert.equal(liveClock(null), '');
});

test('sem period cai na estimativa (não vazio durante o jogo)', () => {
  const kickoff = new Date(Date.now() - 20 * 60000).toISOString();
  const out = liveClock({ status: 'live', kickoff_utc: kickoff });
  assert.ok(out && out !== '');
});
