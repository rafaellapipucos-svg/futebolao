"""Dependencies FastAPI: DB por request, auth via cookie, CSRF, rate limit."""
from __future__ import annotations

from typing import Iterator, Optional

from fastapi import Depends, HTTPException, Request

from ..core import csrf as csrf_mod
from ..core.ratelimit import RateLimiter
from ..core.tokens import TokenInvalidError, verify_access
from ..db.connection import connect
from ..db.repos import users as users_repo
from ..db.connection import Db

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "x-csrf-token"


def get_settings(request: Request):
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Db]:
    conn = connect(request.app.state.settings.db_target)
    try:
        yield conn
    finally:
        conn.close()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str):
    def dep(request: Request) -> None:
        limiter: RateLimiter = request.app.state.limiter
        ok, retry_after = limiter.allow(scope, client_ip(request))
        if not ok:
            raise HTTPException(
                status_code=429,
                detail="muitas tentativas, aguarde um pouco",
                headers={"Retry-After": str(max(1, int(retry_after + 0.5)))},
            )
    return dep


def require_csrf(request: Request) -> None:
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get(CSRF_HEADER, "")
    if not csrf_mod.validate(cookie, header):
        raise HTTPException(status_code=403, detail="CSRF token inválido ou ausente")


def get_current_user(
    request: Request,
    conn: Db = Depends(get_db),
):
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="não autenticado")
    settings = request.app.state.settings
    try:
        user_id = verify_access(token, settings.secret_key)
    except TokenInvalidError:
        raise HTTPException(status_code=401, detail="sessão expirada")
    user = users_repo.by_id(conn, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="usuário não existe")
    return user


def require_admin(user=Depends(get_current_user)):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="acesso restrito a admins")
    return user


def user_payload(user) -> dict:
    avatar_url: Optional[str] = None
    if user["avatar_ver"]:
        avatar_url = f"/u/avatars/{user['id']}.jpg?v={user['avatar_ver']}"
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "is_admin": bool(user["is_admin"]),
        "avatar_url": avatar_url,
        "google_linked": user["google_sub"] is not None,
        "has_password": user["password_hash"] is not None,
    }
