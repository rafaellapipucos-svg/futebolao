import unittest

from app.domain.clinch import analyze, group_finished

from .helpers import finished, mk_match

IDS = [1, 2, 3, 4]


class TestClinch(unittest.TestCase):
    def _round2_scenario(self):
        """Após 2 rodadas: T1=6, T2=2, T3=1, T4=1 (restam 2 jogos: T1xT2? não:
        r1: 1x4, 2x3 | r2: 1x3, 2x4 | r3 (futuros): 1x2, 3x4."""
        return [
            finished(1, 1, 4, 1, 0), finished(2, 2, 3, 0, 0),
            finished(3, 1, 3, 2, 0), finished(4, 2, 4, 1, 1),
            mk_match(mid=5, home=1, away=2), mk_match(mid=6, home=3, away=4),
        ]

    def test_clinched_first_antes_da_ultima_rodada(self):
        out = analyze(IDS, self._round2_scenario())
        self.assertTrue(out[1].clinched_first)
        self.assertEqual(out[1].guaranteed_position, 1)
        # T2 com 2 pts pode chegar a 5; ninguém garante 2º ainda
        self.assertIsNone(out[2].guaranteed_position)

    def test_top2_garantido_sem_primeiro(self):
        # T1=6, T2=6 (2 jogos), T3=0, T4=0; T3/T4 max=3+0? r3 entre 3x4 e 1x2:
        ms = [
            finished(1, 1, 3, 1, 0), finished(2, 2, 4, 1, 0),
            finished(3, 1, 4, 1, 0), finished(4, 2, 3, 1, 0),
            mk_match(mid=5, home=1, away=2), mk_match(mid=6, home=3, away=4),
        ]
        out = analyze(IDS, ms)
        # T3/T4 max = 3 < 6 ⇒ T1 e T2 têm top-2; nenhum tem 1º garantido (6 vs max 9)
        self.assertTrue(out[1].clinched_top2 and out[2].clinched_top2)
        self.assertFalse(out[1].clinched_first or out[2].clinched_first)
        self.assertTrue(out[3].eliminated_top2 and out[4].eliminated_top2)

    def test_nao_clinched_quando_alcancavel(self):
        # T1=4, T2=3, T3=3 com jogos restantes ⇒ nada garantido (conservador)
        ms = [
            finished(1, 1, 4, 0, 0), finished(2, 2, 3, 0, 0),
            finished(3, 1, 2, 1, 0), finished(4, 3, 4, 1, 0),
            mk_match(mid=5, home=1, away=3), mk_match(mid=6, home=2, away=4),
        ]
        out = analyze(IDS, ms)
        self.assertFalse(out[1].clinched_top2)
        self.assertIsNone(out[1].guaranteed_position)

    def test_posicao_2_garantida(self):
        # T1 já com 9 (encerrou); T2=4; T3/T4 max < 4 ⇒ T2 é exatamente 2º
        ms = [
            finished(1, 1, 2, 1, 0), finished(2, 1, 3, 1, 0), finished(3, 1, 4, 1, 0),
            finished(4, 2, 3, 2, 0), finished(5, 2, 4, 1, 1),
            mk_match(mid=6, home=3, away=4),
        ]
        out = analyze(IDS, ms)
        # T2 = 4 pts; T3 max = 0+3=3; T4 max = 1+3=4 >= 4 ⇒ ainda alcançável!
        self.assertIsNone(out[2].guaranteed_position)
        # Agora T4 perde o último: tudo encerrado
        ms[5] = finished(6, 3, 4, 1, 0)
        out2 = analyze(IDS, ms)
        self.assertEqual(out2[2].guaranteed_position, 2)
        self.assertTrue(group_finished(IDS, ms))

    def test_live_conta_como_restante(self):
        from app.domain.entities import MatchStatus
        ms = self._round2_scenario()
        ms[4] = mk_match(mid=5, home=1, away=2, hs=0, as_=3, status=MatchStatus.LIVE)
        out = analyze(IDS, ms)
        # mesmo perdendo ao vivo, pontos de live não contam: T1 segue com 6 e 1º garantido
        self.assertTrue(out[1].clinched_first)


if __name__ == "__main__":
    unittest.main()
