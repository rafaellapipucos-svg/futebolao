// Rodada 16: sigla PT de 3 letras para a tabela compacta (nome nunca cortado).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { siglaPt } from '../js/format.js';

test('código FIFA que já casa com PT repete', () => {
  assert.equal(siglaPt({ code: 'BRA' }), 'BRA');
  assert.equal(siglaPt({ code: 'ARG' }), 'ARG');
  assert.equal(siglaPt({ code: 'POR' }), 'POR');
});

test('traduz onde o FIFA difere do português', () => {
  assert.equal(siglaPt({ code: 'GER' }), 'ALE'); // Alemanha
  assert.equal(siglaPt({ code: 'ENG' }), 'ING'); // Inglaterra
  assert.equal(siglaPt({ code: 'NED' }), 'HOL'); // Holanda
  assert.equal(siglaPt({ code: 'USA' }), 'EUA'); // Estados Unidos
  assert.equal(siglaPt({ code: 'KSA' }), 'ARA'); // Arábia Saudita
  assert.equal(siglaPt({ code: 'RSA' }), 'AFS'); // África do Sul
  assert.equal(siglaPt({ code: 'KOR' }), 'COR'); // Coreia do Sul
});

test('sem clash: Argentina/Argélia, Áustria/Austrália, Irã/Iraque', () => {
  assert.notEqual(siglaPt({ code: 'ARG' }), siglaPt({ code: 'ALG' }));
  assert.notEqual(siglaPt({ code: 'AUS' }), siglaPt({ code: 'AUT' }));
  assert.notEqual(siglaPt({ code: 'IRN' }), siglaPt({ code: 'IRQ' }));
});

test('fallback p/ código desconhecido e time vazio', () => {
  assert.equal(siglaPt({ code: 'XYZ' }), 'XYZ');
  assert.equal(siglaPt(null), '');
});
