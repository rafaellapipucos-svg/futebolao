"""Pontuação de apostas. Regra: resultado certo = 1 ponto; placar exato = +2 (total 3).
Multiplicador por fase (MULTIPLIERS). Puro e determinístico.
"""
from __future__ import annotations

from dataclasses import dataclass

from .entities import MULTIPLIERS, Stage

POINTS_RESULT = 1
POINTS_EXACT_BONUS = 2


@dataclass(frozen=True)
class BetScore:
    hit_result: bool
    hit_exact: bool
    base: int
    multiplier: int
    total: int


def _sign(diff: int) -> int:
    if diff > 0:
        return 1
    if diff < 0:
        return -1
    return 0


def score_bet(
    bet_home: int, bet_away: int, real_home: int, real_away: int, stage: Stage
) -> BetScore:
    """Calcula os pontos de uma aposta dado um placar real (parcial ou final)."""
    for v in (bet_home, bet_away, real_home, real_away):
        if not isinstance(v, int) or v < 0:
            raise ValueError(f"placar inválido: {v!r}")
    hit_exact = bet_home == real_home and bet_away == real_away
    hit_result = _sign(bet_home - bet_away) == _sign(real_home - real_away)
    base = 0
    if hit_result:
        base += POINTS_RESULT
    if hit_exact:
        base += POINTS_EXACT_BONUS
    multiplier = MULTIPLIERS[stage]
    return BetScore(
        hit_result=hit_result,
        hit_exact=hit_exact,
        base=base,
        multiplier=multiplier,
        total=base * multiplier,
    )
