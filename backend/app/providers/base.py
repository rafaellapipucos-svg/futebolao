"""Contrato dos provedores de placar."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol

from ..domain.entities import MatchStatus


@dataclass(frozen=True)
class ScoreUpdate:
    external_id: str
    kickoff_utc: datetime
    home_code: Optional[str]   # código FIFA (None se desconhecido/TBD)
    away_code: Optional[str]
    status: MatchStatus
    home_score: Optional[int]
    away_score: Optional[int]
    minute: Optional[int] = None
    winner_code: Optional[str] = None  # mata-mata decidido em pênaltis/prorrogação
    stoppage: Optional[int] = None
    home_pens: Optional[int] = None    # disputa de pênaltis (tally)
    away_pens: Optional[int] = None
    paused: bool = False               # status cru == PAUSED (intervalo) p/ máquina de fase
    duration: Optional[str] = None     # REGULAR/EXTRA_TIME/PENALTY_SHOOTOUT (do provider)


class ScoreProvider(Protocol):
    name: str

    def fetch(self) -> List[ScoreUpdate]:
        """Busca o estado atual de todas as partidas. Lança exceção em falha."""
        ...
