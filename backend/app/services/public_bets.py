"""Apostas públicas: só são reveladas a partir do apito inicial do jogo.
Antes do kickoff ficam escondidas (cada um aposta às cegas)."""
from __future__ import annotations

from typing import Dict, List, Optional

from ..db.connection import Db
from ..db.repos import bets as bets_repo
from ..db.repos import matches as matches_repo
from ..db.repos import teams as teams_repo
from ..db.repos import users as users_repo
from ..domain.betlock import bet_window, utcnow
from ..domain.entities import STAGE_LABELS_PT, MatchStatus
from .betting import bet_points
from .matches import _team_payload


def _avatar(user) -> Optional[str]:
    if user["avatar_ver"]:
        return f"/u/avatars/{user['id']}.jpg?v={user['avatar_ver']}"
    return None


def match_bets_public(conn: Db, match_id: int) -> Optional[Dict]:
    """Apostas de UM jogo. revealed=False (e bets vazio) antes do kickoff."""
    match = matches_repo.by_id(conn, match_id)
    if match is None:
        return None
    open_, _ = bet_window(match, utcnow())
    if open_:
        return {"match_id": match_id, "revealed": False, "bets": []}
    users = {u["id"]: u for u in users_repo.list_all(conn)}
    out: List[Dict] = []
    for bet in bets_repo.for_match(conn, match_id):
        u = users.get(bet.user_id)
        if u is None:
            continue
        score = bet_points(bet, match)
        out.append({
            "user_id": bet.user_id,
            "display_name": u["display_name"],
            "avatar_url": _avatar(u),
            "home_goals": bet.home_goals,
            "away_goals": bet.away_goals,
            "points": (
                {
                    "total": score.total,
                    "hit_exact": score.hit_exact,
                    "hit_result": score.hit_result,
                    "provisional": match.status == MatchStatus.LIVE,
                } if score else None
            ),
        })
    out.sort(key=lambda b: (-(b["points"]["total"] if b["points"] else 0),
                            b["display_name"].lower()))
    return {"match_id": match_id, "revealed": True, "bets": out}


def live_matches(conn: Db) -> List[Dict]:
    """Jogos AO VIVO agora, cada um com as apostas públicas dos jogadores."""
    teams = teams_repo.all_teams(conn)
    out: List[Dict] = []
    for m in sorted(matches_repo.all_matches(conn), key=lambda x: (x.kickoff_utc, x.id)):
        if m.status != MatchStatus.LIVE:
            continue
        pub = match_bets_public(conn, m.id)
        out.append({
            "id": m.id,
            "status": m.status.value,
            "stage_label": STAGE_LABELS_PT[m.stage],
            "group": m.group,
            "kickoff_utc": m.kickoff_utc.isoformat(),
            "minute": m.minute,
            "period": m.period,
            "period_started_at": m.period_started_at,
            "stoppage": m.stoppage,
            "home_pens": m.home_pens,
            "away_pens": m.away_pens,
            "pens_log": m.pens_log,
            "home": _team_payload(teams.get(m.home_team_id), m.home_source),
            "away": _team_payload(teams.get(m.away_team_id), m.away_source),
            "home_score": m.home_score,
            "away_score": m.away_score,
            "bets": pub["bets"] if pub else [],
        })
    return out
