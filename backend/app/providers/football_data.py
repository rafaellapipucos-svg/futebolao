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

# TLAs da football-data que diferem do código FIFA.
TLA_FIXES = {"KOR": "KOR", "SUI": "SUI", "URU": "URU"}


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
        return TLA_FIXES.get(tla, tla)
    return None


def _score_pair(score: Dict) -> tuple:
    """Placar que VALE para a aposta (Rodada 16): o do FIM DA PRORROGAÇÃO,
    antes dos pênaltis = `fullTime` (já inclui a prorrogação). Em jogo decidido
    no tempo normal, fullTime == placar dos 90min. Pênaltis ficam em `penalties`."""
    full = score.get("fullTime") or {}
    return full.get("home"), full.get("away")


def _derive_period(
    raw_status: str, duration: Optional[str], minute: Optional[int]
) -> Optional[str]:
    """Fase do relógio (heurística sobre status+duration+minuto da football-data)."""
    if raw_status in ("FINISHED", "AWARDED"):
        return "FT"
    if raw_status == "PAUSED":
        return "ET_HT" if duration == "EXTRA_TIME" else "HT"
    if raw_status in ("IN_PLAY", "SUSPENDED"):
        if duration == "PENALTY_SHOOTOUT":
            return "PENS"
        if duration == "EXTRA_TIME":
            return "ET2" if (minute is not None and minute > 105) else "ET1"
        return "2H" if (minute is not None and minute > 45) else "1H"
    return None


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
        period=_derive_period(raw.get("status", ""), score.get("duration"), minute),
        home_pens=home_pens if isinstance(home_pens, int) else None,
        away_pens=away_pens if isinstance(away_pens, int) else None,
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
