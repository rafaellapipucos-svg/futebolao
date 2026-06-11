# Arquitetura — Bolão Copa do Mundo 2026

## 1. Visão

SPA estática (JS moderno, sem build) servida por um backend FastAPI em um único container.
Banco SQLite em volume persistente. Tempo real via SSE. Fonte de placares híbrida:
API football-data.org (opcional) + painel admin manual (sempre disponível, tem prioridade).

```
Browser ──HTTPS──> FastAPI (uvicorn)
  │  SPA estática (frontend/)          │
  │  /api/* JSON + cookies HTTPOnly    ├── SQLite (DATA_DIR/bolao.db, WAL)
  │  /api/live/sse (EventSource)       ├── Avatars (DATA_DIR/avatars/)
  └─────────────────────────────────── └── Poller asyncio ──> football-data.org
```

## 2. Princípio central: Functional Core, Imperative Shell

Restrição do ambiente de desenvolvimento: PyPI/npm indisponíveis no sandbox.
Logo, **toda a lógica de negócio e segurança vive em módulos Python puros (stdlib +
bcrypt/requests/Pillow pré-instalados)**, executáveis e testados aqui com `unittest`.
A camada FastAPI é um adaptador fino (validação de I/O + wiring), coberta por uma
suite `pytest` que roda como **gate no build do Docker** e na máquina do dev.

| Camada | Dependências | Testada onde |
|---|---|---|
| `app/domain/` regras puras | stdlib | sandbox (agora) |
| `app/core/` segurança | stdlib + bcrypt | sandbox (agora) |
| `app/db/` repositórios | stdlib sqlite3 | sandbox (agora) |
| `app/services/` orquestração | acima | sandbox (agora) |
| `app/providers/` integração API | requests (injetável) | sandbox (fake transport) |
| `app/api/` rotas FastAPI | fastapi | pytest no Docker build / local |
| `frontend/js/` | nenhuma | node --check + node:test (agora) |

## 3. Stack

- **Python 3.10+**, FastAPI + uvicorn (produção), sqlite3 stdlib (WAL, foreign_keys ON).
- **Sem ORM**: repositórios com SQL 100% parametrizado (`?`). Teste automatizado garante
  ausência de interpolação em SQL.
- **bcrypt** (cost 12) com pepper: `bcrypt(hmac_sha256(pepper, senha))` — resolve o limite
  de 72 bytes e adiciona segredo de servidor. (Argon2 indisponível; bcrypt aprovado pelo requisito.)
- **JWT HS256 stdlib** (`hmac`+`hashlib`+`base64url`): access 15min + refresh 30d com
  rotação e revogação (jti persistido). Cookies `HttpOnly; SameSite=Lax; Secure(prod)`.
- **CSRF**: double-submit (cookie legível `csrf_token` + header `X-CSRF-Token` obrigatório
  em métodos mutantes) além do SameSite=Lax.
- **Rate limiting**: token bucket em memória por (escopo, IP): login 5/min, registro 3/h,
  refresh 30/min, mutações 60/min, global 240/min.
- **Frontend**: ES modules nativos, mini-router por hash, store reativo (pub/sub),
  componentes-função retornando DOM. CSS puro (design tokens, glassmorphism, dark).
  Zero dependências, zero build.
- **Tempo real**: `GET /api/live/sse` envia `{v}` quando `data_version` muda; cliente
  refaz fetch da view ativa. Fallback: polling `GET /api/live/version` a cada 30s.

## 4. Estrutura de pastas (papel de cada arquivo)

```
futebolão/
├── ARCHITECTURE.md / AGENTS.md / TESTPLAN.md / GOALS.md / REVIEW.md / CONTINUITY.md
├── README.md            # setup, deploy Fly/Railway, env vars, comandos
├── .env.example         # todas as envs documentadas
├── Dockerfile           # multi-stage: test-gate (pytest) → runtime
├── docker-compose.yml   # dev/local com volume
├── fly.toml             # deploy Fly.io (volume SQLite)
├── Makefile             # test-core, test-api, verify-front, run, seed
├── scripts/verify.sh    # roda TODA a verificação possível no ambiente atual
├── backend/
│   ├── requirements.txt       # fastapi, uvicorn[standard], python-multipart, bcrypt, requests, Pillow
│   ├── requirements-dev.txt   # pytest, httpx
│   ├── pytest.ini
│   ├── run_core_tests.py      # unittest discover backend/tests/core (sandbox-ready)
│   ├── app/
│   │   ├── config.py          # Settings de env (SECRET_KEY, DATA_DIR, GOOGLE_*, FOOTBALL_DATA_TOKEN, INVITE_CODE, ADMIN_EMAILS, COOKIE_SECURE, CORS off)
│   │   ├── main.py            # create_app(): routers, static SPA, security headers, lifespan (db init, poller)
│   │   ├── cli.py             # python -m app.cli seed|create-admin|reset-password|sync|recompute
│   │   ├── db/
│   │   │   ├── connection.py  # connect(DATA_DIR), PRAGMAs, helper transacional
│   │   │   ├── schema.py      # DDL idempotente + migração por user_version + meta(data_version)
│   │   │   └── repos/{users,tokens,teams,matches,bets}.py   # CRUD parametrizado por agregado
│   │   ├── domain/            # PURO — sem I/O
│   │   │   ├── entities.py    # dataclasses Team/Match/Bet/User; enums Stage/MatchStatus; constantes multiplicadores
│   │   │   ├── scoring.py     # pontos de aposta: (acertou_resultado, cravada, multiplicador) → pontos
│   │   │   ├── standings.py   # tabela de grupo critérios FIFA (pts→SG→GP→h2h), com jogos live opcionais
│   │   │   ├── clinch.py      # análise só-pontos: posições garantidas/impossíveis com jogos restantes
│   │   │   ├── thirds.py      # ranking dos 3ºs + lookup Annex C (495 combos exatos FIFA)
│   │   │   ├── bracket.py     # resolve slots "1A/2B/3ABCDF/W73/L101"; preenchimento preditivo em cascata
│   │   │   └── betlock.py     # is_bet_open(match, now): scheduled ∧ now<kickoff ∧ times definidos
│   │   ├── core/
│   │   │   ├── passwords.py   # hash/verify bcrypt+pepper; política de força (≥8, não só dígitos)
│   │   │   ├── jwt_hs256.py   # sign/verify compacto, exp/typ/claims, comparação constante
│   │   │   ├── tokens.py      # emissão/rotação/revogação access+refresh (usa repos.tokens)
│   │   │   ├── csrf.py        # gerar token, validar header==cookie (constant-time)
│   │   │   └── ratelimit.py   # TokenBucket thread-safe por chave; decorador/dep helper
│   │   ├── services/
│   │   │   ├── auth.py        # register(invite), login, refresh, logout, change_password
│   │   │   ├── oauth_google.py# authorize_url(state,nonce) + callback(code)→userinfo→login/link (http injetável)
│   │   │   ├── matches.py     # lista jogos agrupados por fase/dia c/ placar, grupo, aposta do user, pontos
│   │   │   ├── betting.py     # upsert aposta (valida 0..20, trava betlock), minhas apostas (futuras/encerradas)
│   │   │   ├── standings_svc.py # standings 12 grupos c/ live + flags clinch
│   │   │   ├── leaderboard.py # ranking: pontos totais, certos, cravadas; parciais live; cache por data_version
│   │   │   ├── bracket_svc.py # monta árvore R32→Final c/ slots resolvidos/preditivos + labels
│   │   │   ├── results.py     # set_score/finalize (valida transições), bump data_version, publica no bus
│   │   │   ├── avatars.py     # valida+reprocessa imagem (Pillow→JPEG 256px, strip metadata)
│   │   │   └── live_bus.py    # pub/sub asyncio p/ SSE; get_version()
│   │   ├── providers/
│   │   │   ├── base.py        # Protocol: fetch() → list[ScoreUpdate]
│   │   │   ├── football_data.py # adapter WC: normaliza status/score, aliases de nomes, casa por external_id→(data,times)
│   │   │   └── sync.py        # aplica ScoreUpdates respeitando manual_lock; retorna mudanças
│   │   ├── jobs/poller.py     # loop asyncio: se jogo na janela [kickoff-5min, +3h], poll 60s
│   │   ├── api/               # FINO: parse/validação HTTP → services
│   │   │   ├── deps.py        # current_user (JWT cookie), require_admin, require_csrf, rate_limit(scope)
│   │   │   ├── auth.py        # POST register/login/refresh/logout; GET me
│   │   │   ├── oauth.py       # GET /oauth/google/start | /callback (state+nonce em cookie)
│   │   │   ├── matches.py     # GET /api/matches
│   │   │   ├── bets.py        # PUT /api/bets/{match_id}; GET /api/bets/mine
│   │   │   ├── standings.py   # GET /api/standings
│   │   │   ├── leaderboard.py # GET /api/leaderboard
│   │   │   ├── bracket.py     # GET /api/bracket
│   │   │   ├── profile.py     # GET/PATCH perfil; POST senha; POST avatar (multipart ≤2MB)
│   │   │   ├── admin.py       # POST score/finalize/lock; POST sync; GET users; POST reset-password
│   │   │   ├── sse.py         # GET /api/live/sse; GET /api/live/version
│   │   │   └── meta.py        # GET /api/meta/config (flags oauth/invite); GET /api/health
│   │   └── seed/
│   │       ├── loader.py      # parse data/* → INSERT teams/matches; valida 104/48/495
│   │       └── data/{teams.json, fixtures.txt, annex_c.txt}
│   └── tests/
│       ├── core/   (unittest, SEM deps externas — executa no sandbox)
│       └── api/    (pytest + TestClient — executa no Docker build/local)
└── frontend/
    ├── index.html             # shell, CSP-friendly, mobile-first
    ├── css/{tokens,base,components}.css
    ├── js/
    │   ├── main.js            # boot: config→auth→router
    │   ├── router.js          # hash router c/ guards (auth, admin)
    │   ├── store.js           # estado reativo (subscribe/set)
    │   ├── api.js             # fetch wrapper: CSRF header, 401→refresh→retry, erros tipados
    │   ├── sse.js             # EventSource + retry + fallback polling
    │   ├── format.js          # datas no fuso do browser, agrupamento por dia
    │   ├── points.js          # espelho do scoring p/ exibição otimista
    │   ├── ui.js              # h(), modal, toast, skeleton, ícones SVG
    │   ├── layout.js          # header + tab bar (bottom no mobile) + live dot
    │   └── views/{login,dashboard,matches,bracket,leaderboard,mybets,profile,admin}.js
    └── tests/  (node:test: points, format, router, store)
```

## 5. Modelo de dados (SQLite)

```sql
users(id PK, email UNIQUE NOT NULL, display_name NOT NULL, password_hash,  -- NULL se só OAuth
      google_sub UNIQUE, avatar_ver INT DEFAULT 0, is_admin INT DEFAULT 0, created_at)
refresh_tokens(jti PK, user_id FK, expires_at, revoked_at, created_at)
teams(id PK, code UNIQUE, name, flag, group_letter)
matches(id PK,            -- = número oficial FIFA 1..104
      stage TEXT,         -- GROUP|R32|R16|QF|SF|THIRD|FINAL
      group_letter, kickoff_utc, venue,
      home_source, away_source,        -- 'BRA' | '1A' | '2B' | '3:ABCDF' | 'W73' | 'L101'
      home_team_id FK NULL, away_team_id FK NULL,  -- resolvidos
      home_score, away_score, status TEXT DEFAULT 'scheduled',  -- scheduled|live|finished
      minute, manual_lock INT DEFAULT 0, external_id, updated_at)
bets(id PK, user_id FK, match_id FK, home_goals, away_goals,
     created_at, updated_at, UNIQUE(user_id, match_id))
meta(key PK, value)       -- schema_version, data_version
```

Pontos **nunca são armazenados** — sempre derivados (scoring é determinístico e barato:
≤104 jogos × N amigos). Cache de leaderboard invalidado por `data_version`.

## 6. Regras de negócio (autoritativas no servidor)

- Pontos: resultado certo = 1; cravada = 3 (1+2). Multiplicador: GROUP×1, R32×2, R16×3,
  QF×4, SF×5, THIRD×5, FINAL×10. Mata-mata: vale o placar dos 90min (empate é válido).
- Trava: `PUT /api/bets/{id}` recusa (409) se `now>=kickoff` ∨ `status≠scheduled` ∨ times
  indefinidos. Verificação dentro da mesma transação do upsert. Scoring ignora apostas
  com `updated_at >= kickoff` (defesa em profundidade).
- Tabela ao vivo: standings incluem placar corrente de jogos `live` (Brasil 1x0 aos 20' ⇒
  +3 pts, +1 SG provisórios). Ranking idem (pontos provisórios marcados `live`).
- Bracket preditivo: slot resolve assim que decidível — vencedor/2º de grupo via clinch
  só-pontos ou grupo encerrado; 3ºs via Annex C quando os 12 grupos encerram; W/L quando
  jogo termina. Cascata: se semifinal já tem os 2 lados decididos, aparece preenchida.
- Provider nunca sobrescreve jogo com `manual_lock=1` (admin assumiu o controle).

## 7. Segurança (checklist implementado)

SQLi: parametrização total + teste estático. XSS: zero `innerHTML` com dado de usuário
(helper `h()` usa `textContent`; teste estático no front), CSP `default-src 'self'`,
avatares re-codificados via Pillow (mata payloads/EXIF). CSRF: SameSite=Lax + double-submit.
Sessão: JWT HTTPOnly, access curto, refresh rotacionado/revogável, logout revoga.
Rate limit por IP+escopo. Senhas: bcrypt+pepper, política de força. Enumeração de e-mail
mitigada (mensagens neutras + mesmo custo). Uploads: limite 2MB, Pillow verify, re-encode.
Admin: flag em DB (nunca confiada do token), rotas com dupla checagem. Headers: CSP,
nosniff, frame-ancestors none, Referrer-Policy, HSTS (prod). Erros não vazam stack.

## 8. Deploy

Imagem única: estágio 1 roda pytest (gate), estágio 2 = runtime uvicorn servindo /api e
frontend estático. Volume em `/data` (SQLite + avatars). `fly.toml` e compose prontos.
Envs obrigatórias: `SECRET_KEY`, `PEPPER`. Opcionais: `GOOGLE_CLIENT_ID/SECRET`,
`FOOTBALL_DATA_TOKEN`, `INVITE_CODE`, `ADMIN_EMAILS`, `PUBLIC_BASE_URL`.
