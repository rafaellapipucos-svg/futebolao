"""Provider extrai pênaltis e o placar que vale (fim da prorrogação). A fase do
relógio (period) é derivada no sync (_next_period) — ver test_sync_period."""
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
        # API real: fullTime = regularTime + extraTime + penalties (a doc soma os
        # pênaltis). ET 1x1 + pênaltis 4x3 ⇒ fullTime 5x4. O placar que vale para a
        # aposta é o do FIM DA PRORROGAÇÃO (1x1).
        "score": {"winner": "HOME_TEAM", "duration": "PENALTY_SHOOTOUT",
                  "fullTime": {"home": 5, "away": 4},
                  "regularTime": {"home": 1, "away": 1},
                  "penalties": {"home": 4, "away": 3}},
    }
    base.update(over)
    return base


class TestProviderLiveState(unittest.TestCase):
    def test_placar_e_o_fim_da_prorrogacao(self):
        upd = parse_match(raw())
        # fullTime 5x4 INCLUI os pênaltis (4x3); o placar que vale é o fim da
        # prorrogação = fullTime - penalties = 1x1.
        self.assertEqual((upd.home_score, upd.away_score), (1, 1))

    def test_extrai_penaltis_e_winner(self):
        upd = parse_match(raw())
        self.assertEqual((upd.home_pens, upd.away_pens), (4, 3))
        self.assertEqual(upd.winner_code, "BRA")

if __name__ == "__main__":
    unittest.main()
