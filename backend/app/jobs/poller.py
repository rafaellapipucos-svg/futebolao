"""Poller assíncrono: consulta o provider quando há jogo na janela ativa.

Janela ativa: existe partida live, ou scheduled com kickoff entre now-10min e
now+10min (pré-jogo), ou live esperada (kickoff < now < kickoff+3h30).
Cadência: 60s na janela (free tier: 10 req/min — ok), 15min fora dela
(captura mudanças de horário/fixtures).
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
IDLE_INTERVAL = 15 * 60.0
PRE_WINDOW = timedelta(minutes=10)
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
