"""Integracao contra POSTGRES REAL (Supabase/local). Roda quando
TEST_DATABASE_URL esta definido; caso contrario, e pulada com aviso.

Como rodar:
  docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
ou
  TEST_DATABASE_URL=postgresql://... python -m pytest tests/pg -q

ATENCAO: a suite DERRUBA E RECRIA as tabelas do banco alvo. Use um banco
de teste (nunca o de producao com apostas reais).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

from app.db.connection import IntegrityError, connect, insert_id, tx
from app.db.repos import bets as bets_repo
from app.db.repos import matches as matches_repo
from app.db.repos import teams as teams_repo
from app.db.repos import users as users_repo
from app.db.schema import bump_data_version, get_data_version, init_db
from app.seed.loader import seed
from app.services.avatars import save_avatar, load_avatar
from app.services.betting import BetLockedError, place_bet
from app.services.leaderboard import leaderboard
from app.services.results import set_score
from app.domain.entities import MatchStatus

URL = os.environ.get("TEST_DATABASE_URL", "").strip()
pytestmark = pytest.mark.skipif(
    not URL, reason="TEST_DATABASE_URL nao definido — suite Postgres pulada"
)

TABLES = ["bets", "avatars", "refresh_tokens", "matches", "teams", "users", "meta"]


@pytest.fixture(scope="module")
def db():
    conn = connect(URL)
    assert conn.dialect == "postgres"
    for table in TABLES:  # banco de teste: comeca do zero, re-rodavel
        conn.execute(f_drop(table))
    init_db(conn)
    init_db(conn)  # idempotente
    seed(conn)
    yield conn
    conn.close()


def f_drop(table: str) -> str:
    # nomes vem de constante propria (sem input externo) — fora do scan por ser teste
    return "DROP TABLE IF EXISTS " + table + " CASCADE"


def png_bytes() -> bytes:
    import io
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (300, 200), (0, 200, 120)).save(buf, format="PNG")
    return buf.getvalue()


def test_seed_completo(db):
    assert teams_repo.count(db) == 48
    assert matches_repo.count(db) == 104
    m1 = matches_repo.by_id(db, 1)
    teams = teams_repo.all_teams(db)
    assert teams[m1.home_team_id].code == "MEX"
    assert m1.kickoff_utc == datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)
    seed(db)  # reseed idempotente
    assert matches_repo.count(db) == 104


def test_insert_id_returning_e_unique(db):
    uid = users_repo.create(db, "pg@test.dev", "PG User", password_hash="h")
    assert isinstance(uid, int) and uid >= 1
    uid2 = users_repo.create(db, "pg2@test.dev", "PG User 2")
    assert uid2 > uid
    with pytest.raises(IntegrityError):
        users_repo.create(db, "pg@test.dev", "Duplicado")


def test_check_constraint_de_gols(db):
    uid = users_repo.create(db, "check@test.dev", "Check")
    with pytest.raises(IntegrityError):
        bets_repo.upsert(db, uid, 1, 99, 0)


def test_tx_rollback_real(db):
    uid = users_repo.create(db, "tx@test.dev", "Tx")
    with pytest.raises(RuntimeError):
        with tx(db):
            users_repo.set_display_name(db, uid, "Mudou")
            raise RuntimeError("boom")
    assert users_repo.by_id(db, uid)["display_name"] == "Tx"


def test_trava_de_aposta_no_postgres(db):
    uid = users_repo.create(db, "bet@test.dev", "Bet")
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    db.execute("UPDATE matches SET kickoff_utc = ? WHERE id = ?", (future, 2))
    bet = place_bet(db, uid, 2, 2, 1)
    assert (bet.home_goals, bet.away_goals) == (2, 1)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    db.execute("UPDATE matches SET kickoff_utc = ? WHERE id = ?", (past, 2))
    with pytest.raises(BetLockedError):
        place_bet(db, uid, 2, 0, 0)


def test_resultado_e_leaderboard(db):
    from app.services import leaderboard as lb_mod
    lb_mod._cache.clear()
    uid = users_repo.create(db, "lb@test.dev", "Cravador")
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    db.execute("UPDATE matches SET kickoff_utc = ? WHERE id = ?", (future, 3))
    place_bet(db, uid, 3, 2, 1)
    set_score(db, 3, 2, 1, MatchStatus.FINISHED)
    rows = leaderboard(db, include_live=True)
    me = next(r for r in rows if r["display_name"] == "Cravador")
    assert me["total"] == 3 and me["exact_hits"] == 1


def test_avatar_bytea_roundtrip(db):
    uid = users_repo.create(db, "ava@test.dev", "Ava")
    version = save_avatar(db, uid, png_bytes())
    assert version == 1
    stored = load_avatar(db, uid)
    assert isinstance(stored, bytes) and stored[:2] == b"\xff\xd8"  # JPEG magic


def test_data_version_bump(db):
    v0 = get_data_version(db)
    assert bump_data_version(db) == v0 + 1
