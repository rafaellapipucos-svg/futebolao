"""Perfil: nome, senha, avatar."""
from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, Request

from ..core.passwords import WeakPasswordError
from ..db.repos import users as users_repo
from ..services import auth as auth_svc
from ..services.avatars import MAX_BYTES, AvatarError, save_avatar
from .deps import get_current_user, get_db, get_settings, rate_limit, require_csrf, user_payload
from .schemas import ChangePasswordIn, DisplayNameIn
from ..db.connection import Db

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
def get_profile(user=Depends(get_current_user)):
    return user_payload(user)


@router.patch("", dependencies=[Depends(rate_limit("mutate")), Depends(require_csrf)])
def update_display_name(
    body: DisplayNameIn,
    conn: Db = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        name = auth_svc.normalize_display_name(body.display_name)
    except auth_svc.ValidationError as exc:
        raise HTTPException(422, str(exc))
    users_repo.set_display_name(conn, user["id"], name)
    return user_payload(users_repo.by_id(conn, user["id"]))


@router.post("/password",
             dependencies=[Depends(rate_limit("mutate")), Depends(require_csrf)])
def change_password(
    body: ChangePasswordIn,
    conn: Db = Depends(get_db),
    user=Depends(get_current_user),
    settings=Depends(get_settings),
):
    try:
        auth_svc.change_password(
            conn, settings, user["id"], body.current_password, body.new_password
        )
    except auth_svc.InvalidCredentialsError as exc:
        raise HTTPException(403, str(exc))
    except WeakPasswordError as exc:
        raise HTTPException(422, str(exc))
    return {"ok": True}


@router.post("/avatar",
             dependencies=[Depends(rate_limit("mutate")), Depends(require_csrf)])
async def upload_avatar(
    request: Request,
    conn: Db = Depends(get_db),
    user=Depends(get_current_user),
    settings=Depends(get_settings),
):
    form = await request.form()
    upload = form.get("file")
    if upload is None or isinstance(upload, str):
        raise HTTPException(422, "envie o arquivo no campo 'file'")
    data = await upload.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "imagem deve ter no máximo 2MB")
    try:
        version = save_avatar(conn, user["id"], data)
    except AvatarError as exc:
        raise HTTPException(415, str(exc))
    return {"avatar_url": f"/u/avatars/{user['id']}.jpg?v={version}"}
