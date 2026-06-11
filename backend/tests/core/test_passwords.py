import unittest

from app.core.passwords import (
    WeakPasswordError,
    hash_password,
    validate_password_strength,
    verify_password,
)

PEPPER = "p" * 48


class TestPasswords(unittest.TestCase):
    def test_hash_e_verify(self):
        h = hash_password("Corinthians2026!", PEPPER)
        self.assertNotIn("Corinthians", h)
        self.assertTrue(verify_password("Corinthians2026!", PEPPER, h))
        self.assertFalse(verify_password("errada", PEPPER, h))

    def test_pepper_errado_falha(self):
        h = hash_password("Corinthians2026!", PEPPER)
        self.assertFalse(verify_password("Corinthians2026!", "x" * 48, h))

    def test_senha_longa_acima_de_72_bytes(self):
        pw = "ç" * 100  # >72 bytes em utf-8; pré-hash resolve
        h = hash_password(pw, PEPPER)
        self.assertTrue(verify_password(pw, PEPPER, h))
        self.assertFalse(verify_password("ç" * 99, PEPPER, h))

    def test_hash_malformado_nunca_autentica(self):
        self.assertFalse(verify_password("x", PEPPER, "nao-e-bcrypt"))

    def test_politica_de_forca(self):
        for weak in ("curta1", "12345678", "123456789012", "password", "senha123"):
            with self.assertRaises(WeakPasswordError, msg=weak):
                validate_password_strength(weak)
        validate_password_strength("Bolao#Copa26")
        with self.assertRaises(WeakPasswordError):
            validate_password_strength("x" * 129)


if __name__ == "__main__":
    unittest.main()
