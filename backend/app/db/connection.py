"""Conexao de banco com dois dialetos: SQLite (dev/testes) e PostgreSQL (prod).

A escolha e pelo alvo: caminho de arquivo/':memory:' -> sqlite3 (stdlib);
URL postgresql:// -> psycopg (v3, preferido) ou psycopg2 (fallback).
Os repositorios escrevem SQL com placeholders '?' — no Postgres o adapter
traduz para '%s'. Erros de integridade sao normalizados em IntegrityError.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional, Sequence, Union


class IntegrityError(Exception):
    """Violacao de UNIQUE/CHECK/FK — normalizada entre drivers."""


def _split_statements(script: str) -> list:
    """Divide DDL em statements por ';' FORA de literais string (B1).
    Robusto a ';' dentro de aspas simples (inclui o escape '' do SQL)."""
    stmts, buf, in_str, i = [], [], False, 0
    while i < len(script):
        c = script[i]
        if c == "'":
            buf.append(c)
            if in_str and i + 1 < len(script) and script[i + 1] == "'":
                buf.append("'")  # '' escapado dentro da string
                i += 2
                continue
            in_str = not in_str
        elif c == ";" and not in_str:
            stmts.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    stmts.append("".join(buf))
    return [s.strip() for s in stmts if s.strip()]


def _to_pg_placeholders(sql: str) -> str:
    """Traduz o paramstyle '?' (qmark) para '%s' do psycopg, FORA de literais
    string, e dobra '%' (psycopg processa %-formatting) — também só fora? Não:
    psycopg exige '%%' em QUALQUER posição. '?' dentro de aspas é preservado (B1)."""
    out, in_str, i = [], False, 0
    while i < len(sql):
        c = sql[i]
        if c == "'":
            out.append(c)
            if in_str and i + 1 < len(sql) and sql[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            in_str = not in_str
        elif c == "%":
            out.append("%%")  # psycopg faz %-format: literal '%' vira '%%'
        elif c == "?" and not in_str:
            out.append("%s")
        else:
            out.append(c)
        i += 1
    return "".join(out)


class Db:
    """Wrapper fino com API uniforme: execute/executescript/close + dialect."""

    def __init__(self, raw: Any, dialect: str, integrity_excs: tuple) -> None:
        self._raw = raw
        self.dialect = dialect  # 'sqlite' | 'postgres'
        self._integrity = integrity_excs

    def _translate(self, sql: str) -> str:
        if self.dialect == "postgres":
            return _to_pg_placeholders(sql)
        return sql

    def execute(self, sql: str, params: Sequence = ()) -> Any:
        try:
            return self._raw.execute(self._translate(sql), params)
        except self._integrity as exc:
            raise IntegrityError(str(exc)) from exc

    def executescript(self, script: str) -> None:
        for stmt in _split_statements(script):
            self.execute(stmt)

    def close(self) -> None:
        self._raw.close()


def _connect_sqlite(database: Union[str, Path]) -> Db:
    conn = sqlite3.connect(
        str(database),
        timeout=10.0,
        detect_types=0,
        isolation_level=None,  # autocommit; transacoes explicitas via tx()
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if str(database) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    return Db(conn, "sqlite", (sqlite3.IntegrityError,))


class _Psycopg2Conn:
    """Adapta psycopg2 (cursor-based) a interface conn.execute do psycopg 3.
    Fecha o cursor ANTERIOR a cada execute para não acumular cursores/portais
    abertos na conexão (B1) — só o último fica vivo (o chamador faz fetch nele)."""

    def __init__(self, conn: Any, cursor_factory: Any) -> None:
        self._conn = conn
        self._cursor_factory = cursor_factory
        self._last: Any = None

    def execute(self, sql: str, params: Sequence = ()) -> Any:
        if self._last is not None:
            self._last.close()
        cur = self._conn.cursor(cursor_factory=self._cursor_factory)
        cur.execute(sql, tuple(params))
        self._last = cur
        return cur

    def close(self) -> None:
        if self._last is not None:
            self._last.close()
        self._conn.close()


def _connect_postgres(url: str, driver: Optional[Any] = None) -> Db:
    if driver is not None:  # testes: driver fake injetado
        return Db(driver.connect(url), "postgres", (driver.IntegrityError,))
    try:
        import psycopg  # v3 — usado em producao

        conn = psycopg.connect(
            url,
            autocommit=True,            # transacoes explicitas via tx()
            prepare_threshold=None,     # PgBouncer/Supabase pooler: sem prepared stmts
            row_factory=psycopg.rows.dict_row,
        )
        return Db(conn, "postgres", (psycopg.IntegrityError,))
    except ImportError:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(url)
        conn.autocommit = True
        wrapped = _Psycopg2Conn(conn, psycopg2.extras.RealDictCursor)
        return Db(wrapped, "postgres", (psycopg2.IntegrityError,))


def is_postgres_target(target: Union[str, Path]) -> bool:
    return str(target).startswith(("postgresql://", "postgres://"))


def normalize_pg_url(url: str) -> str:
    """Supabase/Heroku usam postgres:// — drivers pedem postgresql://."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def connect(target: Union[str, Path], driver: Optional[Any] = None) -> Db:
    if is_postgres_target(target):
        return _connect_postgres(normalize_pg_url(str(target)), driver=driver)
    return _connect_sqlite(target)


def insert_id(db: Db, sql: str, params: Sequence = ()) -> int:
    """INSERT que retorna o id gerado, nos dois dialetos."""
    if db.dialect == "postgres":
        cur = db.execute(sql + " RETURNING id", params)
        row = cur.fetchone()
        return int(row["id"])
    cur = db.execute(sql, params)
    return int(cur.lastrowid)


@contextmanager
def tx(db: Db) -> Iterator[Db]:
    """Transacao explicita; lock imediato no SQLite, BEGIN padrao no Postgres."""
    db.execute("BEGIN IMMEDIATE" if db.dialect == "sqlite" else "BEGIN")
    try:
        yield db
    except BaseException:
        db.execute("ROLLBACK")
        raise
    else:
        db.execute("COMMIT")
