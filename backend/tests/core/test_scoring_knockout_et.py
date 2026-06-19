"""Rodada 16: no mata-mata, a aposta pontua pelo placar do FIM DA PRORROGAÇÃO
(antes dos pênaltis). Os pênaltis são descartados do placar (só definem o vencedor)."""
import unittest
from datetime import datetime, timedelta, timezone

from app.domain.entities import Bet, Match, MatchStatus, Stage
from app.services.betting import bet_points

KICK = datetime(2026, 7, 1, 19, 0, tzinfo=timezone.utc)


def ko_match(hs, as_, *, pens=None, winner=None, stage=Stage.R16):
    home_pens, away_pens = pens if pens else (None, None)
    return Match(
        id=90, stage=stage, group=None, kickoff_utc=KICK, venue="X",
        home_source="W1", away_source="W2", home_team_id=10, away_team_id=20,
        home_score=hs, away_score=as_, status=MatchStatus.FINISHED,
        winner_team_id=winner, home_pens=home_pens, away_pens=away_pens,
    )


def bet(hg, ag):
    return Bet(id=1, user_id=1, match_id=90, home_goals=hg, away_goals=ag,
               created_at=KICK - timedelta(days=1), updated_at=KICK - timedelta(hours=1))


class TestKnockoutEndOfExtraTime(unittest.TestCase):
    def test_flag_went_to_penalties(self):
        self.assertTrue(ko_match(2, 2, pens=(4, 3), winner=10).went_to_penalties)
        self.assertFalse(ko_match(2, 1).went_to_penalties)

    def test_winner_usa_penaltis_no_empate_pos_prorrogacao(self):
        self.assertEqual(ko_match(2, 2, pens=(4, 3), winner=10).winner_id(), 10)
        self.assertEqual(ko_match(3, 1).winner_id(), 10)  # decidido em campo

    def test_aposta_pontua_pelo_placar_fim_da_prorrogacao(self):
        m = ko_match(2, 2, pens=(4, 3), winner=10)  # ET 2x2, pênaltis 4x3
        s = bet_points(bet(2, 2), m)
        self.assertTrue(s.hit_exact)
        self.assertEqual(s.total, 3 * 3)  # cravada × multiplicador R16 (3)

    def test_penaltis_nao_contam_para_a_aposta(self):
        m = ko_match(2, 2, pens=(4, 3), winner=10)
        # Quem "apostou no vencedor dos pênaltis" (vitória do mandante) ERRA:
        # o placar que vale é o do fim da prorrogação (2x2, empate).
        s = bet_points(bet(3, 2), m)
        self.assertFalse(s.hit_result)
        self.assertEqual(s.total, 0)
        # Apostar empate acerta o resultado (sem cravar):
        s2 = bet_points(bet(1, 1), m)
        self.assertTrue(s2.hit_result and not s2.hit_exact)
        self.assertEqual(s2.total, 1 * 3)


if __name__ == "__main__":
    unittest.main()
