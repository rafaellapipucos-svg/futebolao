"""Processamento seguro de foto de perfil — armazenada NO BANCO.

Qualquer upload e DECODIFICADO e RECODIFICADO via Pillow (JPEG 256px, sem
metadata) — payloads maliciosos, EXIF e formatos disfarcados morrem aqui.
Bytes vao para a tabela avatars: sobrevivem a deploys em disco efemero (Render).
"""
from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError

from ..db.connection import Db
from ..db.repos import avatars as avatars_repo
from ..db.repos import users as users_repo

MAX_BYTES = 2 * 1024 * 1024
TARGET_SIZE = 256
JPEG_QUALITY = 85


class AvatarError(Exception):
    pass


def process_image(data: bytes) -> bytes:
    if not data:
        raise AvatarError("arquivo vazio")
    if len(data) > MAX_BYTES:
        raise AvatarError("imagem deve ter no maximo 2MB")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()  # estrutura integra?
        with Image.open(io.BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            img.thumbnail((TARGET_SIZE, TARGET_SIZE))
            side = min(img.size)
            left = (img.width - side) // 2
            top = (img.height - side) // 2
            img = img.crop((left, top, left + side, top + side))
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return out.getvalue()
    except UnidentifiedImageError as exc:
        raise AvatarError("arquivo nao e uma imagem valida") from exc
    except OSError as exc:
        raise AvatarError("imagem corrompida ou formato nao suportado") from exc


def save_avatar(conn: Db, user_id: int, data: bytes) -> int:
    """Processa e grava no banco. Retorna a nova versao (cache-busting)."""
    processed = process_image(data)
    avatars_repo.set_bytes(conn, user_id, processed)
    return users_repo.bump_avatar(conn, user_id)


def load_avatar(conn: Db, user_id: int):
    return avatars_repo.get_bytes(conn, user_id)
