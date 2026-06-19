"""Rodada 16 (feature D): os 8 melhores 3ºs colocados (previsão pelo ranking atual)."""
import unittest

from app.domain.standings import Row
from app.services.standings_svc import mark_qualifying_thirds


def third(code, pts, gd=0, gf=0):
    r = Row(team_id=abs(hash(code)) % 100000, code=code)
    r.points = pts
    r.gf = gf
    r.ga = gf - gd
    return r


class TestThirdsPredictive(unittest.TestCase):
    def test_oito_melhores_por_pontos(self):
        pts = {"A": 6, "B": 5, "C": 4, "D": 4, "E": 3, "F": 3, "G": 2, "H": 2,
               "I": 1, "J": 1, "K": 0, "L": 0}
        rows = {g: third(g + "3", p) for g, p in pts.items()}
        qual = mark_qualifying_thirds(rows)
        self.assertEqual(qual, {"A", "B", "C", "D", "E", "F", "G", "H"})
        self.assertEqual(len(qual), 8)

    def test_desempate_por_saldo_fura_a_ordem_alfabetica(self):
        rows = {g: third(g + "3", 3) for g in "ABCDEFGHIJKL"}
        for g in "IJKL":  # mesmo pts, saldo melhor
            rows[g] = third(g + "3", 3, gd=5, gf=5)
        qual = mark_qualifying_thirds(rows)
        for g in "IJKL":
            self.assertIn(g, qual)
        self.assertEqual(len(qual), 8)


if __name__ == "__main__":
    unittest.main()
