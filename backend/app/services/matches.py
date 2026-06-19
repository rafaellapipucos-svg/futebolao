"""Listagem de jogos para a aba 'Jogos e Apostas' e detalhes com aposta do usuário."""
from __future__ import annotations

from typing import Dict, List, Optional

from ..db.repos import bets as bets_repo
from ..db.repos import matches as matches_repo
from ..db.repos import teams as teams_repo
from ..domain.betlock import bet_window, utcnow
from ..domain.entities import STAGE_LABELS_PT, Team
from .betting import bet_points
from .bracket_svc import source_label
from ..db.connection import Db


def _team_payload(team: Optional[Team], source: str) -> Dict:
    if team is None:
        return {"team": None, "label": source_label(source)}
    return {
        "team": {"id": team.id, "code": team.code, "name": team.name, "flag": team.flag},
        "label": None,
    }


def list_matches(conn: Db, user_id: int) -> List[Dict]:
    now = utcnow()
    teams = teams_repo.all_teams(conn)
    my_bets = {b.match_id: b for b in bets_repo.for_user(conn, user_id)}

    out: List[Dict] = []
    for m in sorted(matches_repo.all_matches(conn), key=lambda x: (x.kickoff_utc, x.id)):
        bet = my_bets.get(m.id)
        score = bet_points(bet, m) if bet else None
        open_, reason = bet_window(m, now)
        out.append({
            "id": m.id,
            "stage": m.stage.value,
            "stage_label": STAGE_LABELS_PT[m.stage],
            "group": m.group,
            "kickoff_utc": m.kickoff_utc.isoformat(),
            "venue": m.venue,
            "status": m.status.value,
            "minute": m.minute,
            "period": m.period,
            "stoppage": m.stoppage,
            "home_pens": m.home_pens,
            "away_pens": m.away_pens,
            "pens_log": m.pens_log,
            "home": _team_payload(teams.get(m.home_team_id), m.home_source),
            "away": _team_payload(teams.get(m.away_team_id), m.away_source),
            "home_score": m.home_score,
            "away_score": m.away_score,
            "bet_open": open_,
            "bet_lock_reason": None if open_ else reason,
            "my_bet": (
                {"home_goals": bet.home_goals, "away_goals": bet.away_goals}
                if bet else None
            ),
            "my_points": (
                {
                    "total": score.total, "base": score.base,
                    "multiplier": score.multiplier,
                    "hit_exact": score.hit_exact, "hit_result": score.hit_result,
                    "provisional": m.status.value == "live",
                }
                if score else None
            ),
        })
    return out
