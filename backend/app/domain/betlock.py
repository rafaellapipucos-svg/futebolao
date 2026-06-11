"""Trava de apostas — única fonte de verdade sobre quando uma aposta é editável."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple

from .entities import Match, MatchStatus


def bet_window(match: Match, now: datetime) -> Tuple[bool, str]:
    """Retorna (aberta?, motivo). `now` DEVE ser timezone-aware (UTC)."""
    if now.tzinfo is None:
        raise ValueError("now deve ser timezone-aware (UTC)")
    if match.home_team_id is None or match.away_team_id is None:
        return False, "confronto ainda não definido"
    if match.status != MatchStatus.SCHEDULED:
        return False, "partida já iniciada ou encerrada"
    if now >= match.kickoff_utc:
        return False, "apostas encerradas no apito inicial"
    return True, "aberta"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
