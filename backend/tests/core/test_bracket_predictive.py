"""Rodada 16 (feature E): mata-mata preditivo a partir do ranking atual.

- O R32 é preenchido com a projeção do ranking atual (predicted=true).
- Grupo encerrado/clinch e jogos decididos viram definitivos (predicted=false).
"""
import unittest

from app.db.repos import matches as matches_repo
from app.domain.entities import MatchStatus, Stage
from app.services.bracket_svc import predicted_bracket_payload
from app.services.results import set_score

from .db_helper import seeded_db


class TestBracketPredictive(unittest.TestCase):
    def setUp(self):
        self.conn = seeded_db()

    def tearDown(self):
        self.conn.close()

    def _finish_group(self, g):
        ms = [m for m in matches_repo.all_matches(self.conn)
              if m.stage == Stage.GROUP and m.group == g]
        for i, m in enumerate(ms):
            set_score(self.conn, m.id, 1 if i % 2 else 2, 0, MatchStatus.FINISHED)

    def test_projeta_r32_do_ranking_atual(self):
        payload = predicted_bracket_payload(self.conn)
        r32 = [m for m in payload if m["stage"] == "R32"]
        self.assertEqual(len(r32), 16)
        # Sem jogo decidido, a projeção preenche os dois lados de todo R32.
        self.assertTrue(all(m["home"]["team"] and m["away"]["team"] for m in r32))
        self.assertTrue(all(m["home"]["predicted"] and m["away"]["predicted"]
                            for m in r32))
        self.assertTrue(all(m["predicted"] for m in r32))

    def test_grupo_encerrado_vira_definitivo(self):
        self._finish_group("A")
        payload = predicted_bracket_payload(self.conn)
        slot = next(m for m in payload
                    if m["home_source"] == "1A" or m["away_source"] == "1A")
        side = "home" if slot["home_source"] == "1A" else "away"
        self.assertIsNotNone(slot[side]["team"])
        self.assertFalse(slot[side]["predicted"])  # garantido, não previsão


if __name__ == "__main__":
    unittest.main()
