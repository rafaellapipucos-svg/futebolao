import unittest
from datetime import datetime, timedelta, timezone

from app.db.repos import matches as matches_repo
from app.db.schema import get_data_version
from app.domain.entities import MatchStatus
from app.jobs.poller import window_active
from app.providers.base import ScoreUpdate
from app.providers.sync import apply_updates

from .db_helper import seeded_db

KICK_M1 = datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)


def upd(**over):
    base = dict(
        external_id="fd-1", kickoff_utc=KICK_M1, home_code="MEX", away_code="RSA",
        status=MatchStatus.LIVE, home_score=1, away_score=0, minute=20,
        winner_code=None,
    )
    base.update(over)
    return ScoreUpdate(**base)


class TestSync(unittest.TestCase):
    def setUp(self):
        self.conn = seeded_db()

    def tearDown(self):
        self.conn.close()

    def test_casa_por_kickoff_e_codigos_e_salva_external_id(self):
        changed = apply_updates(self.conn, [upd()])
        self.assertEqual(changed, 1)
        m1 = matches_repo.by_id(self.conn, 1)
        self.assertEqual((m1.home_score, m1.away_score, m1.status),
                         (1, 0, MatchStatus.LIVE))
        self.assertEqual(m1.external_id, "fd-1")

    def test_idempotente(self):
        apply_updates(self.conn, [upd()])
        v = get_data_version(self.conn)
        changed = apply_updates(self.conn, [upd()])
        self.assertEqual(changed, 0)
        self.assertEqual(get_data_version(self.conn), v)

    def test_manual_lock_vence_api(self):
        matches_repo.set_manual_lock(self.conn, 1, True)
        changed = apply_updates(self.conn, [upd()])
        self.assertEqual(changed, 0)
        self.assertIsNone(matches_repo.by_id(self.conn, 1).home_score)

    def test_update_sem_placar_ignorado(self):
        changed = apply_updates(self.conn, [upd(home_score=None, away_score=None,
                                                status=MatchStatus.SCHEDULED)])
        self.assertEqual(changed, 0)

    def test_jogo_desconhecido_ignorado(self):
        changed = apply_updates(self.conn, [upd(
            external_id="fd-x",
            kickoff_utc=KICK_M1 + timedelta(days=300),
            home_code="XXX", away_code="YYY",
        )])
        self.assertEqual(changed, 0)

    def test_empate_mata_mata_sem_winner_skipa_com_log(self):
        from .db_helper import team_id_by_code
        mex = team_id_by_code(self.conn, "MEX")
        can = team_id_by_code(self.conn, "CAN")
        matches_repo.set_teams(self.conn, 73, mex, can)
        kick73 = matches_repo.by_id(self.conn, 73).kickoff_utc
        with self.assertLogs("bolao.sync", level="WARNING"):
            changed = apply_updates(self.conn, [upd(
                external_id="fd-73", kickoff_utc=kick73,
                home_code="MEX", away_code="CAN",
                status=MatchStatus.FINISHED, home_score=1, away_score=1,
            )])
        self.assertEqual(changed, 0)

    def test_atualizacao_via_external_id_apos_primeiro_match(self):
        apply_updates(self.conn, [upd()])
        changed = apply_updates(self.conn, [upd(
            home_code=None, away_code=None,  # API sem nomes? external_id basta
            home_score=2, away_score=0, minute=60,
        )])
        self.assertEqual(changed, 1)
        self.assertEqual(matches_repo.by_id(self.conn, 1).home_score, 2)

    def test_nao_casa_sem_codigos_fortes(self):
        # M2: sem external_id conhecido E sem os 2 códigos, NÃO casa por
        # proximidade de horário (no mata-mata, jogos do mesmo dia caem na
        # janela; adivinhar atribuiria o placar ao jogo errado).
        changed = apply_updates(self.conn, [upd(
            external_id="fd-anon", home_code=None, away_code=None,
            home_score=3, away_score=3,
        )])
        self.assertEqual(changed, 0)
        self.assertIsNone(matches_repo.by_id(self.conn, 1).home_score)


class TestPollerWindow(unittest.TestCase):
    def setUp(self):
        self.conn = seeded_db()

    def tearDown(self):
        self.conn.close()

    def test_janela(self):
        ms = matches_repo.all_matches(self.conn)
        self.assertFalse(window_active(ms, now=KICK_M1 - timedelta(hours=2)))
        self.assertTrue(window_active(ms, now=KICK_M1 - timedelta(minutes=5)))
        self.assertTrue(window_active(ms, now=KICK_M1 + timedelta(hours=1)))
        # 19:00Z+3h30 = 22:30; jogo 7 (13/06) longe ⇒ inativa às 23h
        self.assertFalse(window_active(ms, now=KICK_M1 + timedelta(hours=4)))
        matches_repo.set_score(self.conn, 1, 1, 0, "live", minute=80)
        ms2 = matches_repo.all_matches(self.conn)
        self.assertTrue(window_active(ms2, now=KICK_M1 + timedelta(hours=9)))


if __name__ == "__main__":
    unittest.main()
