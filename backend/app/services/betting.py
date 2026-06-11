"""Apostas: upsert com trava de kickoff DENTRO da transação + listagem com pontos."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..db.connection import tx
from ..db.repos import bets as bets_repo
from ..db.repos import matches as matches_repo
from ..domain.betlock import bet_window, utcnow
from ..domain.entities import Bet, Match, MatchStatus
from ..domain.scoring import BetScore, score_bet
from ..db.connection import Db

MAX_GOALS = 20


class BetError(Exception):
    pass


class BetLockedError(BetError):
    pass


class BetValidationError(BetError):
    pass


def place_bet(
    conn: Db,
    user_id: int,
    match_id: int,
    home_goals: int,
    away_goals: int,
    now: Optional[datetime] = None,
) -> Bet:
    """Cria/edita aposta. Trava verificada na MESMA transação do write —
    nenhuma corrida permite apostar após o apito."""
    for v in (home_goals, away_goals):
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= MAX_GOALS:
            raise BetValidationError(f"gols devem ser inteiros entre 0 e {MAX_GOALS}")
    current = utcnow() if now is None else now
    with tx(conn):
        match = matches_repo.by_id(conn, match_id)
        if match is None:
            raise BetValidationError("partida inexistente")
        open_, reason = bet_window(match, current)
        if not open_:
            raise BetLockedError(reason)
        # updated_at = horario informado da aposta (determinístico nos testes;
        # em prod e' utcnow). Mantem a defesa: bet_points zera se >= kickoff.
        return bets_repo.upsert(
            conn, user_id, match_id, home_goals, away_goals,
            updated_at=current.isoformat(),
        )


def bet_points(bet: Bet, match: Match) -> Optional[BetScore]:
    """Pontos da aposta (final ou provisório se live). None se sem placar.
    Defesa em profundidade: aposta editada após o kickoff não pontua."""
    if not match.has_score or match.status == MatchStatus.SCHEDULED:
        return None
    if bet.updated_at >= match.kickoff_utc:
        return None
    return score_bet(
        bet.home_goals, bet.away_goals, match.home_score, match.away_score, match.stage
    )


def user_bets_with_points(conn: Db, user_id: int) -> List[Dict]:
    """Apostas do usuário com pontos (provisórios em live, finais em finished)."""
    matches = {m.id: m for m in matches_repo.all_matches(conn)}
    out: List[Dict] = []
    for bet in bets_repo.for_user(conn, user_id):
        match = matches[bet.match_id]
        score = bet_points(bet, match)
        out.append({"bet": bet, "match": match, "score": score})
    return out


def admin_set_bet(
    conn: Db, user_id: int, match_id: int, home_goals: int, away_goals: int
) -> Bet:
    """Admin edita a aposta de qualquer usuario, inclusive em jogos ja
    iniciados/encerrados. bet_points zera apostas com updated_at >= kickoff
    (defesa contra edicao pos-apito do usuario); para a edicao do ADMIN
    pontuar, gravamos updated_at como imediatamente antes do kickoff quando o
    jogo ja comecou. Sem trava de janela (e' acao administrativa)."""
    for v in (home_goals, away_goals):
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= MAX_GOALS:
            raise BetValidationError(f"gols devem ser inteiros entre 0 e {MAX_GOALS}")
    with tx(conn):
        match = matches_repo.by_id(conn, match_id)
        if match is None:
            raise BetValidationError("partida inexistente")
        now = utcnow()
        if now >= match.kickoff_utc:
            ts = (match.kickoff_utc - timedelta(seconds=60)).isoformat()
        else:
            ts = now.isoformat()
        return bets_repo.upsert(
            conn, user_id, match_id, home_goals, away_goals, updated_at=ts
        )
