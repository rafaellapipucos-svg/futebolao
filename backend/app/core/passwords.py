"""Hash de senhas: bcrypt(cost 12) sobre pré-hash HMAC-SHA256 com pepper.

O pré-hash resolve o limite de 72 bytes do bcrypt e adiciona um segredo de
servidor (pepper): vazamento do banco sozinho não permite ataque offline direto.
"""
from __future__ import annotations

import base64
import hashlib
import hmac

import bcrypt

BCRYPT_ROUNDS = 12

# Senhas proibidas óbvias (complementa as regras estruturais).
COMMON_PASSWORDS = {
    "12345678", "123456789", "1234567890", "password", "password1", "senha123",
    "12341234", "qwertyui", "11111111", "00000000", "abc12345", "futebol123",
}


class WeakPasswordError(ValueError):
    pass


def _prehash(password: str, pepper: str) -> bytes:
    digest = hmac.new(pepper.encode("utf-8"), password.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest)  # 44 bytes ASCII, sem NUL


def hash_password(password: str, pepper: str) -> str:
    return bcrypt.hashpw(_prehash(password, pepper), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(password: str, pepper: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password, pepper), stored_hash.encode("ascii"))
    except ValueError:
        # hash armazenado malformado — nunca autentica
        return False


# Hash dummy para equalizar o custo quando o e-mail não existe (anti-enumeração).
_DUMMY_HASH = bcrypt.hashpw(b"dummy-timing-equalizer", bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def dummy_verify(pepper: str) -> None:
    bcrypt.checkpw(_prehash("nope", pepper), _DUMMY_HASH.encode("ascii"))


def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise WeakPasswordError("senha deve ter pelo menos 8 caracteres")
    if len(password) > 128:
        raise WeakPasswordError("senha deve ter no máximo 128 caracteres")
    if password.isdigit():
        raise WeakPasswordError("senha não pode conter apenas números")
    if password.lower() in COMMON_PASSWORDS:
        raise WeakPasswordError("senha muito comum, escolha outra")
