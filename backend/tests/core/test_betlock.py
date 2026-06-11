import unittest
from datetime import timedelta

from app.domain.betlock import bet_window
from app.domain.entities import MatchStatus

from .helpers import KICKOFF, mk_match


class TestBetLock(unittest.TestCase):
    def setUp(self):
        self.match = mk_match(home=1, away=2, kickoff=KICKOFF)

    def test_aberta_antes_do_kickoff(self):
        ok, _ = bet_window(self.match, KICKOFF - timedelta(seconds=1))
        self.assertTrue(ok)

    def test_fecha_exatamente_no_apito(self):
        ok, reason = bet_window(self.match, KICKOFF)
        self.assertFalse(ok)
        self.assertIn("apito", reason)

    def test_fechada_depois(self):
        self.assertFalse(bet_window(self.match, KICKOFF + timedelta(minutes=1))[0])

    def test_fechada_status_nao_scheduled(self):
        for st in (MatchStatus.LIVE, MatchStatus.FINISHED):
            m = mk_match(home=1, away=2, status=st)
            self.assertFalse(bet_window(m, KICKOFF - timedelta(hours=1))[0], st)

    def test_fechada_sem_times_definidos(self):
        m = mk_match(home=None, away=2)
        self.assertFalse(bet_window(m, KICKOFF - timedelta(days=1))[0])

    def test_now_ingenuo_rejeitado(self):
        with self.assertRaises(ValueError):
            bet_window(self.match, KICKOFF.replace(tzinfo=None))


if __name__ == "__main__":
    unittest.main()
