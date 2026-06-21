"""A3: rebuild_bracket recalcula o chaveamento DO ZERO, desfazendo a contaminação
quando um resultado de mata-mata já propagado é corrigido/resetado.

Cenário: o R32 (jogo 74) propaga o vencedor para o R16. Após um reset, o slot do
R16 fica obsoleto (D012 não des-resolve); o recálculo completo limpa/re-propaga.
"""
import unittest

from app.db.repos import matches as matches_repo
from app.domain.entities import MatchStatus
from app.services.bracket_svc import rebuild_bracket
from app.services.results import reset_match, set_score

from .db_helper import seeded_db, team_id_by_code


class TestBracketRebuild(unittest.TestCase):
    def setUp(self):
        self.conn = seeded_db()
        self.a = team_id_by_code(self.conn, "BRA")
        self.b = team_id_by_code(self.conn, "ARG")
        # Descobre dinamicamente o jogo de R16 que recebe o vencedor do R32 74.
        self.r16 = next(
            m for m in matches_repo.all_matches(self.conn)
            if m.home_source == "W74" or m.away_source == "W74"
        )
        self.side = "home" if self.r16.home_source == "W74" else "away"
        matches_repo.set_teams(self.conn, 74, self.a, self.b)

    def tearDown(self):
        self.conn.close()

    def _r16_slot(self):
        m = matches_repo.by_id(self.conn, self.r16.id)
        return m.home_team_id if self.side == "home" else m.away_team_id

    def test_rebuild_limpa_slot_apos_reset(self):
        set_score(self.conn, 74, 2, 0, MatchStatus.FINISHED)  # A vence ⇒ propaga A
        self.assertEqual(self._r16_slot(), self.a)
        reset_match(self.conn, 74)                # volta a scheduled
        self.assertEqual(self._r16_slot(), self.a)  # D012: slot obsoleto (não limpou)
        rebuild_bracket(self.conn)                # recálculo completo
        self.assertIsNone(self._r16_slot())       # slot indefinido foi limpo

    def test_rebuild_propaga_vencedor_corrigido(self):
        set_score(self.conn, 74, 2, 0, MatchStatus.FINISHED)  # A vence
        reset_match(self.conn, 74)
        set_score(self.conn, 74, 0, 2, MatchStatus.FINISHED)  # corrigido: B vence
        rebuild_bracket(self.conn)
        self.assertEqual(self._r16_slot(), self.b)

    def test_rebuild_preserva_jogo_ja_disputado(self):
        # Um jogo de mata-mata já FINISHED não pode ter os times apagados.
        set_score(self.conn, 74, 1, 0, MatchStatus.FINISHED)
        rebuild_bracket(self.conn)
        m = matches_repo.by_id(self.conn, 74)
        self.assertEqual((m.home_team_id, m.away_team_id), (self.a, self.b))


if __name__ == "__main__":
    unittest.main()
