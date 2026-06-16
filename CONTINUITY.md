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
