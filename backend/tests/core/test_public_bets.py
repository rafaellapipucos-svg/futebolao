import unittest
from datetime import datetime, timedelta, timezone

from app.db.repos import matches as matches_repo
from app.db.repos import users as users_repo
from app.services.betting import place_bet
from app.services.public_bets import live_matches, match_bets_public

from .db_helper import seeded_db

BEFORE = datetime(2026, 6, 11, 10, 0, tzinfo=timezone.utc)


class TestPublicBets(unittest.TestCase):
    def setUp(self):
        from app.services import leaderboard as lb_mod
        lb_mod._cache.clear()
        self.conn = seeded_db()
        self.alice = users_repo.create(self.conn, "a@b.c", "Alice")

    def tearDown(self):
        self.conn.close()

    def test_escondido_antes_do_kickoff(self):
        # move o kickoff do jogo 2 p/ o futuro (independente do relógio) ->
        # aposta aberta -> apostas escondidas até começar
        future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        self.conn.execute("UPDATE matches SET kickoff_utc = ? WHERE id = ?", (future, 2))
        place_bet(self.conn, self.alice, 2, 1, 0)
        data = match_bets_public(self.conn, 2)
        self.assertFalse(data["revealed"])
        self.assertEqual(data["bets"], [])

    def test_revelado_apos_kickoff(self):
        place_bet(self.conn, self.alice, 1, 2, 1, now=BEFORE)
        matches_repo.set_score(self.conn, 1, 2, 1, "finished")
        data = match_bets_public(self.conn, 1)
        self.assertTrue(data["revealed"])
        self.assertEqual(len(data["bets"]), 1)
        self.assertEqual(data["bets"][0]["home_goals"], 2)
        self.assertTrue(data["bets"][0]["points"]["hit_exact"])

    def test_live_lista_jogos_ao_vivo_com_apostas(self):
        place_bet(self.conn, self.alice, 1, 2, 1, now=BEFORE)
        matches_repo.set_score(self.conn, 1, 2, 1, "live", minute=30)
        live = live_matches(self.conn)
        self.assertIn(1, [m["id"] for m in live])
        m1 = next(m for m in live if m["id"] == 1)
        self.assertEqual(len(m1["bets"]), 1)
        self.assertTrue(m1["bets"][0]["points"]["provisional"])


if __name__ == "__main__":
    unittest.main()
