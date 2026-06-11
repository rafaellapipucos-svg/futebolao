import unittest
from itertools import combinations

from app.domain.entities import THIRD_SLOTS
from app.domain.standings import Row
from app.domain.thirds import allocate, qualified_thirds, rank_thirds
from app.seed.loader import load_annex_c_table

POOLS = {
    "1A": set("CEFHI"), "1B": set("EFGIJ"), "1D": set("BEFIJ"), "1E": set("ABCDF"),
    "1G": set("AEHIJ"), "1I": set("CDFGH"), "1K": set("DEIJL"), "1L": set("EHIJK"),
}


def row(code, pts, gd, gf):
    r = Row(team_id=ord(code[0]), code=code, points=pts, gf=gf, ga=gf - gd)
    return r


class TestAnnexC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = load_annex_c_table()

    def test_495_combos_completos_e_validos(self):
        expected = {"".join(c) for c in combinations("ABCDEFGHIJKL", 8)}
        self.assertEqual(set(self.table), expected)
        for combo, assign in self.table.items():
            letters = sorted(assign.values())
            self.assertEqual(letters, sorted(set(letters)), combo)
            self.assertTrue(set(assign.values()) <= set(combo), combo)
            for slot, g in assign.items():
                self.assertIn(g, POOLS[slot], f"{combo}: {g} fora do pool {slot}")

    def test_linha_oficial_1(self):
        self.assertEqual(
            self.table["EFGHIJKL"],
            {"1A": "E", "1B": "J", "1D": "I", "1E": "F",
             "1G": "H", "1I": "G", "1K": "L", "1L": "K"},
        )

    def test_linha_oficial_495(self):
        self.assertEqual(
            self.table["ABCDEFGH"],
            {"1A": "H", "1B": "G", "1D": "B", "1E": "C",
             "1G": "A", "1I": "F", "1K": "D", "1L": "E"},
        )


class TestThirdsRanking(unittest.TestCase):
    def test_ranking_e_selecao(self):
        rows = {
            "A": row("A3", 6, 3, 5), "B": row("B3", 6, 3, 4), "C": row("C3", 6, 1, 9),
            "D": row("D3", 4, 0, 2), "E": row("E3", 4, 0, 2), "F": row("F3", 3, -1, 3),
            "G": row("G3", 3, -2, 1), "H": row("H3", 2, -1, 2), "I": row("I3", 2, -2, 1),
            "J": row("J3", 1, -3, 1), "K": row("K3", 1, -4, 0), "L": row("L3", 0, -5, 0),
        }
        ranked = rank_thirds(rows)
        self.assertEqual([g for g, _ in ranked[:3]], ["A", "B", "C"])  # pts>gd>gf
        self.assertEqual(qualified_thirds(rows), sorted("ABCDEFGH"))

    def test_allocate(self):
        table = load_annex_c_table()
        third_team = {g: 100 + i for i, g in enumerate("ABCDEFGH")}
        result = allocate(table, third_team, list("ABCDEFGH"))
        # linha ABCDEFGH: 1A:H 1B:G 1D:B 1E:C 1G:A 1I:F 1K:D 1L:E
        self.assertEqual(result["1A"], third_team["H"])
        self.assertEqual(result["1G"], third_team["A"])
        self.assertEqual(set(result), set(THIRD_SLOTS))

    def test_allocate_incompleto(self):
        table = load_annex_c_table()
        self.assertIsNone(allocate(table, {}, list("ABCDEFG")))


if __name__ == "__main__":
    unittest.main()
