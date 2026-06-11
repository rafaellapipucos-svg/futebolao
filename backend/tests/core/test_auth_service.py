import unittest

from app.db.connection import connect
from app.db.repos import users as users_repo
from app.db.schema import init_db
from app.services import auth

from .settings_helper import make_settings


class TestAuthService(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        init_db(self.conn)
        self.settings = make_settings()

    def tearDown(self):
        self.conn.close()

    def test_register_e_login(self):
        uid = auth.register(
            self.conn, self.settings, "  Rafa@Email.COM ", "Bolao#Copa26", "Rafa"
        )
        user = users_repo.by_id(self.conn, uid)
        self.assertEqual(user["email"], "rafa@email.com")  # normalizado
        logged = auth.login(self.conn, self.settings, "rafa@email.com", "Bolao#Copa26")
        self.assertEqual(logged["id"], uid)

    def test_login_senha_errada_mensagem_neutra(self):
        auth.register(self.conn, self.settings, "a@b.co", "Bolao#Copa26", "A")
        for email, pw in (("a@b.co", "errada123"), ("naoexiste@b.co", "qualquer1")):
            with self.assertRaises(auth.InvalidCredentialsError) as ctx:
                auth.login(self.conn, self.settings, email, pw)
            self.assertEqual(str(ctx.exception), "e-mail ou senha incorretos")

    def test_email_duplicado(self):
        auth.register(self.conn, self.settings, "a@b.co", "Bolao#Copa26", "A")
        with self.assertRaises(auth.EmailTakenError):
            auth.register(self.conn, self.settings, "A@B.CO", "Outra#Senha9", "B")

    def test_invite_obrigatorio_quando_configurado(self):
        settings = make_settings(invite_code="COPA-2026")
        with self.assertRaises(auth.InvalidInviteError):
            auth.register(settings=settings, conn=self.conn, email="a@b.co",
                          password="Bolao#Copa26", display_name="A", invite_code="errado")
        uid = auth.register(self.conn, settings, "a@b.co", "Bolao#Copa26", "A",
                            invite_code="COPA-2026")
        self.assertIsInstance(uid, int)

    def test_admin_via_lista(self):
        uid = auth.register(
            self.conn, self.settings, "admin@bolao.test", "Bolao#Copa26", "Admin"
        )
        self.assertTrue(users_repo.by_id(self.conn, uid)["is_admin"])
        uid2 = auth.register(self.conn, self.settings, "x@y.zz", "Bolao#Copa26", "X")
        self.assertFalse(users_repo.by_id(self.conn, uid2)["is_admin"])

    def test_change_password(self):
        uid = auth.register(self.conn, self.settings, "a@b.co", "Bolao#Copa26", "A")
        with self.assertRaises(auth.InvalidCredentialsError):
            auth.change_password(self.conn, self.settings, uid, "errada", "Nova#Senha9")
        auth.change_password(self.conn, self.settings, uid, "Bolao#Copa26", "Nova#Senha9")
        auth.login(self.conn, self.settings, "a@b.co", "Nova#Senha9")

    def test_oauth_only_define_senha_sem_atual(self):
        uid = users_repo.create(self.conn, "g@oogle.co", "G", password_hash=None,
                                google_sub="sub1")
        auth.change_password(self.conn, self.settings, uid, None, "Nova#Senha9")
        auth.login(self.conn, self.settings, "g@oogle.co", "Nova#Senha9")

    def test_validacoes(self):
        with self.assertRaises(auth.ValidationError):
            auth.register(self.conn, self.settings, "sem-arroba", "Bolao#Copa26", "A")
        with self.assertRaises(auth.ValidationError):
            auth.register(self.conn, self.settings, "a@b.co", "Bolao#Copa26", "")


if __name__ == "__main__":
    unittest.main()
