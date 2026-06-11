import unittest

from app.domain.entities import Stage
from app.domain.scoring import score_bet


class TestScoring(unittest.TestCase):
    def test_cravada_grupo(self):
        s = score_bet(2, 1, 2, 1, Stage.GROUP)
        self.assertTrue(s.hit_result and s.hit_exact)
        self.assertEqual((s.base, s.multiplier, s.total), (3, 1, 3))

    def test_resultado_certo_nao_exato(self):
        s = score_bet(2, 1, 3, 1, Stage.GROUP)
        self.assertTrue(s.hit_result)
        self.assertFalse(s.hit_exact)
        self.assertEqual(s.total, 1)

    def test_erro_total(self):
        s = score_bet(2, 1, 0, 1, Stage.GROUP)
        self.assertEqual((s.hit_result, s.hit_exact, s.total), (False, False, 0))

    def test_empate_cravado_e_generico(self):
        self.assertEqual(score_bet(1, 1, 1, 1, Stage.GROUP).total, 3)
        s = score_bet(1, 1, 2, 2, Stage.GROUP)
        self.assertTrue(s.hit_result)
        self.assertEqual(s.total, 1)

    def test_multiplicadores_por_fase(self):
        expected = {
            Stage.GROUP: 3, Stage.R32: 6, Stage.R16: 9, Stage.QF: 12,
            Stage.SF: 15, Stage.THIRD: 15, Stage.FINAL: 30,
        }
        for stage, total in expected.items():
            self.assertEqual(score_bet(2, 1, 2, 1, stage).total, total, stage)
        self.assertEqual(score_bet(2, 1, 4, 2, Stage.FINAL).total, 10)

    def test_placar_invalido(self):
        with self.assertRaises(ValueError):
            score_bet(-1, 0, 1, 0, Stage.GROUP)
        with self.assertRaises(ValueError):
            score_bet(1, 0, None, 0, Stage.GROUP)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
