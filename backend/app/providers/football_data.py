"""Adapter football-data.org (v4) para a Copa 2026 (competição WC).

HTTP injetável para testes. Free tier: 10 req/min — o poller respeita isso.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from ..domain.entities import MatchStatus
from .base import ScoreUpdate

API_URL = "https://api.football-data.org/v4/competitions/WC/matches"

STATUS_MAP = {
    "SCHEDULED": MatchStatus.SCHEDULED,
    "TIMED": MatchStatus.SCHEDULED,
    "POSTPONED": MatchStatus.SCHEDULED,
    "IN_PLAY": MatchStatus.LIVE,
    "PAUSED": MatchStatus.LIVE,
    "SUSPENDED": MatchStatus.LIVE,
    "FINISHED": MatchStatus.FINISHED,
    "AWARDED": MatchStatus.FINISHED,
}

# Nomes da football-data → código FIFA usado no nosso banco.
NAME_ALIASES: Dict[str, str] = {
    "Mexico": "MEX", "South Africa": "RSA", "Korea Republic": "KOR",
    "South Korea": "KOR", "Czechia": "CZE", "Czech Republic": "CZE",
    "Canada": "CAN", "Bosnia and Herzegovina": "BIH", "Qatar": "QAT",
    "Switzerland": "SUI", "Brazil": "BRA", "Morocco": "MAR", "Haiti": "HAI",
    "Scotland": "SCO", "United States": "USA", "USA": "USA", "Paraguay": "PAR",
    "Australia": "AUS", "Turkey": "TUR", "Türkiye": "TUR", "Germany": "GER",
    "Curaçao": "CUW", "Curacao": "CUW", "Ivory Coast": "CIV",
    "Côte d'Ivoire": "CIV", "Ecuador": "ECU", "Netherlands": "NED",
    "Japan": "JPN", "Sweden": "SWE", "Tunisia": "TUN", "Belgium": "BEL",
    "Egypt": "EGY", "Iran": "IRN", "IR Iran": "IRN", "New Zealand": "NZL",
    "Spain": "ESP", "Cape Verde": "CPV", "Cabo Verde": "CPV",
    "Saudi Arabia": "KSA", "Uruguay": "URU", "France": "FRA", "Senegal": "SEN",
    "Iraq": "IRQ", "Norway": "NOR", "Argentina": "ARG", "Algeria": "ALG",
    "Austria": "AUT", "Jordan": "JOR", "Portugal": "POR",
    "DR Congo": "COD", "Congo DR": "COD", "Uzbekistan": "UZB",
    "Colombia": "COL", "England": "ENG", "Croatia": "CRO", "Ghana": "GHA",
    "Panama": "PAN",
}


def _default_http_get(url: str, token: str) -> Dict:
    import requests

    resp = requests.get(url, headers={"X-Auth-Token": token}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def team_code(team: Optional[Dict]) -> Optional[str]:
    if not team:
        return None
    name = team.get("name")
    if name and name in NAME_ALIASES:
        return NAME_ALIASES[name]
    tla = team.get("tla")
    if tla:
        return tla
    return None


def _score_pair(score: Dict) -> tuple:
    """Placar que VALE para a aposta: o do FIM DA PRORROGAÇÃO (antes dos pênaltis).

    ATENÇÃO (doc oficial "Dealing with scores", v4): `fullTime` SOMA os pênaltis —
    `fullTime = regularTime + extraTime + penalties`. Ex. da doc: ET 1x1 e pênaltis
    6x5 viram `fullTime 7x6`. Logo, quando houve disputa de pênaltis, subtraímos o
    tally do shootout para obter o placar ao fim da prorrogação (= regularTime +
    extraTime). Sem pênaltis, `fullTime` já é o placar do tempo normal/prorrogação."""
    full = score.get("fullTime") or {}
    home, away = full.get("home"), full.get("away")
    pens = score.get("penalties") or {}
    ph, pa = pens.get("home"), pens.get("away")
    if isinstance(home, int) and isinstance(ph, int):
        home -= ph
    if isinstance(away, int) and isinstance(pa, int):
        away -= pa
    return home, away


def parse_match(raw: Dict) -> ScoreUpdate:
    status = STATUS_MAP.get(raw.get("status", ""), MatchStatus.SCHEDULED)
    score = raw.get("score") or {}
    home_score, away_score = _score_pair(score)
    home_code = team_code(raw.get("homeTeam"))
    away_code = team_code(raw.get("awayTeam"))
    winner_code = None
    winner = score.get("winner")
    if winner == "HOME_TEAM":
        winner_code = home_code
    elif winner == "AWAY_TEAM":
        winner_code = away_code
    kickoff = datetime.fromisoformat(raw["utcDate"].replace("Z", "+00:00"))
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)
    minute = raw.get("minute")
    minute = minute if isinstance(minute, int) else None
    pens = score.get("penalties") or {}
    home_pens, away_pens = pens.get("home"), pens.get("away")
    return ScoreUpdate(
        external_id=str(raw["id"]),
        kickoff_utc=kickoff,
        home_code=home_code,
        away_code=away_code,
        status=status,
        home_score=home_score if isinstance(home_score, int) else None,
        away_score=away_score if isinstance(away_score, int) else None,
        minute=minute,
        winner_code=winner_code,
        home_pens=home_pens if isinstance(home_pens, int) else None,
        away_pens=away_pens if isinstance(away_pens, int) else None,
        paused=raw.get("status") == "PAUSED",
        duration=score.get("duration"),
    )


class FootballDataProvider:
    name = "football-data.org"

    def __init__(self, token: str, http_get: Callable[[str, str], Dict] = _default_http_get):
        if not token:
            raise ValueError("FOOTBALL_DATA_TOKEN ausente")
        self._token = token
        self._http_get = http_get

    def fetch(self) -> List[ScoreUpdate]:
        data = self._http_get(API_URL, self._token)
        return [parse_match(m) for m in data.get("matches", [])]
