# AGENTS.md — Pipeline linear de execução

Regra de ouro: **os agentes executam em sequência estrita**. Um agente só inicia quando o
anterior entregou TODOS os seus critérios de "done" (testes verdes incluídos). Nenhum agente
pode editar área de outro sem registrar em CONTINUITY.md. Todos obedecem:
≤300 LOC/arquivo de código, SQL parametrizado, sem try/except vazio, sem fallback silencioso.
Antes de codar: reler ARCHITECTURE.md + TESTPLAN.md (testes já planejados — implementá-los, não inventá-los).

---

## Agente 0 — Fundações (scaffold)
**Entrada**: ARCHITECTURE.md. **Saída**: esqueleto de pastas, configs, Makefile, scripts/verify.sh,
.env.example, .gitignore, requirements*.txt, pytest.ini, run_core_tests.py.
**Done**: `python3 backend/run_core_tests.py` executa (0 testes, exit 0); estrutura confere com ARCHITECTURE.md.

## Agente 1 — Domínio (backend puro)
**Entrada**: Agente 0. **Escopo**: `app/domain/*`, `app/db/*` (connection, schema, repos),
`app/seed/*` (loader + dados reais: teams.json, fixtures.txt 104 jogos, annex_c.txt 495 combos).
**Testes (TESTPLAN §1)**: scoring, standings, clinch, thirds+annex_c, bracket, betlock,
repos sqlite (em memória), seed (104/48/495 + invariantes).
**Done**: testes core do domínio 100% verdes no sandbox; seed valida contra dados oficiais FIFA.

## Agente 2 — Segurança & Auth (núcleo)
**Entrada**: Agente 1. **Escopo**: `app/core/*` (passwords, jwt_hs256, tokens, csrf, ratelimit),
`app/services/auth.py`, `app/services/oauth_google.py`, `app/config.py`.
**Testes (TESTPLAN §2)**: hash/verify+pepper, política de senha, JWT (exp/typ/tamper/alg),
rotação+revogação de refresh, csrf constant-time, buckets de rate limit, register/login/logout,
oauth flow com transporte fake (state inválido, e-mail não verificado, link de conta).
**Done**: testes core de segurança 100% verdes no sandbox.

## Agente 3 — Serviços de negócio
**Entrada**: Agente 2. **Escopo**: `app/services/{matches,betting,standings_svc,leaderboard,bracket_svc,results,avatars,live_bus}.py`.
**Testes (TESTPLAN §3)**: trava de aposta (antes/no/apos kickoff, status, times indefinidos),
upsert, validação de placar, leaderboard (pontos/cravadas/parciais live, cache),
standings live, bracket preditivo fim-a-fim (cenário simulado de Copa), results (transições
válidas), avatars (re-encode, rejeição de não-imagem).
**Done**: testes core de serviços 100% verdes no sandbox.

## Agente 4 — Motor ao vivo & integração externa
**Entrada**: Agente 3. **Escopo**: `app/providers/*`, `app/jobs/poller.py`, `app/cli.py`.
**Testes (TESTPLAN §4)**: normalização football-data (status/score/aliases), casamento de
jogos (external_id, data+times), manual_lock vence API, janela do poller, sync idempotente.
**Done**: testes core de providers 100% verdes; CLI seed/create-admin funcionais no sandbox.

## Agente 5 — Camada HTTP (FastAPI fino)
**Entrada**: Agente 4. **Escopo**: `app/main.py`, `app/api/*`, `backend/tests/api/*` (pytest).
**Regra**: handlers SÓ fazem parse/validação/chamada de serviço/montagem de resposta.
**Testes (TESTPLAN §5 — escritos agora, executados no Docker build/local)**: contratos HTTP,
cookies/headers de segurança, 401/403/409/422/429, CSRF exigido, SSE handshake, multipart.
**Done**: arquivos passam `python3 -m py_compile`; suite pytest escrita e plugada no Dockerfile.

## Agente 6 — Frontend base
**Entrada**: Agente 5 (contratos de API congelados). **Escopo**: index.html, css/*, js/{main,router,store,api,sse,format,points,ui,layout}.js, views/login.js.
**Testes (TESTPLAN §6)**: node:test p/ router/store/format/points; `node --check` em todo js;
greps de segurança (sem innerHTML inseguro, sem eval).
**Done**: verificações verdes no sandbox; login/registro navegáveis (smoke servindo estático).

## Agente 7 — Features frontend (6 abas + admin)
**Entrada**: Agente 6. **Escopo**: views/{dashboard,matches,bracket,leaderboard,mybets,profile,admin}.js + components.css.
**Exigências de UX**: mobile-first, tabela ao vivo com flutuação, inputs de aposta com
estado travado/aberto, countdown p/ kickoff, bracket horizontal navegável, modal "Como Jogar",
filtros em Minhas Apostas, upload com preview, skeletons, toasts, animações sutis.
**Done**: node --check verde; testes node:test das libs usadas pelas views verdes.

## Agente 8 — Integração & deploy
**Entrada**: Agente 7. **Escopo**: Dockerfile (gate de testes), docker-compose.yml, fly.toml,
README.md, .env.example final, scripts/verify.sh final.
**Done**: GOALS.md rodada 1 inteiramente verificada e marcada (evidência por comando).

## Agente 9 — Crítica & segunda rodada
**Entrada**: Agente 8 + GOALS rodada 1 verde. **Escopo**: REVIEW.md com crítica honesta de
CADA parte (domínio, segurança, API, UX/design, deploy); definir GOALS rodada 2 (novos
parâmetros incluindo as correções); implementar TODAS as correções; re-rodar TODA a verificação.
**Done**: GOALS rodada 2 100% verde. Projeto encerrado.

---

### Protocolo de falha
Teste vermelho → corrigir antes de avançar (proibido pular). Limitação de ambiente →
registrar em CONTINUITY.md (Receipts) + compensar com verificação alternativa executável.
