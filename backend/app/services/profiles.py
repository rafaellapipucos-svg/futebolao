"""Perfil público: o que outros jogadores podem ver (SEM e-mail/Google)."""
from __future__ import annotations

from typing import Dict, Optional

from ..db.connection import Db
from ..db.repos import users as users_repo
from .leaderboard import leaderboard
from .matches import list_matches


def _avatar_url(user) -> Optional[str]:
    if user["avatar_ver"]:
        return f"/u/avatars/{user['id']}.jpg?v={user['avatar_ver']}"
    return None


def closed_history(conn: Db, user_id: int) -> list:
    """Apostas de jogos ENCERRADOS feitas pelo usuário (com pontos), da partida
    MAIS RECENTE para a mais antiga (por data do apito, não por id)."""
    items = [
        {
            "match_id": m["id"],
            "stage_label": m["stage_label"],
            "kickoff_utc": m["kickoff_utc"],
            "home": m["home"],
            "away": m["away"],
            "home_score": m["home_score"],
            "away_score": m["away_score"],
            "bet": m["my_bet"],
            "points": m["my_points"],
        }
        for m in list_matches(conn, user_id)
        if m["status"] == "finished" and m["my_bet"]
    ]
    # kickoff_utc é ISO-8601 → ordenação lexical = cronológica. Mais recente 1º.
    items.sort(key=lambda x: x["kickoff_utc"], reverse=True)
    return items


def public_profile(conn: Db, user_id: int) -> Optional[Dict]:
    user = users_repo.by_id(conn, user_id)
    if user is None:
        return None
    lb = leaderboard(conn, include_live=True)
    row = next((r for r in lb if r["user_id"] == user_id), None)
    return {
        "id": user["id"],
        "display_name": user["display_name"],
        "avatar_url": _avatar_url(user),
        "bio": user["bio"],
        "position": row["position"] if row else None,
        "total_points": row["total"] if row else 0,
        "history": closed_history(conn, user_id),
    }
