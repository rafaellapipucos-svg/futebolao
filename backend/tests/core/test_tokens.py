import unittest

from app.core.tokens import (
    TokenInvalidError,
    TokenReuseError,
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

    def test_rotacao_revoga_antigo(self):
        pair = issue_pair(self.conn, self.uid, SECRET)
        uid, new_pair = rotate(self.conn, pair.refresh, SECRET)
        self.assertEqual(uid, self.uid)
        self.assertNotEqual(pair.refresh, new_pair.refresh)
        # reuso do antigo ⇒ TokenReuseError + revogação em massa
        with self.assertRaises(TokenReuseError):
            rotate(self.conn, pair.refresh, SECRET)
        # inclusive o novo morreu (família revogada)
        with self.assertRaises(TokenInvalidError):
            rotate(self.conn, new_pair.refresh, SECRET)

    def test_logout_revoga(self):
        pair = issue_pair(self.conn, self.uid, SECRET)
        revoke_refresh(self.conn, pair.refresh, SECRET)
        with self.assertRaises(TokenInvalidError):
            rotate(self.conn, pair.refresh, SECRET)

    def test_logout_token_lixo_nao_explode(self):
        revoke_refresh(self.conn, "lixo.total.aqui", SECRET)


if __name__ == "__main__":
    unittest.main()
