"""Aplica ScoreUpdates do provider ao banco, respeitando manual_lock."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from ..db.repos import matches as matches_repo
from ..db.repos import teams as teams_repo
from ..db.schema import bump_data_version
from ..domain.entities import Match, MatchStatus, ScoreDetails
from ..services.live_bus import bus
from ..services.results import ResultError, set_score
from .base import ScoreUpdate
from ..db.connection import Db

log = logging.getLogger("bolao.sync")
MATCH_WINDOW = timedelta(hours=3)

# Fases que "correm" (relógio andando) — só nelas carimbamos period_started_at.
_RUNNING_PERIODS = ("1H", "2H", "ET1", "ET2")


def _next_period(
    prev: Optional[str],
    status: MatchStatus,
    paused: bool,
    duration: Optional[str],
) -> Optional[str]:
    """Máquina de fase do relógio ao vivo dirigida pelo STATUS do provider
    (confiável), não pelo minuto (que costuma vir NULL). Recebe a fase anterior
    + status/duração atuais e devolve a fase corrente.

    kickoff→1H; PAUSED no tempo normal→HT; volta→2H; PAUSED na prorrogação→
    ET_HT; EXTRA_TIME depois de ET_HT→ET2 (senão ET1); PENALTY_SHOOTOUT→PENS;
    FINISHED→FT; agendado→None.
    """
    if status == MatchStatus.FINISHED:
        return "FT"
    if status == MatchStatus.SCHEDULED:
        return None
    # LIVE (IN_PLAY/PAUSED/SUSPENDED):
    if paused:
        return "ET_HT" if duration == "EXTRA_TIME" else "HT"
    if duration == "PENALTY_SHOOTOUT":
        return "PENS"
    if duration == "EXTRA_TIME":
        return "ET2" if prev in ("ET_HT", "ET2") else "ET1"
    # tempo normal correndo: 2º tempo se já passou por um intervalo; senão 1º.
    return "2H" if prev in ("HT", "2H") else "1H"


def _index_local(conn: Db) -> Tuple[Dict[str, Match], List[Match]]:
    matches = matches_repo.all_matches(conn)
    by_external = {m.external_id: m for m in matches if m.external_id}
    return by_external, matches


def _find_local(
    update: ScoreUpdate,
    by_external: Dict[str, Match],
    matches: List[Match],
    code_of: Dict[int, str],
) -> Optional[Match]:
    """Casamento FORTE apenas (M2): por external_id já conhecido OU por janela de
    horário + os DOIS códigos de time. NUNCA adivinha pelo 'único candidato' na
    janela — no mata-mata vários jogos do mesmo dia caem na janela e os slots
    podem estar indefinidos (TBD). Sem match forte, devolve None (o chamador pula
    e loga), coerente com 'se falhar, falhe' em vez de atribuir ao jogo errado."""
    m = by_external.get(update.external_id)
    if m is not None:
        return m
    if update.home_code and update.away_code:
        for m in matches:
            if abs(m.kickoff_utc - update.kickoff_utc) > MATCH_WINDOW:
                continue
            if (code_of.get(m.home_team_id) == update.home_code
                    and code_of.get(m.away_team_id) == update.away_code):
                return m
    return None


def apply_updates(conn: Db, updates: List[ScoreUpdate]) -> int:
    """Retorna o número de partidas alteradas (placar + kickoff)."""
    teams = teams_repo.all_teams(conn)
    code_of = {tid: t.code for tid, t in teams.items()}
    id_of_code = {t.code: tid for tid, t in teams.items()}
    by_external, matches = _index_local(conn)
    changed = 0
    kickoff_changed = 0

    for upd in updates:
        local = _find_local(upd, by_external, matches, code_of)
        if local is None:
            # Sem match forte: pula (não adivinha). Normal p/ jogos do provider
            # fora do nosso fixture ou confrontos de KO ainda TBD.
            log.debug("sync sem match local p/ ext=%s (%s x %s)",
                      upd.external_id, upd.home_code, upd.away_code)
            continue
        if local.external_id != upd.external_id:
            matches_repo.set_external_id(conn, local.id, upd.external_id)

        # Atualiza kickoff se o provider reportou um horário diferente (>60s)
        # e o jogo ainda não começou (não sobrescreve jogo em andamento/encerrado).
        if local.status == MatchStatus.SCHEDULED:
            diff = abs((local.kickoff_utc - upd.kickoff_utc).total_seconds())
            if diff > 60:
                matches_repo.set_kickoff(conn, local.id, upd.kickoff_utc.isoformat())
                log.info("kickoff atualizado jogo %s: %s", local.id, upd.kickoff_utc)
                kickoff_changed += 1

        if local.manual_lock:
            continue  # admin assumiu este jogo
        if upd.home_score is None or upd.away_score is None:
            continue  # nada a aplicar (jogo futuro)
        # Fase do relógio dirigida pelo STATUS (confiável), não pelo minuto. Só
        # carimba period_started_at na TRANSIÇÃO p/ uma fase que corre: 1H começa
        # no kickoff; 2H/ET1/ET2 começam "agora" (dentro da cadência do poll).
        # Sem mudança de fase, preserva o carimbo anterior (o front conta a partir
        # dele e segue 45+X/90+X até o provider mudar o status — sem chutar intervalo).
        new_period = _next_period(local.period, upd.status, upd.paused, upd.duration)
        period_started_at = local.period_started_at
        if new_period != local.period and new_period in _RUNNING_PERIODS:
            period_started_at = (
                local.kickoff_utc.isoformat() if new_period == "1H"
                else datetime.now(timezone.utc).isoformat()
            )
        same = (
            local.home_score == upd.home_score
            and local.away_score == upd.away_score
            and local.status == upd.status
            and local.minute == upd.minute
            and local.period == new_period
            and local.home_pens == upd.home_pens
            and local.away_pens == upd.away_pens
        )
        if same:
            continue
        winner_team_id = id_of_code.get(upd.winner_code) if upd.winner_code else None
        try:
            set_score(
                conn, local.id, upd.home_score, upd.away_score, upd.status,
                force=True,
                details=ScoreDetails(
                    minute=upd.minute, winner_team_id=winner_team_id,
                    period=new_period, stoppage=upd.stoppage,
                    home_pens=upd.home_pens, away_pens=upd.away_pens,
                    period_started_at=period_started_at,
                ),
            )
            changed += 1
        except ResultError as exc:
            # ex.: mata-mata empatado sem winner — exige intervenção do admin
            log.warning("sync ignorou jogo %s: %s", local.id, exc)

    # Notifica clientes se apenas kickoffs mudaram (sem mudança de placar,
    # que já notifica dentro de set_score).
    if kickoff_changed and not changed:
        version = bump_data_version(conn)
        bus.publish(version)

    return changed + kickoff_changed
