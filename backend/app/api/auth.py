"""Rotas de autenticação email/senha."""
from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..core.passwords import WeakPasswordError
from ..core.tokens import TokenInvalidError, issue_pair, revoke_refresh, rotate
from ..db.repos import users as users_repo
from ..services import auth as auth_svc
from .cookies import clear_session_cookies, set_session_cookies
from .deps import (
    REFRESH_COOKIE, get_current_user, get_db, get_settings,
    rate_limit, require_csrf, user_payload,
)
from .schemas import LoginIn, RegisterIn
from ..db.connection import Db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201,
             dependencies=[Depends(rate_limit("register")), Depends(require_csrf)])
def register(
    body: RegisterIn,
    response: Response,
    conn: Db = Depends(get_db),
    settings=Depends(get_settings),
):
    try:
        user_id = auth_svc.register(
            conn, settings, body.email, body.password, body.display_name,
            invite_code=body.invite_code,
        )
    except auth_svc.EmailTakenError as exc:
        raise HTTPException(409, str(exc))
    except auth_svc.InvalidInviteError as exc:
        raise HTTPException(403, str(exc))
    except (auth_svc.ValidationError, WeakPasswordError) as exc:
        raise HTTPException(422, str(exc))
    pair = issue_pair(conn, user_id, settings.secret_key)
    set_session_cookies(response, settings, pair)
    return user_payload(users_repo.by_id(conn, user_id))


@router.post("/login",
             dependencies=[Depends(rate_limit("login")), Depends(require_csrf)])
def login(
    body: LoginIn,
    response: Response,
    conn: Db = Depends(get_db),
    settings=Depends(get_settings),
):
    try:
        user = auth_svc.login(conn, settings, body.email, body.password)
    except auth_svc.InvalidCredentialsError as exc:
        raise HTTPException(401, str(exc))
    pair = issue_pair(conn, user["id"], settings.secret_key)
    set_session_cookies(response, settings, pair)
    return user_payload(user)


@router.post("/refresh",
             dependencies=[Depends(rate_limit("refresh")), Depends(require_csrf)])
def refresh(
    request: Request,
    response: Response,
    conn: Db = Depends(get_db),
    settings=Depends(get_settings),
):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(401, "sem sessão para renovar")
    try:
        user_id, pair = rotate(conn, token, settings.secret_key)
    except TokenInvalidError:
        clear_session_cookies(response)
        raise HTTPException(401, "sessão inválida, entre novamente")
    set_session_cookies(response, settings, pair)
    user = users_repo.by_id(conn, user_id)
    if user is None:
        clear_session_cookies(response)
        raise HTTPException(401, "usuário não existe")
    return user_payload(user)


@router.post("/logout", dependencies=[Depends(require_csrf)])
def logout(
    request: Request,
    response: Response,
    conn: Db = Depends(get_db),
    settings=Depends(get_settings),
):
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        revoke_refresh(conn, token, settings.secret_key)
    clear_session_cookies(response)
    return {"ok": True}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user_payload(user)
