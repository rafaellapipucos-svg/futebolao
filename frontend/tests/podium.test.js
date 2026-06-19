// Rodada 16 (feature G): pódio guiado por POSIÇÃO — empate em 2º = duas pratas,
// nenhum bronze indevido (o bug das imagens).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { podiumSlots } from '../js/views/leaderboard.js';

test('empate em 2º: duas pratas e NENHUM bronze', () => {
  const ps = podiumSlots([
    { position: 1, display_name: 'davi' },
    { position: 2, display_name: 'arthur' },
    { position: 2, display_name: 'novelino' },
  ]);
  assert.equal(ps.first.medal, 'gold');
  assert.equal(ps.second.medal, 'silver');
  assert.equal(ps.second.entries.length, 2);
  assert.equal(ps.third, null); // ninguém em 3º ⇒ sem bronze
});

test('1-2-3 distintos: ouro/prata/bronze', () => {
  const ps = podiumSlots([{ position: 1 }, { position: 2 }, { position: 3 }]);
  assert.equal(ps.first.medal, 'gold');
  assert.equal(ps.second.medal, 'silver');
  assert.equal(ps.third.medal, 'bronze');
});

test('empate triplo em 1º: três ouros, sem prata/bronze', () => {
  const ps = podiumSlots([{ position: 1 }, { position: 1 }, { position: 1 }]);
  assert.equal(ps.first.entries.length, 3);
  assert.equal(ps.second, null);
  assert.equal(ps.third, null);
});
