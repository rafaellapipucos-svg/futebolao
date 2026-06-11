"""Repositorio de avatares — bytes no banco (discos de PaaS sao efemeros)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..connection import Db


def set_bytes(conn: Db, user_id: int, data: bytes) -> None:
    conn.execute(
        "INSERT INTO avatars (user_id, data, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT (user_id) DO UPDATE SET data = excluded.data, "
        "updated_at = excluded.updated_at",
        (user_id, data, datetime.now(timezone.utc).isoformat()),
    )


def get_bytes(conn: Db, user_id: int) -> Optional[bytes]:
    row = conn.execute(
        "SELECT data FROM avatars WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    return bytes(row["data"])
