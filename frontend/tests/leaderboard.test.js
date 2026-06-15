// Testes das funções puras do ranking (medalha por posição + detecção de empate).
import test from 'node:test';
import assert from 'node:assert/strict';
import { medalForPosition, tiedPositions } from '../js/views/leaderboard.js';

test('medalForPosition mapeia top-3 e nada além', () => {
  assert.equal(medalForPosition(1), 'gold');
  assert.equal(medalForPosition(2), 'silver');
  assert.equal(medalForPosition(3), 'bronze');
  assert.equal(medalForPosition(4), null);
  assert.equal(medalForPosition(0), null);
});

test('tiedPositions encontra posições repetidas (empate)', () => {
  // backend dá a MESMA posição a empatados: 1, 2, 2, 4
  const rows = [
    { position: 1 }, { position: 2 }, { position: 2 }, { position: 4 },
  ];
  const ties = tiedPositions(rows);
  assert.ok(ties.has(2));
  assert.ok(!ties.has(1));
  assert.ok(!ties.has(4));
  assert.equal(ties.size, 1);
});

test('tiedPositions sem empates retorna conjunto vazio', () => {
  const rows = [{ position: 1 }, { position: 2 }, { position: 3 }];
  assert.equal(tiedPositions(rows).size, 0);
});

test('tiedPositions com empate triplo conta como uma posição empatada', () => {
  const rows = [{ position: 1 }, { position: 1 }, { position: 1 }, { position: 4 }];
  const ties = tiedPositions(rows);
  assert.ok(ties.has(1));
  assert.equal(ties.size, 1);
});
