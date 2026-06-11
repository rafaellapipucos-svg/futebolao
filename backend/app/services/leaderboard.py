"""Ranking com parciais ao vivo e cache por data_version."""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from ..db.repos import bets as bets_repo
from ..db.repos import matches as matches_repo
from ..db.repos import users as users_repo
from ..db.schema import get_data_version
from ..domain.entities import MatchStatus
from .betting import bet_points
from ..db.connection import Db

_cache_lock = threading.Lock()
_cache: Dict[Tuple[int, bool], List[Dict]] = {}


def _compute(conn: Db, include_live: bool) -> List[Dict]:
    users = users_repo.list_all(conn)
    matches = {m.id: m for m in matches_repo.all_matches(conn)}
    per_user: Dict[int, Dict] = {
        u["id"]: {
            "user_id": u["id"],
            "display_name": u["display_name"],
            "avatar_ver": u["avatar_ver"],
            "total": 0, "final_total": 0, "live_total": 0,
            "exact_hits": 0, "result_hits": 0, "bets_scored": 0,
            "has_live": False,
        }
        for u in users
    }

    for bet in bets_repo.all_bets(conn):
        match = matches[bet.match_id]
        if match.status == MatchStatus.LIVE and not include_live:
            continue
        score = bet_points(bet, match)
        if score is None:
            continue
        row = per_user[bet.user_id]
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

    rows = sorted(
        per_user.values(),
        key=lambda r: (-r["total"], -r["exact_hits"], -r["result_hits"],
                       r["display_name"].lower()),
    )
    position, last_key = 0, None
    for i, r in enumerate(rows, start=1):
        key = (r["total"], r["exact_hits"], r["result_hits"])
        if key != last_key:
            position = i
            last_key = key
        r["position"] = position
    return rows


def leaderboard(conn: Db, include_live: bool = True) -> List[Dict]:
    version = get_data_version(conn)
    cache_key = (version, include_live)
    with _cache_lock:
        cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    rows = _compute(conn, include_live)
    with _cache_lock:
        _cache.clear()  # versões antigas não interessam
        _cache[cache_key] = rows
    return rows
