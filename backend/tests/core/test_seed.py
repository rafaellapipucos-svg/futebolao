import unittest
from datetime import datetime, timezone

from app.db.connection import connect
from app.db.repos import bets as bets_repo
from app.db.repos import matches as matches_repo
from app.db.repos import teams as teams_repo
from app.db.repos import users as users_repo
from app.db.schema import init_db
from app.domain.entities import Stage
from app.seed.loader import seed

R32_SOURCES = {
    73: ("2A", "2B"), 74: ("1E", "3:ABCDF"), 75: ("1F", "2C"), 76: ("1C", "2F"),
    77: ("1I", "3:CDFGH"), 78: ("2E", "2I"), 79: ("1A", "3:CEFHI"),
    80: ("1L", "3:EHIJK"), 81: ("1D", "3:BEFIJ"), 82: ("1G", "3:AEHIJ"),
    83: ("2K", "2L"), 84: ("1H", "2J"), 85: ("1B", "3:EFGIJ"), 86: ("1J", "2H"),
    87: ("1K", "3:DEIJL"), 88: ("2D", "2G"),
}
KO_REFS = {
    89: ("W74", "W77"), 90: ("W73", "W75"), 91: ("W76", "W78"), 92: ("W79", "W80"),
    93: ("W83", "W84"), 94: ("W81", "W82"), 95: ("W86", "W88"), 96: ("W85", "W87"),
    97: ("W89", "W90"), 98: ("W93", "W94"), 99: ("W91", "W92"), 100: ("W95", "W96"),
    101: ("W97", "W98"), 102: ("W99", "W100"), 103: ("L101", "L102"),
    104: ("W101", "W102"),
}


class TestSeed(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        init_db(self.conn)
        seed(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_contagens(self):
        self.assertEqual(teams_repo.count(self.conn), 48)
        self.assertEqual(matches_repo.count(self.conn), 104)
        ms = matches_repo.all_matches(self.conn)
        per_stage = {}
        for m in ms:
            per_stage[m.stage] = per_stage.get(m.stage, 0) + 1
        self.assertEqual(per_stage[Stage.GROUP], 72)
        self.assertEqual(per_stage[Stage.R32], 16)
        self.assertEqual(per_stage[Stage.FINAL], 1)

    def test_jogo_1_e_104(self):
        m1 = matches_repo.by_id(self.conn, 1)
        self.assertEqual(
            m1.kickoff_utc, datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)
        )
        teams = teams_repo.all_teams(self.conn)
        self.assertEqual(teams[m1.home_team_id].code, "MEX")
        self.assertEqual(teams[m1.away_team_id].code, "RSA")
        m104 = matches_repo.by_id(self.conn, 104)
        self.assertEqual(m104.stage, Stage.FINAL)
        self.assertEqual(
            m104.kickoff_utc, datetime(2026, 7, 19, 19, 0, tzinfo=timezone.utc)
        )

    def test_grupos_dos_jogos_informados(self):
        ms = matches_repo.all_matches(self.conn)
        for m in ms:
            if m.stage == Stage.GROUP:
                self.assertIsNotNone(m.group, m.id)
            else:
                self.assertIsNone(m.group, m.id)

    def test_sources_oficiais(self):
        for mid, (h, a) in {**R32_SOURCES, **KO_REFS}.items():
            m = matches_repo.by_id(self.conn, mid)
            self.assertEqual((m.home_source, m.away_source), (h, a), mid)

    def test_kickoffs_validos(self):
        ms = matches_repo.all_matches(self.conn)
        for m in ms:
            self.assertIsNotNone(m.kickoff_utc.tzinfo, m.id)
        first = min(m.kickoff_utc for m in ms)
        last = max(m.kickoff_utc for m in ms)
        self.assertEqual(first.date().isoformat(), "2026-06-11")
        self.assertEqual(last.date().isoformat(), "2026-07-19")

    def test_reseed_idempotente_preserva_estado(self):
        uid = users_repo.create(self.conn, "a@b.c", "Alice")
        bets_repo.upsert(self.conn, uid, 1, 2, 1)
        matches_repo.set_score(self.conn, 1, 3, 1, "finished")
        seed(self.conn)  # re-rodar
        self.assertEqual(matches_repo.count(self.conn), 104)
        m1 = matches_repo.by_id(self.conn, 1)
        self.assertEqual((m1.home_score, m1.away_score, m1.status.value), (3, 1, "finished"))
        self.assertEqual(len(bets_repo.for_user(self.conn, uid)), 1)


if __name__ == "__main__":
    unittest.main()
