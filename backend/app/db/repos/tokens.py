"""Repositório de refresh tokens (revogáveis, rotacionados)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from ..connection import Db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def insert(
    conn: Db, jti: str, user_id: int, expires_at: datetime
) -> None:
    conn.execute(
        "INSERT INTO refresh_tokens (jti, user_id, expires_at, created_at) "
        "VALUES (?, ?, ?, ?)",
        (jti, user_id, expires_at.isoformat(), _now().isoformat()),
    )


def get(conn: Db, jti: str) -> Optional[Any]:
    return conn.execute(
        "SELECT * FROM refresh_tokens WHERE jti = ?", (jti,)
    ).fetchone()


def is_active(conn: Db, jti: str) -> bool:
    row = get(conn, jti)
    if row is None or row["revoked_at"] is not None:
        return False
    return datetime.fromisoformat(row["expires_at"]) > _now()


def revoke(conn: Db, jti: str) -> None:
    conn.execute(
        "UPDATE refresh_tokens SET revoked_at = ? WHERE jti = ? AND revoked_at IS NULL",
        (_now().isoformat(), jti),
    )


def revoke_all_for_user(conn: Db, user_id: int) -> None:
    conn.execute(
        "UPDATE refresh_tokens SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
        (_now().isoformat(), user_id),
    )


def delete(conn: Db, jti: str) -> None:
    """Apaga o token de vez (logout): não fica 'revogado recente' p/ a graça de reuso."""
    conn.execute("DELETE FROM refresh_tokens WHERE jti = ?", (jti,))


def delete_all_for_user(conn: Db, user_id: int) -> None:
    """Mata todas as sessões do usuário (resposta a replay/roubo)."""
    conn.execute("DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,))


def purge_expired(conn: Db) -> int:
    cur = conn.execute(
        "DELETE FROM refresh_tokens WHERE expires_at < ?",
        (_now().isoformat(),),
    )
    return cur.rowcount
