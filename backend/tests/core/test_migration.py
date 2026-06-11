import unittest

from app.db.connection import connect
from app.db.repos import users as users_repo
from app.db.schema import _column_exists, init_db


class TestMigration(unittest.TestCase):
    def test_init_db_adiciona_bio_em_users_legado(self):
        conn = connect(":memory:")
        # simula DB "v2": users SEM a coluna bio
        conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, "
            "display_name TEXT NOT NULL, password_hash TEXT, google_sub TEXT, "
            "avatar_ver INTEGER NOT NULL DEFAULT 0, is_admin INTEGER NOT NULL DEFAULT 0, "
            "created_at TEXT NOT NULL)")
        self.assertFalse(_column_exists(conn, "users", "bio"))
        init_db(conn)               # roda a migração idempotente
        self.assertTrue(_column_exists(conn, "users", "bio"))
        init_db(conn)               # idempotente: rodar de novo não quebra
        self.assertTrue(_column_exists(conn, "users", "bio"))

    def test_set_bio_persiste(self):
        conn = connect(":memory:")
        init_db(conn)
        uid = users_repo.create(conn, "a@b.c", "Alice")
        users_repo.set_bio(conn, uid, "Torcedor raiz, palpiteiro nato")
        self.assertEqual(users_repo.by_id(conn, uid)["bio"], "Torcedor raiz, palpiteiro nato")


if __name__ == "__main__":
    unittest.main()
