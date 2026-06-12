import unittest
from datetime import datetime, timedelta, timezone

from app.db.repos import matches as matches_repo
from app.db.repos import bets as bets_repo
from app.db.repos import users as users_repo
from app.services.betting import place_bet
from app.services.leaderboard import leaderboard

from .db_helper import seeded_db

BEFORE = datetime(2026, 6, 11, 10, 0, tzinfo=timezone.utc)


class TestLeaderboard(unittest.TestCase):
    def setUp(self):
        from app.services import leaderboard as lb_mod
        lb_mod._cache.clear()  # cache é global; DBs de teste compartilham versões
        self.conn = seeded_db()
        self.alice = users_repo.create(self.conn, "alice@b.c", "Alice")
        self.bob = users_repo.create(self.conn, "bob@b.c", "Bob")
        self.caro = users_repo.create(self.conn, "caro@b.c", "Caro")
        # Jogo 1 (grupos): Alice crava 2x1; Bob acerta resultado 3x1; Caro erra
        place_bet(self.conn, self.alice, 1, 2, 1, now=BEFORE)
        place_bet(self.conn, self.bob, 1, 3, 1, now=BEFORE)
        place_bet(self.conn, self.caro, 1, 0, 0, now=BEFORE)

    def tearDown(self):
        self.conn.close()

    def test_totais_e_contadores(self):
        matches_repo.set_score(self.conn, 1, 2, 1, "finished")
        rows = leaderboard(self.conn, include_live=True)
        by_name = {r["display_name"]: r for r in rows}
        self.assertEqual(by_name["Alice"]["total"], 3)
        self.assertEqual(by_name["Alice"]["exact_hits"], 1)
        self.assertEqual(by_name["Alice"]["result_hits"], 0)
        self.assertEqual(by_name["Bob"]["total"], 1)
        self.assertEqual(by_name["Bob"]["result_hits"], 1)
        self.assertEqual(by_name["Caro"]["total"], 0)
        self.assertEqual([r["display_name"] for r in rows[:2]], ["Alice", "Bob"])
        self.assertEqual(rows[0]["position"], 1)

    def test_parciais_ao_vivo_flutuam(self):
        matches_repo.set_score(self.conn, 1, 2, 1, "live", minute=20)
        com_live = leaderboard(self.conn, include_live=True)
        alice = next(r for r in com_live if r["display_name"] == "Alice")
        self.assertEqual(alice["total"], 3)
        self.assertEqual(alice["live_total"], 3)
        self.assertTrue(alice["has_live"])
        sem_live = leaderboard(self.conn, include_live=False)
        alice2 = next(r for r in sem_live if r["display_name"] == "Alice")
        self.assertEqual(alice2["total"], 0)

    def test_cache_invalida_por_versao(self):
        from app.db.schema import bump_data_version
        matches_repo.set_score(self.conn, 1, 2, 1, "finished")
        bump_data_version(self.conn)
        r1 = leaderboard(self.conn)
        self.assertEqual(r1, leaderboard(self.conn))  # cache hit
        matches_repo.set_score(self.conn, 1, 0, 0, "finished")
        bump_data_version(self.conn)
        r2 = leaderboard(self.conn)
        alice = next(r for r in r2 if r["display_name"] == "Alice")
        self.assertEqual(alice["total"], 0)

    def test_empate_ordena_por_cravadas_depois_nome(self):
        matches_repo.set_score(self.conn, 1, 2, 1, "finished")
        # Dani sem apostas: 0 pontos, fica atrás de Caro (0 tb) por nome? Não:
        # Caro=0 e Dani=0 empatam ⇒ posição igual, ordem alfabética
        users_repo.create(self.conn, "dani@b.c", "Dani")
        from app.db.schema import bump_data_version
        bump_data_version(self.conn)
        rows = leaderboard(self.conn)
        zeros = [r for r in rows if r["total"] == 0]
        self.assertEqual([r["display_name"] for r in zeros], ["Caro", "Dani"])
        self.assertEqual(zeros[0]["position"], zeros[1]["position"])

    def test_multiplicador_em_fase_eliminatoria(self):
        # define times do jogo 73 manualmente e aposta
        from .db_helper import team_id_by_code
        mex, can = team_id_by_code(self.conn, "MEX"), team_id_by_code(self.conn, "CAN")
        matches_repo.set_teams(self.conn, 73, mex, can)
        kick73 = matches_repo.by_id(self.conn, 73).kickoff_utc
        place_bet(self.conn, self.alice, 73, 1, 0, now=kick73 - timedelta(hours=1))
        matches_repo.set_score(self.conn, 73, 1, 0, "finished")
        from app.db.schema import bump_data_version
        bump_data_version(self.conn)
        rows = leaderboard(self.conn)
        alice = next(r for r in rows if r["display_name"] == "Alice")
        self.assertEqual(alice["total"], 6)  # cravada (3) × R32 (2)

    def test_cache_invalida_quando_usuarios_mudam(self):
        # Regressao do bug de producao: novo usuario / troca de avatar NAO
        # bumpava data_version, entao o ranking ficava preso no cache antigo
        # (so o 1o usuario, foto velha). Agora a lista de usuarios e mesclada fresca.
        matches_repo.set_score(self.conn, 1, 2, 1, "finished")
        self.assertNotIn("Eva", {r["display_name"] for r in leaderboard(self.conn)})
        eva_id = users_repo.create(self.conn, "eva@b.c", "Eva")
        # aparece SEM bump_data_version manual:
        self.assertIn("Eva", {r["display_name"] for r in leaderboard(self.conn)})
        eva = next(r for r in leaderboard(self.conn) if r["display_name"] == "Eva")
        self.assertEqual(eva["avatar_ver"], 0)
        # troca de avatar reflete no ranking SEM bump_data_version:
        users_repo.bump_avatar(self.conn, eva_id)
        eva2 = next(r for r in leaderboard(self.conn) if r["display_name"] == "Eva")
        self.assertEqual(eva2["avatar_ver"], 1)

    def test_admin_exclui_perfil_some_do_ranking(self):
        matches_repo.set_score(self.conn, 1, 2, 1, "finished")
        self.assertIn("Bob", {r["display_name"] for r in leaderboard(self.conn)})
        users_repo.delete(self.conn, self.bob)
        from app.db.schema import bump_data_version
        bump_data_version(self.conn)
        self.assertNotIn("Bob", {r["display_name"] for r in leaderboard(self.conn)})
        # apostas do usuario excluido somem junto (cascade explicito):
        self.assertEqual(bets_repo.for_user(self.conn, self.bob), [])

    def test_admin_edita_aposta_passada_e_recalcula(self):
        # Jogo 1 ja comecou/encerrou (placar 2x1). Caro tinha apostado 0x0 (0 pts).
        # Admin corrige para 2x1: deve virar cravada (3 pts) MESMO sendo edicao
        # pos-kickoff — admin_set_bet grava updated_at antes do kickoff.
        from app.services.betting import admin_set_bet
        from app.db.schema import bump_data_version
        matches_repo.set_score(self.conn, 1, 2, 1, "finished")
        antes = next(r for r in leaderboard(self.conn) if r["display_name"] == "Caro")
        self.assertEqual(antes["total"], 0)
        admin_set_bet(self.conn, self.caro, 1, 2, 1)
        bump_data_version(self.conn)
        depois = next(r for r in leaderboard(self.conn) if r["display_name"] == "Caro")
        self.assertEqual(depois["total"], 3)  # cravada em fase de grupos
        self.assertEqual(depois["exact_hits"], 1)

    def test_admin_cria_aposta_para_quem_nao_apostou(self):
        from app.services.betting import admin_set_bet
        from app.db.schema import bump_data_version
        matches_repo.set_score(self.conn, 1, 2, 1, "finished")
        ze = users_repo.create(self.conn, "ze@b.c", "Ze")
        self.assertIsNone(bets_repo.get(self.conn, ze, 1))
        admin_set_bet(self.conn, ze, 1, 2, 1)  # cravada (3 pts)
        bump_data_version(self.conn)
        row = next(r for r in leaderboard(self.conn) if r["display_name"] == "Ze")
        self.assertEqual(row["total"], 3)


if __name__ == "__main__":
    unittest.main()
