"""JWT HS256 com stdlib (hmac/hashlib/base64). Compacto, estrito e testado.

Recusa: alg != HS256 (inclusive 'none'), assinatura invalida, exp ausente,
exp vencido (com leeway), typ inesperado, estrutura malformada.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional


class JwtError(ValueError):
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(data + padding)
    except Exception as exc:
        raise JwtError("base64url invalido") from exc


def _json_or_jwt_error(blob: bytes, what: str) -> Any:
    try:
        return json.loads(blob)
    except (ValueError, UnicodeDecodeError) as exc:
        raise JwtError(what + " invalido") from exc


def sign(payload: Dict[str, Any], key: str) -> str:
    if "exp" not in payload:
        raise JwtError("payload deve conter exp")
    header = _b64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = (header + "." + body).encode("ascii")
    sig = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return header + "." + body + "." + _b64url_encode(sig)


def verify(
    token: str,
    key: str,
    expected_typ: Optional[str] = None,
    leeway_seconds: int = 10,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise JwtError("estrutura invalida")
    header_b64, body_b64, sig_b64 = parts

    header = _json_or_jwt_error(_b64url_decode(header_b64), "header")
    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise JwtError("algoritmo nao permitido")

    signing_input = (header_b64 + "." + body_b64).encode("ascii")
    expected_sig = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_sig, _b64url_decode(sig_b64)):
        raise JwtError("assinatura invalida")

    payload = _json_or_jwt_error(_b64url_decode(body_b64), "payload")
    if not isinstance(payload, dict):
        raise JwtError("payload deve ser objeto")

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        raise JwtError("exp ausente")
    current = time.time() if now is None else now
    if current > exp + leeway_seconds:
        raise JwtError("token expirado")

    if expected_typ is not None and payload.get("typ") != expected_typ:
        raise JwtError("tipo de token inesperado")
    return payload
