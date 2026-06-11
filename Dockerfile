# ============================================================
# Estagio base — dependencias de producao
# ============================================================
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /src
COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================
# Estagio devbase — deps de teste + codigo (usado pelo compose de testes PG)
# ============================================================
FROM base AS devbase
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
WORKDIR /src/backend

# ============================================================
# Estagio test — GATE: a imagem final so nasce se a suite passar
# (testes core + HTTP em SQLite; a suite tests/pg roda via
#  docker-compose.test.yml ou TEST_DATABASE_URL apontando p/ Postgres real)
# ============================================================
FROM devbase AS test
RUN python run_core_tests.py && python -m pytest tests/api -q

# ============================================================
# Estagio runtime — enxuto
# ============================================================
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    PORT=8000

RUN useradd --create-home --uid 1001 bolao
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=test /src/backend/app ./app
COPY --from=test /src/frontend ../frontend

RUN mkdir -p /data && chown -R bolao:bolao /data /app
USER bolao
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD ["python", "-m", "app.healthcheck"]

CMD ["sh", "-c", "uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT}"]
