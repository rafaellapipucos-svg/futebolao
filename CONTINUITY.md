# CONTINUITY — Bolao Copa 2026 ("futebolao")

## Snapshot
- **Goal**: Site de bolao da Copa 2026 p/ amigos: apostas em placar exato, tabela
  ao vivo, bracket preditivo, ranking live. 100% deploy-ready. [USER] 2026-06-10
- **Status**: ✅ CONCLUIDO — rodadas 1 e 2 dos GOALS verdes (ver GOALS.md/REVIEW.md).
- **Stack**: FastAPI (shell fino) sobre nucleo puro stdlib + sqlite3 + bcrypt +
  requests + Pillow. Frontend ES modules SEM build. Container unico (Fly/Railway),
  SQLite em volume. [USER aprovou] 2026-06-10
- **Dados**: hibrido football-data.org (opcional) + admin manual. Seed real:
  48 times, 104 jogos, Annex C FIFA (495 combos exatos). [TOOL] 2026-06-10
- **Constraint sandbox**: PyPI/npm bloqueados. Testes core (130, unittest stdlib)
  executados aqui; suite pytest HTTP roda como GATE no build do Docker. [TOOL]
- **Copa comeca 2026-06-11 19:00Z** — deploy urgente: docker build + fly deploy.

## Invariants
- Arquivos de codigo ≤300 LOC; modular. SQL 100% parametrizado (teste AST).
- Trava de aposta server-side no kickoff, dentro da transacao do upsert.
- Pontos: resultado=1, cravada=3; mult: G x1, R32 x2, R16 x3, QF x4, SF x5,
  THIRD x5, FINAL x10. Mata-mata: placar dos 90min.

## Decisions (ADR-lite)
- D001 ACTIVE: FastAPI + JS vanilla sem build; nucleo testavel stdlib. [USER]
- D002 ACTIVE: sqlite3 stdlib + repository pattern (sem ORM).
- D003 ACTIVE: bcrypt cost12 + pepper HMAC-SHA256 (Argon2 indisponivel).
- D004 ACTIVE: JWT HS256 stdlib; access 15min + refresh 30d rotacionado/revogavel
  (reuso revoga familia); cookies HttpOnly SameSite=Lax; CSRF double-submit.
- D005 ACTIVE: aposta em mata-mata = placar dos 90min (empate vale).
- D006 ACTIVE: THIRD multiplicador x5. [ASSUMPTION documentada no Como Jogar]
- D007 ACTIVE: aposta so com os 2 times definidos.
- D008 ACTIVE: 3os = tabela Annex C exata; slots 1o/2o resolvem cedo via clinch
  so-pontos; 3os exigem 12 grupos encerrados.
- D009 ACTIVE: SSE push de data_version + polling 30s fallback; poller 60s em
  janela de jogo, 15min fora.
- D010 ACTIVE: sem SMTP; INVITE_CODE opcional; reset de senha via admin/CLI.
- D011 ACTIVE: desempate FIFA pts>SG>GP>h2h; fallback codigo + flag tie_unresolved.
- D012 ACTIVE: persist_resolutions nunca des-resolve confronto ja propagado
  (reset de KO propagado exige correcao manual; documentado no README).

## Incidents
- I001 RECORRENTE/MITIGADO: Write/Edit no FS montado trunca arquivo ocasionalmente
  (jwt_hs256 2x, ratelimit 2x, package.json, main.py, GOALS, CONTINUITY, base.css,
  views.css). Mitigacao adotada: pos-edit SEMPRE verificar tail/balanco; reescrever
  via bash heredoc; varredura final de integridade executada (tails + chaves CSS
  + py_compile + node --check). 2026-06-10 [TOOL]
- I002 NOTA: git nao funciona no FS montado (virtiofs) — `.git/config` corrompe
  (vira NUL bytes) e arquivos de lock dao EPERM (nao da p/ deletar). Sandbox bash
  tambem NAO acessa github.com (proxy HTTP 403 + SOCKS5 falha; web_fetch consegue
  ler github.com via outro mecanismo, mas e GET-only). Workaround: copiar projeto
  p/ /tmp (FS local), `git init`+commit la, exportar .zip p/ outputs; usuario
  extrai local e roda `git push` 1x (push real nao pode ser feito pelo sandbox).
  Sobrou pasta `.git-broken-pode-apagar` em C:\...\futebolão — apagar pelo
  Explorer (EPERM so existe no sandbox, NTFS normal funciona). 2026-06-11 [TOOL]

## State
### Done
- 2026-06-10 Agentes 0-9 completos. 130 testes core + 19 node verdes no sandbox.
  py_compile/node --check/greps/limite-300/TODO-zero verdes (scripts/verify.sh).
  GOALS rodadas 1 e 2 ✅. REVIEW.md com critica e fixes R2-F1..F6 aplicados.
### Next (para o usuario)
- `docker build .` na maquina local (executa pytest HTTP como gate) OU deploy
  direto: README.md secao Fly.io. Configurar secrets; opcional: GOOGLE_*,
  FOOTBALL_DATA_TOKEN, INVITE_CODE. Criar conta com email de ADMIN_EMAILS.

## Working set
- backend/app/** (dominio, core, services, providers, api), backend/tests/**
- frontend/{index.html, css/*, js/**, tests/*}
- Dockerfile, docker-compose.yml, fly.toml, scripts/verify.sh, README.md
- Docs: ARCHITECTURE.md, AGENTS.md, TESTPLAN.md, GOALS.md, REVIEW.md

## Receipts (ultimos)
- 2026-06-10 [TOOL] fixturedownload.com -> 104 jogos oficiais OK
- 2026-06-10 [TOOL] Wikipedia knockout stage -> bracket refs + Annex C 495 OK
- 2026-06-10 [TOOL] pip/npm 403 (proxy) -> estrategia nucleo-testavel adotada
- 2026-06-10 [CODE] Annex C validada: 495 combos, pools FIFA, 0 erros
- 2026-06-10 [CODE] run_core_tests: 130 OK | node --test: 19 OK | verify.sh: VERDE
- 2026-06-10 [CODE] GOALS R1 ✅ + R2 ✅ — projeto encerrado

## Rodada 3 — Postgres/Supabase (2026-06-11)
- D013 ACTIVE: Postgres via DATABASE_URL (Supabase) usando psycopg3 SEM ORM;
  adapter dual-dialeto em db/connection.py; SQLite permanece p/ dev/testes;

## Rodada 4 — fix deploy Render (2026-06-11)
- I003 RESOLVIDO: build Docker no Render falhou (FAILED errors=43) com
  FileNotFoundError em annex_c.txt no estagio `test`. Causa: regra `data/` no
  .gitignore (sem ancora) casava backend/app/seed/data/, logo annex_c.txt +
  fixtures.txt + teams.json NUNCA entraram no repo (git ls-files vazio; unico
  commit 71e1bee nao os contem). So aparece no Render porque os arquivos
  existem no disco local mas faltam no repo clonado. Fix: .gitignore passa a
  usar `/data/` (ancorado na raiz) + comentario; `*.db` cobre bolao.db em
  qualquer lugar. check-ignore confirma seed liberada e runtime ainda ignorado.
  Sem .dockerignore, basta commitar p/ entrar no build context. [TOOL] 2026-06-11
- CORRECAO DE FATOS (supersede Rodada 3): branch real = `master` (nao `main`);
  remote = github.com/rafaellapipucos-svg/futebolao.git (nao `tabolao`). [TOOL]
- I001 reincidiu: Edit truncou .gitignore em "Ancora"; reescrito via heredoc. [TOOL]
- NEXT [USER] (maquina local, no repo, 1x): apagar .git/index.lock se existir;
  `git add .gitignore backend/app/seed/data`;
  `git commit -m "fix: versiona seed (gitignore ancorado em /data/)"`;
  `git push origin master`. Render re-builda e o gate de testes acha os arquivos.

## Rodada 5 — fix gate trava no build (Google Cloud, 2026-06-11)
- I004 RESOLVIDO: build (Cloud Build/Run) trava no step 12/25 (`RUN python
  run_core_tests.py && python -m pytest tests/api -q`) — run_core_tests.py
  termina OK (148 testes), mas pytest tests/api fica pendurado p/ sempre,
  sem erro. Causa: test_sse_responde_event_stream usa
  `with client.stream(...)` (TestClient sincrono = transporte por
  thread/portal); o close() ao sair do `with` nao garante que
  request.is_disconnected() vire True a tempo p/ o generator infinito do
  SSE (ping a cada 25s) retornar — resp.close() fica pendurado para sempre.
  Fix: reescrito o teste com httpx.ASGITransport (mesma event loop do
  teste, sem thread) + anyio.fail_after(5) como teto extra; adicionado
  `pytest-timeout` (timeout=60 global em backend/pytest.ini) como rede de
  seguranca p/ qualquer trava futura falhar rapido em vez de pendurar o
  build. anyio + pytest-timeout adicionados a requirements-dev.txt;
  anyio_backend fixture em conftest.py. [TOOL] 2026-06-11
- I001 reincidiu (3x): Edit truncou conftest.py, test_http_misc.py,
  pytest.ini, requirements-dev.txt e este CONTINUITY.md apos escrita.
  Reescritos via heredoc bash + verificacao repetida com sleep. [TOOL]
- NOTA: usuario tambem testando deploy via Google Cloud (Cloud Build/Run),
  alem de Render — mesmo Dockerfile/gate serve para ambos.
- NEXT [USER] (maquina local, no repo): commitar
  backend/tests/api/conftest.py, backend/tests/api/test_http_misc.py,
  backend/pytest.ini, backend/requirements-dev.txt; push; re-disparar o
  build.

## Rodada 5 — fix gate de testes API no Render (2026-06-11)
Pos-fix da seed, o step 12 (RUN run_core_tests && pytest tests/api) avancou:
148 core OK, mas 2 testes de API derrubavam o build.
- I004 RESOLVIDO: test_avatar_404_e_upload falhava (200 em
  /u/avatars/../../etc/passwd). Causa: catch-all `@app.get("/{path:path}")`
  (spa_fallback) servia index.html (200) para QUALQUER caminho, inclusive o
  traversal (httpx nao normaliza `..`, manda o path cru). Fix: spa_fallback
  retorna 404 quando `".." in path` (traversal nunca e' rota de SPA). Nao
  afeta /qualquer/coisa nem estaticos. [CODE] backend/app/main.py
- I005 RESOLVIDO: test_sse_responde_event_stream pendurava o build (o "step 12
  travado por horas"). SSE e' generator infinito; tanto TestClient.stream
  quanto httpx.ASGITransport penduram no fechamento (ASGITransport bufferiza/
  nao cancela o app). Fix: teste dirige o app ASGI direto, com receive() que
  devolve http.disconnect apos o 1o chunk -> encerra por 2 vias
  (listen_for_disconnect + request.is_disconnected), dentro de anyio.fail_after(5).
  Removido import httpx (nao usado). Validado por simulacao asyncio do
  StreamingResponse: termina ~5ms, status 200, 1o chunk "retry:", finally roda.
  [CODE] backend/tests/api/test_http_misc.py
- pytest.ini (timeout=60) do usuario fica: e' o backstop que impede o build de
  pendurar para sempre se algo regredir. [TOOL]
- Sandbox sem PyPI (proxy 403) impede rodar pytest/httpx aqui; verificacao por
  py_compile + simulacao asyncio do fluxo. Gate real roda no build do Render. [TOOL]
- NEXT [USER] (maquina local, no repo): `git add backend/app/main.py backend/tests/api/test_http_misc.py CONTINUITY.md`;
  `git commit -m "fix(api): bloqueia path traversal no SPA e torna teste SSE nao-pendurante"`;
  `git push origin master`. Render rebuilda; o gate tests/api deve passar.

## Rodada 6 — fix final do gate API (2026-06-11)
Build do Render confirmou: SSE (I005) PASSOU; sobrou so test_avatar_404_e_upload.
- I004 CORRIGIDO DE VERDADE (a hipotese da Rodada 5 estava errada): o
  Starlette TestClient (httpx) NORMALIZA ".." ANTES de enviar, entao o servidor
  recebe "/etc/passwd" (sem ".."), a guarda `".." in path` NUNCA dispara e o
  catch-all SPA responde 200 (HTML shell). Nao da p/ o servidor 404ar isso sem
  quebrar o SPA fallback de /qualquer/coisa. Fix correto: ajustar o teste p/
  validar a garantia REAL — o pedido normalizado cai no shell SPA e JAMAIS serve
  arquivo do disco (assert sem content-type image/* e sem "root:") + checar a
  validacao do handler (/u/avatars/passwd -> 404). A guarda `".." in path` no
  main.py FICA como hardening (pega clientes que mandam ".." cru/sem normalizar).
  [CODE] backend/tests/api/test_http_misc.py, backend/app/main.py
- LICAO: httpx normaliza dot-segments no path; nao da p/ testar traversal de URL
  esperando que o ".." chegue cru ao app via TestClient. [TOOL]
- NEXT [USER]: `git add backend/app/main.py backend/tests/api/test_http_misc.py CONTINUITY.md`;
  `git commit -m "fix(test): valida traversal de avatar pela garantia real (cliente normaliza ..)"`;
  `git push origin master`. Esperado: gate tests/api 100% verde -> runtime.

## Rodada 7 — alvo real = Google Cloud Run (2026-06-11)
- CORRECAO DE FATO (supersede Fly/Railway): o deploy NAO e' Render/Fly — e'
  Google Cloud Run via Cloud Build (GitHub trigger). Projeto futebolao-499113,
  regiao southamerica-east1. Build verde: e12489eb / commit 43fc059. [USER/TOOL]
- Mensagem "Nao ha codigo-fonte para edicao" no console NAO e' erro: e' deploy
  continuo a partir do git (esperado). [TOOL]
- IMPLICACOES Cloud Run (stateless, FS efemero, HTTPS, PORT injetado):
  * SECRET_KEY e PEPPER (>=32 chars) sao OBRIGATORIOS — sem eles config.py
    levanta RuntimeError e a revisao NAO sobe (boot crash). [CODE config.py]
  * SQLite NAO serve (FS efemero/nao compartilhado): dados somem a cada cold
    start. Precisa DATABASE_URL (Supabase Postgres, D013). 
  * COOKIE_SECURE=true (Cloud Run e' HTTPS); PUBLIC_BASE_URL = URL .run.app.
  * PORT e' injetado pelo Cloud Run; CMD ja usa ${PORT} -> ok.
- NEXT [USER]: setar env/secrets na revisao do Cloud Run (Editar e implantar
  nova revisao -> Variaveis e secrets): SECRET_KEY, PEPPER, ADMIN_EMAILS,
  DATABASE_URL (Supabase), PUBLIC_BASE_URL, COOKIE_SECURE=true. Opcional:
  INVITE_CODE, GOOGLE_*, FOOTBALL_DATA_TOKEN.

## Rodada 8 — bug do ranking (cache stale) (2026-06-11)
App no ar (Cloud Run). Usuario relatou: (a) so o 1o usuario aparece no ranking;
(b) foto do ranking nao atualiza ao trocar no perfil.
- I006 RESOLVIDO: AMBOS tem a MESMA causa. services/leaderboard.py cacheia o
  ranking com chave = (data_version, include_live). data_version so muda em
  RESULTADO de jogo (results.py/admin). Registrar usuario, renomear ou trocar
  avatar NAO bumpava nada -> cache preso no estado antigo (so o 1o usuario; foto
  velha / avatar_ver 0 -> iniciais). Fix: nova users_version no meta, bumpada em
  users_repo.create/set_display_name/bump_avatar; chave do cache passa a
  (data_version, users_version, include_live). Multi-instancia-safe (contador no
  DB, igual data_version). [CODE] schema.py, db/repos/users.py, services/leaderboard.py
- Teste de regressao test_cache_invalida_quando_usuarios_mudam: provado que
  FALHA sem o fix ('Eva' nao aparece) e passa com ele. Suite core 149 verdes. [CODE]
- NEXT [USER]: `git add backend/app/db/schema.py backend/app/db/repos/users.py backend/app/services/leaderboard.py backend/tests/core/test_leaderboard.py CONTINUITY.md`;
  `git commit -m "fix(ranking): invalida cache do leaderboard quando usuarios/avatares mudam"`;
  `git push origin master`. Deploy automatico (Cloud Run). Apos subir, o ranking
  ja mostra todos e a foto atualiza na hora.

## Rodada 9 — features pedidas pelo usuário (2026-06-11)
- Bandeiras ENG/SCO (🏴+tags viram quadrado preto): novo format.teamFlag()
  mostra a sigla quando a bandeira começa com U+1F3F4. Aplicado em
  bracket/matches/dashboard/admin. [CODE]
- Mata-mata: bracket.js agora mostra UMA fase por vez via seletor (chips
  R32/R16/QF/SF/3º/Grande Final) — menos poluição. "Decisões"/"Final"
  renomeados para "Grande Final" no app todo + entities.STAGE_LABELS_PT. [CODE]
- Admin: pode EXCLUIR qualquer perfil (menos o próprio; cascade explícito de
  bets/tokens/avatars) e EDITAR apostas passadas com recálculo. Endpoints:
  DELETE /api/admin/users/{id}, GET .../bets, PUT .../bets/{match}. UI nova em
  views/admin_users.js (api.del adicionado). [USER pediu 2 dos 4 poderes]
  - D014 ACTIVE: admin_set_bet grava updated_at = kickoff-60s em jogos já
    iniciados, p/ a edição pontuar (bet_points zera updated_at>=kickoff). Bumpa
    data_version+SSE. [CODE betting.py]
- Tema CLARO é o padrão; ESCURO (UI original) via [data-theme="dark"]. tokens.css
  reestruturado (paleta clara default + dark variant); botão sol/lua na navbar
  (theme.js, lembra no localStorage; init inline no index.html sem flash);
  tokenizado .btn:hover e input bg (--hover/--input-bg). [USER escolheu toggle]
- I007 (relógio-bomba, CRÍTICO): place_bet gravava updated_at = horário da
  ESCRITA, não o da aposta. Quando o relógio passou do 1º kickoff (Copa começou
  19:00Z hoje), 5 testes core zeravam e o GATE do build ficaria VERMELHO p/
  qualquer deploy. Fix: place_bet grava updated_at = `current` (o now informado).
  Determinístico + mais correto. 151 core verdes. [CODE betting.py]
- I008 NOTA: scripts/verify.sh falha no sandbox por /tmp/*.log de processo
  anterior sem permissão de escrita (redirect falha antes de rodar). Não é bug
  do código: rodar com logs em $(mktemp -d) → core 151, node 20, node --check 0
  falhas, py_compile limpo, todos ≤300 linhas. [TOOL]
- NEXT [USER]: `git add -A && git commit -m "feat: bandeiras, mata-mata por fase, admin (excluir/editar apostas), tema claro + fix relogio-bomba" && git push origin master`.
