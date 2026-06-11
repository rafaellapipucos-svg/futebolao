"""Google OAuth 2.0 (authorization code, server-side).

Troca o code no endpoint de token do Google (TLS servidor-a-servidor) e lê o
perfil via userinfo — dispensa validação local de JWKS. Transporte HTTP é
injetável para testes determinísticos.
"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from ..config import Settings
from ..db.repos import users as users_repo
from .auth import normalize_display_name
from ..db.connection import Db

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"


class OAuthError(Exception):
    pass


def _default_post(url: str, data: Dict[str, str]) -> Dict:
    import requests

    resp = requests.post(url, data=data, timeout=10)
    if resp.status_code != 200:
        raise OAuthError(f"token endpoint retornou {resp.status_code}")
    return resp.json()


def _default_get(url: str, bearer: str) -> Dict:
    import requests

    resp = requests.get(url, headers={"Authorization": f"Bearer {bearer}"}, timeout=10)
    if resp.status_code != 200:
        raise OAuthError(f"userinfo retornou {resp.status_code}")
    return resp.json()


@dataclass
class GoogleOAuth:
    client_id: str
    client_secret: str
    redirect_uri: str
    http_post: Callable[[str, Dict[str, str]], Dict] = field(default=_default_post)
    http_get: Callable[[str, str], Dict] = field(default=_default_get)

    def authorize_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
        return f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"

    def fetch_userinfo(self, code: str) -> Dict:
        token_data = self.http_post(
            TOKEN_ENDPOINT,
            {
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        access_token = token_data.get("access_token")
        if not access_token:
            raise OAuthError("resposta de token sem access_token")
        return self.http_get(USERINFO_ENDPOINT, access_token)


def login_or_link(conn: Db, settings: Settings, userinfo: Dict) -> int:
    """Cria, loga ou vincula a conta Google. Retorna user_id."""
    sub = userinfo.get("sub")
    email = (userinfo.get("email") or "").strip().lower()
    verified = userinfo.get("email_verified")
    if not sub or not email:
        raise OAuthError("userinfo incompleto")
    if verified is not True and verified != "true":
        raise OAuthError("e-mail Google não verificado")

    existing = users_repo.by_google_sub(conn, str(sub))
    if existing is not None:
        return existing["id"]

    by_email = users_repo.by_email(conn, email)
    if by_email is not None:
        users_repo.set_google_sub(conn, by_email["id"], str(sub))
        return by_email["id"]

    raw_name = userinfo.get("name") or email.split("@")[0]
    display_name = normalize_display_name(str(raw_name)[:40])
    return users_repo.create(
        conn, email, display_name,
        password_hash=None, google_sub=str(sub),
        is_admin=email in settings.admin_emails,
    )
