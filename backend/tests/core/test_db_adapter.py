"""Adapter de banco: caminho Postgres exercitado com driver fake instrumentado.

O fake implementa o subconjunto psycopg usado pelo adapter e REGISTRA cada SQL
executado — validamos traducao de placeholders, RETURNING, BEGIN/COMMIT,
normalizacao de IntegrityError, split de DDL e deteccao de URL.
"""
import unittest

from app.db.connection import (
    Db, IntegrityError, connect, insert_id, is_postgres_target,
    normalize_pg_url, tx,
)
from app.db.schema import render_ddl


class FakePgIntegrity(Exception):
    pass


class FakePgConn:
    def __init__(self):
        self.executed = []  # [(sql, params)]
        self.raise_integrity_on = None
        self.fetchone_value = {"id": 42}
        self.closed = False

    def execute(self, sql, params=()):
        self.executed.append((sql, tuple(params)))
        if self.raise_integrity_on and self.raise_integrity_on in sql:
            raise FakePgIntegrity("duplicate key value violates unique constraint")
        conn = self

        class Cur:
            def fetchone(self_inner):
                return conn.fetchone_value
            rowcount = 1
        return Cur()

    def close(self):
        self.closed = True


class FakeDriver:
    IntegrityError = FakePgIntegrity

    def __init__(self):
        self.conns = []
        self.last_url = None

    def connect(self, url):
        self.last_url = url
        conn = FakePgConn()
        self.conns.append(conn)
        return conn


class TestUrlHandling(unittest.TestCase):
    def test_deteccao_de_alvo(self):
        self.assertTrue(is_postgres_target("postgresql://u:p@h:5432/db"))
        self.assertTrue(is_postgres_target("postgres://u:p@h/db"))
        self.assertFalse(is_postgres_target(":memory:"))
        self.assertFalse(is_postgres_target("/data/bolao.db"))

    def test_normalize_heroku_supabase(self):
        self.assertEqual(
            normalize_pg_url("postgres://u:p@h/db"), "postgresql://u:p@h/db"
        )
        self.assertEqual(
            normalize_pg_url("postgresql://u:p@h/db"), "postgresql://u:p@h/db"
        )


class TestAdapterPostgres(unittest.TestCase):
    def setUp(self):
        self.driver = FakeDriver()
        self.db = connect("postgres://u:p@host/db", driver=self.driver)

    def test_url_normalizada_chega_ao_driver(self):
        self.assertEqual(self.driver.last_url, "postgresql://u:p@host/db")
        self.assertEqual(self.db.dialect, "postgres")

    def test_traducao_de_placeholders(self):
        self.db.execute("SELECT * FROM users WHERE email = ? AND id = ?", ("a", 1))
        sql, params = self.driver.conns[0].executed[-1]
        self.assertEqual(sql, "SELECT * FROM users WHERE email = %s AND id = %s")
        self.assertEqual(params, ("a", 1))

    def test_traducao_preserva_interrogacao_em_string(self):  # B1
        self.db.execute("SELECT * FROM t WHERE nome = 'a?b' AND id = ?", (1,))
        sql, params = self.driver.conns[0].executed[-1]
        self.assertEqual(sql, "SELECT * FROM t WHERE nome = 'a?b' AND id = %s")
        self.assertEqual(params, (1,))

    def test_traducao_dobra_porcento(self):  # B1 (psycopg %-format)
        self.db.execute("SELECT * FROM t WHERE nome LIKE '%x%' AND id = ?", (1,))
        sql, _ = self.driver.conns[0].executed[-1]
        self.assertEqual(sql, "SELECT * FROM t WHERE nome LIKE '%%x%%' AND id = %s")

    def test_split_ddl_ignora_ponto_e_virgula_em_string(self):  # B1
        before = len(self.driver.conns[0].executed)
        self.db.executescript("INSERT INTO t (s) VALUES ('a;b'); CREATE TABLE x (y INT)")
        executed = self.driver.conns[0].executed[before:]
        self.assertEqual(len(executed), 2)

    def test_insert_id_usa_returning(self):
        new_id = insert_id(self.db, "INSERT INTO users (email) VALUES (?)", ("a",))
        sql, _ = self.driver.conns[0].executed[-1]
        self.assertTrue(sql.endswith("VALUES (%s) RETURNING id"))
        self.assertEqual(new_id, 42)

    def test_tx_begin_commit_padrao(self):
        with tx(self.db):
            self.db.execute("UPDATE meta SET value = ?", ("1",))
        sqls = [s for s, _ in self.driver.conns[0].executed]
        self.assertEqual(sqls[0], "BEGIN")
        self.assertEqual(sqls[-1], "COMMIT")
        self.assertNotIn("BEGIN IMMEDIATE", sqls)

    def test_tx_rollback_em_erro(self):
        with self.assertRaises(RuntimeError):
            with tx(self.db):
                raise RuntimeError("boom")
        sqls = [s for s, _ in self.driver.conns[0].executed]
        self.assertEqual(sqls[-1], "ROLLBACK")

    def test_integrity_normalizada(self):
        self.driver.conns[0].raise_integrity_on = "INSERT INTO users"
        with self.assertRaises(IntegrityError):
            self.db.execute("INSERT INTO users (email) VALUES (?)", ("dup",))

    def test_executescript_divide_statements(self):
        before = len(self.driver.conns[0].executed)
        self.db.executescript("CREATE TABLE a (x INT);\nCREATE TABLE b (y INT);")
        executed = self.driver.conns[0].executed[before:]
        self.assertEqual(len(executed), 2)

    def test_ddl_renderizado_roda_no_fake(self):
        self.db.executescript(render_ddl("postgres"))
        sqls = [s for s, _ in self.driver.conns[0].executed]
        self.assertTrue(any("GENERATED BY DEFAULT AS IDENTITY" in s for s in sqls))
        self.assertTrue(any("BYTEA" in s for s in sqls))

    def test_close_propaga(self):
        self.db.close()
        self.assertTrue(self.driver.conns[0].closed)


class TestDdlDialetos(unittest.TestCase):
    def test_postgres_sem_residuos_sqlite(self):
        ddl = render_ddl("postgres")
        self.assertIn("BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY", ddl)
        self.assertIn("BYTEA", ddl)
        self.assertNotIn("{PK_AUTO}", ddl)
        self.assertNotIn("{BLOB}", ddl)
        self.assertNotIn("AUTOINCREMENT", ddl)
        self.assertNotIn("PRAGMA", ddl)

    def test_sqlite_compativel(self):
        ddl = render_ddl("sqlite")
        self.assertIn("INTEGER PRIMARY KEY", ddl)
        self.assertIn("BLOB", ddl)
        self.assertNotIn("IDENTITY", ddl)
        self.assertNotIn("BYTEA", ddl)

    def test_dialeto_desconhecido_falha_alto(self):
        with self.assertRaises(KeyError):
            render_ddl("oracle")


class TestSqliteIntactoViaAdapter(unittest.TestCase):
    """O caminho SQLite (usado por TODOS os outros testes) segue exato."""

    def test_sqlite_roundtrip(self):
        db = connect(":memory:")
        self.assertEqual(db.dialect, "sqlite")
        db.executescript("CREATE TABLE t (id INTEGER PRIMARY KEY, nome TEXT)")
        new_id = insert_id(db, "INSERT INTO t (nome) VALUES (?)", ("ze",))
        self.assertEqual(new_id, 1)
        row = db.execute("SELECT * FROM t WHERE id = ?", (1,)).fetchone()
        self.assertEqual(row["nome"], "ze")
        with self.assertRaises(IntegrityError):
            db.execute("INSERT INTO t (id, nome) VALUES (?, ?)", (1, "dup"))
        db.close()


if __name__ == "__main__":
    unittest.main()


class TestSettingsDatabaseUrl(unittest.TestCase):
    def _env(self, **extra):
        base = {"SECRET_KEY": "s" * 48, "PEPPER": "p" * 48}
        base.update(extra)
        return base

    def test_sem_database_url_usa_sqlite(self):
        from app.config import load_settings
        s = load_settings(self._env(DATA_DIR="/data"))
        self.assertFalse(s.uses_postgres)
        self.assertTrue(s.db_target.endswith("bolao.db"))

    def test_database_url_normalizada(self):
        from app.config import load_settings
        s = load_settings(self._env(
            DATABASE_URL="postgres://u:p@supa:5432/db",
            PUBLIC_BASE_URL="https://app.example.com", COOKIE_SECURE="true"))
        self.assertTrue(s.uses_postgres)
        self.assertEqual(s.db_target, "postgresql://u:p@supa:5432/db")

    def test_database_url_invalida_derruba_boot(self):
        from app.config import load_settings
        with self.assertRaises(RuntimeError):
            load_settings(self._env(DATABASE_URL="mysql://nao-suportado"))

    def test_prod_exige_public_base_url(self):  # M3
        from app.config import load_settings
        with self.assertRaises(RuntimeError):
            load_settings(self._env(DATABASE_URL="postgres://u:p@supa:5432/db",
                                    COOKIE_SECURE="true"))

    def test_prod_rejeita_public_base_url_localhost(self):  # M3
        from app.config import load_settings
        with self.assertRaises(RuntimeError):
            load_settings(self._env(DATABASE_URL="postgres://u:p@supa:5432/db",
                                    PUBLIC_BASE_URL="http://localhost:8000",
                                    COOKIE_SECURE="true"))

    def test_prod_exige_cookie_secure(self):  # M3
        from app.config import load_settings
        with self.assertRaises(RuntimeError):
            load_settings(self._env(DATABASE_URL="postgres://u:p@supa:5432/db",
                                    PUBLIC_BASE_URL="https://app.example.com"))

    def test_prod_ok_com_envs_corretas(self):  # M3
        from app.config import load_settings
        s = load_settings(self._env(DATABASE_URL="postgres://u:p@supa:5432/db",
                                    PUBLIC_BASE_URL="https://app.example.com",
                                    COOKIE_SECURE="true"))
        self.assertTrue(s.cookie_secure)
        self.assertEqual(s.public_base_url, "https://app.example.com")
