"""Aplicação de placares/resultados (admin e provider) com transições válidas."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from ..db.connection import tx
from ..db.repos import matches as matches_repo
from ..db.schema import bump_data_version
from ..domain.entities import LIVE_PERIODS, MatchStatus, ScoreDetails, Stage
from .live_bus import bus
from ..db.connection import Db

VALID_TRANSITIONS = {
    MatchStatus.SCHEDULED: {MatchStatus.SCHEDULED, MatchStatus.LIVE, MatchStatus.FINISHED},
    MatchStatus.LIVE: {MatchStatus.LIVE, MatchStatus.FINISHED},
    MatchStatus.FINISHED: {MatchStatus.FINISHED},  # reabrir só com force
}


class ResultError(Exception):
    pass


def _validate_pens_log(pens_log: str) -> None:
    """pens_log é JSON: lista de [team, scored] na ordem das cobranças.
    Ex.: [["home", true], ["away", false]]. Inválido derruba (fail loud)."""
    try:
        parsed = json.loads(pens_log)
    except (ValueError, TypeError) as exc:
        raise ResultError("pens_log inválido: JSON malformado") from exc
    if not isinstance(parsed, list):
        raise ResultError("pens_log deve ser uma lista de cobranças")
    for kick in parsed:
        if (not isinstance(kick, list) or len(kick) != 2
                or kick[0] not in ("home", "away")
                or not isinstance(kick[1], bool)):
            raise ResultError(
                'cada cobrança do pens_log deve ser ["home"|"away", true|false]'
            )


def set_score(
    conn: Db,
    match_id: int,
    home_score: int,
    away_score: int,
    status: MatchStatus,
    *,
    force: bool = False,
    set_lock: Optional[bool] = None,
    details: Optional[ScoreDetails] = None,
) -> None:
    """Aplica um placar. `details` (ScoreDetails) carrega os campos opcionais
    (minuto, vencedor, período, acréscimo, pênaltis); force/set_lock são flags."""
    d = details or ScoreDetails()
    for v in (home_score, away_score):
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 99:
            raise ResultError("placar deve ser inteiro entre 0 e 99")
    if d.minute is not None and not 0 <= d.minute <= 130:
        raise ResultError("minuto inválido")
    if d.period is not None and d.period not in LIVE_PERIODS:
        raise ResultError(f"período inválido: {d.period!r}")
    if d.stoppage is not None and not 0 <= d.stoppage <= 30:
        raise ResultError("acréscimo inválido")
    for v in (d.home_pens, d.away_pens):
        if v is not None and (not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 99):
            raise ResultError("pênaltis devem ser inteiros entre 0 e 99")
    if d.pens_log is not None:
        _validate_pens_log(d.pens_log)

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
            and d.winner_team_id is None
        ):
            raise ResultError(
                "mata-mata empatado exige winner_team_id (pênaltis/prorrogação)"
            )
        if d.winner_team_id is not None and d.winner_team_id not in (
            match.home_team_id, match.away_team_id
        ):
            raise ResultError("winner_team_id deve ser um dos times da partida")

        matches_repo.set_score(
            conn, match_id, home_score, away_score, status.value, d.minute,
            d.winner_team_id, period=d.period, stoppage=d.stoppage,
            home_pens=d.home_pens, away_pens=d.away_pens, pens_log=d.pens_log,
            period_started_at=d.period_started_at,
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
