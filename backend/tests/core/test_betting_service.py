import unittest
from datetime import timedelta, timezone, datetime

from app.db.repos import matches as matches_repo
from app.db.repos import users as users_repo
from app.services import betting
from app.services.betting import BetLockedError, BetValidationError, place_bet

from .db_helper import seeded_db

KICK_M1 = datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)


class TestBettingService(unittest.TestCase):
    def setUp(self):
        self.conn = seeded_db()
        self.uid = users_repo.create(self.conn, "a@b.c", "Alice")

    def tearDown(self):
        self.conn.close()

    def test_cria_e_edita_antes_do_kickoff(self):
        before = KICK_M1 - timedelta(hours=2)
        bet = place_bet(self.conn, self.uid, 1, 2, 1, now=before)
        self.assertEqual((bet.home_goals, bet.away_goals), (2, 1))
        bet2 = place_bet(self.conn, self.uid, 1, 0, 0, now=before + timedelta(minutes=5))
        self.assertEqual(bet.id, bet2.id)
        self.assertEqual((bet2.home_goals, bet2.away_goals), (0, 0))

    def test_trava_no_apito_e_depois(self):
        for now in (KICK_M1, KICK_M1 + timedelta(seconds=1), KICK_M1 + timedelta(days=1)):
            with self.assertRaises(BetLockedError):
                place_bet(self.conn, self.uid, 1, 1, 0, now=now)

    def test_trava_por_status_mesmo_antes_do_horario(self):
        matches_repo.set_score(self.conn, 1, 0, 0, "live", minute=1)
        with self.assertRaises(BetLockedError):
            place_bet(self.conn, self.uid, 1, 1, 0, now=KICK_M1 - timedelta(hours=1))

    def test_jogo_sem_times_definidos_bloqueado(self):
        with self.assertRaises(BetLockedError):
            place_bet(self.conn, self.uid, 73, 1, 0, now=KICK_M1)  # R32 TBD

    def test_validacoes_de_placar(self):
        before = KICK_M1 - timedelta(hours=2)
        for h, a in ((-1, 0), (0, 21), ("2", 1), (True, 0), (None, 1)):
            with self.assertRaises(BetValidationError):
                place_bet(self.conn, self.uid, 1, h, a, now=before)
        with self.assertRaises(BetValidationError):
            place_bet(self.conn, self.uid, 9999, 1, 0, now=before)

    def test_pontos_provisorios_e_finais(self):
        before = KICK_M1 - timedelta(hours=2)
        place_bet(self.conn, self.uid, 1, 2, 1, now=before)
        rows = betting.user_bets_with_points(self.conn, self.uid)
        self.assertIsNone(rows[0]["score"])  # sem placar ainda
        matches_repo.set_score(self.conn, 1, 2, 1, "live", minute=30)
        rows = betting.user_bets_with_points(self.conn, self.uid)
        self.assertEqual(rows[0]["score"].total, 3)  # cravada provisória
        matches_repo.set_score(self.conn, 1, 2, 2, "finished")
        rows = betting.user_bets_with_points(self.conn, self.uid)
        self.assertEqual(rows[0]["score"].total, 0)  # virou e errou

    def test_defesa_aposta_pos_kickoff_nao_pontua(self):
        """Mesmo que uma aposta burlasse a trava, o scoring a ignora."""
        from app.db.repos import bets as bets_repo
        bets_repo.upsert(self.conn, self.uid, 1, 2, 1)  # direto no repo (sem trava)
        forged = (KICK_M1 + timedelta(minutes=10)).isoformat()
        self.conn.execute(
            "UPDATE bets SET updated_at = ? WHERE user_id = ? AND match_id = ?",
            (forged, self.uid, 1),
        )
        matches_repo.set_score(self.conn, 1, 2, 1, "finished")
        rows = betting.user_bets_with_points(self.conn, self.uid)
        self.assertIsNone(rows[0]["score"])


if __name__ == "__main__":
    unittest.main()
