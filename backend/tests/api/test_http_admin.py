from .conftest import LOCKED_MATCH, csrf


def test_nao_admin_403(client, user):
    resp = client.post(
        f"/api/admin/matches/{LOCKED_MATCH}/score",
        json={"home_score": 1, "away_score": 0, "status": "live"},
        headers=csrf(client),
    )
    assert resp.status_code == 403


def test_admin_score_e_versao(admin_client):
    v0 = admin_client.get("/api/live/version").json()["v"]
    resp = admin_client.post(
        f"/api/admin/matches/{LOCKED_MATCH}/score",
        json={"home_score": 1, "away_score": 0, "status": "live", "minute": 12},
        headers=csrf(admin_client),
    )
    assert resp.status_code == 200, resp.text
    v1 = admin_client.get("/api/live/version").json()["v"]
    assert v1 == v0 + 1
    standings = admin_client.get("/api/standings").json()["groups"]
    flat = [r for g in standings for r in g["rows"]]
    assert any(r["live"] and r["points"] == 3 for r in flat)


def test_admin_transicao_invalida_422(admin_client):
    headers = csrf(admin_client)
    admin_client.post(
        f"/api/admin/matches/{LOCKED_MATCH}/score",
        json={"home_score": 2, "away_score": 0, "status": "finished"},
        headers=headers,
    )
    resp = admin_client.post(
        f"/api/admin/matches/{LOCKED_MATCH}/score",
        json={"home_score": 0, "away_score": 0, "status": "live"},
        headers=headers,
    )
    assert resp.status_code == 422
    forced = admin_client.post(
        f"/api/admin/matches/{LOCKED_MATCH}/score",
        json={"home_score": 0, "away_score": 0, "status": "live", "force": True},
        headers=headers,
    )
    assert forced.status_code == 200


def test_admin_sync_sem_token_503(admin_client):
    resp = admin_client.post("/api/admin/sync", headers=csrf(admin_client))
    assert resp.status_code == 503


def test_admin_lista_usuarios(admin_client):
    resp = admin_client.get("/api/admin/users")
    assert resp.status_code == 200
    assert any(u["email"] == "admin@test.dev" for u in resp.json()["users"])


def test_admin_recompute(admin_client):
    resp = admin_client.post("/api/admin/recompute", headers=csrf(admin_client))
    assert resp.status_code == 200
