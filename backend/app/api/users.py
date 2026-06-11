"""Perfil público de jogadores (sem dados privados)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..db.connection import Db
from ..services.profiles import public_profile
from .deps import get_current_user, get_db

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/{user_id}")
def get_public_profile(
    user_id: int, conn: Db = Depends(get_db), _=Depends(get_current_user)
):
    data = public_profile(conn, user_id)
    if data is None:
        raise HTTPException(404, "usuário não encontrado")
    return data
