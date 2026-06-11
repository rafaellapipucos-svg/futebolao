"""Sessões: access token curto + refresh token rotacionado e revogável.

Reuso de refresh já rotacionado = roubo provável ⇒ revoga TODAS as sessões
do usuário (detecção de replay).
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Tuple

from ..db.repos import tokens as tokens_repo
from . import jwt_hs256

ACCESS_TTL_SECONDS = 15 * 60
REFRESH_TTL_SECONDS = 30 * 24 * 3600


class TokenInvalidError(ValueError):
    pass


class TokenReuseError(TokenInvalidError):
    pass


@dataclass(frozen=True)
class TokenPair:
    access: str
    refresh: str


def issue_pair(conn: Db, user_id: int, secret: str) -> TokenPair:
    now = int(time.time())
    access = jwt_hs256.sign(
        {"sub": str(user_id), "typ": "access", "iat": now, "exp": now + ACCESS_TTL_SECONDS},
        secret,
    )
    jti = secrets.token_urlsafe(24)
    refresh = jwt_hs256.sign(
        {"sub": str(user_id), "typ": "refresh", "jti": jti, "iat": now,
         "exp": now + REFRESH_TTL_SECONDS},
        secret,
    )
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TTL_SECONDS)
    tokens_repo.insert(conn, jti, user_id, expires_at)
    return TokenPair(access=access, refresh=refresh)


def verify_access(token: str, secret: str) -> int:
    try:
        payload = jwt_hs256.verify(token, secret, expected_typ="access")
    except jwt_hs256.JwtError as exc:
        raise TokenInvalidError(str(exc)) from exc
    return int(payload["sub"])


def rotate(conn: Db, refresh_token: str, secret: str) -> Tuple[int, TokenPair]:
    try:
        payload = jwt_hs256.verify(refresh_token, secret, expected_typ="refresh")
    except jwt_hs256.JwtError as exc:
        raise TokenInvalidError(str(exc)) from exc
    jti = payload.get("jti")
    user_id = int(payload["sub"])
    if not isinstance(jti, str):
        raise TokenInvalidError("refresh sem jti")
    if not tokens_repo.is_active(conn, jti):
        row = tokens_repo.get(conn, jti)
        if row is not None and row["revoked_at"] is not None:
            tokens_repo.revoke_all_for_user(conn, user_id)  # replay detectado
            raise TokenReuseError("refresh reutilizado — sessões revogadas")
        raise TokenInvalidError("refresh inválido ou expirado")
    tokens_repo.revoke(conn, jti)
    return user_id, issue_pair(conn, user_id, secret)


def revoke_refresh(conn: Db, refresh_token: str, secret: str) -> None:
    try:
        payload = jwt_hs256.verify(refresh_token, secret, expected_typ="refresh", leeway_seconds=0)
    except jwt_hs256.JwtError:
        return  # logout com token inválido/expirado: nada a revogar
    jti = payload.get("jti")
    if isinstance(jti, str):
        tokens_repo.revoke(conn, jti)
