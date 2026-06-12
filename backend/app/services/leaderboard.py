"""Ranking com parciais ao vivo.

Cache em DUAS camadas para nunca recalcular à toa:
- PONTUAÇÃO (cara: itera todas as apostas) é cacheada por `data_version` —
  só muda quando muda placar de jogo (ou um admin edita aposta/exclui alguém).
- EXIBIÇÃO (barata: lista de usuários + ordenação) é mesclada FRESCA a cada
  chamada — quem entrou, nome e foto sempre atuais, SEM re-pontuar.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Tuple

from ..db.connection import Db
from ..db.repos import bets as bets_repo
from ..db.repos import matches as matches_repo
from ..db.repos import users as users_repo
from ..db.schema import get_data_version
from ..domain.entities import MatchStatus
from .betting import bet_points

_cache_lock = threading.Lock()
_cache: Dict[Tuple[int, bool], Dict[int, Dict]] = {}

_ZERO = {
    "total": 0, "final_total": 0, "live_total": 0,
    "exact_hits": 0, "result_hits": 0, "bets_scored": 0, "has_live": False,
}


def _score_index(conn: Db, include_live: bool) -> Dict[int, Dict]:
    """Pontuação por usuário. Parte CARA (todas as apostas) — cacheada."""
    matches = {m.id: m for m in matches_repo.all_matches(conn)}
    idx: Dict[int, Dict] = {}
    for bet in bets_repo.all_bets(conn):
        match = matches[bet.match_id]
        if match.status == MatchStatus.LIVE and not include_live:
            continue
        score = bet_points(bet, match)
        if score is None:
            continue
        row = idx.setdefault(bet.user_id, dict(_ZERO))
        is_live = match.status == MatchStatus.LIVE
        row["total"] += score.total
        if is_live:
            row["live_total"] += score.total
            row["has_live"] = row["has_live"] or score.total > 0
        else:
            row["final_total"] += score.total
        if score.total > 0:
            row["bets_scored"] += 1
        if score.hit_exact:
            row["exact_hits"] += 1
        elif score.hit_result:
            row["result_hits"] += 1
    return idx


def _cached_index(conn: Db, include_live: bool) -> Dict[int, Dict]:
    key = (get_data_version(conn), include_live)
    with _cache_lock:
        cached = _cache.get(key)
    if cached is not None:
        return cached
    idx = _score_index(conn, include_live)
    with _cache_lock:
        _cache.clear()  # versões antigas não interessam
        _cache[key] = idx
    return idx


def leaderboard(conn: Db, include_live: bool = True) -> List[Dict]:
    idx = _cached_index(conn, include_live)
    rows = [
        {
            "user_id": u["id"],
            "display_name": u["display_name"],
            "avatar_ver": u["avatar_ver"],
            **idx.get(u["id"], _ZERO),
        }
        for u in users_repo.list_all(conn)
    ]
    rows.sort(key=lambda r: (-r["total"], -r["exact_hits"], -r["result_hits"],
                             r["display_name"].lower()))
    position, last_key = 0, None
    for i, r in enumerate(rows, start=1):
        key = (r["total"], r["exact_hits"], r["result_hits"])
        if key != last_key:
            position = i
            last_key = key
        r["position"] = position
    return rows
