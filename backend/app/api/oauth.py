"""Google OAuth: start (redirect) e callback."""
from __future__ import annotations

import asyncio
import hmac
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..core.tokens import issue_pair
from ..services.oauth_google import GoogleOAuth, OAuthError, login_or_link
from .cookies import set_session_cookies
from .deps import get_db, get_settings, rate_limit
from ..db.connection import Db

router = APIRouter(prefix="/api/oauth/google", tags=["oauth"])
STATE_COOKIE = "oauth_state"


def _oauth_client(settings) -> GoogleOAuth:
    if not settings.google_oauth_enabled:
        raise HTTPException(503, "login com Google não está configurado")
    return GoogleOAuth(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=f"{settings.public_base_url}/api/oauth/google/callback",
    )


@router.get("/start", dependencies=[Depends(rate_limit("oauth"))])
def start(settings=Depends(get_settings)):
    client = _oauth_client(settings)
    state = secrets.token_urlsafe(24)
    response = RedirectResponse(client.authorize_url(state), status_code=302)
    response.set_cookie(
        STATE_COOKIE, state, max_age=600, httponly=True, samesite="lax",
        secure=settings.cookie_secure, path="/api/oauth/google",
    )
    return response


@router.get("/callback", dependencies=[Depends(rate_limit("oauth"))])
async def callback(
    request: Request,
    conn: Db = Depends(get_db),
    settings=Depends(get_settings),
):
    client = _oauth_client(settings)
    state = request.query_params.get("state", "")
    code = request.query_params.get("code", "")
    saved_state = request.cookies.get(STATE_COOKIE, "")
    if not code or not state or not saved_state or not hmac.compare_digest(state, saved_state):
        return RedirectResponse("/#/login?error=oauth_state", status_code=303)
    try:
        userinfo = await asyncio.to_thread(client.fetch_userinfo, code)
        user_id = login_or_link(conn, settings, userinfo)
    except OAuthError:
        return RedirectResponse("/#/login?error=oauth", status_code=303)
    pair = issue_pair(conn, user_id, settings.secret_key)
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(STATE_COOKIE, path="/api/oauth/google")
    set_session_cookies(response, settings, pair)
    return response
