import unittest
import urllib.parse

from app.db.connection import connect
from app.db.repos import users as users_repo
from app.db.schema import init_db
from app.services.oauth_google import GoogleOAuth, OAuthError, login_or_link

from .settings_helper import make_settings

USERINFO = {
    "sub": "g-123", "email": "rafa@gmail.com", "email_verified": True,
    "name": "Rafaell Pipucos",
}


def make_oauth(post_resp=None, get_resp=None):
    calls = {}

    def fake_post(url, data):
        calls["post"] = (url, data)
        return post_resp if post_resp is not None else {"access_token": "tok-1"}

    def fake_get(url, bearer):
        calls["get"] = (url, bearer)
        return get_resp if get_resp is not None else dict(USERINFO)

    oauth = GoogleOAuth(
        client_id="cid", client_secret="sec",
        redirect_uri="http://testserver/api/oauth/google/callback",
        http_post=fake_post, http_get=fake_get,
    )
    return oauth, calls


class TestGoogleOAuth(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        init_db(self.conn)
        self.settings = make_settings()

    def tearDown(self):
        self.conn.close()

    def test_authorize_url(self):
        oauth, _ = make_oauth()
        url = oauth.authorize_url(state="st-abc")
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(parsed.netloc, "accounts.google.com")
        self.assertEqual(qs["state"], ["st-abc"])
        self.assertEqual(qs["response_type"], ["code"])
        self.assertIn("email", qs["scope"][0])

    def test_fetch_userinfo_fluxo(self):
        oauth, calls = make_oauth()
        info = oauth.fetch_userinfo("code-xyz")
        self.assertEqual(info["sub"], "g-123")
        self.assertEqual(calls["post"][1]["code"], "code-xyz")
        self.assertEqual(calls["get"][1], "tok-1")

    def test_token_sem_access_token(self):
        oauth, _ = make_oauth(post_resp={"error": "invalid_grant"})
        with self.assertRaises(OAuthError):
            oauth.fetch_userinfo("code")

    def test_cria_usuario_novo(self):
        uid = login_or_link(self.conn, self.settings, dict(USERINFO))
        user = users_repo.by_id(self.conn, uid)
        self.assertEqual(user["email"], "rafa@gmail.com")
        self.assertEqual(user["google_sub"], "g-123")
        self.assertIsNone(user["password_hash"])

    def test_idempotente_por_sub(self):
        uid1 = login_or_link(self.conn, self.settings, dict(USERINFO))
        uid2 = login_or_link(self.conn, self.settings, dict(USERINFO))
        self.assertEqual(uid1, uid2)

    def test_vincula_conta_existente_por_email(self):
        uid = users_repo.create(self.conn, "rafa@gmail.com", "Rafa", password_hash="h")
        linked = login_or_link(self.conn, self.settings, dict(USERINFO))
        self.assertEqual(linked, uid)
        self.assertEqual(users_repo.by_id(self.conn, uid)["google_sub"], "g-123")

    def test_email_nao_verificado_rejeitado(self):
        info = dict(USERINFO, email_verified=False)
        with self.assertRaises(OAuthError):
            login_or_link(self.conn, self.settings, info)

    def test_admin_email_vira_admin(self):
        info = dict(USERINFO, email="admin@bolao.test", sub="g-admin")
        uid = login_or_link(self.conn, self.settings, info)
        self.assertTrue(users_repo.by_id(self.conn, uid)["is_admin"])


if __name__ == "__main__":
    unittest.main()
