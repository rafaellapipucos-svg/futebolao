"""Standings dos 12 grupos com modo ao vivo e flags de clinch."""
from __future__ import annotations

from typing import Dict, List

from ..db.repos import matches as matches_repo
from ..db.repos import teams as teams_repo
from ..domain import clinch as clinch_mod
from ..domain.entities import GROUPS, Stage, Team
from ..domain.standings import Row, compute_group
from ..domain.thirds import qualified_thirds
from ..db.connection import Db


def _team_payload(team: Team) -> Dict:
    return {"id": team.id, "code": team.code, "name": team.name, "flag": team.flag}


def mark_qualifying_thirds(third_rows: Dict[str, Row]) -> set:
    """{grupo: Row do 3º colocado} → letras dos grupos cujos 3ºs estão entre os 8
    melhores (previsão de classificação pelo ranking ATUAL). Rodada 16 (feature D)."""
    return set(qualified_thirds(third_rows))


def standings(conn: Db, include_live: bool = True) -> List[Dict]:
    teams = teams_repo.all_teams(conn)
    all_matches = matches_repo.all_matches(conn)
    group_matches = [m for m in all_matches if m.stage == Stage.GROUP]

    # 1ª passada: linhas de cada grupo + o 3º colocado de cada um.
    per_group: Dict[str, tuple] = {}
    third_rows: Dict[str, Row] = {}
    for g in GROUPS:
        ids = {tid: t.code for tid, t in teams.items() if t.group == g}
        mine = [m for m in group_matches if m.group == g]
        rows = compute_group(ids, mine, include_live=include_live)
        per_group[g] = (ids, mine, rows)
        third_rows[g] = rows[2]
    qualifying = mark_qualifying_thirds(third_rows)  # 8 melhores 3ºs (previsão)

    out: List[Dict] = []
    for g in GROUPS:
        ids, mine, rows = per_group[g]
        outlook = clinch_mod.analyze(ids.keys(), mine)
        finished = clinch_mod.group_finished(ids.keys(), mine)
        payload_rows = []
        for r in rows:
            o = outlook[r.team_id]
            # Grupo encerrado: posição final (com desempates de saldo/GP/H2H) já é
            # definitiva. O clinch é conservador (só pontos) e não enxerga isso, então
            # a classificação garantida passa a vir da posição. Ver clinch.py docstring.
            clinched_first = o.clinched_first or (finished and r.position == 1)
            clinched_top2 = o.clinched_top2 or (finished and r.position <= 2)
            eliminated_top2 = o.eliminated_top2 or (finished and r.position > 2)
            row = {
                "team": _team_payload(teams[r.team_id]),
                "position": r.position,
                "played": r.played, "won": r.won, "drawn": r.drawn, "lost": r.lost,
                "gf": r.gf, "ga": r.ga, "gd": r.gd, "points": r.points,
                "live": r.live, "tie_unresolved": r.tie_unresolved,
                "clinched_first": clinched_first,
                "clinched_top2": clinched_top2,
                "eliminated_top2": eliminated_top2,
            }
            if r.position == 3:  # 3º colocado: marca se passaria entre os 8 melhores
                row["third_qualifying"] = g in qualifying
            payload_rows.append(row)
        out.append({"group": g, "finished": finished, "rows": payload_rows})
    return out
