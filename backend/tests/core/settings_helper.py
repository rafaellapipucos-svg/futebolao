"""Settings de teste (segredos longos o suficiente, dirs temporários)."""
from __future__ import annotations

from pathlib import Path

from app.config import Settings


def make_settings(**overrides) -> Settings:
    base = dict(
        secret_key="s" * 48,
        pepper="p" * 48,
        data_dir=Path("/tmp/bolao-test"),
        database_url=None,
        public_base_url="http://testserver",
        admin_emails={"admin@bolao.test"},
        invite_code=None,
        google_client_id=None,
        google_client_secret=None,
        football_data_token=None,
        cookie_secure=False,
    )
    base.update(overrides)
    return Settings(**base)
