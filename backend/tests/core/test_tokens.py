import unittest

from app.core.tokens import (
    TokenInvalidError,
    issue_pair,
    revoke_refresh,
    rotate,
    verify_access,
)
from app.db.connection import connect
from app.db.repos import users as users_repo
from app.db.schema import init_db

SECRET = "s" * 48


class TestTokens(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        init_db(self.conn)
        self.uid = users_repo.create(self.conn, "a@b.c", "Alice")

    def tearDown(self):
        self.conn.close()

    def test_issue_e_verify_access(self):
        pair = issue_pair(self.conn, self.uid, SECRET)
        self.assertEqual(verify_access(pair.access, SECRET), self.uid)

    def test_refresh_nao_vale_como_access(self):
        pair = issue_pair(self.conn, self.uid, SECRET)
        with self.assertRaises(TokenInvalidError):
            verify_access(pair.refresh, SECRET)

    def _backdate_revocation(self, refresh_token, seconds_ago):
        # Empurra o revoked_at do token p/ o passado (simula reuso TARDIO).
        from datetime import datetime, timedelta, timezone
        from app.core import jwt_hs256
        jti = jwt_hs256.verify(refresh_token, SECRET, expected_typ="refresh")["jti"]
        old = (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()
        self.conn.execute(
            "UPDATE refresh_tokens SET revoked_at = ? WHERE jti = ?", (old, jti))

    def test_rotacao_emite_novo_par(self):
        pair = issue_pair(self.conn, self.uid, SECRET)
        uid, new_pair = rotate(self.conn, pair.refresh, SECRET)
        self.assertEqual(uid, self.uid)
        self.assertNotEqual(pair.refresh, new_pair.refresh)

    def test_reuso_imediato_e_corrida_benigna(self):
        # 2 abas/retry renovando juntas: reuso LOGO após a rotação NÃO derruba a sessão.
        pair = issue_pair(self.conn, self.uid, SECRET)
        _, new_pair = rotate(self.conn, pair.refresh, SECRET)
        _, race_pair = rotate(self.conn, pair.refresh, SECRET)  # dentro da graça
        self.assertNotEqual(race_pair.refresh, new_pair.refresh)
        # a sessão nova segue VÁLIDA (família não foi revogada):
        uid, _ = rotate(self.conn, new_pair.refresh, SECRET)
        self.assertEqual(uid, self.uid)

    def test_reuso_tardio_rejeita_so_o_token(self):
        from app.core import tokens as tok
        pair = issue_pair(self.conn, self.uid, SECRET)
        _, new_pair = rotate(self.conn, pair.refresh, SECRET)
        self._backdate_revocation(pair.refresh, tok.REUSE_GRACE_SECONDS + 120)
        with self.assertRaises(TokenInvalidError):  # reuso tardio: rejeita só ele
            rotate(self.conn, pair.refresh, SECRET)
        # as OUTRAS sessões/dispositivos seguem vivos (não derruba ninguém):
        uid, _ = rotate(self.conn, new_pair.refresh, SECRET)
        self.assertEqual(uid, self.uid)

    def test_tres_dispositivos_independentes(self):
        # 3 logins separados = 3 cadeias; rotacionar uma NÃO afeta as outras.
        a = issue_pair(self.conn, self.uid, SECRET)
        b = issue_pair(self.conn, self.uid, SECRET)
        c = issue_pair(self.conn, self.uid, SECRET)
        rotate(self.conn, a.refresh, SECRET)
        self.assertEqual(rotate(self.conn, b.refresh, SECRET)[0], self.uid)
        self.assertEqual(rotate(self.conn, c.refresh, SECRET)[0], self.uid)

    def test_logout_revoga(self):
        pair = issue_pair(self.conn, self.uid, SECRET)
        revoke_refresh(self.conn, pair.refresh, SECRET)
        with self.assertRaises(TokenInvalidError):
            rotate(self.conn, pair.refresh, SECRET)

    def test_logout_token_lixo_nao_explode(self):
        revoke_refresh(self.conn, "lixo.total.aqui", SECRET)


if __name__ == "__main__":
    unittest.main()
