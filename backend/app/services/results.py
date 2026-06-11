"""Aplicação de placares/resultados (admin e provider) com transições válidas."""
from __future__ import annotations

from typing import Optional

from ..db.connection import tx
from ..db.repos import matches as matches_repo
from ..db.schema import bump_data_version
from ..domain.entities import MatchStatus, Stage
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
) -> None:
    for v in (home_score, away_score):
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 99:
            raise ResultError("placar deve ser inteiro entre 0 e 99")
    if minute is not None and not 0 <= minute <= 130:
        raise ResultError("minuto inválido")

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
            conn, match_id, home_score, away_score, status.value, minute, winner_team_id
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
