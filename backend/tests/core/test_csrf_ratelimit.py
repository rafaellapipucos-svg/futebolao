import unittest

from app.core.csrf import generate_token, validate
from app.core.ratelimit import RateLimiter, default_limiter


class TestCsrf(unittest.TestCase):
    def test_token_aleatorio_e_longo(self):
        a, b = generate_token(), generate_token()
        self.assertNotEqual(a, b)
        self.assertGreaterEqual(len(a), 40)

    def test_validacao(self):
        t = generate_token()
        self.assertTrue(validate(t, t))
        self.assertFalse(validate(t, t + "x"))
        self.assertFalse(validate(t, ""))
        self.assertFalse(validate("", t))
        self.assertFalse(validate("", ""))


class TestRateLimiter(unittest.TestCase):
    def test_estoura_no_limite_e_reabastece(self):
        rl = RateLimiter()
        rl.configure("login", 3, 60)
        now = 1000.0
        for i in range(3):
            ok, _ = rl.allow("login", "1.2.3.4", now=now + i)
            self.assertTrue(ok, i)
        ok, retry = rl.allow("login", "1.2.3.4", now=now + 3)
        self.assertFalse(ok)
        self.assertGreater(retry, 0)
        # 20s depois reabasteceu 1 token (3/60s)
        ok, _ = rl.allow("login", "1.2.3.4", now=now + 25)
        self.assertTrue(ok)

    def test_chaves_independentes(self):
        rl = RateLimiter()
        rl.configure("login", 1, 60)
        self.assertTrue(rl.allow("login", "ip-a", now=1.0)[0])
        self.assertFalse(rl.allow("login", "ip-a", now=1.1)[0])
        self.assertTrue(rl.allow("login", "ip-b", now=1.2)[0])

    def test_escopo_desconhecido_lanca(self):
        rl = RateLimiter()
        with self.assertRaises(KeyError):
            rl.allow("nao-existe", "k")

    def test_default_limiter_escopos(self):
        rl = default_limiter()
        for scope in ("login", "register", "refresh", "mutate", "global", "oauth"):
            self.assertTrue(rl.allow(scope, "x", now=1.0)[0], scope)


if __name__ == "__main__":
    unittest.main()
