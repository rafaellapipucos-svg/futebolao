"""App factory FastAPI: wiring de routers, estaticos, seguranca e ciclo de vida."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import admin, auth, bets, game, meta, oauth, profile, sse, users
from .config import load_settings
from .core.ratelimit import default_limiter
from .db.connection import connect
from .db.schema import init_db
from .seed.loader import seed
from .services.live_bus import bus

log = logging.getLogger("bolao")
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    # style-src com 'unsafe-inline': as views usam atributos style= (REVIEW R2-F1);
    # scripts permanecem 100% restritos a 'self'.
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
}


def create_app() -> FastAPI:
    settings = load_settings()
    if not settings.uses_postgres:
        settings.data_dir.mkdir(parents=True, exist_ok=True)

    boot = connect(settings.db_target)
    init_db(boot)
    seed(boot)
    boot.close()

    poller_holder = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        import asyncio

        bus.attach_loop(asyncio.get_running_loop())
        if settings.football_data_token:
            from .db.repos import matches as matches_repo
            from .jobs.poller import Poller
            from .providers.football_data import FootballDataProvider
            from .providers.sync import apply_updates

            provider = FootballDataProvider(settings.football_data_token)
            poller = Poller(
                connect_db=lambda: connect(settings.db_target),
                sync_once=lambda conn: apply_updates(conn, provider.fetch()),
                list_matches=matches_repo.all_matches,
            )
            poller.start()
            poller_holder["poller"] = poller
            log.info("poller football-data ativo")
        else:
            log.info("sem FOOTBALL_DATA_TOKEN - modo manual (admin)")
        yield
        if "poller" in poller_holder:
            await poller_holder["poller"].stop()

    app = FastAPI(title="Bolao Copa 2026", docs_url=None, redoc_url=None,
                  openapi_url=None, lifespan=lifespan)
    app.state.settings = settings
    app.state.limiter = default_limiter()

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        if settings.cookie_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("erro nao tratado em %s", request.url.path)
        return JSONResponse({"detail": "erro interno"}, status_code=500)

    for router in (auth.router, oauth.router, game.router, bets.router,
                   profile.router, admin.router, sse.router, meta.router,
                   users.router):
        app.include_router(router)

    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str):
        # Caminho com ".." nunca e' rota de SPA: bloqueia path traversal
        # (ex.: /u/avatars/../../etc/passwd) em vez de servir o shell com 200.
        if ".." in path:
            raise HTTPException(404)
        # SPA usa rotas por hash; qualquer caminho desconhecido volta ao shell
        return FileResponse(FRONTEND_DIR / "index.html")

    return app
