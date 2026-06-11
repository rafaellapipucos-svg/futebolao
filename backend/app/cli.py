"""CLI administrativa: python -m app.cli <comando>

Comandos: seed | create-admin | reset-password | sync | recompute
"""
from __future__ import annotations

import argparse
import getpass
import sys

from .config import load_settings
from .db.connection import connect
from .db.schema import bump_data_version, init_db
from .seed.loader import seed as run_seed


def _conn(settings):
    if not settings.uses_postgres:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(settings.db_target)
    init_db(conn)
    return conn


def cmd_seed(settings, _args) -> int:
    conn = _conn(settings)
    info = run_seed(conn)
    print(f"seed ok: {info['teams']} times, {info['matches']} jogos")
    return 0


def cmd_create_admin(settings, args) -> int:
    from .db.repos import users as users_repo
    from .services import auth

    conn = _conn(settings)
    password = args.password or getpass.getpass("senha do admin: ")
    uid = auth.register(conn, settings, args.email, password, args.name)
    users_repo.set_admin(conn, uid, True)
    print(f"admin criado: {args.email} (id {uid})")
    return 0


def cmd_reset_password(settings, args) -> int:
    from .core.passwords import hash_password, validate_password_strength
    from .db.repos import tokens as tokens_repo
    from .db.repos import users as users_repo

    conn = _conn(settings)
    user = users_repo.by_email(conn, args.email.strip().lower())
    if user is None:
        print("usuário não encontrado", file=sys.stderr)
        return 1
    password = args.password or getpass.getpass("nova senha: ")
    validate_password_strength(password)
    users_repo.set_password(conn, user["id"], hash_password(password, settings.pepper))
    tokens_repo.revoke_all_for_user(conn, user["id"])
    print("senha redefinida e sessões revogadas")
    return 0


def cmd_sync(settings, _args) -> int:
    from .providers.football_data import FootballDataProvider
    from .providers.sync import apply_updates

    if not settings.football_data_token:
        print("FOOTBALL_DATA_TOKEN não configurado", file=sys.stderr)
        return 1
    conn = _conn(settings)
    provider = FootballDataProvider(settings.football_data_token)
    changed = apply_updates(conn, provider.fetch())
    print(f"sync ok: {changed} jogos atualizados")
    return 0


def cmd_recompute(settings, _args) -> int:
    from .services.bracket_svc import persist_resolutions

    conn = _conn(settings)
    changed = persist_resolutions(conn)
    bump_data_version(conn)
    print(f"recompute ok: {changed} confrontos resolvidos")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed")
    p_admin = sub.add_parser("create-admin")
    p_admin.add_argument("email")
    p_admin.add_argument("name")
    p_admin.add_argument("--password")
    p_reset = sub.add_parser("reset-password")
    p_reset.add_argument("email")
    p_reset.add_argument("--password")
    sub.add_parser("sync")
    sub.add_parser("recompute")
    args = parser.parse_args(argv)

    settings = load_settings()
    handlers = {
        "seed": cmd_seed,
        "create-admin": cmd_create_admin,
        "reset-password": cmd_reset_password,
        "sync": cmd_sync,
        "recompute": cmd_recompute,
    }
    return handlers[args.cmd](settings, args)


if __name__ == "__main__":
    raise SystemExit(main())
