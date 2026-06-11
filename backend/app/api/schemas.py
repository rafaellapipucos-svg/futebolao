"""Modelos de entrada (Pydantic v2 — vem com FastAPI). Validação fina fica
nos serviços; aqui só tipos/limites estruturais."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)
    display_name: str = Field(max_length=80)
    invite_code: Optional[str] = Field(default=None, max_length=64)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class BetIn(BaseModel):
    home_goals: int = Field(ge=0, le=20)
    away_goals: int = Field(ge=0, le=20)


class DisplayNameIn(BaseModel):
    display_name: str = Field(max_length=80)


class ChangePasswordIn(BaseModel):
    current_password: Optional[str] = Field(default=None, max_length=128)
    new_password: str = Field(max_length=128)


class AdminScoreIn(BaseModel):
    home_score: int = Field(ge=0, le=99)
    away_score: int = Field(ge=0, le=99)
    status: str = Field(pattern="^(scheduled|live|finished)$")
    minute: Optional[int] = Field(default=None, ge=0, le=130)
    winner_team_id: Optional[int] = None
    force: bool = False
    lock: Optional[bool] = None


class AdminResetPasswordIn(BaseModel):
    new_password: str = Field(max_length=128)
