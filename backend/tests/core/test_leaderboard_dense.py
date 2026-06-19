"""Rodada 16 (feature F): ranking com posição DENSA (1,1,1,2 — não 1,1,1,4)."""
import unittest
from datetime import datetime, timezone

from app.db.repos import users as users_repo
from app.services.betting import place_bet
from app.services.leaderboard import leaderboard

from .db_helper import seeded_db

BEFORE = datetime(2026, 6, 11, 10, 0, tzinfo=timezone.utc)


class TestLeaderboardDense(unittest.TestCase):
    def setUp(self):
        from app.services import leaderboard as lb_mod
        lb_mod._cache.clear()
        self.conn = seeded_db()

    def tearDown(self):
        self.conn.close()

    def test_empate_triplo_proxima_posicao_e_2(self):
        # Três cravam o jogo 1 (mesma pontuação) e um erra: 1,1,1,2.
        from app.db.repos import matches as matches_repo
        from app.db.schema import bump_data_version
        a = users_repo.create(self.conn, "a@x.c", "Lucas")
        b = users_repo.create(self.conn, "b@x.c", "Marcelo")
        c = users_repo.create(self.conn, "c@x.c", "Manuela")
        d = users_repo.create(self.conn, "d@x.c", "Bruno")
        for u in (a, b, c):
            place_bet(self.conn, u, 1, 2, 1, now=BEFORE)  # cravada
        place_bet(self.conn, d, 1, 0, 0, now=BEFORE)      # erro
        matches_repo.set_score(self.conn, 1, 2, 1, "finished")
        bump_data_version(self.conn)
        rows = {r["display_name"]: r for r in leaderboard(self.conn)}
        self.assertEqual(rows["Lucas"]["position"], 1)
        self.assertEqual(rows["Marcelo"]["position"], 1)
        self.assertEqual(rows["Manuela"]["position"], 1)
        self.assertEqual(rows["Bruno"]["position"], 2)  # densa: 2, não 4


if __name__ == "__main__":
    unittest.main()
