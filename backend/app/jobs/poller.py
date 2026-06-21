"""Poller assíncrono: consulta o provider quando há jogo na janela ativa.

Janela ativa: existe partida live, ou scheduled com kickoff em [-30min, +3h30]
(PRE_WINDOW/POST_WINDOW). Cadência: 60s na janela (free tier: 10 req/min — ok),
5min fora dela (IDLE_INTERVAL — curto p/ capturar mudança de horário/fixture sem
admin). Mantenha estes números em sincronia com as constantes abaixo.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Optional

from ..domain.entities import Match, MatchStatus
from ..db.connection import Db

log = logging.getLogger("bolao.poller")

ACTIVE_INTERVAL = 60.0
# Ocioso = 5min (free tier: 10 req/min sobra). Curto o suficiente p/ capturar
# mudança de horário/fixture SEM input manual do admin (feature C, Rodada 16).
IDLE_INTERVAL = 5 * 60.0
# Janela de pré-jogo larga: pega jogo antecipado (ex.: 22:00 -> 21:30) mesmo se o
# kickoff salvo ainda estiver desatualizado, virando poll ativo na hora certa.
PRE_WINDOW = timedelta(minutes=30)
POST_WINDOW = timedelta(hours=3, minutes=30)


def window_active(matches: Iterable[Match], now: Optional[datetime] = None) -> bool:
    current = now or datetime.now(timezone.utc)
    for m in matches:
        if m.status == MatchStatus.LIVE:
            return True
        if m.status == MatchStatus.SCHEDULED:
            if m.kickoff_utc - PRE_WINDOW <= current <= m.kickoff_utc + POST_WINDOW:
                return True
    return False


class Poller:
    def __init__(
        self,
        connect_db: Callable[[], Db],
        sync_once: Callable[[Db], int],
        list_matches: Callable[[Db], list],
    ) -> None:
        self._connect_db = connect_db
        self._sync_once = sync_once
        self._list_matches = list_matches
        self._task: Optional[asyncio.Task] = None

    async def _tick(self) -> float:
        conn = self._connect_db()
        try:
            matches = self._list_matches(conn)
            active = window_active(matches)
            try:
                changed = await asyncio.to_thread(self._sync_once, conn)
                if changed:
                    log.info("sync aplicou %d mudanças", changed)
            except Exception as exc:  # rede/API falhou: loga e tenta no próximo tick
                log.warning("sync falhou: %s", exc)
            return ACTIVE_INTERVAL if active else IDLE_INTERVAL
        finally:
            conn.close()

    async def _loop(self) -> None:
        while True:
            interval = await self._tick()
            await asyncio.sleep(interval)

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
