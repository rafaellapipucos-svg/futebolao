"""Rodada 16 (feature B): provider extrai período/acréscimo/pênaltis e o placar
que vale (fim da prorrogação)."""
import unittest

from app.providers.football_data import parse_match


def raw(**over):
    base = {
        "id": 700,
        "utcDate": "2026-07-01T19:00:00Z",
        "status": "FINISHED",
        "minute": None,
        "homeTeam": {"name": "Brazil", "tla": "BRA"},
        "awayTeam": {"name": "Argentina", "tla": "ARG"},
        "score": {"winner": "HOME_TEAM", "duration": "PENALTY_SHOOTOUT",
                  "fullTime": {"home": 2, "away": 2},
                  "regularTime": {"home": 1, "away": 1},
                  "penalties": {"home": 4, "away": 3}},
    }
    base.update(over)
    return base


class TestProviderLiveState(unittest.TestCase):
    def test_placar_e_o_fim_da_prorrogacao(self):
        upd = parse_match(raw())
        self.assertEqual((upd.home_score, upd.away_score), (2, 2))  # fullTime, não 1x1

    def test_extrai_penaltis_e_winner(self):
        upd = parse_match(raw())
        self.assertEqual((upd.home_pens, upd.away_pens), (4, 3))
        self.assertEqual(upd.winner_code, "BRA")

    def test_periodo_primeiro_tempo(self):
        upd = parse_match(raw(status="IN_PLAY", minute=30,
                              score={"duration": "REGULAR",
                                     "fullTime": {"home": 0, "away": 0}}))
        self.assertEqual(upd.period, "1H")

    def test_periodo_segundo_tempo(self):
        upd = parse_match(raw(status="IN_PLAY", minute=75,
                              score={"duration": "REGULAR",
                                     "fullTime": {"home": 1, "away": 0}}))
        self.assertEqual(upd.period, "2H")

    def test_periodo_prorrogacao(self):
        upd = parse_match(raw(status="IN_PLAY", minute=100,
                              score={"duration": "EXTRA_TIME",
                                     "fullTime": {"home": 1, "away": 1}}))
        self.assertEqual(upd.period, "ET1")

    def test_periodo_intervalo(self):
        upd = parse_match(raw(status="PAUSED", minute=45,
                              score={"duration": "REGULAR",
                                     "fullTime": {"home": 0, "away": 0}}))
        self.assertEqual(upd.period, "HT")


if __name__ == "__main__":
    unittest.main()
