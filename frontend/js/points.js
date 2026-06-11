// points.js — espelho client-side do scoring do backend (exibição otimista).
// A fonte de verdade é SEMPRE o servidor; isto só dá feedback instantâneo.

export const MULTIPLIERS = {
  GROUP: 1, R32: 2, R16: 3, QF: 4, SF: 5, THIRD: 5, FINAL: 10,
};

export const STAGE_LABELS = {
  GROUP: 'Fase de Grupos',
  R32: '16 avos de final',
  R16: 'Oitavas de final',
  QF: 'Quartas de final',
  SF: 'Semifinais',
  THIRD: 'Disputa de 3º lugar',
  FINAL: 'Final',
};

export const POINTS_RESULT = 1;
export const POINTS_EXACT_BONUS = 2;

function sign(n) {
  if (n > 0) return 1;
  if (n < 0) return -1;
  return 0;
}

export function computePoints(betHome, betAway, realHome, realAway, stage) {
  if (![betHome, betAway, realHome, realAway].every(
    (v) => Number.isInteger(v) && v >= 0,
  )) {
    return null;
  }
  const multiplier = MULTIPLIERS[stage];
  if (!multiplier) return null;
  const hitExact = betHome === realHome && betAway === realAway;
  const hitResult = sign(betHome - betAway) === sign(realHome - realAway);
  let base = 0;
  if (hitResult) base += POINTS_RESULT;
  if (hitExact) base += POINTS_EXACT_BONUS;
  return { hitResult, hitExact, base, multiplier, total: base * multiplier };
}

export function pointsChipClass(points) {
  if (!points || points.total === 0) return 'chip';
  if (points.hitExact) return 'chip chip-green';
  return 'chip chip-cyan';
}

export function pointsText(points) {
  if (!points) return '';
  if (points.total === 0) return '0 pts';
  const tag = points.hitExact ? 'cravada' : 'resultado';
  if (points.multiplier > 1) {
    return `+${points.total} pts (${tag} ×${points.multiplier})`;
  }
  return `+${points.total} ${points.total === 1 ? 'pt' : 'pts'} (${tag})`;
}
