"""Configuracao via variaveis de ambiente (.env opcional). Sem fallbacks
silenciosos: segredos obrigatorios ausentes/fracos derrubam o boot.

Banco: DATABASE_URL presente -> PostgreSQL (Supabase/RDS/etc.);
ausente -> SQLite em DATA_DIR (dev local e testes).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set

from .db.connection import normalize_pg_url


def _load_dotenv(path: Path) -> None:
    """Parser .env minimalista (KEY=VALUE, # comentarios). Nao sobrescreve env."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    secret_key: str
    pepper: str
    data_dir: Path
    database_url: Optional[str]
    public_base_url: str
    admin_emails: Set[str]
    invite_code: Optional[str]
    google_client_id: Optional[str]
    google_client_secret: Optional[str]
    football_data_token: Optional[str]
    cookie_secure: bool

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def uses_postgres(self) -> bool:
        return self.database_url is not None

    @property
    def db_target(self) -> str:
        """Alvo de conexao: URL Postgres ou caminho do arquivo SQLite."""
        if self.database_url:
            return self.database_url
        return str(self.data_dir / "bolao.db")


def load_settings(env: Optional[dict] = None) -> Settings:
    if env is None:
        _load_dotenv(Path(".env"))
        env = dict(os.environ)

    secret_key = env.get("SECRET_KEY", "")
    pepper = env.get("PEPPER", "")
    if len(secret_key) < 32:
        raise RuntimeError(
            "SECRET_KEY ausente ou curta (>=32 chars). Gere com: "
            "python3 -c \"import secrets;print(secrets.token_urlsafe(48))\""
        )
    if len(pepper) < 32:
        raise RuntimeError("PEPPER ausente ou curta (>=32 chars). Gere como a SECRET_KEY.")

    database_url = env.get("DATABASE_URL", "").strip() or None
    if database_url:
        database_url = normalize_pg_url(database_url)
        if not database_url.startswith("postgresql://"):
            raise RuntimeError(
                "DATABASE_URL invalida: esperado postgresql://... (recebido inicio "
                f"'{database_url[:16]}...')"
            )

    data_dir = Path(env.get("DATA_DIR", "./data"))
    admin_emails = {
        e.strip().lower() for e in env.get("ADMIN_EMAILS", "").split(",") if e.strip()
    }
    return Settings(
        secret_key=secret_key,
        pepper=pepper,
        data_dir=data_dir,
        database_url=database_url,
        public_base_url=env.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/"),
        admin_emails=admin_emails,
        invite_code=env.get("INVITE_CODE") or None,
        google_client_id=env.get("GOOGLE_CLIENT_ID") or None,
        google_client_secret=env.get("GOOGLE_CLIENT_SECRET") or None,
        football_data_token=env.get("FOOTBALL_DATA_TOKEN") or None,
        cookie_secure=env.get("COOKIE_SECURE", "false").lower() in ("1", "true", "yes"),
    )
