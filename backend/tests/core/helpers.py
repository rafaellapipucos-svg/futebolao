"""Fábricas compartilhadas dos testes core."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from app.domain.entities import GROUPS, Match, MatchStatus, Stage, Team

KICKOFF = datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)


def mk_match(
    mid: int = 1,
    stage: Stage = Stage.GROUP,
    group: Optional[str] = "A",
    home: Optional[int] = None,
    away: Optional[int] = None,
    hs: Optional[int] = None,
    as_: Optional[int] = None,
    status: MatchStatus = MatchStatus.SCHEDULED,
    kickoff: datetime = KICKOFF,
    home_source: str = "X",
    away_source: str = "Y",
    winner: Optional[int] = None,
) -> Match:
    return Match(
        id=mid, stage=stage, group=group, kickoff_utc=kickoff, venue="Test Arena",
        home_source=home_source, away_source=away_source,
        home_team_id=home, away_team_id=away, home_score=hs, away_score=as_,
        status=status, winner_team_id=winner,
    )


def finished(mid, home, away, hs, as_, group="A", stage=Stage.GROUP, winner=None) -> Match:
    return mk_match(
        mid=mid, stage=stage, group=group, home=home, away=away, hs=hs, as_=as_,
        status=MatchStatus.FINISHED, winner=winner,
    )


def make_teams_48() -> Dict[int, Team]:
    """48 times: ids 1..48; grupo A = ids 1-4 (códigos A1..A4), B = 5-8, ..."""
    teams: Dict[int, Team] = {}
    tid = 0
    for g in GROUPS:
        for n in range(1, 5):
            tid += 1
            teams[tid] = Team(id=tid, code=f"{g}{n}", name=f"Time {g}{n}", flag="🏳️", group=g)
    return teams


def group_ids(g: str) -> List[int]:
    base = GROUPS.index(g) * 4
    return [base + 1, base + 2, base + 3, base + 4]


def full_group_results(start_mid: int, g: str) -> Tuple[List[Match], int]:
    """6 jogos encerrados: ordem final = T1 > T2 > T3 > T4 (T_n = n-ésimo do grupo).

    Placares decrescentes garantem thirds com critérios distintos por grupo? Não —
    todos os grupos usam os MESMOS placares, então 3ºs empatam e rankeiam por código.
    T1 vence todos 2-0; T2 vence T3 e T4 1-0; T3 vence T4 1-0.
    """
    a, b, c, d = group_ids(g)
    ms = [
        finished(start_mid, a, b, 2, 0, group=g),
        finished(start_mid + 1, a, c, 2, 0, group=g),
        finished(start_mid + 2, a, d, 2, 0, group=g),
        finished(start_mid + 3, b, c, 1, 0, group=g),
        finished(start_mid + 4, b, d, 1, 0, group=g),
        finished(start_mid + 5, c, d, 1, 0, group=g),
    ]
    return ms, start_mid + 6
