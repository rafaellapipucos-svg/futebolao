"""Sessões: access token curto + refresh com renovação TOLERANTE.

A sessão é "grudenta" de propósito (bolão de amigos): enquanto a LINHA do refresh
existir no banco e não tiver expirado, `rotate` re-emite um novo par — mesmo que o
token apresentado já tenha sido rotacionado. Isso elimina o logout falso por reuso
tardio: celular dormindo, resposta de rede perdida, cold start do Cloud Run, várias
abas. Só re-loga de verdade quando a sessão é ENCERRADA de propósito — logout e
troca de senha APAGAM a linha (delete) — ou quando o refresh expira (90 dias).
(D027/D028; supersede a janela de graça de I014/REUSE_GRACE_SECONDS.)
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
REFRESH_TTL_SECONDS = 90 * 24 * 3600  # 90 dias: cobre a Copa toda com folga (D028)


class TokenInvalidError(ValueError):
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
    """Renova a sessão de forma TOLERANTE (ver docstring do módulo).

    Re-emite enquanto a linha existir e não expirou; rejeita só quando a linha foi
    APAGADA (logout / troca de senha = kill real) ou quando o refresh expirou.
    """
    try:
        payload = jwt_hs256.verify(refresh_token, secret, expected_typ="refresh")
    except jwt_hs256.JwtError as exc:
        raise TokenInvalidError(str(exc)) from exc
    jti = payload.get("jti")
    user_id = int(payload["sub"])
    if not isinstance(jti, str):
        raise TokenInvalidError("refresh sem jti")
    row = tokens_repo.get(conn, jti)
    if row is None:
        raise TokenInvalidError("sessão encerrada, entre novamente")
    if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
        raise TokenInvalidError("sessão expirada, entre novamente")
    if row["revoked_at"] is None:
        tokens_repo.revoke(conn, jti)  # 1º uso deste token: rotaciona
    # Reuso tardio de um token já rotacionado NÃO desloga — re-emite par novo.
    return user_id, issue_pair(conn, user_id, secret)


def revoke_refresh(conn: Db, refresh_token: str, secret: str) -> None:
    try:
        payload = jwt_hs256.verify(refresh_token, secret, expected_typ="refresh", leeway_seconds=0)
    except jwt_hs256.JwtError:
        return  # logout com token inválido/expirado: nada a apagar
    jti = payload.get("jti")
    if isinstance(jti, str):
        tokens_repo.delete(conn, jti)  # logout: APAGA a linha (kill real)
