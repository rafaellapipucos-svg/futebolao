// Espelha os casos do test_scoring.py do backend (TESTPLAN §6).
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { MULTIPLIERS, computePoints, pointsText } from '../js/points.js';

test('cravada na fase de grupos vale 3', () => {
  const p = computePoints(2, 1, 2, 1, 'GROUP');
  assert.equal(p.total, 3);
  assert.equal(p.hitExact, true);
  assert.equal(p.hitResult, true);
});

test('resultado certo não exato vale 1', () => {
  const p = computePoints(2, 1, 3, 1, 'GROUP');
  assert.deepEqual([p.total, p.hitExact, p.hitResult], [1, false, true]);
});

test('erro total vale 0', () => {
  const p = computePoints(2, 1, 0, 1, 'GROUP');
  assert.deepEqual([p.total, p.hitExact, p.hitResult], [0, false, false]);
});

test('empate cravado e genérico', () => {
  assert.equal(computePoints(1, 1, 1, 1, 'GROUP').total, 3);
  assert.equal(computePoints(1, 1, 2, 2, 'GROUP').total, 1);
});

test('multiplicadores por fase iguais ao backend', () => {
  const expected = { GROUP: 3, R32: 6, R16: 9, QF: 12, SF: 15, THIRD: 15, FINAL: 30 };
  for (const [stage, total] of Object.entries(expected)) {
    assert.equal(computePoints(2, 1, 2, 1, stage).total, total, stage);
  }
  assert.equal(computePoints(2, 1, 4, 2, 'FINAL').total, 10);
  assert.deepEqual(MULTIPLIERS, { GROUP: 1, R32: 2, R16: 3, QF: 4, SF: 5, THIRD: 5, FINAL: 10 });
});

test('entradas inválidas retornam null', () => {
  assert.equal(computePoints(-1, 0, 1, 0, 'GROUP'), null);
  assert.equal(computePoints(1, 0, null, 0, 'GROUP'), null);
  assert.equal(computePoints(1, 0, 1, 0, 'FASE_FALSA'), null);
});

test('pointsText descreve o ganho', () => {
  assert.match(pointsText(computePoints(2, 1, 2, 1, 'FINAL')), /\+30 pts \(cravada ×10\)/);
  assert.match(pointsText(computePoints(2, 1, 3, 1, 'GROUP')), /\+1 pt \(resultado\)/);
  assert.equal(pointsText(computePoints(0, 0, 2, 1, 'GROUP')), '0 pts');
});
