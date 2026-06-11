"""Repositório de times."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...domain.entities import Team
from ..connection import Db


def upsert(
    conn: Db, code: str, name: str, flag: str, group_letter: str
) -> None:
    conn.execute(
        "INSERT INTO teams (code, name, flag, group_letter) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(code) DO UPDATE SET name = excluded.name, flag = excluded.flag, "
        "group_letter = excluded.group_letter",
        (code, name, flag, group_letter),
    )


def _to_entity(row: Any) -> Team:
    return Team(
        id=row["id"],
        code=row["code"],
        name=row["name"],
        flag=row["flag"],
        group=row["group_letter"],
    )


def all_teams(conn: Db) -> Dict[int, Team]:
    rows = conn.execute("SELECT * FROM teams ORDER BY code").fetchall()
    return {r["id"]: _to_entity(r) for r in rows}


def by_code(conn: Db, code: str) -> Optional[Team]:
    row = conn.execute("SELECT * FROM teams WHERE code = ?", (code,)).fetchone()
    return _to_entity(row) if row else None


def count(conn: Db) -> int:
    return conn.execute("SELECT COUNT(*) AS c FROM teams").fetchone()["c"]
