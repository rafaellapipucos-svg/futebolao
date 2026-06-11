import base64
import json
import time
import unittest

from app.core.jwt_hs256 import JwtError, sign, verify

KEY = "k" * 48


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class TestJwt(unittest.TestCase):
    def test_roundtrip(self):
        now = int(time.time())
        token = sign({"sub": "7", "typ": "access", "exp": now + 60}, KEY)
        payload = verify(token, KEY, expected_typ="access")
        self.assertEqual(payload["sub"], "7")

    def test_expirado(self):
        token = sign({"sub": "7", "typ": "access", "exp": int(time.time()) - 100}, KEY)
        with self.assertRaises(JwtError):
            verify(token, KEY)

    def test_leeway(self):
        now = int(time.time())
        token = sign({"sub": "7", "typ": "access", "exp": now - 5}, KEY)
        verify(token, KEY, leeway_seconds=10)  # dentro do leeway
        with self.assertRaises(JwtError):
            verify(token, KEY, leeway_seconds=0)

    def test_typ_errado(self):
        token = sign({"sub": "7", "typ": "refresh", "exp": int(time.time()) + 60}, KEY)
        with self.assertRaises(JwtError):
            verify(token, KEY, expected_typ="access")

    def test_assinatura_adulterada(self):
        token = sign({"sub": "7", "typ": "access", "exp": int(time.time()) + 60}, KEY)
        h, b, s = token.split(".")
        body = json.loads(base64.urlsafe_b64decode(b + "=="))
        body["sub"] = "1"  # tenta virar outro usuário
        forged = f"{h}.{b64url(json.dumps(body).encode())}.{s}"
        with self.assertRaises(JwtError):
            verify(forged, KEY)

    def test_alg_none_rejeitado(self):
        now = int(time.time())
        header = b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
        body = b64url(json.dumps({"sub": "7", "exp": now + 60}).encode())
        for evil in (f"{header}.{body}.", f"{header}.{body}.AAAA"):
            with self.assertRaises(JwtError):
                verify(evil, KEY)

    def test_chave_errada(self):
        token = sign({"sub": "7", "typ": "access", "exp": int(time.time()) + 60}, KEY)
        with self.assertRaises(JwtError):
            verify(token, "outra" * 10)

    def test_estruturas_invalidas(self):
        for bad in ("", "a.b", "a.b.c.d", "!!!.@@@.###"):
            with self.assertRaises(JwtError):
                verify(bad, KEY)

    def test_exp_obrigatorio(self):
        with self.assertRaises(JwtError):
            sign({"sub": "7"}, KEY)


if __name__ == "__main__":
    unittest.main()
