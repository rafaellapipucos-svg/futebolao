"""Seed do banco com dados oficiais da Copa 2026.

Idempotente: re-rodar atualiza fixtures sem tocar placares, status ou apostas.
Valida invariantes (48 times, 104 jogos, 495 combos Annex C) e FALHA alto se
os dados estiverem corrompidos.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from ..db.repos import matches as matches_repo
from ..db.repos import teams as teams_repo
from ..domain.entities import GROUPS, Stage
from ..domain.thirds import parse_annex_c

DATA_DIR = Path(__file__).parent / "data"

EXPECTED_STAGE_COUNTS = {
    Stage.GROUP: 72, Stage.R32: 16, Stage.R16: 8, Stage.QF: 4,
    Stage.SF: 2, Stage.THIRD: 1, Stage.FINAL: 1,
}


def load_annex_c_table() -> Dict[str, Dict[str, str]]:
    return parse_annex_c((DATA_DIR / "annex_c.txt").read_text(encoding="utf-8"))


def _parse_kickoff(value: str) -> str:
    dt = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    return dt.isoformat()


def seed(conn: Db) -> Dict[str, int]:
    teams_raw = json.loads((DATA_DIR / "teams.json").read_text(encoding="utf-8"))
    if len(teams_raw) != 48:
        raise ValueError(f"teams.json deve ter 48 times, tem {len(teams_raw)}")
    per_group: Dict[str, int] = {g: 0 for g in GROUPS}
    for t in teams_raw:
        per_group[t["group"]] += 1
        teams_repo.upsert(conn, t["code"], t["name"], t["flag"], t["group"])
    if any(v != 4 for v in per_group.values()):
        raise ValueError(f"grupos desbalanceados: {per_group}")

    code_to_id = {t.code: tid for tid, t in teams_repo.all_teams(conn).items()}

    lines = [
        ln.strip()
        for ln in (DATA_DIR / "fixtures.txt").read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if len(lines) != 104:
        raise ValueError(f"fixtures.txt deve ter 104 jogos, tem {len(lines)}")

    stage_counts: Dict[Stage, int] = {s: 0 for s in Stage}
    for line in lines:
        mid, stage_s, group, kickoff, venue, home, away = line.split("|")
        stage = Stage(stage_s)
        stage_counts[stage] += 1
        home_id = code_to_id.get(home) if stage == Stage.GROUP else None
        away_id = code_to_id.get(away) if stage == Stage.GROUP else None
        if stage == Stage.GROUP and (home_id is None or away_id is None):
            raise ValueError(f"time desconhecido no jogo {mid}: {home}/{away}")
        matches_repo.upsert_fixture(
            conn,
            match_id=int(mid),
            stage=stage.value,
            group_letter=group or None,
            kickoff_utc=_parse_kickoff(kickoff),
            venue=venue,
            home_source=home,
            away_source=away,
            home_team_id=home_id,
            away_team_id=away_id,
        )

    if stage_counts != EXPECTED_STAGE_COUNTS:
        raise ValueError(f"contagem por fase incorreta: {stage_counts}")

    load_annex_c_table()  # valida as 495 combinações (parse_annex_c lança se errado)
    return {"teams": len(teams_raw), "matches": len(lines)}
