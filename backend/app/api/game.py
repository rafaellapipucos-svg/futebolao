"""Rotas de leitura do jogo: partidas, standings, leaderboard, bracket."""
from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException

from ..services.bracket_svc import predicted_bracket_payload
from ..services.leaderboard import leaderboard
from ..services.matches import list_matches
from ..services.public_bets import live_matches, match_bets_public
from ..services.standings_svc import standings
from .deps import get_current_user, get_db
from ..db.connection import Db

router = APIRouter(prefix="/api", tags=["game"])


@router.get("/matches")
def matches(
    conn: Db = Depends(get_db), user=Depends(get_current_user)
):
    return {"matches": list_matches(conn, user["id"])}


@router.get("/standings")
def get_standings(
    conn: Db = Depends(get_db), user=Depends(get_current_user)
):
    return {"groups": standings(conn, include_live=True)}


@router.get("/leaderboard")
def get_leaderboard(
    conn: Db = Depends(get_db), user=Depends(get_current_user)
):
    rows = leaderboard(conn, include_live=True)
    payload = []
    for r in rows:
        avatar_url = (
            f"/u/avatars/{r['user_id']}.jpg?v={r['avatar_ver']}"
            if r["avatar_ver"] else None
        )
        payload.append({
            "position": r["position"],
            "user_id": r["user_id"],
            "display_name": r["display_name"],
            "avatar_url": avatar_url,
            "total": r["total"],
            "live_total": r["live_total"],
            "exact_hits": r["exact_hits"],
            "result_hits": r["result_hits"],
            "has_live": r["has_live"],
            "is_me": r["user_id"] == user["id"],
        })
    return {"leaderboard": payload}


@router.get("/matches/{match_id}/bets")
def match_bets(
    match_id: int, conn: Db = Depends(get_db), user=Depends(get_current_user)
):
    data = match_bets_public(conn, match_id)
    if data is None:
        raise HTTPException(404, "partida inexistente")
    return data


@router.get("/live/matches")
def live(conn: Db = Depends(get_db), user=Depends(get_current_user)):
    return {"matches": live_matches(conn)}


@router.get("/bracket")
def get_bracket(
    conn: Db = Depends(get_db), user=Depends(get_current_user)
):
    return {"matches": predicted_bracket_payload(conn)}
