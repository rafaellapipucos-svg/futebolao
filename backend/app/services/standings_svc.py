"""Standings dos 12 grupos com modo ao vivo e flags de clinch."""
from __future__ import annotations

from typing import Dict, List

from ..db.repos import matches as matches_repo
from ..db.repos import teams as teams_repo
from ..domain import clinch as clinch_mod
from ..domain.entities import GROUPS, Stage, Team
from ..domain.standings import compute_group
from ..db.connection import Db


def _team_payload(team: Team) -> Dict:
    return {"id": team.id, "code": team.code, "name": team.name, "flag": team.flag}


def standings(conn: Db, include_live: bool = True) -> List[Dict]:
    teams = teams_repo.all_teams(conn)
    all_matches = matches_repo.all_matches(conn)
    group_matches = [m for m in all_matches if m.stage == Stage.GROUP]

    out: List[Dict] = []
    for g in GROUPS:
        ids = {tid: t.code for tid, t in teams.items() if t.group == g}
        mine = [m for m in group_matches if m.group == g]
        rows = compute_group(ids, mine, include_live=include_live)
        outlook = clinch_mod.analyze(ids.keys(), mine)
        finished = clinch_mod.group_finished(ids.keys(), mine)
        payload_rows = []
        for r in rows:
            o = outlook[r.team_id]
            payload_rows.append({
                "team": _team_payload(teams[r.team_id]),
                "position": r.position,
                "played": r.played, "won": r.won, "drawn": r.drawn, "lost": r.lost,
                "gf": r.gf, "ga": r.ga, "gd": r.gd, "points": r.points,
                "live": r.live, "tie_unresolved": r.tie_unresolved,
                "clinched_first": o.clinched_first,
                "clinched_top2": o.clinched_top2,
                "eliminated_top2": o.eliminated_top2,
            })
        out.append({"group": g, "finished": finished, "rows": payload_rows})
    return out
