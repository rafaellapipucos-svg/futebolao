"""Repositório de apostas. A trava de kickoff é aplicada no serviço, dentro
da MESMA transação do upsert (ver services/betting.py)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from ...domain.entities import Bet
from ..connection import Db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_entity(row: Any) -> Bet:
    return Bet(
        id=row["id"],
        user_id=row["user_id"],
        match_id=row["match_id"],
        home_goals=row["home_goals"],
        away_goals=row["away_goals"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def upsert(
    conn: Db,
    user_id: int,
    match_id: int,
    home_goals: int,
    away_goals: int,
    updated_at: Optional[str] = None,
) -> Bet:
    now = updated_at or _now()
    conn.execute(
        "INSERT INTO bets (user_id, match_id, home_goals, away_goals, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, match_id) DO UPDATE SET "
        "home_goals = excluded.home_goals, away_goals = excluded.away_goals, "
        "updated_at = excluded.updated_at",
        (user_id, match_id, home_goals, away_goals, now, now),
    )
    return get(conn, user_id, match_id)


def get(conn: Db, user_id: int, match_id: int) -> Optional[Bet]:
    row = conn.execute(
        "SELECT * FROM bets WHERE user_id = ? AND match_id = ?", (user_id, match_id)
    ).fetchone()
    return to_entity(row) if row else None


def for_user(conn: Db, user_id: int) -> List[Bet]:
    rows = conn.execute(
        "SELECT * FROM bets WHERE user_id = ? ORDER BY match_id", (user_id,)
    ).fetchall()
    return [to_entity(r) for r in rows]


def all_bets(conn: Db) -> List[Bet]:
    rows = conn.execute("SELECT * FROM bets ORDER BY match_id, user_id").fetchall()
    return [to_entity(r) for r in rows]
