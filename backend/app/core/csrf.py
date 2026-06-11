"""CSRF double-submit: cookie legível + header obrigatório em métodos mutantes.

Defesa em profundidade junto ao SameSite=Lax dos cookies de sessão.
"""
from __future__ import annotations

import hmac
import secrets


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def validate(cookie_value: str, header_value: str) -> bool:
    if not cookie_value or not header_value:
        return False
    return hmac.compare_digest(cookie_value, header_value)
