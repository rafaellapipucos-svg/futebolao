import unittest
from datetime import datetime, timezone

from app.db.repos import matches as matches_repo
from app.db.repos import users as users_repo
from app.services.betting import place_bet
from app.services.profiles import public_profile

from .db_helper import seeded_db

BEFORE = datetime(2026, 6, 11, 10, 0, tzinfo=timezone.utc)


class TestPublicProfile(unittest.TestCase):
    def setUp(self):
        from app.services import leaderboard as lb_mod
        lb_mod._cache.clear()
        self.conn = seeded_db()
        self.alice = users_repo.create(self.conn, "alice@b.c", "Alice")
        users_repo.set_bio(self.conn, self.alice, "Palpiteira raiz")
        place_bet(self.conn, self.alice, 1, 2, 1, now=BEFORE)
        matches_repo.set_score(self.conn, 1, 2, 1, "finished")

    def tearDown(self):
        self.conn.close()

    def test_nao_vaza_email_nem_google(self):
        prof = public_profile(self.conn, self.alice)
        for chave in ("email", "google_linked", "has_password"):
            self.assertNotIn(chave, prof)
        self.assertEqual(prof["display_name"], "Alice")
        self.assertEqual(prof["bio"], "Palpiteira raiz")

    def test_tem_posicao_pontos_e_historico(self):
        prof = public_profile(self.conn, self.alice)
        self.assertEqual(prof["total_points"], 3)   # cravada em grupo
        self.assertEqual(prof["position"], 1)
        self.assertEqual(len(prof["history"]), 1)
        self.assertTrue(prof["history"][0]["points"]["hit_exact"])

    def test_inexistente_retorna_none(self):
        self.assertIsNone(public_profile(self.conn, 99999))


if __name__ == "__main__":
    unittest.main()
