"""Rodada 16: set_score aceita período/acréscimo/pênaltis e persiste."""
import unittest

from app.db.repos import matches as matches_repo
from app.domain.entities import MatchStatus
from app.services.results import ResultError, set_score

from .db_helper import seeded_db, team_id_by_code


class TestResultsPenalties(unittest.TestCase):
    def setUp(self):
        self.conn = seeded_db()
        self.mex = team_id_by_code(self.conn, "MEX")
        self.can = team_id_by_code(self.conn, "CAN")
        matches_repo.set_teams(self.conn, 73, self.mex, self.can)  # R32

    def tearDown(self):
        self.conn.close()

    def test_persiste_periodo_e_acrescimo_ao_vivo(self):
        set_score(self.conn, 73, 1, 0, MatchStatus.LIVE, minute=47,
                  period="1H", stoppage=2)
        m = matches_repo.by_id(self.conn, 73)
        self.assertEqual(m.period, "1H")
        self.assertEqual(m.stoppage, 2)

    def test_persiste_penaltis_no_mata_mata(self):
        set_score(self.conn, 73, 1, 1, MatchStatus.FINISHED, period="FT",
                  home_pens=4, away_pens=2, winner_team_id=self.mex,
                  pens_log='[["home",true],["away",false]]')
        m = matches_repo.by_id(self.conn, 73)
        self.assertEqual((m.home_pens, m.away_pens), (4, 2))
        self.assertTrue(m.went_to_penalties)
        self.assertEqual(m.winner_id(), self.mex)
        self.assertEqual(m.pens_log, '[["home",true],["away",false]]')

    def test_periodo_invalido_rejeitado(self):
        with self.assertRaises(ResultError):
            set_score(self.conn, 73, 0, 0, MatchStatus.LIVE, period="ZZZ")

    def test_empate_pos_prorrogacao_sem_winner_rejeitado(self):
        with self.assertRaises(ResultError):
            set_score(self.conn, 73, 1, 1, MatchStatus.FINISHED, period="FT")


if __name__ == "__main__":
    unittest.main()
