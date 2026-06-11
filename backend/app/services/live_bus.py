"""Pub/sub em memória para SSE: publica a data_version quando algo muda.

asyncio-friendly: assinantes recebem via Queue; publicação é thread-safe
(chamada também de código síncrono via loop.call_soon_threadsafe).
"""
from __future__ import annotations

import asyncio
import threading
from typing import Optional, Set


class LiveBus:
    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.last_version: int = 0

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=32)
        with self._lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock:
            self._subscribers.discard(q)

    def publish(self, version: int) -> None:
        """Thread-safe; descarta para assinantes com fila cheia (eles fazem polling)."""
        self.last_version = version
        with self._lock:
            subs = list(self._subscribers)
        if not subs:
            return
        if self._loop is None or self._loop.is_closed():
            return
        def _fanout() -> None:
            for q in subs:
                if not q.full():
                    q.put_nowait(version)
        self._loop.call_soon_threadsafe(_fanout)


bus = LiveBus()
