"""Entidades e constantes do domínio. Puro: sem I/O, sem dependências externas."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class Stage(str, Enum):
    GROUP = "GROUP"
    R32 = "R32"
    R16 = "R16"
    QF = "QF"
    SF = "SF"
    THIRD = "THIRD"
    FINAL = "FINAL"


# Multiplicadores de pontuação por fase (regra do bolão).
MULTIPLIERS = {
    Stage.GROUP: 1,
    Stage.R32: 2,
    Stage.R16: 3,
    Stage.QF: 4,
    Stage.SF: 5,
    Stage.THIRD: 5,
    Stage.FINAL: 10,
}

STAGE_LABELS_PT = {
    Stage.GROUP: "Fase de Grupos",
    Stage.R32: "16 avos de final",
    Stage.R16: "Oitavas de final",
    Stage.QF: "Quartas de final",
    Stage.SF: "Semifinais",
    Stage.THIRD: "Disputa de 3º lugar",
    Stage.FINAL: "Grande Final",
}


class MatchStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"


# Fases do relógio ao vivo (coluna `period` de matches).
LIVE_PERIODS = {"1H", "HT", "2H", "ET1", "ET_HT", "ET2", "PENS", "FT"}


@dataclass(frozen=True)
class Team:
    id: int
    code: str
    name: str
    flag: str
    group: str


@dataclass
class Match:
    id: int  # número oficial FIFA (1..104)
    stage: Stage
    kickoff_utc: datetime  # timezone-aware (UTC)
    venue: str
    home_source: str  # 'BRA' | '1A' | '2B' | '3:ABCDF' | 'W73' | 'L101'
    away_source: str
    group: Optional[str] = None
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: MatchStatus = MatchStatus.SCHEDULED
    minute: Optional[int] = None
    winner_team_id: Optional[int] = None  # mata-mata: vencedor (pênaltis etc.)
    manual_lock: bool = False
    external_id: Optional[str] = None
    period: Optional[str] = None     # relógio ao vivo: 1H/HT/2H/ET1/ET_HT/ET2/PENS/FT
    stoppage: Optional[int] = None   # acréscimos da fase atual (45+X, 90+X, ...)
    home_pens: Optional[int] = None  # disputa de pênaltis (None se não houve)
    away_pens: Optional[int] = None
    pens_log: Optional[str] = None   # JSON chute-a-chute (opcional, p/ mini-placar)
    period_started_at: Optional[str] = None  # ISO: início da fase atual (relógio ao vivo)

    @property
    def has_score(self) -> bool:
        return self.home_score is not None and self.away_score is not None

    @property
    def is_finished(self) -> bool:
        return self.status == MatchStatus.FINISHED

    @property
    def is_live(self) -> bool:
        return self.status == MatchStatus.LIVE

    @property
    def went_to_penalties(self) -> bool:
        return self.home_pens is not None and self.away_pens is not None

    def winner_id(self) -> Optional[int]:
        """Vencedor do confronto (para propagação no bracket).

        Placar do FIM DA PRORROGAÇÃO decide; empate exige winner_team_id
        explícito (vencedor dos pênaltis, informado por admin ou provider).
        """
        if not self.is_finished or not self.has_score:
            return None
        if self.home_score > self.away_score:
            return self.home_team_id
        if self.away_score > self.home_score:
            return self.away_team_id
        return self.winner_team_id

    def loser_id(self) -> Optional[int]:
        win = self.winner_id()
        if win is None or self.home_team_id is None or self.away_team_id is None:
            return None
        return self.away_team_id if win == self.home_team_id else self.home_team_id


@dataclass
class Bet:
    id: int
    user_id: int
    match_id: int
    home_goals: int
    away_goals: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ScoreDetails:
    """Campos OPCIONAIS de um placar (relógio ao vivo + mata-mata) agrupados, para
    set_score não carregar uma lista longa de parâmetros (B5). O placar em si
    (home_score/away_score/status) e as flags (force/set_lock) ficam fora — são
    dados obrigatórios e controle, não detalhes."""
    minute: Optional[int] = None
    winner_team_id: Optional[int] = None
    period: Optional[str] = None
    stoppage: Optional[int] = None
    home_pens: Optional[int] = None
    away_pens: Optional[int] = None
    pens_log: Optional[str] = None
    period_started_at: Optional[str] = None


GROUPS = "ABCDEFGHIJKL"

# Slots da Annex C na ordem das colunas oficiais e seus jogos do R32.
THIRD_SLOTS = ["1A", "1B", "1D", "1E", "1G", "1I", "1K", "1L"]
THIRD_SLOT_TO_MATCH = {"1A": 79, "1B": 85, "1D": 81, "1E": 74, "1G": 82, "1I": 77, "1K": 87, "1L": 80}
MATCH_TO_THIRD_SLOT = {m: s for s, m in THIRD_SLOT_TO_MATCH.items()}
