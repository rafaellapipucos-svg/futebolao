"""Emissão/limpeza dos cookies de sessão e CSRF."""
from __future__ import annotations

from fastapi import Response

from ..config import Settings
from ..core import csrf as csrf_mod
from ..core.tokens import ACCESS_TTL_SECONDS, REFRESH_TTL_SECONDS, TokenPair

REFRESH_PATH = "/api/auth"


def set_session_cookies(response: Response, settings: Settings, pair: TokenPair) -> None:
    response.set_cookie(
        "access_token", pair.access,
        max_age=ACCESS_TTL_SECONDS, httponly=True, samesite="lax",
        secure=settings.cookie_secure, path="/",
    )
    response.set_cookie(
        "refresh_token", pair.refresh,
        max_age=REFRESH_TTL_SECONDS, httponly=True, samesite="lax",
        secure=settings.cookie_secure, path=REFRESH_PATH,
    )
    ensure_csrf_cookie(response, settings)


def ensure_csrf_cookie(response: Response, settings: Settings) -> str:
    token = csrf_mod.generate_token()
    response.set_cookie(
        "csrf_token", token,
        max_age=REFRESH_TTL_SECONDS, httponly=False, samesite="lax",
        secure=settings.cookie_secure, path="/",
    )
    return token


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path=REFRESH_PATH)
    response.delete_cookie("csrf_token", path="/")
