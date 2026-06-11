import unittest

from app.db.repos import matches as matches_repo
from app.db.schema import get_data_version
from app.domain.entities import MatchStatus
from app.services.results import ResultError, reset_match, set_score

from .db_helper import seeded_db, team_id_by_code


class TestResultsService(unittest.TestCase):
    def setUp(self):
        self.conn = seeded_db()

    def tearDown(self):
        self.conn.close()

    def test_fluxo_scheduled_live_finished(self):
        set_score(self.conn, 1, 0, 0, MatchStatus.LIVE, minute=1)
        set_score(self.conn, 1, 1, 0, MatchStatus.LIVE, minute=44)
        set_score(self.conn, 1, 2, 0, MatchStatus.FINISHED)
        m = matches_repo.by_id(self.conn, 1)
        self.assertEqual((m.home_score, m.away_score, m.status), (2, 0, MatchStatus.FINISHED))

    def test_reabrir_exige_force(self):
        set_score(self.conn, 1, 2, 0, MatchStatus.FINISHED)
        with self.assertRaises(ResultError):
            set_score(self.conn, 1, 0, 0, MatchStatus.LIVE)
        set_score(self.conn, 1, 0, 0, MatchStatus.LIVE, force=True)
        self.assertEqual(matches_repo.by_id(self.conn, 1).status, MatchStatus.LIVE)

    def test_validacoes(self):
        with self.assertRaises(ResultError):
            set_score(self.conn, 1, -1, 0, MatchStatus.LIVE)
        with self.assertRaises(ResultError):
            set_score(self.conn, 1, 0, 100, MatchStatus.LIVE)
        with self.assertRaises(ResultError):
            set_score(self.conn, 9999, 1, 0, MatchStatus.FINISHED)
        with self.assertRaises(ResultError):
            set_score(self.conn, 73, 1, 0, MatchStatus.FINISHED)  # sem times

    def test_mata_mata_empatado_exige_winner(self):
        mex = team_id_by_code(self.conn, "MEX")
        can = team_id_by_code(self.conn, "CAN")
        matches_repo.set_teams(self.conn, 73, mex, can)
        with self.assertRaises(ResultError):
            set_score(self.conn, 73, 1, 1, MatchStatus.FINISHED)
        set_score(self.conn, 73, 1, 1, MatchStatus.FINISHED, winner_team_id=can)
        self.assertEqual(matches_repo.by_id(self.conn, 73).winner_id(), can)
        with self.assertRaises(ResultError):
            set_score(self.conn, 73, 1, 1, MatchStatus.FINISHED,
                      winner_team_id=9999, force=True)

    def test_bump_versao_e_reset(self):
        v0 = get_data_version(self.conn)
        set_score(self.conn, 1, 1, 0, MatchStatus.LIVE)
        self.assertEqual(get_data_version(self.conn), v0 + 1)
        reset_match(self.conn, 1)
        m = matches_repo.by_id(self.conn, 1)
        self.assertEqual((m.status, m.home_score), (MatchStatus.SCHEDULED, None))
        self.assertEqual(get_data_version(self.conn), v0 + 2)


if __name__ == "__main__":
    unittest.main()
