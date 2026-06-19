"""Aplica ScoreUpdates do provider ao banco, respeitando manual_lock."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

from ..db.repos import matches as matches_repo
from ..db.repos import teams as teams_repo
from ..db.schema import bump_data_version
from ..domain.entities import Match, MatchStatus
from ..services.live_bus import bus
from ..services.results import ResultError, set_score
from .base import ScoreUpdate
from ..db.connection import Db

log = logging.getLogger("bolao.sync")
MATCH_WINDOW = timedelta(hours=3)


def _index_local(conn: Db) -> Tuple[Dict[str, Match], List[Match]]:
    matches = matches_repo.all_matches(conn)
    by_external = {m.external_id: m for m in matches if m.external_id}
    return by_external, matches


def _find_local(
    update: ScoreUpdate,
    by_external: Dict[str, Match],
    matches: List[Match],
    code_of: Dict[int, str],
) -> Optional[Match]:
    m = by_external.get(update.external_id)
    if m is not None:
        return m
    candidates = [
        m for m in matches
        if abs(m.kickoff_utc - update.kickoff_utc) <= MATCH_WINDOW
    ]
    if update.home_code and update.away_code:
        for m in candidates:
            home = code_of.get(m.home_team_id)
            away = code_of.get(m.away_team_id)
            if home == update.home_code and away == update.away_code:
                return m
    if len(candidates) == 1:
        return candidates[0]
    return None


def apply_updates(conn: Db, updates: List[ScoreUpdate]) -> int:
    """Retorna o número de partidas alteradas (placar + kickoff)."""
    teams = teams_repo.all_teams(conn)
    code_of = {tid: t.code for tid, t in teams.items()}
    id_of_code = {t.code: tid for tid, t in teams.items()}
    by_external, matches = _index_local(conn)
    changed = 0
    kickoff_changed = 0

    for upd in updates:
        local = _find_local(upd, by_external, matches, code_of)
        if local is None:
            continue
        if local.external_id != upd.external_id:
            matches_repo.set_external_id(conn, local.id, upd.external_id)

        # Atualiza kickoff se o provider reportou um horário diferente (>60s)
        # e o jogo ainda não começou (não sobrescreve jogo em andamento/encerrado).
        if local.status == MatchStatus.SCHEDULED:
            diff = abs((local.kickoff_utc - upd.kickoff_utc).total_seconds())
            if diff > 60:
                matches_repo.set_kickoff(conn, local.id, upd.kickoff_utc.isoformat())
                log.info("kickoff atualizado jogo %s: %s", local.id, upd.kickoff_utc)
                kickoff_changed += 1

        if local.manual_lock:
            continue  # admin assumiu este jogo
        if upd.home_score is None or upd.away_score is None:
            continue  # nada a aplicar (jogo futuro)
        same = (
            local.home_score == upd.home_score
            and local.away_score == upd.away_score
            and local.status == upd.status
            and local.minute == upd.minute
            and local.period == upd.period
            and local.home_pens == upd.home_pens
            and local.away_pens == upd.away_pens
        )
        if same:
            continue
        winner_team_id = id_of_code.get(upd.winner_code) if upd.winner_code else None
        try:
            set_score(
                conn, local.id, upd.home_score, upd.away_score, upd.status,
                minute=upd.minute, winner_team_id=winner_team_id, force=True,
                period=upd.period, stoppage=upd.stoppage,
                home_pens=upd.home_pens, away_pens=upd.away_pens,
            )
            changed += 1
        except ResultError as exc:
            # ex.: mata-mata empatado sem winner — exige intervenção do admin
            log.warning("sync ignorou jogo %s: %s", local.id, exc)

    # Notifica clientes se apenas kickoffs mudaram (sem mudança de placar,
    # que já notifica dentro de set_score).
    if kickoff_changed and not changed:
        version = bump_data_version(conn)
        bus.publish(version)

    return changed + kickoff_changed
