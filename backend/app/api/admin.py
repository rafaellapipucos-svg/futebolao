"""Rotas administrativas (placar manual, sync, usuários)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from ..core.passwords import WeakPasswordError, hash_password, validate_password_strength
from ..db.repos import matches as matches_repo
from ..db.repos import tokens as tokens_repo
from ..db.repos import users as users_repo
from ..db.schema import bump_data_version
from ..domain.entities import MatchStatus
from ..services.bracket_svc import persist_resolutions
from ..services.live_bus import bus
from ..services.results import ResultError, reset_match, set_score
from .deps import get_db, get_settings, rate_limit, require_admin, require_csrf
from .schemas import AdminResetPasswordIn, AdminScoreIn
from ..db.connection import Db

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin), Depends(rate_limit("mutate"))],
)


@router.post("/matches/{match_id}/score", dependencies=[Depends(require_csrf)])
def admin_set_score(
    match_id: int, body: AdminScoreIn, conn: Db = Depends(get_db)
):
    try:
        set_score(
            conn, match_id, body.home_score, body.away_score,
            MatchStatus(body.status), minute=body.minute,
            winner_team_id=body.winner_team_id, force=body.force,
            set_lock=body.lock,
        )
    except ResultError as exc:
        raise HTTPException(422, str(exc))
    return {"ok": True}


@router.post("/matches/{match_id}/reset", dependencies=[Depends(require_csrf)])
def admin_reset_match(match_id: int, conn: Db = Depends(get_db)):
    try:
        reset_match(conn, match_id)
    except ResultError as exc:
        raise HTTPException(422, str(exc))
    return {"ok": True}


@router.post("/matches/{match_id}/lock", dependencies=[Depends(require_csrf)])
def admin_toggle_lock(
    match_id: int, lock: bool, conn: Db = Depends(get_db)
):
    if matches_repo.by_id(conn, match_id) is None:
        raise HTTPException(404, "partida inexistente")
    matches_repo.set_manual_lock(conn, match_id, lock)
    return {"ok": True, "manual_lock": lock}


@router.post("/sync", dependencies=[Depends(require_csrf)])
async def admin_sync(
    conn: Db = Depends(get_db), settings=Depends(get_settings)
):
    if not settings.football_data_token:
        raise HTTPException(503, "FOOTBALL_DATA_TOKEN não configurado")
    from ..providers.football_data import FootballDataProvider
    from ..providers.sync import apply_updates

    provider = FootballDataProvider(settings.football_data_token)
    updates = await asyncio.to_thread(provider.fetch)
    changed = await asyncio.to_thread(apply_updates, conn, updates)
    return {"ok": True, "changed": changed}


@router.post("/recompute", dependencies=[Depends(require_csrf)])
def admin_recompute(conn: Db = Depends(get_db)):
    changed = persist_resolutions(conn)
    version = bump_data_version(conn)
    bus.publish(version)
    return {"ok": True, "resolved": changed}


@router.get("/users")
def admin_users(conn: Db = Depends(get_db)):
    return {
        "users": [
            {
                "id": u["id"], "email": u["email"],
                "display_name": u["display_name"],
                "is_admin": bool(u["is_admin"]), "created_at": u["created_at"],
            }
            for u in users_repo.list_all(conn)
        ]
    }


@router.post("/users/{user_id}/reset-password", dependencies=[Depends(require_csrf)])
def admin_reset_password(
    user_id: int,
    body: AdminResetPasswordIn,
    conn: Db = Depends(get_db),
    settings=Depends(get_settings),
):
    if users_repo.by_id(conn, user_id) is None:
        raise HTTPException(404, "usuário não encontrado")
    try:
        validate_password_strength(body.new_password)
    except WeakPasswordError as exc:
        raise HTTPException(422, str(exc))
    users_repo.set_password(
        conn, user_id, hash_password(body.new_password, settings.pepper)
    )
    tokens_repo.revoke_all_for_user(conn, user_id)
    return {"ok": True}
