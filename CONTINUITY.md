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
