"""Chaveamento: resolução preditiva, persistência dos confrontos e payload da API."""
from __future__ import annotations

from typing import Dict, List, Optional

from ..db.repos import matches as matches_repo
from ..db.repos import teams as teams_repo
from ..domain import clinch as clinch_mod
from ..domain.bracket import build_context, resolve_all
from ..domain.entities import GROUPS, STAGE_LABELS_PT, Stage
from ..domain.standings import compute_group
from ..domain.thirds import allocate, qualified_thirds
from ..seed.loader import load_annex_c_table
from ..db.connection import Db

_ANNEX_CACHE: Optional[dict] = None


def _annex() -> dict:
    global _ANNEX_CACHE
    if _ANNEX_CACHE is None:
        _ANNEX_CACHE = load_annex_c_table()
    return _ANNEX_CACHE


def _third_assignment(conn: Db) -> Optional[Dict[str, int]]:
    """Annex C exige os 12 grupos encerrados (conjunto dos 8 melhores 3ºs)."""
    teams = teams_repo.all_teams(conn)
    group_matches = [
        m for m in matches_repo.all_matches(conn) if m.stage == Stage.GROUP
    ]
    third_rows, third_team = {}, {}
    for g in GROUPS:
        ids = {tid: t.code for tid, t in teams.items() if t.group == g}
        mine = [m for m in group_matches if m.group == g]
        if not clinch_mod.group_finished(ids.keys(), mine):
            return None
        rows = compute_group(ids, mine, include_live=False)
        third_rows[g] = rows[2]
        third_team[g] = rows[2].team_id
    return allocate(_annex(), third_team, qualified_thirds(third_rows))


def persist_resolutions(conn: Db) -> int:
    """Grava times resolvidos nos jogos de mata-mata. Retorna nº de mudanças.
    Nunca sobrescreve um time já definido com None (não 'des-resolve')."""
    teams = teams_repo.all_teams(conn)
    all_matches = matches_repo.all_matches(conn)
    ctx = build_context(teams, all_matches, third_assignment=_third_assignment(conn))
    resolved = resolve_all(ctx)
    changed = 0
    for mid, (home, away) in resolved.items():
        m = ctx.matches_by_id[mid]
        new_home = home if home is not None else m.home_team_id
        new_away = away if away is not None else m.away_team_id
        if (new_home, new_away) != (m.home_team_id, m.away_team_id):
            matches_repo.set_teams(conn, mid, new_home, new_away)
            changed += 1
    return changed


def source_label(source: str) -> str:
    if source.startswith("3:"):
        return "3º (" + "/".join(source[2:]) + ")"
    if source.startswith("W"):
        return f"Vencedor J{source[1:]}"
    if source.startswith("L"):
        return f"Perdedor J{source[1:]}"
    if len(source) == 2 and source[0] in "12":
        return f"{source[0]}º do Grupo {source[1]}"
    return source


def bracket_payload(conn: Db) -> List[Dict]:
    teams = teams_repo.all_teams(conn)

    def side(team_id: Optional[int], source: str) -> Dict:
        if team_id is not None and team_id in teams:
            t = teams[team_id]
            return {"team": {"id": t.id, "code": t.code, "name": t.name, "flag": t.flag},
                    "label": None}
        return {"team": None, "label": source_label(source)}

    out: List[Dict] = []
    for m in matches_repo.all_matches(conn):
        if m.stage == Stage.GROUP:
            continue
        out.append({
            "id": m.id,
            "stage": m.stage.value,
            "stage_label": STAGE_LABELS_PT[m.stage],
            "kickoff_utc": m.kickoff_utc.isoformat(),
            "venue": m.venue,
            "status": m.status.value,
            "minute": m.minute,
            "home": side(m.home_team_id, m.home_source),
            "away": side(m.away_team_id, m.away_source),
            "home_score": m.home_score,
            "away_score": m.away_score,
            "winner_team_id": m.winner_id(),
        })
    return out
