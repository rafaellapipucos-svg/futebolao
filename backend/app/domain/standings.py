"""Classificação de grupo — critérios FIFA.

Ordem: pontos > saldo > gols pró > confronto direto entre empatados (pts, saldo,
gols pró) > código do time (determinístico; sinalizado tie_unresolved, já que
fair play/sorteio não estão disponíveis).

`include_live=True` incorpora placares correntes de jogos ao vivo (tabela "ao vivo").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .entities import Match, MatchStatus


@dataclass
class Row:
    team_id: int
    code: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    gf: int = 0
    ga: int = 0
    points: int = 0
    live: bool = False  # linha afetada por jogo em andamento
    position: int = 0
    tie_unresolved: bool = False

    @property
    def gd(self) -> int:
        return self.gf - self.ga


def _counted(matches: Iterable[Match], include_live: bool) -> List[Match]:
    out = []
    for m in matches:
        if not m.has_score or m.home_team_id is None or m.away_team_id is None:
            continue
        if m.status == MatchStatus.FINISHED or (include_live and m.status == MatchStatus.LIVE):
            out.append(m)
    return out


def _apply(rows: Dict[int, Row], m: Match) -> None:
    home, away = rows[m.home_team_id], rows[m.away_team_id]
    live = m.status == MatchStatus.LIVE
    for r, gf, ga in ((home, m.home_score, m.away_score), (away, m.away_score, m.home_score)):
        r.played += 1
        r.gf += gf
        r.ga += ga
        r.live = r.live or live
    if m.home_score > m.away_score:
        home.won += 1
        home.points += 3
        away.lost += 1
    elif m.away_score > m.home_score:
        away.won += 1
        away.points += 3
        home.lost += 1
    else:
        home.drawn += 1
        away.drawn += 1
        home.points += 1
        away.points += 1


def _h2h_key(row: Row, cluster_ids: set, matches: List[Match]) -> tuple:
    """Mini-tabela apenas com jogos entre os empatados."""
    pts = gf = ga = 0
    for m in matches:
        if m.home_team_id in cluster_ids and m.away_team_id in cluster_ids:
            if m.home_team_id == row.team_id:
                mine, theirs = m.home_score, m.away_score
            elif m.away_team_id == row.team_id:
                mine, theirs = m.away_score, m.home_score
            else:
                continue
            gf += mine
            ga += theirs
            if mine > theirs:
                pts += 3
            elif mine == theirs:
                pts += 1
    return (-pts, -(gf - ga), -gf)


def compute_group(
    teams: Dict[int, str], matches: Iterable[Match], include_live: bool = False
) -> List[Row]:
    """teams: {team_id: code}. Retorna linhas ordenadas com posição 1..n."""
    rows = {tid: Row(team_id=tid, code=code) for tid, code in teams.items()}
    counted = _counted(matches, include_live)
    for m in counted:
        if m.home_team_id in rows and m.away_team_id in rows:
            _apply(rows, m)

    ordered = sorted(rows.values(), key=lambda r: (-r.points, -r.gd, -r.gf, r.code))

    # Desempate por confronto direto dentro de clusters (pts, sg, gp) idênticos.
    result: List[Row] = []
    i = 0
    while i < len(ordered):
        j = i
        while (
            j + 1 < len(ordered)
            and (ordered[j + 1].points, ordered[j + 1].gd, ordered[j + 1].gf)
            == (ordered[i].points, ordered[i].gd, ordered[i].gf)
        ):
            j += 1
        cluster = ordered[i : j + 1]
        if len(cluster) > 1:
            ids = {r.team_id for r in cluster}
            keyed = sorted(cluster, key=lambda r: (_h2h_key(r, ids, counted), r.code))
            h2h_keys = [_h2h_key(r, ids, counted) for r in keyed]
            for idx, r in enumerate(keyed):
                r.tie_unresolved = h2h_keys.count(h2h_keys[idx]) > 1
            cluster = keyed
        result.extend(cluster)
        i = j + 1

    for pos, r in enumerate(result, start=1):
        r.position = pos
    return result
