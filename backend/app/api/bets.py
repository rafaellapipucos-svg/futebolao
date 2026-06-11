"""Rotas de apostas."""
from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException

from ..services.betting import (
    BetLockedError, BetValidationError, place_bet, user_bets_with_points,
)
from .deps import get_current_user, get_db, rate_limit, require_csrf
from .schemas import BetIn
from ..db.connection import Db

router = APIRouter(prefix="/api/bets", tags=["bets"])


@router.put("/{match_id}",
            dependencies=[Depends(rate_limit("mutate")), Depends(require_csrf)])
def put_bet(
    match_id: int,
    body: BetIn,
    conn: Db = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        bet = place_bet(conn, user["id"], match_id, body.home_goals, body.away_goals)
    except BetLockedError as exc:
        raise HTTPException(409, str(exc))
    except BetValidationError as exc:
        raise HTTPException(422, str(exc))
    return {
        "match_id": bet.match_id,
        "home_goals": bet.home_goals,
        "away_goals": bet.away_goals,
        "updated_at": bet.updated_at.isoformat(),
    }


@router.get("/mine")
def my_bets(
    conn: Db = Depends(get_db), user=Depends(get_current_user)
):
    rows = user_bets_with_points(conn, user["id"])
    out = []
    for r in rows:
        bet, match, score = r["bet"], r["match"], r["score"]
        out.append({
            "match_id": match.id,
            "home_goals": bet.home_goals,
            "away_goals": bet.away_goals,
            "updated_at": bet.updated_at.isoformat(),
            "points": (
                {
                    "total": score.total, "base": score.base,
                    "multiplier": score.multiplier,
                    "hit_exact": score.hit_exact, "hit_result": score.hit_result,
                    "provisional": match.status.value == "live",
                } if score else None
            ),
        })
    return {"bets": out}
