import io

from PIL import Image

from .conftest import csrf


def _png(size=(400, 300)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (10, 200, 120)).save(buf, format="PNG")
    return buf.getvalue()


def test_headers_de_seguranca_em_todas_as_rotas(client):
    for path in ("/", "/api/health", "/api/meta/config", "/rota/desconhecida"):
        resp = client.get(path)
        assert resp.headers.get("X-Content-Type-Options") == "nosniff", path
        assert "default-src 'self'" in resp.headers.get("Content-Security-Policy", ""), path
        assert resp.headers.get("Referrer-Policy"), path


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_spa_fallback_serve_index(client):
    resp = client.get("/qualquer/coisa")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<div id=\"app\">" in resp.text


def test_estaticos_servidos(client):
    assert client.get("/css/tokens.css").status_code == 200
    assert client.get("/js/main.js").status_code == 200
    index = client.get("/")
    assert index.status_code == 200


def test_avatar_404_e_upload(client, user):
    assert client.get("/u/avatars/999999.jpg").status_code == 404
    assert client.get("/u/avatars/../../etc/passwd").status_code in (404, 422)
    resp = client.post(
        "/api/profile/avatar",
        files={"file": ("foto.png", _png(), "image/png")},
        headers=csrf(client),
    )
    assert resp.status_code == 200, resp.text
    url = resp.json()["avatar_url"]
    img = client.get(url.split("?")[0])
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/jpeg"


def test_avatar_nao_imagem_415(client, user):
    resp = client.post(
        "/api/profile/avatar",
        files={"file": ("x.txt", b"isto nao e imagem", "text/plain")},
        headers=csrf(client),
    )
    assert resp.status_code == 415


def test_avatar_muito_grande_413(client, user):
    blob = b"\x89PNG" + b"0" * (2 * 1024 * 1024 + 10)
    resp = client.post(
        "/api/profile/avatar",
        files={"file": ("big.png", blob, "image/png")},
        headers=csrf(client),
    )
    assert resp.status_code == 413


def test_perfil_nome_e_senha(client, user):
    headers = csrf(client)
    resp = client.patch("/api/profile", json={"display_name": "  Novo   Nome "},
                        headers=headers)
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Novo Nome"
    bad = client.post(
        "/api/profile/password",
        json={"current_password": "errada123", "new_password": "Nova#Senha9"},
        headers=headers,
    )
    assert bad.status_code == 403
    ok = client.post(
        "/api/profile/password",
        json={"current_password": "Senha#Forte9", "new_password": "Nova#Senha9"},
        headers=headers,
    )
    assert ok.status_code == 200


def test_sse_responde_event_stream(client):
    with client.stream("GET", "/api/live/sse") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        first = next(resp.iter_lines())
        assert first.startswith("retry:")


def test_oauth_start_sem_config_503(client):
    resp = client.get("/api/oauth/google/start", follow_redirects=False)
    assert resp.status_code == 503


def test_leaderboard_e_bracket_autenticados(client, user):
    lb = client.get("/api/leaderboard")
    assert lb.status_code == 200
    assert any(r["is_me"] for r in lb.json()["leaderboard"])
    br = client.get("/api/bracket")
    assert br.status_code == 200
    assert len(br.json()["matches"]) == 32
