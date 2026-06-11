"""Repositório de partidas."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from ...domain.entities import Match, MatchStatus, Stage
from ..connection import Db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_entity(row: Any) -> Match:
    return Match(
        id=row["id"],
        stage=Stage(row["stage"]),
        group=row["group_letter"],
        kickoff_utc=datetime.fromisoformat(row["kickoff_utc"]),
        venue=row["venue"],
        home_source=row["home_source"],
        away_source=row["away_source"],
        home_team_id=row["home_team_id"],
        away_team_id=row["away_team_id"],
        home_score=row["home_score"],
        away_score=row["away_score"],
        status=MatchStatus(row["status"]),
        minute=row["minute"],
        winner_team_id=row["winner_team_id"],
        manual_lock=bool(row["manual_lock"]),
        external_id=row["external_id"],
    )


def upsert_fixture(
    conn: Db,
    match_id: int,
    stage: str,
    group_letter: Optional[str],
    kickoff_utc: str,
    venue: str,
    home_source: str,
    away_source: str,
    home_team_id: Optional[int],
    away_team_id: Optional[int],
) -> None:
    """Seed idempotente: nunca toca placar/status/apostas existentes."""
    conn.execute(
        "INSERT INTO matches (id, stage, group_letter, kickoff_utc, venue, "
        "home_source, away_source, home_team_id, away_team_id, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET stage = excluded.stage, "
        "group_letter = excluded.group_letter, kickoff_utc = excluded.kickoff_utc, "
        "venue = excluded.venue, home_source = excluded.home_source, "
        "away_source = excluded.away_source",
        (
            match_id, stage, group_letter, kickoff_utc, venue,
            home_source, away_source, home_team_id, away_team_id, _now(),
        ),
    )


def all_matches(conn: Db) -> List[Match]:
    rows = conn.execute("SELECT * FROM matches ORDER BY id").fetchall()
    return [to_entity(r) for r in rows]


def by_id(conn: Db, match_id: int) -> Optional[Match]:
    row = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    return to_entity(row) if row else None


def set_score(
    conn: Db,
    match_id: int,
    home_score: int,
    away_score: int,
    status: str,
    minute: Optional[int] = None,
    winner_team_id: Optional[int] = None,
) -> None:
    conn.execute(
        "UPDATE matches SET home_score = ?, away_score = ?, status = ?, minute = ?, "
        "winner_team_id = ?, updated_at = ? WHERE id = ?",
        (home_score, away_score, status, minute, winner_team_id, _now(), match_id),
    )


def reset_match(conn: Db, match_id: int) -> None:
    conn.execute(
        "UPDATE matches SET home_score = NULL, away_score = NULL, "
        "status = 'scheduled', minute = NULL, winner_team_id = NULL, updated_at = ? "
        "WHERE id = ?",
        (_now(), match_id),
    )


def set_teams(
    conn: Db,
    match_id: int,
    home_team_id: Optional[int],
    away_team_id: Optional[int],
) -> None:
    conn.execute(
        "UPDATE matches SET home_team_id = ?, away_team_id = ?, updated_at = ? "
        "WHERE id = ?",
        (home_team_id, away_team_id, _now(), match_id),
    )


def set_manual_lock(conn: Db, match_id: int, lock: bool) -> None:
    conn.execute(
        "UPDATE matches SET manual_lock = ?, updated_at = ? WHERE id = ?",
        (int(lock), _now(), match_id),
    )


def set_external_id(conn: Db, match_id: int, external_id: str) -> None:
    conn.execute(
        "UPDATE matches SET external_id = ?, updated_at = ? WHERE id = ?",
        (external_id, _now(), match_id),
    )


def count(conn: Db) -> int:
    return conn.execute("SELECT COUNT(*) AS c FROM matches").fetchone()["c"]
