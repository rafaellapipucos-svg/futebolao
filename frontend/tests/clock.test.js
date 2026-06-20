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

test('conta a partir do INÍCIO DA FASE carimbado pelo backend (status manda)', () => {
  const base = Date.parse('2026-06-15T20:00:00Z');
  const ago = (m) => new Date(base - m * 60000).toISOString();
  // 2º tempo começou há 12 min → 45+12 = 57'
  assert.equal(
    liveClock({ status: 'live', period: '2H', minute: null, period_started_at: ago(12) }, base),
    "57'",
  );
  // 1º tempo há 50 min e o provider AINDA não sinalizou intervalo → segue 45+5
  // (NÃO vira "Intervalo" por tempo: a fronteira é do status, não do relógio).
  assert.equal(
    liveClock({ status: 'live', period: '1H', minute: null, period_started_at: ago(50) }, base),
    "45+5'",
  );
  // prorrogação (ET1) há 8 min → base 90 + 8 = 98'
  assert.equal(
    liveClock({ status: 'live', period: 'ET1', minute: null, period_started_at: ago(8) }, base),
    "98'",
  );
  // minuto do provider, quando vier, tem precedência sobre o carimbo
  assert.equal(
    liveClock({ status: 'live', period: '2H', minute: 80, period_started_at: ago(40) }, base),
    "80'",
  );
});

test('SEM minuto do provider: estima pelo relógio e NÃO trava em 45', () => {
  const base = Date.parse('2026-06-15T18:00:00Z');
  const ago = (m) => new Date(base - m * 60000).toISOString();
  // o bug: period vinha "1H" e minuto NULL → mostrava 45'. Agora estima:
  // ~89 min de relógio ≈ 74' de jogo (desconta ~15 de intervalo).
  assert.equal(liveClock({ status: 'live', period: '1H', minute: null, kickoff_utc: ago(89) }, base), "74'");
  // minuto 0/ausente = sem dado → estima também
  assert.equal(liveClock({ status: 'live', minute: 0, kickoff_utc: ago(20) }, base), "20'");
  assert.equal(liveClock({ status: 'live', period: '1H', minute: null, kickoff_utc: ago(47) }, base), "45+2'");
  // intervalo aproximado (entre os tempos)
  assert.equal(liveClock({ status: 'live', minute: null, kickoff_utc: ago(54) }, base), 'Intervalo');
});
