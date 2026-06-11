from .conftest import csrf, register_user


def test_cookie_flags(client):
    email = register_user(client)["email"]
    client.post("/api/auth/logout", headers=csrf(client))
    resp = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Senha#Forte9"},
        headers=csrf(client),
    )
    assert resp.status_code == 200
    set_cookies = resp.headers.get_list("set-cookie")
    access = next(c for c in set_cookies if c.startswith("access_token="))
    refresh = next(c for c in set_cookies if c.startswith("refresh_token="))
    csrf_c = next(c for c in set_cookies if c.startswith("csrf_token="))
    for c in (access, refresh):
        assert "httponly" in c.lower()
        assert "samesite=lax" in c.lower()
    assert "httponly" not in csrf_c.lower()  # legível pelo JS (double-submit)
    assert "path=/api/auth" in refresh.lower()


def test_me_sem_cookie_401(client):
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401


def test_me_logado(client, user):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == user["email"]
    assert resp.json()["has_password"] is True


def test_refresh_rotaciona(client, user):
    old_refresh = client.cookies["refresh_token"]
    resp = client.post("/api/auth/refresh", headers=csrf(client))
    assert resp.status_code == 200
    assert client.cookies["refresh_token"] != old_refresh
    assert client.get("/api/auth/me").status_code == 200


def test_logout_revoga_e_limpa(client, user):
    client.post("/api/auth/logout", headers=csrf(client))
    assert client.get("/api/auth/me").status_code == 401


def test_csrf_obrigatorio_em_mutacao(client):
    client.get("/api/meta/config")
    resp = client.post(
        "/api/auth/register",
        json={"email": "x@y.zz", "password": "Senha#Forte9", "display_name": "X"},
    )  # sem header X-CSRF-Token
    assert resp.status_code == 403


def test_register_validacoes(client):
    bad = client.post(
        "/api/auth/register",
        json={"email": "sem-arroba", "password": "Senha#Forte9", "display_name": "X"},
        headers=csrf(client),
    )
    assert bad.status_code == 422
    weak = client.post(
        "/api/auth/register",
        json={"email": "w@y.zz", "password": "12345678", "display_name": "X"},
        headers=csrf(client),
    )
    assert weak.status_code == 422


def test_email_duplicado_409(client):
    info = register_user(client)
    client.post("/api/auth/logout", headers=csrf(client))
    resp = client.post(
        "/api/auth/register",
        json={"email": info["email"], "password": "Senha#Forte9",
              "display_name": "Dup"},
        headers=csrf(client),
    )
    assert resp.status_code == 409


def test_login_errado_mensagem_neutra(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "nope@test.dev", "password": "errada123"},
        headers=csrf(client),
    )
    assert resp.status_code == 401
    assert "incorretos" in resp.json()["detail"]


def test_rate_limit_login_429(app, client):
    limiter = app.state.limiter
    limiter.configure("login", 3, 60)
    limiter.reset("login")
    try:
        headers = csrf(client)
        status = [
            client.post(
                "/api/auth/login",
                json={"email": "brute@test.dev", "password": "errada123"},
                headers=headers,
            ).status_code
            for _ in range(4)
        ]
        assert status[:3] == [401, 401, 401]
        assert status[3] == 429
        r = client.post(
            "/api/auth/login",
            json={"email": "brute@test.dev", "password": "errada123"},
            headers=headers,
        )
        assert r.headers.get("Retry-After") is not None
    finally:
        limiter.configure("login", 1000, 60)
        limiter.reset("login")
