"""Rodada 16: relógio ao vivo dirigido por STATUS — máquina de fase + carimbo
do início de cada fase (period_started_at).

O minuto do provider costuma vir NULL; portanto a fase e suas FRONTEIRAS
(intervalo, volta do intervalo, fim) vêm do `status`/`duration`, que são
confiáveis. O front conta o minuto a partir de period_started_at e segue
"45+X"/"90+X" até o provider mudar o status — sem chutar o intervalo por tempo.
"""
import unittest
from datetime import datetime, timezone

from app.db.repos import matches as matches_repo
from app.domain.entities import MatchStatus
from app.providers.base import ScoreUpdate
from app.providers.sync import _next_period, apply_updates

from .db_helper import seeded_db


class TestNextPeriod(unittest.TestCase):
    """Máquina de fase pura: decide só por status/duração/fase-anterior."""

    def test_kickoff_vira_primeiro_tempo(self):
        self.assertEqual(_next_period(None, MatchStatus.LIVE, False, "REGULAR"), "1H")

    def test_pausa_no_tempo_normal_vira_intervalo(self):
        self.assertEqual(_next_period("1H", MatchStatus.LIVE, True, "REGULAR"), "HT")

    def test_volta_do_intervalo_vira_segundo_tempo(self):
        self.assertEqual(_next_period("HT", MatchStatus.LIVE, False, "REGULAR"), "2H")

    def test_segundo_tempo_se_mantem(self):
        self.assertEqual(_next_period("2H", MatchStatus.LIVE, False, "REGULAR"), "2H")

    def test_entra_na_prorrogacao_apos_segundo_tempo(self):
        self.assertEqual(_next_period("2H", MatchStatus.LIVE, False, "EXTRA_TIME"), "ET1")

    def test_pausa_na_prorrogacao(self):
        self.assertEqual(_next_period("ET1", MatchStatus.LIVE, True, "EXTRA_TIME"), "ET_HT")

    def test_segundo_tempo_da_prorrogacao(self):
        self.assertEqual(_next_period("ET_HT", MatchStatus.LIVE, False, "EXTRA_TIME"), "ET2")

    def test_disputa_de_penaltis(self):
        self.assertEqual(
            _next_period("ET2", MatchStatus.LIVE, False, "PENALTY_SHOOTOUT"), "PENS"
        )

    def test_fim_de_jogo(self):
        self.assertEqual(_next_period("2H", MatchStatus.FINISHED, False, "REGULAR"), "FT")

    def test_agendado_nao_tem_fase(self):
        self.assertIsNone(_next_period(None, MatchStatus.SCHEDULED, False, None))


def _upd(kick, **over):
    base = dict(
        external_id="fd-1", kickoff_utc=kick, home_code="MEX", away_code="RSA",
        status=MatchStatus.LIVE, home_score=0, away_score=0, minute=None,
        winner_code=None, paused=False, duration="REGULAR",
    )
    base.update(over)
    return ScoreUpdate(**base)


class TestCarimboDeFase(unittest.TestCase):
    """apply_updates grava period_started_at na transição (integração)."""

    def setUp(self):
        self.conn = seeded_db()
        self.kick = matches_repo.by_id(self.conn, 1).kickoff_utc

    def tearDown(self):
        self.conn.close()

    def test_primeiro_tempo_carimba_no_proprio_kickoff(self):
        apply_updates(self.conn, [_upd(self.kick)])
        m = matches_repo.by_id(self.conn, 1)
        self.assertEqual(m.period, "1H")
        # 1º tempo: o carimbo é o PRÓPRIO apito inicial, não "agora".
        self.assertEqual(m.period_started_at, self.kick.isoformat())

    def test_segundo_tempo_recebe_carimbo_novo(self):
        apply_updates(self.conn, [_upd(self.kick)])                 # 1H
        first = matches_repo.by_id(self.conn, 1).period_started_at
        apply_updates(self.conn, [_upd(self.kick, paused=True)])    # HT (intervalo)
        apply_updates(self.conn, [_upd(self.kick)])                 # volta → 2H
        m = matches_repo.by_id(self.conn, 1)
        self.assertEqual(m.period, "2H")
        self.assertIsNotNone(m.period_started_at)
        self.assertNotEqual(m.period_started_at, first)  # recarimbado na volta

    def test_intervalo_preserva_o_carimbo_anterior(self):
        apply_updates(self.conn, [_upd(self.kick)])                 # 1H
        stamp = matches_repo.by_id(self.conn, 1).period_started_at
        apply_updates(self.conn, [_upd(self.kick, paused=True)])    # HT não corre
        # intervalo não recarimba (não é fase que corre): mantém o do 1º tempo.
        self.assertEqual(matches_repo.by_id(self.conn, 1).period_started_at, stamp)


if __name__ == "__main__":
    unittest.main()
