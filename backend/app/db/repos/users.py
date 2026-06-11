"""Repositorio de usuarios. Todas as queries parametrizadas (dialeto-agnostico)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from ..connection import Db, insert_id
from ..schema import bump_users_version


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create(
    conn: Db,
    email: str,
    display_name: str,
    password_hash: Optional[str] = None,
    google_sub: Optional[str] = None,
    is_admin: bool = False,
) -> int:
    user_id = insert_id(
        conn,
        "INSERT INTO users (email, display_name, password_hash, google_sub, is_admin, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (email, display_name, password_hash, google_sub, int(is_admin), _now()),
    )
    bump_users_version(conn)  # novo usuario aparece no ranking na hora
    return user_id


def by_id(conn: Db, user_id: int) -> Optional[Any]:
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def by_email(conn: Db, email: str) -> Optional[Any]:
    return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def by_google_sub(conn: Db, sub: str) -> Optional[Any]:
    return conn.execute("SELECT * FROM users WHERE google_sub = ?", (sub,)).fetchone()


def set_password(conn: Db, user_id: int, password_hash: str) -> None:
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id)
    )


def set_bio(conn: Db, user_id: int, bio) -> None:
    # bio não entra no ranking, então não bumpa users_version.
    conn.execute("UPDATE users SET bio = ? WHERE id = ?", (bio, user_id))


def set_display_name(conn: Db, user_id: int, name: str) -> None:
    conn.execute("UPDATE users SET display_name = ? WHERE id = ?", (name, user_id))
    bump_users_version(conn)


def set_google_sub(conn: Db, user_id: int, sub: str) -> None:
    conn.execute("UPDATE users SET google_sub = ? WHERE id = ?", (sub, user_id))


def set_admin(conn: Db, user_id: int, is_admin: bool) -> None:
    conn.execute("UPDATE users SET is_admin = ? WHERE id = ?", (int(is_admin), user_id))


def bump_avatar(conn: Db, user_id: int) -> int:
    conn.execute(
        "UPDATE users SET avatar_ver = avatar_ver + 1 WHERE id = ?", (user_id,)
    )
    bump_users_version(conn)  # ranking reflete a nova foto na hora
    row = conn.execute(
        "SELECT avatar_ver FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return int(row["avatar_ver"])


def list_all(conn: Db) -> list:
    return conn.execute(
        "SELECT id, email, display_name, avatar_ver, is_admin, created_at "
        "FROM users ORDER BY LOWER(display_name)"
    ).fetchall()


def delete(conn: Db, user_id: int) -> None:
    """Remove o usuario e tudo que e' dele (apostas, sessoes, avatar).
    Explicito nos dois dialetos (nao depende de ON DELETE CASCADE)."""
    conn.execute("DELETE FROM bets WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM avatars WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    bump_users_version(conn)
