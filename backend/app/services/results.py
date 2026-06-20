"""Aplicação de placares/resultados (admin e provider) com transições válidas."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..db.connection import tx
from ..db.repos import matches as matches_repo
from ..db.schema import bump_data_version
from ..domain.entities import LIVE_PERIODS, MatchStatus, Stage
from .live_bus import bus
from ..db.connection import Db

VALID_TRANSITIONS = {
    MatchStatus.SCHEDULED: {MatchStatus.SCHEDULED, MatchStatus.LIVE, MatchStatus.FINISHED},
    MatchStatus.LIVE: {MatchStatus.LIVE, MatchStatus.FINISHED},
    MatchStatus.FINISHED: {MatchStatus.FINISHED},  # reabrir só com force
}


class ResultError(Exception):
    pass


def set_score(
    conn: Db,
    match_id: int,
    home_score: int,
    away_score: int,
    status: MatchStatus,
    minute: Optional[int] = None,
    winner_team_id: Optional[int] = None,
    force: bool = False,
    set_lock: Optional[bool] = None,
    period: Optional[str] = None,
    stoppage: Optional[int] = None,
    home_pens: Optional[int] = None,
    away_pens: Optional[int] = None,
    pens_log: Optional[str] = None,
    period_started_at: Optional[str] = None,
) -> None:
    for v in (home_score, away_score):
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 99:
            raise ResultError("placar deve ser inteiro entre 0 e 99")
    if minute is not None and not 0 <= minute <= 130:
        raise ResultError("minuto inválido")
    if period is not None and period not in LIVE_PERIODS:
        raise ResultError(f"período inválido: {period!r}")
    if stoppage is not None and not 0 <= stoppage <= 30:
        raise ResultError("acréscimo inválido")
    for v in (home_pens, away_pens):
        if v is not None and (not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 99):
            raise ResultError("pênaltis devem ser inteiros entre 0 e 99")

    with tx(conn):
        match = matches_repo.by_id(conn, match_id)
        if match is None:
            raise ResultError("partida inexistente")
        if match.home_team_id is None or match.away_team_id is None:
            raise ResultError("confronto ainda sem times definidos")
        if not force and status not in VALID_TRANSITIONS[match.status]:
            raise ResultError(
                f"transição inválida {match.status.value} → {status.value} (use force)"
            )
        if (
            status == MatchStatus.FINISHED
            and match.stage != Stage.GROUP
            and home_score == away_score
            and winner_team_id is None
        ):
            raise ResultError(
                "mata-mata empatado exige winner_team_id (pênaltis/prorrogação)"
            )
        if winner_team_id is not None and winner_team_id not in (
            match.home_team_id, match.away_team_id
        ):
            raise ResultError("winner_team_id deve ser um dos times da partida")

        matches_repo.set_score(
            conn, match_id, home_score, away_score, status.value, minute, winner_team_id,
            period=period, stoppage=stoppage, home_pens=home_pens,
            away_pens=away_pens, pens_log=pens_log, period_started_at=period_started_at,
        )
        if set_lock is not None:
            matches_repo.set_manual_lock(conn, match_id, set_lock)
        from .bracket_svc import persist_resolutions  # import tardio: evita ciclo

        persist_resolutions(conn)  # propaga chaveamento na MESMA transação
        version = bump_data_version(conn)
    bus.publish(version)


def reset_match(conn: Db, match_id: int) -> None:
    """Volta a partida para 'scheduled' (corrigir erro grosseiro). Admin only."""
    with tx(conn):
        if matches_repo.by_id(conn, match_id) is None:
            raise ResultError("partida inexistente")
        matches_repo.reset_match(conn, match_id)
        version = bump_data_version(conn)
    bus.publish(version)


def update_kickoff(conn: Db, match_id: int, kickoff_utc_iso: str) -> None:
    """Atualiza o horário de um jogo e notifica clientes via SSE."""
    try:
        dt = datetime.fromisoformat(kickoff_utc_iso.replace("Z", "+00:00"))
    except ValueError:
        raise ResultError("formato de data inválido (use ISO 8601, ex: 2026-06-20T18:00:00Z)")
    if dt.tzinfo is None:
        raise ResultError("kickoff_utc deve incluir fuso horário (ex: Z ou +00:00)")
    with tx(conn):
        if matches_repo.by_id(conn, match_id) is None:
            raise ResultError("partida inexistente")
        matches_repo.set_kickoff(conn, match_id, dt.isoformat())
        version = bump_data_version(conn)
    bus.publish(version)
