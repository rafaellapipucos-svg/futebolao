"""Análise de vagas matematicamente garantidas (clinch) — conservadora, só pontos.

Saldo de gols é ilimitado em jogos futuros, então garantias usam apenas pontos:
- clinched_first: ninguém mais alcança meus pontos atuais ⇒ 1º garantido.
- clinched_top2: no máximo 1 adversário pode me alcançar ⇒ vaga direta garantida.
- eliminated_top2: ≥2 adversários já têm mais pontos do que meu máximo possível.
- guaranteed_position: 1 ou 2 quando a posição EXATA é certa só por pontos.

Jogos ao vivo NÃO contam como pontos ganhos (resultado pode mudar): contam como
restantes. Para grupos encerrados, use standings (ordem exata com desempates).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .entities import Match, MatchStatus


@dataclass(frozen=True)
class Outlook:
    team_id: int
    points: int
    remaining: int
    max_points: int
    clinched_first: bool
    clinched_top2: bool
    eliminated_top2: bool
    guaranteed_position: Optional[int]  # 1, 2 ou None


def analyze(team_ids: Iterable[int], matches: Iterable[Match]) -> Dict[int, Outlook]:
    ids = list(team_ids)
    idset = set(ids)
    points = {t: 0 for t in ids}
    remaining = {t: 0 for t in ids}

    for m in matches:
        if m.home_team_id not in idset or m.away_team_id not in idset:
            continue
        if m.status == MatchStatus.FINISHED and m.has_score:
            if m.home_score > m.away_score:
                points[m.home_team_id] += 3
            elif m.away_score > m.home_score:
                points[m.away_team_id] += 3
            else:
                points[m.home_team_id] += 1
                points[m.away_team_id] += 1
        else:
            remaining[m.home_team_id] += 1
            remaining[m.away_team_id] += 1

    max_points = {t: points[t] + 3 * remaining[t] for t in ids}
    out: Dict[int, Outlook] = {}
    for t in ids:
        others = [o for o in ids if o != t]
        can_reach_me = sum(1 for o in others if max_points[o] >= points[t])
        strictly_above = sum(1 for o in others if points[o] > max_points[t])
        clinched_first = can_reach_me == 0
        clinched_top2 = can_reach_me <= 1
        eliminated = strictly_above >= 2
        pos: Optional[int] = None
        if clinched_first:
            pos = 1
        elif clinched_top2 and strictly_above >= 1:
            # exatamente um garantido acima (se fossem 2+, eu não teria top2)
            pos = 2
        out[t] = Outlook(
            team_id=t,
            points=points[t],
            remaining=remaining[t],
            max_points=max_points[t],
            clinched_first=clinched_first,
            clinched_top2=clinched_top2,
            eliminated_top2=eliminated,
            guaranteed_position=pos,
        )
    return out


def group_finished(team_ids: Iterable[int], matches: Iterable[Match]) -> bool:
    idset = set(team_ids)
    group_matches = [
        m for m in matches if m.home_team_id in idset and m.away_team_id in idset
    ]
    return len(group_matches) == 6 and all(m.is_finished for m in group_matches)
