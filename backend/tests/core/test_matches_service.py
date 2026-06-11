"""R2-F4: cobertura direta do payload da aba Jogos (services/matches.py)."""
import unittest
from datetime import datetime, timedelta, timezone

from app.db.repos import matches as matches_repo
from app.db.repos import users as users_repo
from app.services.betting import place_bet
from app.services.matches import list_matches

from .db_helper import seeded_db

KICK_M1 = datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)


class TestMatchesService(unittest.TestCase):
    def setUp(self):
        self.conn = seeded_db()
        self.uid = users_repo.create(self.conn, "a@b.c", "Alice")

    def tearDown(self):
        self.conn.close()

    def test_payload_completo_e_ordenado(self):
        data = list_matches(self.conn, self.uid)
        self.assertEqual(len(data), 104)
        kicks = [m["kickoff_utc"] for m in data]
        self.assertEqual(kicks, sorted(kicks))
        m1 = next(m for m in data if m["id"] == 1)
        self.assertEqual(m1["group"], "A")
        self.assertEqual(m1["stage_label"], "Fase de Grupos")
        self.assertEqual(m1["home"]["team"]["code"], "MEX")
        self.assertIsNone(m1["my_bet"])
        m73 = next(m for m in data if m["id"] == 73)
        self.assertIsNone(m73["home"]["team"])
        self.assertEqual(m73["home"]["label"], "2º do Grupo A")
        self.assertFalse(m73["bet_open"])  # times indefinidos

    def test_minha_aposta_e_pontos_aparecem(self):
        place_bet(self.conn, self.uid, 1, 2, 1, now=KICK_M1 - timedelta(hours=2))
        matches_repo.set_score(self.conn, 1, 2, 1, "live", minute=30)
        data = list_matches(self.conn, self.uid)
        m1 = next(m for m in data if m["id"] == 1)
        self.assertEqual(m1["my_bet"], {"home_goals": 2, "away_goals": 1})
        self.assertEqual(m1["my_points"]["total"], 3)
        self.assertTrue(m1["my_points"]["provisional"])
        self.assertFalse(m1["bet_open"])
        self.assertEqual(m1["status"], "live")

    def test_bet_open_depende_do_relogio_real(self):
        # jogo 104 (19/07/2026) está no futuro em relação ao relógio do teste?
        # Independente da data de execução: movemos o kickoff para garantir.
        future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        self.conn.execute(
            "UPDATE matches SET kickoff_utc = ? WHERE id = ?", (future, 1)
        )
        data = list_matches(self.conn, self.uid)
        m1 = next(m for m in data if m["id"] == 1)
        self.assertTrue(m1["bet_open"])
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self.conn.execute(
            "UPDATE matches SET kickoff_utc = ? WHERE id = ?", (past, 1)
        )
        data2 = list_matches(self.conn, self.uid)
        m1b = next(m for m in data2 if m["id"] == 1)
        self.assertFalse(m1b["bet_open"])
        self.assertIn("apito", m1b["bet_lock_reason"])


if __name__ == "__main__":
    unittest.main()
