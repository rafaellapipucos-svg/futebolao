"""Fixtures pytest da camada HTTP (rodam no build do Docker / máquina local).

Independente de relógio: ajusta kickoffs de jogos-fixture para o futuro/passado
relativos a AGORA, para a suite passar em qualquer data.
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

TMP = tempfile.mkdtemp(prefix="bolao-api-tests-")
os.environ.update({
    "SECRET_KEY": "s" * 48,
    "PEPPER": "p" * 48,
    "DATA_DIR": TMP,
    "ADMIN_EMAILS": "admin@test.dev",
    "COOKIE_SECURE": "false",
    "PUBLIC_BASE_URL": "http://testserver",
})

from fastapi.testclient import TestClient  # noqa: E402

from app.db.connection import connect  # noqa: E402
from app.main import create_app  # noqa: E402

OPEN_MATCH = 1     # kickoff movido para +2 dias (aposta aberta)
LOCKED_MATCH = 2   # kickoff movido para -1 hora (aposta travada)


@pytest.fixture(scope="session")
def app():
    application = create_app()
    # Limites generosos por padrão (testes específicos apertam e restauram)
    for scope in ("login", "register", "refresh", "mutate", "global", "oauth"):
        application.state.limiter.configure(scope, 1000, 60)
    conn = connect(Path(TMP) / "bolao.db")
    now = datetime.now(timezone.utc)
    conn.execute(
        "UPDATE matches SET kickoff_utc = ? WHERE id = ?",
        ((now + timedelta(days=2)).isoformat(), OPEN_MATCH),
    )
    conn.execute(
        "UPDATE matches SET kickoff_utc = ? WHERE id = ?",
        ((now - timedelta(hours=1)).isoformat(), LOCKED_MATCH),
    )
    conn.close()
    return application


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c


def csrf(client: TestClient) -> dict:
    """Garante cookie CSRF e retorna o header para métodos mutantes."""
    if "csrf_token" not in client.cookies:
        client.get("/api/meta/config")
    return {"X-CSRF-Token": client.cookies["csrf_token"]}


_counter = {"n": 0}


def register_user(client: TestClient, email=None, password="Senha#Forte9",
                  name=None) -> dict:
    _counter["n"] += 1
    email = email or f"user{_counter['n']}@test.dev"
    name = name or f"User {_counter['n']}"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": name},
        headers=csrf(client),
    )
    assert resp.status_code == 201, resp.text
    return {"email": email, "password": password, **resp.json()}


@pytest.fixture()
def user(client):
    return register_user(client)


@pytest.fixture()
def admin_client(app):
    with TestClient(app) as c:
        try:
            register_user(c, email="admin@test.dev", name="Admin")
        except AssertionError:
            login = c.post(
                "/api/auth/login",
                json={"email": "admin@test.dev", "password": "Senha#Forte9"},
                headers=csrf(c),
            )
            assert login.status_code == 200, login.text
        yield c
