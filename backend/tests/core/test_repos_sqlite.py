import ast
import unittest
from pathlib import Path

from app.db.connection import Db, IntegrityError, connect, tx
from app.db.repos import bets as bets_repo
from app.db.repos import matches as matches_repo
from app.db.repos import teams as teams_repo
from app.db.repos import tokens as tokens_repo
from app.db.repos import users as users_repo
from app.db.schema import bump_data_version, get_data_version, init_db

APP_DIR = Path(__file__).resolve().parents[2] / "app"


def fresh_db() -> Db:
    conn = connect(":memory:")
    init_db(conn)
    return conn


class TestRepos(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()

    def tearDown(self):
        self.conn.close()

    def test_users_crud_e_unique_email(self):
        uid = users_repo.create(self.conn, "a@b.c", "Alice", password_hash="h")
        self.assertEqual(users_repo.by_id(self.conn, uid)["email"], "a@b.c")
        with self.assertRaises(IntegrityError):
            users_repo.create(self.conn, "a@b.c", "Outra")
        users_repo.set_display_name(self.conn, uid, "Alicia")
        self.assertEqual(users_repo.by_email(self.conn, "a@b.c")["display_name"], "Alicia")

    def test_bets_unique_user_match_e_check(self):
        uid = users_repo.create(self.conn, "a@b.c", "Alice")
        teams_repo.upsert(self.conn, "BRA", "Brasil", "🇧🇷", "C")
        tid = teams_repo.by_code(self.conn, "BRA").id
        matches_repo.upsert_fixture(
            self.conn, 1, "GROUP", "C", "2026-06-13T22:00:00+00:00", "X", "BRA", "MAR", tid, tid,
        )
        b1 = bets_repo.upsert(self.conn, uid, 1, 2, 1)
        b2 = bets_repo.upsert(self.conn, uid, 1, 3, 0)  # edita, não duplica
        self.assertEqual(b1.id, b2.id)
        self.assertEqual((b2.home_goals, b2.away_goals), (3, 0))
        self.assertEqual(len(bets_repo.for_user(self.conn, uid)), 1)
        with self.assertRaises(IntegrityError):
            bets_repo.upsert(self.conn, uid, 1, 99, 0)  # CHECK 0..20

    def test_fk_on(self):
        with self.assertRaises(IntegrityError):
            bets_repo.upsert(self.conn, 999, 999, 1, 1)

    def test_tx_rollback(self):
        uid = users_repo.create(self.conn, "a@b.c", "Alice")
        try:
            with tx(self.conn):
                users_repo.set_display_name(self.conn, uid, "Mudou")
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        self.assertEqual(users_repo.by_id(self.conn, uid)["display_name"], "Alice")

    def test_data_version(self):
        v0 = get_data_version(self.conn)
        v1 = bump_data_version(self.conn)
        self.assertEqual(v1, v0 + 1)

    def test_tokens_lifecycle(self):
        from datetime import datetime, timedelta, timezone
        uid = users_repo.create(self.conn, "a@b.c", "Alice")
        exp = datetime.now(timezone.utc) + timedelta(days=1)
        tokens_repo.insert(self.conn, "jti1", uid, exp)
        self.assertTrue(tokens_repo.is_active(self.conn, "jti1"))
        tokens_repo.revoke(self.conn, "jti1")
        self.assertFalse(tokens_repo.is_active(self.conn, "jti1"))
        past = datetime.now(timezone.utc) - timedelta(days=1)
        tokens_repo.insert(self.conn, "jti2", uid, past)
        self.assertFalse(tokens_repo.is_active(self.conn, "jti2"))
        self.assertEqual(tokens_repo.purge_expired(self.conn), 1)


class TestNoSqlInterpolation(unittest.TestCase):
    """Garante que NENHUMA chamada execute() usa f-string/format/concat/%."""

    def test_scan_estatico(self):
        offenders = []
        for py in APP_DIR.rglob("*.py"):
            if py.name == "connection.py":
                continue  # adapter: unico concat e o sufixo estatico ' RETURNING id'
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = getattr(func, "attr", getattr(func, "id", ""))
                if name not in {"execute", "executemany", "executescript"}:
                    continue
                if not node.args:
                    continue
                sql = node.args[0]
                if isinstance(sql, ast.JoinedStr):
                    offenders.append(f"{py.name}:{node.lineno} f-string em SQL")
                if isinstance(sql, ast.BinOp):
                    offenders.append(f"{py.name}:{node.lineno} concat/% em SQL")
                if (
                    isinstance(sql, ast.Call)
                    and getattr(sql.func, "attr", "") == "format"
                ):
                    offenders.append(f"{py.name}:{node.lineno} .format em SQL")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
