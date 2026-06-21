"""Cenário integrado: simula a Copa inteira via results.set_score e verifica a
propagação automática do chaveamento (persist_resolutions) até a final."""
import unittest

from app.db.repos import matches as matches_repo
from app.db.repos import teams as teams_repo
from app.domain.entities import GROUPS, MatchStatus, Stage
from app.services.bracket_svc import source_label
from app.services.results import set_score
from app.services.standings_svc import standings

from .db_helper import seeded_db


class TestBracketIntegrado(unittest.TestCase):
    def setUp(self):
        self.conn = seeded_db()

    def tearDown(self):
        self.conn.close()

    def _play_groups(self):
        """1º do grupo = maior id? Não: define vencedor = time da casa do 1º jogo
        do grupo etc. Mais simples: home sempre vence 2x0 ⇒ ordem determinística."""
        for m in matches_repo.all_matches(self.conn):
            if m.stage == Stage.GROUP:
                set_score(self.conn, m.id, 2, 0, MatchStatus.FINISHED)

    def test_r32_resolve_apos_grupos(self):
        # Antes dos grupos: R32 sem times; o slot mostra o rótulo da fonte.
        m73 = matches_repo.by_id(self.conn, 73)
        self.assertIsNone(m73.home_team_id)
        self.assertEqual(source_label(m73.home_source), "2º do Grupo A")

        self._play_groups()
        for m in matches_repo.all_matches(self.conn):
            if m.stage == Stage.R32:
                self.assertIsNotNone(m.home_team_id, m.id)
                self.assertIsNotNone(m.away_team_id, m.id)
        # R16 ainda indefinido (depende de jogos do R32): fonte = vencedor de J74.
        m89 = matches_repo.by_id(self.conn, 89)
        self.assertIsNone(m89.home_team_id)
        self.assertEqual(source_label(m89.home_source), "Vencedor J74")

    def test_cascata_ate_final_e_terceiro(self):
        self._play_groups()
        for mid in range(73, 105):
            m = matches_repo.by_id(self.conn, mid)
            self.assertIsNotNone(m.home_team_id, mid)  # resolvido em cascata
            set_score(self.conn, mid, 1, 0, MatchStatus.FINISHED)
        final = matches_repo.by_id(self.conn, 104)
        third = matches_repo.by_id(self.conn, 103)
        teams = teams_repo.all_teams(self.conn)
        # home sempre vence ⇒ final = vencedores de 101 (W97) e 102 (W99)
        self.assertEqual(final.status, MatchStatus.FINISHED)
        self.assertIsNotNone(final.winner_id())
        self.assertNotEqual(final.home_team_id, third.home_team_id)
        # todos os 32 jogos de mata-mata com times reais distintos por jogo
        for mid in range(73, 105):
            m = matches_repo.by_id(self.conn, mid)
            self.assertNotEqual(m.home_team_id, m.away_team_id, mid)
            self.assertIn(m.home_team_id, teams, mid)

    def test_standings_flags_clinch_expostos(self):
        # 2 rodadas do grupo A (jogos 1, 2, 25, 28) — MEX vence as duas
        for mid in (1, 2):
            set_score(self.conn, mid, 2, 0, MatchStatus.FINISHED)
        set_score(self.conn, 28, 2, 0, MatchStatus.FINISHED)  # MEX x KOR
        set_score(self.conn, 25, 0, 0, MatchStatus.FINISHED)  # CZE x RSA
        data = standings(self.conn, include_live=True)
        ga = next(g for g in data if g["group"] == "A")
        mex_row = next(r for r in ga["rows"] if r["team"]["code"] == "MEX")
        self.assertEqual(mex_row["points"], 6)
        self.assertTrue(mex_row["clinched_top2"])

    def test_source_labels(self):
        self.assertEqual(source_label("3:ABCDF"), "3º (A/B/C/D/F)")
        self.assertEqual(source_label("W73"), "Vencedor J73")
        self.assertEqual(source_label("L101"), "Perdedor J101")
        self.assertEqual(source_label("1A"), "1º do Grupo A")


if __name__ == "__main__":
    unittest.main()
