"""Rodada 16: migração v4 — colunas de relógio/pênaltis em matches."""
import unittest

from app.db.connection import connect
from app.db.schema import SCHEMA_VERSION, init_db


def _match_cols(conn):
    rows = conn.execute("PRAGMA table_info(matches)").fetchall()
    return {r["name"] for r in rows}


class TestSchemaV4Migration(unittest.TestCase):
    NEW_COLS = ("period", "stoppage", "home_pens", "away_pens", "pens_log",
                "period_started_at")

    def test_schema_version_atual(self):
        self.assertEqual(SCHEMA_VERSION, 5)

    def test_migra_matches_legado(self):
        conn = connect(":memory:")
        # DB "v3": matches SEM as colunas novas
        conn.execute(
            "CREATE TABLE matches (id INTEGER PRIMARY KEY, stage TEXT NOT NULL, "
            "group_letter TEXT, kickoff_utc TEXT NOT NULL, venue TEXT NOT NULL, "
            "home_source TEXT NOT NULL, away_source TEXT NOT NULL, "
            "home_team_id BIGINT, away_team_id BIGINT, home_score INTEGER, "
            "away_score INTEGER, status TEXT NOT NULL DEFAULT 'scheduled', "
            "minute INTEGER, winner_team_id BIGINT, "
            "manual_lock INTEGER NOT NULL DEFAULT 0, external_id TEXT, "
            "updated_at TEXT NOT NULL)")
        cols = _match_cols(conn)
        for c in self.NEW_COLS:
            self.assertNotIn(c, cols)
        init_db(conn)  # migração idempotente
        cols = _match_cols(conn)
        for c in self.NEW_COLS:
            self.assertIn(c, cols)
        init_db(conn)  # roda de novo: não quebra
        self.assertTrue(set(self.NEW_COLS) <= _match_cols(conn))


if __name__ == "__main__":
    unittest.main()
