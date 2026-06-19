"""Rodada 16 (I012): re-seed (roda a cada boot) NÃO pode reverter um horário já
atualizado pelo provider/admin — o bug fazia o jogo voltar ao horário hardcoded
do fixtures.txt a cada cold start."""
import unittest
from datetime import timedelta

from app.db.repos import matches as matches_repo
from app.seed.loader import seed

from .db_helper import seeded_db


class TestReseedPreservaKickoff(unittest.TestCase):
    def test_reseed_nao_reverte_kickoff_atualizado(self):
        conn = seeded_db()
        try:
            original = matches_repo.by_id(conn, 1).kickoff_utc
            novo = (original - timedelta(minutes=30)).isoformat()  # provider antecipa
            matches_repo.set_kickoff(conn, 1, novo)
            seed(conn)  # simula novo boot (main.py chama seed no lifespan)
            self.assertEqual(matches_repo.by_id(conn, 1).kickoff_utc.isoformat(), novo)
        finally:
            conn.close()

    def test_reseed_ainda_preenche_kickoff_em_jogo_novo(self):
        # Garante que o 1º INSERT continua gravando o horário do seed.
        conn = seeded_db()
        try:
            self.assertIsNotNone(matches_repo.by_id(conn, 1).kickoff_utc)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
