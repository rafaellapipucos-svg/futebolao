"""Rodada 16 (feature C): horário do jogo atualiza SOZINHO a partir do provider."""
import unittest
from datetime import timedelta

from app.db.repos import matches as matches_repo
from app.db.schema import get_data_version
from app.domain.entities import MatchStatus
from app.providers.base import ScoreUpdate
from app.providers.sync import apply_updates

from .db_helper import seeded_db


class TestSyncKickoff(unittest.TestCase):
    def setUp(self):
        self.conn = seeded_db()

    def tearDown(self):
        self.conn.close()

    def _update(self, match_id, new_kickoff, status=MatchStatus.SCHEDULED):
        matches_repo.set_external_id(self.conn, match_id, f"EXT-{match_id}")
        return ScoreUpdate(
            external_id=f"EXT-{match_id}", kickoff_utc=new_kickoff,
            home_code=None, away_code=None, status=status,
            home_score=None, away_score=None,
        )

    def test_kickoff_antecipado_atualiza_e_notifica(self):
        m = matches_repo.by_id(self.conn, 1)
        novo = m.kickoff_utc - timedelta(minutes=30)  # 22:00 -> 21:30
        v0 = get_data_version(self.conn)
        n = apply_updates(self.conn, [self._update(1, novo)])
        self.assertEqual(n, 1)
        self.assertEqual(matches_repo.by_id(self.conn, 1).kickoff_utc, novo)
        self.assertGreater(get_data_version(self.conn), v0)  # SSE notificado

    def test_jogo_ao_vivo_nao_tem_kickoff_alterado(self):
        matches_repo.set_score(self.conn, 1, 0, 0, "live", minute=10)
        orig = matches_repo.by_id(self.conn, 1).kickoff_utc
        apply_updates(self.conn, [self._update(1, orig - timedelta(hours=1),
                                               status=MatchStatus.LIVE)])
        self.assertEqual(matches_repo.by_id(self.conn, 1).kickoff_utc, orig)

    def test_poller_idle_e_responsivo(self):
        # Para mudanças de horário aparecerem sozinhas, o poll ocioso não pode
        # ser raro: exigimos <= 5 min.
        from app.jobs.poller import IDLE_INTERVAL
        self.assertLessEqual(IDLE_INTERVAL, 300)


if __name__ == "__main__":
    unittest.main()
