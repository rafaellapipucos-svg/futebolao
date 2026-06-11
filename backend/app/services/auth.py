"""Registro, login e gestão de credenciais."""
from __future__ import annotations

import hmac
import re
from typing import Optional

from ..config import Settings
from ..core.passwords import (
    dummy_verify,
    hash_password,
    validate_password_strength,
    verify_password,
)
from ..db.repos import users as users_repo
from ..db.connection import Db, IntegrityError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(Exception):
    pass


class EmailTakenError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class InvalidInviteError(AuthError):
    pass


class ValidationError(AuthError):
    pass


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise ValidationError("e-mail inválido")
    return email


def normalize_display_name(name: str) -> str:
    name = " ".join(name.split())
    if not 1 <= len(name) <= 40:
        raise ValidationError("nome de exibição deve ter entre 1 e 40 caracteres")
    return name


def check_invite(settings: Settings, invite_code: Optional[str]) -> None:
    if settings.invite_code is None:
        return
    if not invite_code or not hmac.compare_digest(settings.invite_code, invite_code):
        raise InvalidInviteError("código de convite inválido")


def register(
    conn: Db,
    settings: Settings,
    email: str,
    password: str,
    display_name: str,
    invite_code: Optional[str] = None,
) -> int:
    email = normalize_email(email)
    display_name = normalize_display_name(display_name)
    check_invite(settings, invite_code)
    validate_password_strength(password)
    if users_repo.by_email(conn, email) is not None:
        raise EmailTakenError("e-mail já cadastrado")
    is_admin = email in settings.admin_emails
    try:
        return users_repo.create(
            conn, email, display_name,
            password_hash=hash_password(password, settings.pepper),
            is_admin=is_admin,
        )
    except IntegrityError as exc:
        raise EmailTakenError("e-mail já cadastrado") from exc


def login(conn: Db, settings: Settings, email: str, password: str):
    """Retorna a row do usuário; mensagem neutra e custo constante em falha."""
    try:
        email = normalize_email(email)
    except ValidationError:
        dummy_verify(settings.pepper)
        raise InvalidCredentialsError("e-mail ou senha incorretos")
    user = users_repo.by_email(conn, email)
    if user is None or user["password_hash"] is None:
        dummy_verify(settings.pepper)
        raise InvalidCredentialsError("e-mail ou senha incorretos")
    if not verify_password(password, settings.pepper, user["password_hash"]):
        raise InvalidCredentialsError("e-mail ou senha incorretos")
    _sync_admin_flag(conn, settings, user)
    return users_repo.by_id(conn, user["id"])


def change_password(
    conn: Db,
    settings: Settings,
    user_id: int,
    current_password: Optional[str],
    new_password: str,
) -> None:
    user = users_repo.by_id(conn, user_id)
    if user is None:
        raise InvalidCredentialsError("usuário não encontrado")
    if user["password_hash"] is not None:
        if not current_password or not verify_password(
            current_password, settings.pepper, user["password_hash"]
        ):
            raise InvalidCredentialsError("senha atual incorreta")
    validate_password_strength(new_password)
    users_repo.set_password(conn, user_id, hash_password(new_password, settings.pepper))


def _sync_admin_flag(conn: Db, settings: Settings, user) -> None:
    should_be_admin = user["email"] in settings.admin_emails
    if should_be_admin and not user["is_admin"]:
        users_repo.set_admin(conn, user["id"], True)
