"""Config pública, health e avatares (servidos do banco)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..db.connection import Db
from ..db.schema import get_data_version
from ..services.avatars import load_avatar
from .cookies import ensure_csrf_cookie
from .deps import CSRF_COOKIE, get_db, get_settings

router = APIRouter(tags=["meta"])


@router.get("/api/meta/config")
def config(request: Request, response: Response, settings=Depends(get_settings)):
    if CSRF_COOKIE not in request.cookies:
        ensure_csrf_cookie(response, settings)  # pré-auth: registro/login precisam
    return {
        "google_oauth": settings.google_oauth_enabled,
        "invite_required": settings.invite_code is not None,
        "live_provider": settings.football_data_token is not None,
    }


@router.get("/api/health")
def health(conn: Db = Depends(get_db)):
    return {"ok": True, "data_version": get_data_version(conn)}


@router.get("/u/avatars/{filename}")
def avatar(filename: str, conn: Db = Depends(get_db)):
    if not filename.endswith(".jpg"):
        raise HTTPException(404)
    stem = filename[:-4]
    if not stem.isdigit():
        raise HTTPException(404)
    data = load_avatar(conn, int(stem))
    if data is None:
        raise HTTPException(404)
    return Response(
        content=data, media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
