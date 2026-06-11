from .conftest import LOCKED_MATCH, OPEN_MATCH, csrf


def test_apostar_e_editar_antes_do_kickoff(client, user):
    headers = csrf(client)
    r1 = client.put(f"/api/bets/{OPEN_MATCH}",
                    json={"home_goals": 2, "away_goals": 1}, headers=headers)
    assert r1.status_code == 200, r1.text
    r2 = client.put(f"/api/bets/{OPEN_MATCH}",
                    json={"home_goals": 0, "away_goals": 0}, headers=headers)
    assert r2.status_code == 200
    mine = client.get("/api/bets/mine").json()["bets"]
    mine_match = next(b for b in mine if b["match_id"] == OPEN_MATCH)
    assert (mine_match["home_goals"], mine_match["away_goals"]) == (0, 0)


def test_aposta_apos_kickoff_409(client, user):
    resp = client.put(f"/api/bets/{LOCKED_MATCH}",
                      json={"home_goals": 1, "away_goals": 0}, headers=csrf(client))
    assert resp.status_code == 409
    assert "apito" in resp.json()["detail"] or "iniciada" in resp.json()["detail"]


def test_aposta_em_mata_mata_sem_times_409(client, user):
    resp = client.put("/api/bets/73",
                      json={"home_goals": 1, "away_goals": 0}, headers=csrf(client))
    assert resp.status_code == 409
    assert "definido" in resp.json()["detail"]


def test_payload_invalido_422(client, user):
    headers = csrf(client)
    for payload in ({"home_goals": -1, "away_goals": 0},
                    {"home_goals": 21, "away_goals": 0},
                    {"home_goals": "x", "away_goals": 0},
                    {"away_goals": 0}):
        resp = client.put(f"/api/bets/{OPEN_MATCH}", json=payload, headers=headers)
        assert resp.status_code == 422, payload


def test_sem_auth_401(client):
    client.cookies.clear()
    client.get("/api/meta/config")
    resp = client.put(f"/api/bets/{OPEN_MATCH}",
                      json={"home_goals": 1, "away_goals": 0}, headers=csrf(client))
    assert resp.status_code == 401


def test_sem_csrf_403(client, user):
    resp = client.put(f"/api/bets/{OPEN_MATCH}",
                      json={"home_goals": 1, "away_goals": 0})
    assert resp.status_code == 403


def test_matches_lista_com_minha_aposta(client, user):
    client.put(f"/api/bets/{OPEN_MATCH}",
               json={"home_goals": 3, "away_goals": 1}, headers=csrf(client))
    data = client.get("/api/matches").json()["matches"]
    assert len(data) == 104
    m = next(x for x in data if x["id"] == OPEN_MATCH)
    assert m["my_bet"] == {"home_goals": 3, "away_goals": 1}
    assert m["bet_open"] is True
    locked = next(x for x in data if x["id"] == LOCKED_MATCH)
    assert locked["bet_open"] is False
    assert m["group"] is not None  # fase de grupos informa o grupo
