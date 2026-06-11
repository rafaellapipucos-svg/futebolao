"""Tempo real: SSE (push) + endpoint de versão (fallback polling)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..db.schema import get_data_version
from ..services.live_bus import bus
from .deps import get_db
from ..db.connection import Db

router = APIRouter(prefix="/api/live", tags=["live"])
PING_INTERVAL = 25.0


@router.get("/version")
def version(conn: Db = Depends(get_db)):
    return {"v": get_data_version(conn)}


@router.get("/sse")
async def sse(request: Request):
    settings = request.app.state.settings

    def _current_version() -> int:
        from ..db.connection import connect

        conn = connect(settings.db_target)
        try:
            return get_data_version(conn)
        finally:
            conn.close()

    async def stream():
        queue = bus.subscribe()
        try:
            v = await asyncio.to_thread(_current_version)
            yield "retry: 5000\n\n"
            yield f"data: {{\"v\": {v}}}\n\n"
            while True:
                if await request.is_disconnected():
                    return
                try:
                    v = await asyncio.wait_for(queue.get(), timeout=PING_INTERVAL)
                    yield f"data: {{\"v\": {v}}}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            bus.unsubscribe(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
