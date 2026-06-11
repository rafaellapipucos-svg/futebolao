import unittest

from app.domain.bracket import build_context, resolve_all, resolve_source
from app.domain.entities import GROUPS, Stage
from app.domain.thirds import allocate, qualified_thirds
from app.seed.loader import load_annex_c_table
from app.domain.standings import compute_group

from .helpers import finished, full_group_results, group_ids, make_teams_48, mk_match


def knockout_fixtures():
    """Jogos 73..104 com sources oficiais (espelha fixtures.txt)."""
    spec = {
        73: ("2A", "2B"), 74: ("1E", "3:ABCDF"), 75: ("1F", "2C"), 76: ("1C", "2F"),
        77: ("1I", "3:CDFGH"), 78: ("2E", "2I"), 79: ("1A", "3:CEFHI"),
        80: ("1L", "3:EHIJK"), 81: ("1D", "3:BEFIJ"), 82: ("1G", "3:AEHIJ"),
        83: ("2K", "2L"), 84: ("1H", "2J"), 85: ("1B", "3:EFGIJ"), 86: ("1J", "2H"),
        87: ("1K", "3:DEIJL"), 88: ("2D", "2G"),
        89: ("W74", "W77"), 90: ("W73", "W75"), 91: ("W76", "W78"), 92: ("W79", "W80"),
        93: ("W83", "W84"), 94: ("W81", "W82"), 95: ("W86", "W88"), 96: ("W85", "W87"),
        97: ("W89", "W90"), 98: ("W93", "W94"), 99: ("W91", "W92"), 100: ("W95", "W96"),
        101: ("W97", "W98"), 102: ("W99", "W100"),
        103: ("L101", "L102"), 104: ("W101", "W102"),
    }
    stage_of = lambda i: (
        Stage.R32 if i <= 88 else Stage.R16 if i <= 96 else Stage.QF if i <= 100
        else Stage.SF if i <= 102 else Stage.THIRD if i == 103 else Stage.FINAL
    )
    return [
        mk_match(mid=i, stage=stage_of(i), group=None,
                 home_source=h, away_source=a)
        for i, (h, a) in spec.items()
    ]


def team_of(g: str, n: int) -> int:
    return group_ids(g)[n - 1]


class TestBracket(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teams = make_teams_48()
        cls.annex = load_annex_c_table()

    def _all_groups_finished(self):
        ms, mid = [], 1
        for g in GROUPS:
            res, mid = full_group_results(mid, g)
            ms.extend(res)
        return ms

    def _third_assignment(self, group_matches):
        third_rows, third_team = {}, {}
        for g in GROUPS:
            ids = {t: self.teams[t].code for t in group_ids(g)}
            rows = compute_group(ids, [m for m in group_matches if m.group == g])
            third_rows[g] = rows[2]
            third_team[g] = rows[2].team_id
        qual = qualified_thirds(third_rows)
        return allocate(self.annex, third_team, qual), qual

    def test_grupos_indecisos_nada_resolve(self):
        ctx = build_context(self.teams, knockout_fixtures())
        resolved = resolve_all(ctx)
        for mid, (h, a) in resolved.items():
            self.assertIsNone(h, mid)
            self.assertIsNone(a, mid)

    def test_clinch_resolve_slot_cedo(self):
        # Grupo A com 1º garantido após 2 rodadas (cenário do test_clinch)
        a1, a2, a3, a4 = group_ids("A")
        ms = [
            finished(1, a1, a4, 1, 0, group="A"), finished(2, a2, a3, 0, 0, group="A"),
            finished(3, a1, a3, 2, 0, group="A"), finished(4, a2, a4, 1, 1, group="A"),
            mk_match(mid=5, group="A", home=a1, away=a2),
            mk_match(mid=6, group="A", home=a3, away=a4),
        ] + knockout_fixtures()
        ctx = build_context(self.teams, ms)
        self.assertEqual(resolve_source(ctx, "1A", 79), a1)
        self.assertIsNone(resolve_source(ctx, "2A", 73))

    def test_terceiros_so_com_12_grupos_encerrados(self):
        group_ms = self._all_groups_finished()
        ms = group_ms + knockout_fixtures()
        ctx = build_context(self.teams, ms)  # sem third_assignment
        self.assertIsNone(resolve_source(ctx, "3:ABCDF", 74))
        assignment, qual = self._third_assignment(group_ms)
        # todos os 3ºs empatados (3 pts, mesmos gols) ⇒ melhores 8 por código: A..H
        self.assertEqual(qual, sorted("ABCDEFGH"))
        ctx2 = build_context(self.teams, ms, third_assignment=assignment)
        # linha ABCDEFGH da Annex C: 1E recebe 3C
        self.assertEqual(resolve_source(ctx2, "3:ABCDF", 74), team_of("C", 3))
        self.assertEqual(resolve_source(ctx2, "3:AEHIJ", 82), team_of("A", 3))

    def test_cascata_completa_ate_a_final(self):
        group_ms = self._all_groups_finished()
        assignment, _ = self._third_assignment(group_ms)
        kos = knockout_fixtures()
        ms = group_ms + kos
        ctx = build_context(self.teams, ms, third_assignment=assignment)
        # R32 inteiro resolvido (grupos encerrados + annex)
        resolved = resolve_all(ctx)
        for mid in range(73, 89):
            h, a = resolved[mid]
            self.assertIsNotNone(h, mid)
            self.assertIsNotNone(a, mid)
        # R16 ainda TBD (jogos do R32 não disputados)
        self.assertEqual(resolved[89], (None, None))

        # Disputa todo o mata-mata: mandante sempre vence 1x0
        finished_kos = []
        for ko in kos:
            h, a = resolved[ko.id] if ko.id in resolved else (None, None)
            m = finished(ko.id, None, None, 1, 0, group=None, stage=ko.stage)
            m.home_source, m.away_source = ko.home_source, ko.away_source
            finished_kos.append(m)
        # resolve em ordem, preenchendo times e jogando 1x0
        all_ms = group_ms + finished_kos
        for m in finished_kos:
            ctx_i = build_context(self.teams, all_ms, third_assignment=assignment)
            h, a = resolve_all(ctx_i)[m.id]
            m.home_team_id, m.away_team_id = h, a
        final_ctx = build_context(self.teams, all_ms, third_assignment=assignment)
        final_resolved = resolve_all(final_ctx)
        # Cadeia (mandante vence): final = 1E × 1C ; 3º lugar = 2K × 1J
        self.assertEqual(final_resolved[104], (team_of("E", 1), team_of("C", 1)))
        self.assertEqual(final_resolved[103], (team_of("K", 2), team_of("J", 1)))
        self.assertEqual(final_resolved[89], (team_of("E", 1), team_of("I", 1)))

    def test_empate_mata_mata_exige_winner(self):
        group_ms = self._all_groups_finished()
        assignment, _ = self._third_assignment(group_ms)
        kos = knockout_fixtures()
        m73 = next(m for m in kos if m.id == 73)
        a2, b2 = team_of("A", 2), team_of("B", 2)
        m73.home_team_id, m73.away_team_id = a2, b2
        m73.home_score = m73.away_score = 1
        from app.domain.entities import MatchStatus
        m73.status = MatchStatus.FINISHED
        ctx = build_context(self.teams, group_ms + kos, third_assignment=assignment)
        self.assertIsNone(resolve_source(ctx, "W73", 90))  # sem winner explícito
        m73.winner_team_id = b2
        ctx2 = build_context(self.teams, group_ms + kos, third_assignment=assignment)
        self.assertEqual(resolve_source(ctx2, "W73", 90), b2)


if __name__ == "__main__":
    unittest.main()
