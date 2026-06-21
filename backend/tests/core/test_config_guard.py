"""Guard de boot: producao em disco efemero (Cloud Run) exige DATABASE_URL.

Sem isso o SQLite local some a cada deploy/cold start — zera contas, apostas e
sessoes (todo mundo reloga). Ver D025 e incidente I017 no CONTINUITY.md.
"""
from __future__ import annotations

import unittest

from app.config import load_settings

BASE = {"SECRET_KEY": "s" * 48, "PEPPER": "p" * 48}
PG = "postgresql://u:p@host:5432/db"


class EphemeralPlatformGuardTest(unittest.TestCase):
    def test_cloud_run_sem_database_url_falha(self):
        with self.assertRaises(RuntimeError) as ctx:
            load_settings({**BASE, "K_SERVICE": "futebolao"})
        self.assertIn("DATABASE_URL", str(ctx.exception))

    def test_cloud_run_com_database_url_ok(self):
        s = load_settings({
            **BASE, "K_SERVICE": "futebolao", "DATABASE_URL": PG,
            "PUBLIC_BASE_URL": "https://futebolao.run.app", "COOKIE_SECURE": "true",
        })
        self.assertTrue(s.uses_postgres)

    def test_dev_local_sem_plataforma_ok(self):
        self.assertFalse(load_settings({**BASE}).uses_postgres)

    def test_escape_hatch_explicito_ok(self):
        s = load_settings({**BASE, "K_SERVICE": "x", "ALLOW_EPHEMERAL_DB": "true"})
        self.assertFalse(s.uses_postgres)


if __name__ == "__main__":
    unittest.main()
