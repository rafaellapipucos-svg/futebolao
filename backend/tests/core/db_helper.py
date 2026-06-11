"""Banco em memória com seed real para testes de serviços."""
from __future__ import annotations

import sqlite3

from app.db.connection import connect
from app.db.repos import teams as teams_repo
from app.db.schema import init_db
from app.seed.loader import seed


def seeded_db() -> sqlite3.Connection:
    conn = connect(":memory:")
    init_db(conn)
    seed(conn)
    return conn


def team_id_by_code(conn: sqlite3.Connection, code: str) -> int:
    team = teams_repo.by_code(conn, code)
    assert team is not None, code
    return team.id
