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
  THIRD x5, FINAL x10. Mata-mata: placar do FIM DA PRORROGACAO (antes dos
  penaltis). [CORRIGIDO 2026-06-21: era "90min", contradizia codigo/UI/PLANO §1.1]

## Decisions (ADR-lite)
- D001 ACTIVE: FastAPI + JS vanilla sem build; nucleo testavel stdlib. [USER]
- D002 ACTIVE: sqlite3 stdlib + repository pattern (sem ORM).
- D003 ACTIVE: bcrypt cost12 + pepper HMAC-SHA256 (Argon2 indisponivel).
- D004 ACTIVE: JWT HS256 stdlib; access 15min + refresh 30d rotacionado/revogavel
  (reuso revoga familia); cookies HttpOnly SameSite=Lax; CSRF double-submit.
- D005 SUPERSEDED (por PLANO_RODADA16 §1.1, formalizado 2026-06-21): aposta em
  mata-mata = placar do FIM DA PRORROGACAO, antes dos penaltis (empate vale; os
  penaltis so definem quem avanca). O texto antigo ("90min") estava errado e
  contradizia codigo/teste/UI/ARCHITECTURE. _score_pair agora subtrai os penaltis
  do fullTime (a API football-data SOMA o shootout no fullTime — ver M1/2026-06-21).
- D006 ACTIVE: THIRD multiplicador x5. [ASSUMPTION documentada no Como Jogar]
- D007 ACTIVE: aposta so com os 2 times definidos.
- D008 ACTIVE: 3os = tabela Annex C exata; slots 1o/2o resolvem cedo via clinch
  so-pontos; 3os exigem 12 grupos encerrados.
- D009 ACTIVE: SSE push de data_version + polling 30s fallback; poller 60s em
  janela de jogo, 5min fora (IDLE_INTERVAL=5min no codigo; texto "15min" corrigido
  2026-06-21 — Rodada 16 reduziu p/ capturar mudanca de horario sem admin).
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

## Rodada 18 — fix do ✓ em grupo encerrado + setinhas no placar (2026-06-26)
- [USER] Pergunta: Canadá (2º no Grupo B) sem ✓ mesmo com grupo encerrado.
- [CODE] Causa: o ✓ (clinchMark em dashboard.js) lê só clinched_first/top2 do
  clinch.py, que é conservador (SÓ pontos). Canadá empatado em pontos com a
  Bósnia (4) ⇒ clinch enxerga 2 times "alcançando" ⇒ top2=False. O 2º lugar é
  decidido por saldo, que mora em standings.py, não em clinch.py.
- D013 ACTIVE: para grupo ENCERRADO, standings_svc deriva clinched_first/top2/
  eliminated_top2 da POSIÇÃO final (com desempates), não só dos pontos. Grupo em
  andamento mantém clinch conservador. (clinch.py já recomendava isso no docstring.)
- D014 ACTIVE: desempate do RANKING = pontos > resultados corretos > cravadas >
  nome (antes: cravadas antes de resultados). [USER 2026-06-26] Só lógica do
  backend (leaderboard.py); UI/front inalterados. result_hits = acerto de
  resultado NÃO-exato (cravadas contam em exact_hits, desempate mais profundo).
- [USER] Pedido: restaurar setinhas − / + nos campos de gol da aba de apostas
  (some no celular sem precisar de teclado; haviam sido removidas no rework e0c3790).
- [CODE] betbox.js: goalField → goalStepper (input + botões − / +, mesmo
  saneamento 0–20, drafts, aria-labels). CSS .goal-stepper/.step-btn (tokens) +
  shrink ≤360px. Reaproveita intenção do stepper original de f2ee419.
  NOTA: .bet-stepper/.bet-value em components.css ficaram como CSS morto (rework
  passou a usar .bet-input); novas classes são .goal-stepper/.step-btn.

## Receipts (ultimos)
- 2026-06-26 [CODE] backend core 218 OK (pytest) + frontend 68 OK (node --test)
  + render-test stub: setinhas inc/dec, clamp 0–20, 2 steppers independentes OK
- 2026-06-26 [CODE] backend core 219 OK (+1: test_desempate_resultados_antes_de_
  cravadas prova resultados > cravadas em empate de pontos). leaderboard.py via py.
- 2026-06-26 [TOOL] I001 RECORREU no Edit tool: truncou standings_svc.py,
  betbox.js, components.css, views-extra.css e o próprio CONTINUITY.md.
  Mitigação: reescrita via heredoc/python a partir do git HEAD + sweep
  (py_compile/node --check/brace-balance). I002 EPERM no rm exigiu
  allow_cowork_file_delete p/ limpar temp.
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

## Rodada 10 — ajustes pós-feedback (2026-06-11)
- Flags ENG/SCO gigantes: .team-flag é 1.7rem e texto não tem padding como
  emoji. Fix: teamFlag agora dá sigla de 2 letras (ENG→IN, SCO→SC) e
  ui.flagContent envolve em .flag-abbr (0.62em mono) p/ ficar do tamanho das
  outras. flagIsAbbr exportado. Views usam flagContent; admin usa teamFlag str.
- Contraste do claro ruim: .topbar/.tabbar tinham fundo DARK hardcoded
  (rgba(5,10,22)/rgba(7,13,29)). Tokenizado --topbar-bg/--tabbar-bg (claro=
  branco translúcido). Textos do claro escurecidos (text-1 #313f56, text-2
  #51607a) e borda um tico mais forte. [CODE tokens.css, components.css]
- Admin: último jogo colidia com Usuários — margin-top var(--sp-5) na seção.
- "Não apostou" registrado e visível:
  * mybets aba Encerradas agora lista TODOS os jogos já iniciados (não só os
    apostados); betbox.lockedView sem aposta mostra "Você não apostou · 0 pts".
  * GET /api/admin/users/{id}/bets retorna todos os jogos com 2 times definidos
    (ou já apostados) → admin vê "não apostou" e pode criar/editar a aposta
    (admin_set_bet faz upsert; pontua via D014). [USER pediu]
- Testes: teamFlag (IN/SC) atualizado; novo core test admin cria aposta p/ quem
  não apostou. core 152 / node 20 verdes; node --check 0 falhas; py_compile ok;
  todos ≤300 linhas. [TOOL]
- NEXT [USER]: `git add -A && git commit -m "fix(ui): siglas IN/SC, contraste do tema claro, espacamento admin, registro de nao-apostou" && git push origin master`.

## Rodada 11 — grande atualização (plano: PLAN_RODADA11.md) (2026-06-11)
Aprovado: 1 agente em fases (não 8 paralelos); rename só texto; revelar aposta no
kickoff; perfil público com ranking+pontos. Fundações F0 PRONTAS:
- F0.1 [CODE] users.bio + SCHEMA_VERSION=3 + migração idempotente cross-dialeto
  (_migrate/_column_exists, whitelist PRAGMA p/ passar scanner). test_migration.
- F0.2 [CODE] services/profiles.public_profile (SEM email/google) + GET
  /api/users/{id} + PATCH /api/profile aceita bio + user_payload.bio. test_profiles.
- F0.3 [CODE] services/public_bets (revela só pós-kickoff) + GET
  /api/matches/{id}/bets + GET /api/live/matches. bets_repo.for_match. test_public_bets.
- F0.4 [CODE] anti-contraste definitivo: TODA cor via token (12 literais
  tokenizados), modal agora SÓLIDO (var(--surface-solid)) — corrige modal escuro
  no claro; novos tokens --overlay/--glow-*/--red-*/--gold-border; TRAVA no
  verify.sh (falha se voltar cor hardcoded fora de tokens.css).
- F0.5 [CODE] CSRF à prova de falha: logout/clear_session_cookies REEMITE
  csrf_token (não apaga); api.js re-tenta 1x em 403-CSRF buscando config. api.test.
- Status testes: core 160, node 21, py_compile ok. (D013..D014 mantidos.)
- D015 ACTIVE: revelar apostas públicas só a partir do kickoff (bet_open=false).
- NEXT: fases A..H (flags IN/SC tamanho, bugs/modal-singleton, perfil, ao-vivo,
  perfis clicáveis, rename+subtítulos, redesign ranking/mata-mata, crítica).

### Rodada 11 — progresso (fases A,B,F-parcial) 2026-06-11
- A [CODE] .flag-abbr 0.8em fonte normal (era 0.62em mono, ficava menor que os
  pares). Teste estrutural ui.test (flagContent → span .flag-abbr "IN"). Paridade
  de pixel a confirmar na tela pós-deploy.
- B [CODE] modal() é singleton: remove .modal-backdrop aberto antes de abrir
  (corrige janelas empilhando no admin ao clicar várias vezes).
- F-parcial [CODE] rename "Futebolão"→"Tabolão" (title, splash, brand, login,
  token comment); subtítulos novos de Tabela/Mata-mata/Ranking/Apostas.
  (Falta: opção "Live" dentro de Apostas — vai junto da aba Ao Vivo / fase D.)
- Verde: core 160, node 23, node --check 0 fail, py_compile ok, trava contraste ✓.
- FALTAM (próxima leva): C perfil (descrição/histórico/botões sair-perfil),
  D aba Ao Vivo + sub-bio, E perfis clicáveis, F-live, G redesign ranking/
  mata-mata + animações, H crítica. Fundações p/ tudo isso já prontas (F0.*).

### Rodada 11 — CONCLUÍDA (fases C–H) 2026-06-11
- C [CODE] perfil reformulado: aba "Perfil" saiu da navbar; foto abre o perfil;
  botão SAIR = portinha com círculo vermelho (.logoutbtn, maior); caixa de
  DESCRIÇÃO (bio via PATCH); HISTÓRICO colorido (dourado=cravada, verde=
  resultado, vermelho=erro). Email saiu do subtítulo (vai num card). outcomeClass
  testado (ui.test).
- D [CODE] nova aba "Ao Vivo" (views/live.js, rota ao-vivo): jogos LIVE agora +
  foto/nome/aposta pública de cada jogador (revelada no apito). Sub-bio do perfil
  coberta na fase C.
- E [CODE] views/profile_modal.openProfile: clicar em jogador (ranking/podium e
  aba Ao Vivo) abre perfil público (nome/foto/descrição/ranking+pts/histórico;
  sem email/Google).
- F-live [CODE] aba "Ao vivo" em Minhas Apostas (status=live); Encerradas agora
  = só finished (live não aparece lá).
- G [CODE] redesign/polish (CSS, 100% via token): pódio #1 com glow/float, top-3
  coloridos, hover em cards (match/live/bracket), glow no filtro ativo, final do
  mata-mata pulsante, micro-interações; keyframes floatY/glowPulse.
- H: revisão crítica + verificação. core 160, node 24, node --check 0 fail,
  py_compile ok, contraste 100% tokenizado, todos <250 linhas. SEM pendências.
- D016: novas chaves de cache no front: store.live + ENDPOINTS.live; SSE invalida
  live junto. Novos endpoints: /api/users/{id}, /api/live/matches,
  /api/matches/{id}/bets (todos exigem login; público não vaza email/Google).
- NEXT [USER]: git add -A && commit && push origin master (deploy Cloud Run).

### Rodada 12 — performance percebida (2026-06-11)
- openProfile agora abre o modal INSTANTÂNEO com skeleton e preenche ao chegar
  (antes dava await antes de abrir → sem feedback). [CODE profile_modal.js]
- data.prefetch + main.js: 600ms após o 1º paint, aquece matches/standings/
  leaderboard/bracket em 2º plano → abas ficam instantâneas (cache + SSE). [CODE]
- NOTA cold start: "1ª carga lenta após recarregar" é principalmente cold start
  do Cloud Run (min-instances=0 → container dorme). Fix real = min-instances=1
  (config no Cloud Run, custa um pouco), não código. [USER decide]
- core 160, node 24, node --check ok, contraste tokenizado.

### Rodada 12b — cache do ranking em 2 camadas (2026-06-11)
- D017 ACTIVE: leaderboard separa PONTUAÇÃO (cache por data_version — só muda com
  placar/edição-admin) da EXIBIÇÃO (users_repo.list_all mesclado FRESCO a cada
  chamada: quem entrou/nome/foto sempre atuais). Perfil reusa o índice cacheado,
  NÃO recalcula por abertura. [CODE leaderboard.py]
- users_version REMOVIDO (virou redundante): a mescla fresca já reflete membership/
  nome/foto sem re-pontuar. Tirados os bumps (users.py) e get/bump_users_version +
  seed (schema.py). Comentário do test_leaderboard atualizado.
- I009: relógio-bomba em test_public_bets (apostava no jogo 2 já passado) — teste
  agora move o kickoff p/ o futuro (clock-independent).
- Verde: core 160, node 24, node --check ok, contraste tokenizado.
- min-instances: setting do Cloud Run (console), não do repo — usuário já pôs 1.

## Rodada 13 — polish de UI (retomada do fable; agentes 4–7) (2026-06-15)
Continuação da sessão "Eight design agents coordination" do fable, que travou no
limite de uso após coordenar `frontend/DESIGN_SYSTEM.md` (Ag.0) + concluir Ag.1–3
(bandeiras Twemoji incl. ENG/SCO; aba Tabela; aba Jogos). Fable 5 foi descontinuado
(403 "use Opus 4.8"), então Opus retomou do ponto exato (Ag.4) e rodou Ag.4–7
SEQUENCIALMENTE (pipeline do DESIGN_SYSTEM §8 — editam views.css/components.css
compartilhados, não podem rodar em paralelo), com testes por agente. [USER pediu retomada; TOOL]
- Ag.4 Ao Vivo [CODE]: live.js — bloco de placar coeso (grid 1fr/auto/1fr), dot
  pulsante reforçado (.chip-live .dot em base.css), cards de bettor brancos
  (--card-bg), palpite NEUTRO vs pontuação em destaque, ordenação por quem pontua
  (sortBettors), truncamento+title (shortName), estados is-scoring/is-exact.
  +tests/live.test.js (3). Seção "Ao Vivo (Agente 4)" em views.css.
- Ag.5 Mata-mata [CODE]: bracket.js — card centrado com conector "×", placeholder
  circular de bandeira (fim do tracejado), tag de data legível (--text-1), chip
  ativo com --text-on-accent, H1 grad-text. Filterbar CANÔNICA criada em
  components.css (consumida por Jogos/Mata-mata/Apostas). +tests/bracket.test.js
  (3, fmtMatchDate). Removidos CSS órfãos (.bracket-cols/.count-badge global).
- Ag.6 Ranking [CODE]: leaderboard.js — "Como Jogar" com ícone help (era emoji ❓
  vermelho/baixo contraste), pódio truncado+title e pts em --text-0 (ouro só p/ 1º),
  colunas alinhadas/tnum, zebra striping, medalha (ícone novo) no top-3, empates
  (medalForPosition/tiedPositions). Ícones help+medal ADD em ui.js (ICON_PATHS, sem
  remoções). +tests/leaderboard.test.js (4).
- Ag.7 Apostas [CODE]: mybets.js — barra de status única (troféu/alvo/tique) no
  lugar de 3 cartões; filtros na filterbar canônica c/ dot "ao vivo" + count-badge;
  betbox.js — editor com 2 campos numéricos limpos (sem stepper) + "×", botão
  full-width, countdown com barra de progresso (clampScore/kickoffProgress). lockedView
  (Ag.3) PRESERVADO (override CSS escopado via :has(.bet-inputs)). +tests/betbox.test.js (5).
- D018 ACTIVE: criado `frontend/css/views-extra.css` (overflow do views.css p/ caber
  ≤300 LOC) + `<link>` após views.css no index.html. Seções Mata-mata/Ranking/Minhas
  apostas vivem lá; views.css mantém ponteiros. [CODE Ag.5; usado por Ag.6/7]
- FIX coordenação (Ag.0/Opus) [CODE]: components.css `.match-card:hover` tinha
  `rgba()` hardcoded (resquício do Ag.3) que QUEBRARIA a trava de contraste do
  verify.sh (o -o extrai o rgba, o filtro var( não pega) → trocado por var(--shadow-1)
  (theme-aware). Único literal fora de tokens.css; agora trava VERDE.
- Verificação [TOOL]: node --test = 43 verdes (28 base +3+3+4+5), 0 fail; node --check
  OK em todos os js; trava de contraste VERDE (0 cor hardcoded fora de tokens.css em
  base/components/views.css); todos os arquivos ≤300 LOC (components.css 296 é o maior).
- I010 (ambiente, relacionado a I001/I002): o mount bash (virtiofs) serviu versões
  STALE/TRUNCADAS de arquivos recém-escritos pelo file tool (live.js/bracket.js/
  ui.js/leaderboard.js etc. liam truncados no `cat`/`cp`/`node`), e `rm` deu EPERM.
  O file tool (Read/Write) = VERDADE (disco Windows). Mitigação: verificação rodada
  reconstruindo os arquivos em /tmp a partir do conteúdo do file tool; `rm` dos
  temporários resolvido com a permissão de delete do cowork. NÃO confiar em
  `wc`/`ls`/`node --check` do bash p/ arquivo recém-escrito nesta sessão. [TOOL]
- NEXT [USER] (máquina local, repo): `git add -A && git commit -m "feat(ui): polish abas Ao Vivo/Mata-mata/Ranking/Apostas (agentes 4-7) + DESIGN_SYSTEM, views-extra.css" && git push origin master`. Deploy automático (Cloud Run). Conferir visual nos 2 temas após subir.

## Rodada 14 — 5 bugs pós-deploy (2026-06-16)
[USER] reportou 5 problemas; corrigidos em ordem:
- BUG1 tabela do Ranking quebrada (posição em cima, nome embaixo): causa = `display:flex`
  direto no `<td>` (pos e player) quebra a linha da tabela. Fix: conteúdo das células
  em wrappers `.pos-inner`/`.player-inner`; `<td>` volta a ser célula; `table-layout:
  fixed` + larguras (#40 / Pts48 / num66) p/ números alinharem e nome truncar.
  [CODE leaderboard.js, views-extra.css]
- BUG2+BUG3 (mesma raiz) animações "aceleradas" + tela piscando: cada update SSE
  ZERAVA os caches (`matches:null`…) → view piscava p/ skeleton e voltava; + tickers
  de 30s (`store.set({})`) re-renderizavam o app TODO (replaceChildren recarrega
  imagens/reinicia animações). Fix: (a) data.js revalida sem piscar (Set `stale` +
  `markStale`/`refreshData`; `ensureData` devolve o dado atual e revalida em 2º plano);
  (b) main.js rastreia versão em closure (sem re-render só por bump) e revalida só a
  view ativa; (c) tickers removidos de matches.js/mybets.js → novo `countdown_ticker.js`
  atualiza os countdowns IN-PLACE (texto/largura) a cada 1s, sem re-render.
  [CODE data.js, main.js, countdown_ticker.js (novo), betbox.js (+data-kickoff),
  matches.js, mybets.js]
- BUG4 histórico do perfil incompleto/fora de ordem: `closed_history` não trazia
  `kickoff_utc` e o front ordenava por `match_id` (≠ cronológico). Fix: backend inclui
  `kickoff_utc` e ordena desc (mais recente 1º); front ordena por `kickoff_utc` desc.
  [CODE services/profiles.py, profile_modal.js]
- BUG5 minutagem ausente no Ao Vivo: `m.minute` vem null (sem provider/admin). Fix:
  novo `format.liveMinute(kickoff, serverMinute)` — usa o minuto do servidor se houver,
  senão ESTIMA pelo relógio (com ~15min de intervalo). Usado em live.js e matches.js.
  [CODE format.js, live.js, matches.js]
- Verificação: core backend 160/160 (profiles.py reconstruído no /tmp p/ furar o
  cache do mount); liveMinute 10/10 (teste standalone + novo teste em format.test.js);
  todos os arquivos editados inspecionados (sintaxe ok), sem refs órfãs
  (minuteLabel/ticker), sem cor hardcoded. [TOOL]
- I010 reincidiu forte: o mount do bash serviu TODOS os arquivos recém-escritos
  truncados (node --check/py_compile falhavam no mount, mas o disco via file tool
  estava íntegro). Suíte frontend não roda limpa aqui; rodar `node --test` localmente.
- NEXT [USER]: `git add -A && git commit -m "fix(ui): tabela do ranking, flicker/anim (revalida sem piscar + countdown in-place), historico por data, minutagem ao vivo" && git push origin master`. Deploy Cloud Run; conferir nos 2 temas.

## Rodada 15 — redesign da aba Tabela + tema escuro padrão (2026-06-16)
- Aba TABELA (standings dos grupos, dashboard.js) refeita conforme crítica do [USER]:
  * SEM rolagem horizontal (mobile e desktop): `.standings-table` agora é
    `table-layout: fixed; width:100%` (numéricas 26px fixas, nome trunca); removido
    `overflow-x:auto` do `.group-card`; grid `minmax(min(100%,340px),1fr)` p/ nunca
    exceder a viewport (e body já tem overflow-x:hidden como rede).
  * Contraste/redundância: removidas as PÍLULAS atrás da posição e os FUNDOS de
    linha (verde/dourado) — fim do "3" dourado sobre pílula clara. Zona agora é só
    BORDA ESQUERDA colorida no nome (verde 1º–2º, dourado 3º). Posição = texto.
  * Hierarquia: nome 700/--text-0; estatísticas (J V E D GP GC SG) 500/--text-1
    fs-xs (não competem); Pts 800/--text-0 fs-sm (âncora à direita).
  * Espaçamento: gap pos↔bandeira↔nome 10px; cabeçalho com divisória mais forte
    (2px --border-strong) que as linhas (1px --border); tabular-nums em tudo.
  [CODE views/dashboard.js, css/views.css seção Dashboard]
- D019 ACTIVE: TEMA PADRÃO = ESCURO (claro só por escolha explícita). theme.js
  getTheme() default 'dark'; init inline do index.html default 'dark'; meta
  theme-color #04070f. [USER pediu]
- Verificação: dashboard.js + theme.js node --check OK (via /tmp); views.css sem
  cor hardcoded (trava verde), seções intactas, `pos-badge` 100% removido; ≤300 LOC.
  Mount I010 segue truncando no bash — validado por /tmp + file tool. [TOOL]
- NEXT [USER]: `git add -A && git commit -m "feat(ui): tabela sem rolagem + criticas (borda de zona, hierarquia, contraste); tema escuro padrao" && git push origin master`. Deploy Cloud Run.

## Rodada 16 — 9 features + reorg de agentes (2026-06-19)
[USER] pediu: reescrever instruções de agentes num único .md + executar em loop.
- `PLANO_RODADA16.md` = ÚNICA fonte de instruções p/ agentes (Contratos §1, Agente 0
  tests-first, Agentes 1–10, loop/DoD). `AGENTS.md` e `PLAN_RODADA11.md` APAGADOS;
  `TESTPLAN.md` e `frontend/DESIGN_SYSTEM.md` reescritos SEM instruções de agente. [CODE]
- D020 ACTIVE (supersede D005): mata-mata pontua pelo placar do FIM DA PRORROGAÇÃO
  (antes dos pênaltis); pênaltis descartados (só definem o vencedor). [USER]
- D021 ACTIVE: schema v4 — matches.period/stoppage/home_pens/away_pens/pens_log
  (migração idempotente). provider `_score_pair`=fullTime; parse extrai period/pens.
- BACKEND (Agentes 1–4) COMPLETO + VERDE: **184 testes core OK** (160 + 24 novos).
  H (scoring ET) · C (kickoff auto: poller idle 5min + PRE_WINDOW 30min + sync) ·
  B-dados (period/pens nos payloads matches/live) · D-back (mark_qualifying_thirds +
  third_qualifying) · E-back (predicted_bracket_payload, `predicted` por lado) ·
  F (ranking densa 1,1,1,2). /api/bracket agora devolve o preditivo.
- I011 (=I010, pior): o mount virtiofs serve TRUNCADO todo arquivo EDITADO nesta sessão
  (cat/cp/python leem cortado). File tool = VERDADE (disco). Verificação feita
  reconstruindo os 15 arquivos editados via sidecars `_r16_*.py` (arquivo NOVO propaga
  ok) em /tmp/bk3 → 184 OK; sidecars apagados. `pytest tests/api` só roda no gate Docker.
- FRONTEND (Agentes 5–9) COMPLETO + VERDE: **61 testes node OK**, node --check limpo.
  A (tema escuro default + reset único `theme_reset`) · B (relógio `liveClock`
  45+X/90+X/prorrogação/pênaltis + mini-placar `pensBoard`) · D-front (tabela:
  amarelo só nos 3ºs que passam, vermelho nos demais via `zoneFor`) · E-front
  (mata-mata preditivo: banner + chip "prev." + lado projetado) · F+G (pódio por
  POSIÇÃO via `podiumSlots`: empate em 2º = 2 pratas, 0 bronze; ranking denso) ·
  I (aba JOGOS unificando Jogos+Ao Vivo+Apostas: subdivisões Futuros/Ao vivo/
  Encerrados, filtro por fase, ordenação, fundo verde/dourado/vermelho;
  "Como Jogar" movido p/ cá em `howtoplay.js`).
- D022 ACTIVE: rotas `ao-vivo`/`apostas` → redirect p/ `jogos` (links antigos seguem ok);
  nav = Tabela · Mata-mata · Jogos · Ranking. `mybets.js` e `renderMatches` ficam
  órfãos (mas `matchCard`/`liveContent` são reusados); não removidos p/ não arriscar.
- Verificação Rodada 16 [TOOL]: core **184 OK**; node:test **61 OK**; node --check limpo;
  CSS novo 100% via token; arquivos novos ≤300 LOC. Reconstrução via sidecars `_r16_*`
  em /tmp (I011) p/ furar o mount truncado; sidecars apagados. Visual nos 2 temas: conferir no deploy.
- State: TODAS as 9 features entregues e VERDES nos testes automatizáveis (core + node).
- NEXT [USER]: `git add -A && git commit -m "feat(r16): scoring ET, sync auto, 3os/mata-mata preditivos, ranking denso/podio, tema escuro, aba Jogos unificada" && git push origin master`
  (deploy Cloud Run); `docker build .` local roda o gate `pytest tests/api`. Conferir
  visual nos 2 temas após subir.

### Rodada 16 — I012: horário "voltava" pro hardcoded (2026-06-19)
[USER] mostrou: API paga TEM o horário novo (BRA×HAI J29 = 21:30) mas o site mostra
22:00. Causa-raiz (NÃO era a cadência do poller): `main.py` roda `seed()` a CADA boot
e `matches.upsert_fixture` reescrevia `kickoff_utc = excluded` no ON CONFLICT → todo
cold start do Cloud Run revertia o horário pro hardcoded de `fixtures.txt`
(J29 = 2026-06-20T01:00Z = 22:00 BRT). Placar atualizava (seed não toca placar); só o
horário voltava. FIX: `upsert_fixture` NÃO atualiza mais `kickoff_utc` no ON CONFLICT
(grava só no 1º INSERT; provider/admin donos depois). +`test_reseed_kickoff` (2 testes).
Core agora **186 OK**. Cadência (idle 5min/PRE 30min) segue válida, mas ESTE era o motivo
do "22h fixo". Pós-deploy, o poller corrige o J29 p/ 21:30 em ~5min e NÃO reverte mais.
[CODE db/repos/matches.py] [TOOL]

### Rodada 16 — siglas PT na Tabela (2026-06-19)
[USER] nomes da Tabela cortados, sem querer scroll → escolheu "sigla no celular,
oficial e em português". Solução: `format.siglaPt(team)` (mapa code→sigla PT dos 48
times: GER=ALE, ENG=ING, NED=HOL, USA=EUA, KSA=ARA, RSA=AFS, KOR=COR, JPN=JAP…; sem
clash ARG/ALG, AUS/AUT, IRN/IRQ; fallback = 3 letras do código). `dashboard.js`
renderiza nome completo + sigla; CSS usa CONTAINER QUERY em `.group-card`
(`@container (max-width:400px)`) → card estreito mostra sigla, card largo mostra o
nome inteiro; grid min subiu 340→440px p/ o desktop caber o nome. Verde: node:test
**65 OK** (+4 sigla); mapa validado (48, 0 duplicadas, todas 3 letras). [CODE]
- Siglas a confirmar no uso (convenção BR pode variar): NZL (Nova Zelândia), CAB
  (Cabo Verde), RDC (RD Congo), GAN (Gana), CDM (Costa do Marfim) — fáceis de trocar.

### Rodada 16 — I013: botão de tema discordava da tela (2026-06-19)
[USER] botão mostrava sol (achava escuro) mas a tela estava clara; só ia p/ escuro
no 2º clique. Causa: DOIS cálculos do tema — o inline do index.html pinta o
data-theme; o `getTheme()` recalculava por conta própria p/ o ícone do botão. Se
divergem (ex.: index.html em cache antigo sem o reset), botão e tela ficam
inconsistentes e o 1º clique "não faz nada". NÃO havia data-theme hardcoded.
FIX: `getTheme()` agora LÊ o data-theme já aplicado (fonte única = a tela); +
`initTheme()` no boot do main.js reaplica reset+tema (rede de segurança p/ cache).
tokens.css: `:root`=claro, `:root[data-theme="dark"]`=escuro (default vem do inline/init).
Verde: theme.test 4 OK + simulação dos cenários A–D. [CODE theme.js, main.js]

### Rodada 16 — enxugar filtros da aba Jogos (2026-06-19)
[USER] 3 fileiras de botão poluíam. Decisão: filtro de Fase vira DROPDOWN e só
aparece nos Encerrados; ordenar vira botão ↕ (swap_vert; ícone `sort` novo em
ui.js) à DIREITA; "Como Jogar" à direita também no celular. [CODE]
- jogos.js: Futuros/Ao vivo SEM filtro de fase; closedView usa `phaseSelect`
  (<select> "Fase") + `sortButton` (↕) em `.closed-controls` (space-between).
  Removidos phaseFilter/sortToggle (pílulas) e o estado `futurePhase`.
- Fix Como Jogar à esquerda no mobile: `.page-head` tem flex-wrap, e space-between
  alinhava o botão à esquerda quando quebrava linha → `.page-head .howtoplay-btn
  { margin-left:auto }` (classe nova no howToPlayButton).
- CSS novo (views-extra) 100% via token; node:test **65 OK**; node --check jogos OK.
- NOTA: Futuros ficou SEM filtro de fase (pedido do user). Reverter é trivial se quiser.

### Rodada 16 — palpites de todos no jogo encerrado (2026-06-19)
[USER] clicar num jogo encerrado deve mostrar os palpites de TODOS, mesma lógica de
cores. FEITO: cartão encerrado vira clicável (role=button + Enter/Espaço) → modal
`openMatchBets` (novo `js/views/match_bets_modal.js`) que busca `GET /api/matches/
{id}/bets` (endpoint já existia, usado pelo Ao Vivo) e lista cada palpite colorido
por acerto — reusa `outcomeClass` (hist-gold/green/red) + `.hist-item`/`.hist-list`;
cada linha abre o perfil público. CSS novo em `css/match-bets.css` (+`<link>` no
index.html) p/ não estourar os 300 LOC dos CSS existentes. Verde: node:test 65 OK;
node --check ok. [CODE jogos.js, match_bets_modal.js, match-bets.css, index.html]

### Rodada 16 — relógio ao vivo quebrado + logout frequente (2026-06-19)
[USER] (1) cronômetro da sub-aba "ao vivo" sumiu (só o dot vermelho); (2) app
deslogando muito, quer só pedir login no logout manual.
- I015 relógio: o payload de `/api/live/matches` NÃO tinha `status`, e o novo
  `liveClock` retornava '' quando `status !== 'live'` (regressão vs o antigo
  `liveMinute`, que não checava status). FIX: live_matches passa a enviar `status`;
  e `liveClock` só esconde se o status for EXPLICITAMENTE não-live (sem status =
  assume ao vivo). [CODE services/public_bets.py, js/format.js]
- I014 logout frequente: `rotate` revogava a FAMÍLIA inteira a qualquer reuso de
  refresh. Com access de 15min, 2 abas/retry mandam o MESMO refresh no mesmo ciclo
  → falso "replay" → derrubava todas as sessões. FIX: janela de graça de 60s — reuso
  logo após a rotação = corrida benigna (só re-emite, NÃO derruba). Logout e a
  resposta a replay agora APAGAM o token (`tokens_repo.delete`/`delete_all_for_user`)
  p/ não caírem na graça (logout mata na hora; replay tardio mata tudo). Sessão dura
  os 30d do refresh renovando sozinha → só pede login no logout manual (ou 30d sem abrir).
  [CODE core/tokens.py, db/repos/tokens.py] +3 testes (corrida benigna/replay tardio/logout).
- Verde: core **188 OK**; node:test **65 OK**; node --check limpo.

### Rodada 16 — multi-dispositivo + hover dos filtros (2026-06-19)
[USER] (1) 3 dispositivos na mesma conta dão problema? (2) hover dos botões da aba
Jogos corta o topo.
- Multi-dispositivo: cada login = cadeia de refresh INDEPENDENTE (3 aparelhos = 3
  cadeias; rotacionar uma não toca nas outras — funciona no uso normal). Para blindar
  o caso raro de rede (refresh cuja resposta se perdeu, re-tentado >60s depois),
  TROQUEI a resposta a reuso tardio: de "revoga TODAS as sessões" (delete_all) para
  REJEITAR SÓ aquele token (TokenInvalidError) — o aparelho re-loga sozinho, os outros
  seguem. Roubo de token velho continua bloqueado (token rejeitado); abre mão só do
  "roubo desloga em todo lugar" (ok p/ bolão de amigos). (supersede a parte de
  delete_all do I014.) +test_tres_dispositivos_independentes / _reuso_tardio_rejeita_so_o_token.
  [CODE core/tokens.py, tests]
- Hover cortando o topo: `.filterbar` tinha `padding-bottom:6px` mas SEM top, e
  `overflow-x:auto` força clip vertical → o lift do hover (translateY -1px) e o glow
  do chip ativo cortavam em cima. FIX mínimo: `padding: 6px 0` (top simétrico ao bottom
  que já existia — completa a intenção original). [CODE components.css]
- Verde: core **189 OK**; node:test 65 OK.

### Rodada 16 — relógio ao vivo travado em 45' (2026-06-19)
[USER] aos 74' o relógio marcava 45'. Causa-raiz: o provider quase nunca manda
`minute` ao vivo na LISTA de jogos (vem null); aí `_derive_period` caía em '1H' e o
`liveClock` mostrava a base "45'". (Regressão minha: troquei o `liveMinute`, que
ESTIMAVA pelo relógio, por confiar no period/minute do provider.) FIX (frontend,
format.js): `liveClock` volta a ESTIMAR pelo tempo decorrido desde o kickoff quando
não há minuto confiável (`_estimateClock` = modelo do liveMinute + acréscimos 45+X/90+X);
usa o minuto do provider só quando vier número >0; estados parados (HT/ET_HT/PENS)
vêm do period. +teste (89min de relógio → "74'", não 45'). node:test verde.
[CODE js/format.js, tests/clock.test.js]

## Rodada 17 — relógio dirigido por STATUS (não por chute de tempo) (2026-06-20)
[USER] corrigiu o approach da R16: se o provider sinaliza intervalo/volta/fim de forma
confiável (status), NÃO se deve estimar/adivinhar o intervalo por tempo — só contar o
minuto dentro da fase e seguir 45+X/90+X até o provider mudar o status.
- D023 ACTIVE (supersede o `_estimateClock` como caminho principal da R16): o relógio
  ao vivo é dirigido pelo STATUS. O backend roda uma MÁQUINA DE FASE (`sync._next_period`,
  pura) a partir de status+duration+fase-anterior (o `minute` vem null e NÃO é usado p/
  fase): kickoff→1H, PAUSED→HT, volta→2H, EXTRA_TIME→ET1/ET2 (ET2 só após ET_HT),
  PENALTY_SHOOTOUT→PENS, FINISHED→FT. Carimba `period_started_at` SÓ na transição p/ fase
  que corre (1H=kickoff; 2H/ET1/ET2=agora). O front (`liveClock`) conta `base+(agora−carimbo)`
  e mostra `limite+X` ao passar do fim do tempo, até o provider mudar a fase. Precedência:
  minuto do provider (se >0) > contagem desde o carimbo > estimativa pelo kickoff (só
  último recurso/legado). `_estimateClock` permanece como fallback. [CODE]
- D024 ACTIVE: schema **v5** — nova coluna `matches.period_started_at TEXT` (migração
  idempotente em `_MATCH_V4_COLUMNS`); entidade/repo/results/sync/payloads (matches+live)
  threaded; ScoreUpdate ganhou `paused`/`duration` (status cru p/ a máquina). [CODE]
- Doc confirmada (docs.football-data.org/general/v4/match.html): status workflow
  IN_PLAY→PAUSED→FINISHED é o sinal de fase ("players rest (PAUSED)", "final whistle →
  FINISHED"); LIVE = IN_PLAY+PAUSED. Existe `minute` (top-level) e `injuryTime` — mas na
  prática vinham null ao vivo (origem do bug R16). Design novo é robusto aos dois casos.
  injuryTime fica como melhoria futura p/ acréscimo exato (hoje some por elapsed). [TOOL]
- I016 (=I011, pior): NESTA sessão o mount truncou TODO arquivo editado (entities@115,
  format.js@119, etc.) — `cat`/`cp`/`python`/`node` liam cortado; `git status` marcava
  tudo M (truncação parece deleção). Verificação furou o mount via `git archive HEAD`
  (lê do object store, sem truncar) → árvore R16 limpa em /tmp + overlay dos diffs R17
  (patches `old→new` precisos) + sidecars `_r17_*` (arquivo novo propaga). File tool =
  VERDADE (disco Windows intacto; o app do usuário NÃO é afetado). [TOOL]
- Verificação R17 [TOOL]: core **202 OK** (+13: `test_sync_period` máquina de fase +
  carimbo) ; node:test **66 OK** (+1: contagem desde o início da fase, sem chutar
  intervalo) ; todo .py do backend parseia ; format.js `node --check` ok.
- NEXT [USER]: `git add -A && git commit -m "feat(r17): relogio ao vivo dirigido por status (period_started_at, maquina de fase); schema v5" && git push origin master` (deploy Cloud Run). Conferir num jogo ao vivo: 1ºT conta do apito, vira "Intervalo" só quando o provider pausar, 2ºT conta de 45, "90+X" até o apito final.

## Auditoria de más práticas (2026-06-21)
- 2026-06-21 [TOOL] Revisão crítica integral -> `AUDITORIA_MAS_PRATICAS.md` (raiz).
- ACHADO CRÍTICO C1 [CODE]: regra do mata-mata CONTRADIZ este ledger. Invariants
  ("placar dos 90min") + D005 dizem 90min; código/UI/teste usam FIM DA PRORROGAÇÃO
  (`howtoplay.js:30`, `test_scoring_knock
## Rodada 17 — correções da auditoria (2026-06-21)
Decisões do [USER] (3 rodadas de perguntas): C1=fim da prorrogação (corrigir docs);
C2=pênaltis manuais completos (placar+log); A3=recalcular bracket do zero; A2/A4=pool
+ 1 instância; A1=apagar dead code e reapontar testes; M3=boot fail-fast em prod;
M5=pin exato+lockfile; refactors=todos (B2/B4/B5); M2=match forte; M6=pênaltis no
bracket; B6 poller=5min; B1=endurecer adapter.

### DONE + VERIFICADO (suíte core: 212 testes verdes no sandbox)
- M1 [CODE/BUG REAL achado na verificação]: `_score_pair` usava `fullTime` cru, mas a
  doc oficial football-data v4 SOMA os pênaltis no fullTime (ET 1x1 + pên 6x5 ⇒
  fullTime 7x6). Corrigido: fullTime − penalties. Fixtures dos testes (que eram
  IRREAIS) corrigidos. [web_fetch docs.football-data.org/general/v4/overtime.html]
- C2 [CODE]: `AdminScoreIn` + endpoint admin aceitam home_pens/away_pens/pens_log;
  `_validate_pens_log` (fail loud). +2 testes.
- A3 [CODE]: `bracket_svc.rebuild_bracket` (limpa KO scheduled + re-propaga, atômico);
  `/api/admin/recompute` e `cli recompute` usam o rebuild. +3 testes (test_bracket_rebuild).
- M2 [CODE]: `sync._find_local` exige match forte (external_id OU 2 códigos); sem
  isso pula+loga (não adivinha por "único candidato"). +1 teste.
- M3 [CODE]: `config.load_settings` derruba o boot se DATABASE_URL presente e
  PUBLIC_BASE_URL ausente/localhost/http ou COOKIE_SECURE!=true. +4 testes.
- Dead code: removidos `TokenReuseError` (tokens.py) e `TLA_FIXES` (no-op, football_data).
- C1/B6/B3 docs: README + ARCHITECTURE(já ok) + invariante; D005 SUPERSEDED; D009=5min;
  docstrings poller/tokens; .env.example e-mail→placeholder + notas M3.

### NEXT (lote 2 — ainda não feito)
- B5 DTO em set_score (camada de serviço; repo estável); A2 pool de conexões;
  B1 adapter (placeholder/DDL split/cursor psycopg2); remover _derive_period+ScoreUpdate.period.
- Frontend: A1 dead code (mybets.js/renderMatches/renderLive/bracket_payload + reapontar
  betbox.test/test_bracket_svc/format.test); C2-UI (inputs de pênaltis no admin.js — SEM
  isso o C2 não é usável end-to-end no modo manual); M6 (pênaltis no bracket.js); M4
  (unificar em liveClock, remover liveMinute/minuteLabel); B4 (estado de UI → store).
- M5 deps pin+lock; B2 teste de paridade dos multiplicadores front×back.

### Gate autoritativo (I010 impede suíte completa confiável no sandbox)
- Sandbox: `python3 backend/run_core_tests.py` rodou 212 verdes (via espelho /tmp por
  causa do I010 que trunca leituras de arquivos recém-escritos no mount).
- [USER] rodar localmente: `bash scripts/verify.sh` + `docker build .` (gate pytest HTTP).

### Rodada 17 — LOTE 2 concluído (2026-06-21)
Todas as pendências da auditoria fechadas. Verificado no sandbox (espelho /tmp por I010):
core 213 testes verdes; front node --test 67 verdes + node --check limpo; contraste
(0 cor fora de tokens), ≤300 LOC, innerHTML/eval zero, TODO/FIXME zero, py_compile OK.
- B5 [CODE]: DTO `ScoreDetails` em domain/entities; `results.set_score(.., *, force,
  set_lock, details)` (era 14 params). Callers (admin/sync) e testes atualizados. Repo estável.
- B1 [CODE]: adapter SQL endurecido — `_to_pg_placeholders` (ignora ? e dobra % dentro de
  strings), `_split_statements` por ';' fora de string, cursor do psycopg2 fechado. +3 testes.
- A2 [CODE]: pool de conexões Postgres (psycopg_pool) no lifespan + get_db (checkout/return);
  SQLite inalterado. DEPLOY: Cloud Run max-instances=1 (SSE/cache/rate-limit em memória).
- A1 [CODE]: removidos mybets.js (delete), renderMatches, renderLive, bracket_payload,
  minuteLabel, liveMinute, _derive_period, ScoreUpdate.period. Testes reapontados
  (betbox→jogos.tallyBets; test_bracket_svc→matches_repo+source_label; format→liveClock).
- M4 [CODE]: relógio ao vivo unificado em liveClock; matches.js usa-o; format.test cobre liveClock.
- M6 [CODE]: pênaltis exibidos no bracket.js (.bracket-pens em views-extra.css, layout só).
- C2-UI [CODE]: inputs de pênaltis (tally + pens_log) no admin.js → /api/admin/score.
- B4 [CODE]: estado de UI (jogosTab/closedPhase/closedSort/bracketStage) no store (slice `ui`
  + setUi); fim do `store.set({})` vazio nessas views.
- B2 [CODE]: test_multiplier_parity — multiplicadores/pontos front (points.js) × back batem.
- M5 [CODE]: requirements pinados exato + psycopg-pool; alvo `make lock` (pip-compile/hashes).
- Bônus: verify.sh — grep de TODO agora usa \bTODO\b (não casava "TODOS" em português).
- D012 status: mantido por padrão; `/api/admin/recompute` e `cli recompute` agora fazem
  rebuild do zero (A3) — o admin tem o opt-in de um clique.
- NEXT [USER] (local): `bash scripts/verify.sh` + `docker build .` (gate pytest HTTP);
  rodar `make lock` 1x p/ gerar requirements.lock; setar max-instances=1 no Cloud Run.

## Rodada 18 — "lembrar de mim" / blindagem do deploy (2026-06-21)
- [USER] pedido: ninguém deve cair a cada deploy (só por motivo sério de segurança).
  Diagnóstico: a sessão JÁ é persistente (cookie 30d + refresh rotacionado/deslizante
  + refresh-em-401 silencioso no api.js). Logout-no-deploy NÃO é código: é Cloud Run
  com SQLite EFÊMERO (sem DATABASE_URL) — cada deploy/cold start zera contas+apostas+sessões.
- D025 ACTIVE: boot RECUSA subir em plataforma de disco efêmero (Cloud Run via K_SERVICE)
  sem DATABASE_URL (config.py `_detect_ephemeral_platform`); escape explícito
  ALLOW_EPHEMERAL_DB=true só p/ descartável. +4 testes (tests/core/test_config_guard.py).
- D026 ACTIVE: boot loga fingerprint sha256[:8] de SECRET_KEY/PEPPER (NÃO-reversível) via
  _log_boot_fingerprint (main.py) + basicConfig(INFO). Se a fp mudar entre deploys, a chave
  não está fixa = causa de "caiu todo mundo". Nunca loga o segredo em si.
- I017 (=I011/I016, RECORRÊNCIA): ao chegar, o working tree tinha ~20 arquivos TRUNCADOS no
  disco (main.py@116, config.py, connection.py, requirements.txt@1L, tokens.py, schemas.py,
  +6 do frontend). master ÍNTEGRO e atual (commit 4560ffc). Recuperação: `git archive master`
  p/ FS local, validar (217 testes OK), restaurar cada truncado via `cp`+md5 em loop
  (Edit/open() truncam no virtiofs; cp+verificação md5 gruda). Entrega = PATCH sobre master.
- NEXT [USER] (Cloud Run, resolve o logout): setar DATABASE_URL (Supabase) + SECRET_KEY/PEPPER
  FIXOS no Secret Manager + `--min/max-instances 1`; aplicar futebolao-remember-me.patch sobre
  master (`git restore .` antes, limpa truncamentos); commit+push. Guia: README "Deploy: Google Cloud Run".

## Rodada 19 — sessão grudenta (fim do logout falso) (2026-06-21)
- [USER] sintoma: pessoas (e o próprio dono) deslogadas em horas imprevisíveis, mesmo
  com DATABASE_URL+SECRET_KEY fixos no Supabase. Tentativa anterior (aumentar tempo de
  cookie) não resolveu — nada expira; o servidor é que RECUSAVA o refresh.
- Causa-raiz: rotate() rejeitava reuso de refresh já rotacionado após 60s (REUSE_GRACE).
  Reuso tardio é comum e legítimo: celular dormindo, resposta de rede perdida, cold start
  do Cloud Run, várias abas → "sessão expirada" falsa. E o api.js desistia na 1ª falha de
  refresh (sem retry) → logout em qualquer 429/5xx/oscilação.
- D027 ACTIVE (supersede D004/I014): renovação TOLERANTE. rotate() re-emite enquanto a
  LINHA do refresh existir e não expirou — token rotacionado NÃO desloga. Só rejeita quando
  a linha foi APAGADA (kill real) ou o refresh expirou. REUSE_GRACE_SECONDS removido.
- D028 ACTIVE: kills reais agora APAGAM a linha (delete), não só revogam. logout já fazia
  delete; admin_reset_password (api/admin.py) e cli reset-password trocaram
  revoke_all_for_user→delete_all_for_user → troca de senha encerra TODAS as sessões na hora.
  REFRESH_TTL 30d→90d; ACCESS fica 15min.
- Frontend: api.js tryRefresh com retry/backoff (400/1200/3000ms) p/ rede/429/5xx; desiste
  só em 401/403. +1 teste node (api.test.js). test_tokens.py reescrito (reuso tardio re-emite;
  logout/troca de senha rejeitam). Suítes: 218 core + 68 front, zero falhas.
- Troca de segurança ACEITA [USER]: refresh válido por mais tempo (detecção de replay
  relaxada); logout e troca de senha encerram na hora. Bloat: linhas revogadas acumulam
  (lookup por PK, perf ok); purge_expired disponível p/ limpeza futura [follow-up menor].
- Entrega: futebolao-remember-me.patch agora cobre TUDO (10 arquivos). Aplicar sobre master
  limpo (`git restore .` antes) + commit + push.
