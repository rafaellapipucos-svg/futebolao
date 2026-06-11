import unittest

from app.domain.entities import MatchStatus
from app.domain.standings import compute_group

from .helpers import finished, mk_match

TEAMS = {1: "AAA", 2: "BBB", 3: "CCC", 4: "DDD"}


class TestStandings(unittest.TestCase):
    def test_tres_vitorias_nove_pontos(self):
        ms = [
            finished(1, 1, 2, 2, 0), finished(2, 1, 3, 1, 0), finished(3, 1, 4, 3, 1),
        ]
        rows = compute_group(TEAMS, ms)
        top = rows[0]
        self.assertEqual((top.team_id, top.points, top.won, top.gd), (1, 9, 3, 5))

    def test_ordenacao_pts_sg_gp(self):
        ms = [
            finished(1, 1, 2, 1, 0),   # 1 vence
            finished(2, 3, 4, 4, 0),   # 3 vence com saldo maior
        ]
        rows = compute_group(TEAMS, ms)
        self.assertEqual([r.team_id for r in rows[:2]], [3, 1])

    def test_h2h_resolve_empate_total(self):
        # T1 e T2: 6 pts, SG +1, GP 2 — h2h: T1 venceu T2.
        ms = [
            finished(1, 1, 2, 1, 0),
            finished(2, 1, 3, 0, 1), finished(3, 1, 4, 1, 0),
            finished(4, 2, 3, 1, 0), finished(5, 2, 4, 1, 0),
            finished(6, 3, 4, 0, 1),
        ]
        rows = compute_group(TEAMS, ms)
        self.assertEqual([r.team_id for r in rows], [1, 2, 4, 3])
        self.assertFalse(any(r.tie_unresolved for r in rows[:2]))

    def test_empate_irresoluvel_flag(self):
        # Todos com 4 pts, SG 0, GP 1 — loop perfeito.
        ms = [
            finished(1, 1, 2, 1, 0), finished(2, 3, 4, 1, 0),
            finished(3, 2, 3, 1, 0), finished(4, 4, 1, 1, 0),
            finished(5, 1, 3, 0, 0), finished(6, 2, 4, 0, 0),
        ]
        rows = compute_group(TEAMS, ms)
        self.assertTrue(all(r.points == 4 for r in rows))
        self.assertTrue(all(r.tie_unresolved for r in rows))
        self.assertEqual([r.code for r in rows], sorted(TEAMS.values()))

    def test_live_incluido_apenas_quando_pedido(self):
        ms = [
            finished(1, 1, 2, 1, 1),
            mk_match(mid=2, home=3, away=4, hs=1, as_=0, status=MatchStatus.LIVE),
        ]
        sem_live = compute_group(TEAMS, ms, include_live=False)
        self.assertEqual([r.points for r in sem_live if r.team_id == 3], [0])
        com_live = compute_group(TEAMS, ms, include_live=True)
        row3 = next(r for r in com_live if r.team_id == 3)
        self.assertEqual((row3.points, row3.gd, row3.live), (3, 1, True))
        row1 = next(r for r in com_live if r.team_id == 1)
        self.assertFalse(row1.live)

    def test_grupo_sem_jogos(self):
        rows = compute_group(TEAMS, [])
        self.assertTrue(all(r.points == 0 and r.played == 0 for r in rows))
        self.assertEqual([r.code for r in rows], sorted(TEAMS.values()))
        self.assertEqual([r.position for r in rows], [1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
