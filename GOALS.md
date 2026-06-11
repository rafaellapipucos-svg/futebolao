# GOALS — parametros finais (/goal)

Execucao obrigatoria: so parar quando TODOS os parametros da rodada vigente
estiverem verificados com evidencia (comando + resultado). Limitacao de ambiente
registrada em CONTINUITY.md compensa com verificacao alternativa, nunca omissao.

## Rodada 1 — criterios

G1. python3 backend/run_core_tests.py -> 100% verde (testes core §1-§4).
G2. py_compile em todos os .py de backend/ -> sem erros.
G3. node --check em todos os .js de frontend/ -> sem erros.
G4. node --test frontend/tests/ -> 100% verde.
G5. Greps de seguranca: zero SQL interpolado em app/ (scan AST); zero innerHTML
    com variavel/eval/document.write no front.
G6. Seed real validado: 48 times, 104 jogos, 495 combos Annex C, jogo 1 e 104 corretos.
G7. Smoke no sandbox: frontend servido estaticamente, recursos 200.
G8. Suite pytest §5 escrita e plugada como gate no Dockerfile (estagio test).
G9. Dockerfile, docker-compose.yml, fly.toml, README.md, .env.example completos.
G10. Nenhum arquivo de codigo >300 linhas (scripts/verify.sh checa).
G11. 6 abas + login + admin implementadas conforme briefing.
G12. CONTINUITY.md atualizado; zero TODO/FIXME no codigo.

## Status — Rodada 1 (2026-06-10) ✅ COMPLETA

G1 ✅ 127 testes core verdes. G2 ✅ py_compile limpo. G3 ✅ node --check (28 js).
G4 ✅ 19/19 node tests. G5 ✅ scan AST + greps limpos. G6 ✅ validado por teste
(J1=MEX x RSA 11/06 19:00Z; J104=final 19/07; 48/104/495). G7 ✅ 8 recursos 200.
G8 ✅ Dockerfile estagio test roda core+pytest. G9 ✅ todos presentes/coerentes.
G10 ✅ verify.sh confirma. G11 ✅ views/*.js + routers completos. G12 ✅ limpo.

## Rodada 2 — criterios (pos-REVIEW.md)

R1. Todo problema apontado em REVIEW.md corrigido OU justificado por decisao registrada.
R2. Rodada 1 re-executada e verde apos as correcoes.
R3. Design: contraste AA, estados vazios, skeletons, responsivo 360-1440px sem
    overflow horizontal.
R4. Robustez: API fora do ar -> frontend degrada com mensagem clara; SSE cai ->
    polling assume.
R5. Relogio: toda comparacao de tempo timezone-aware (zero datetime.now() nu).
R6. Documentacao permite deploy do zero por terceiros (Fly, Railway, OAuth,
    football-data, admin, backup).

## Status — Rodada 2 (2026-06-10) ✅ COMPLETA

R1 ✅ R2-F1 (CSP style-src), R2-F2 (healthcheck.py), R2-F3 (mutate 120/min),
R2-F4 (test_matches_service), R2-F5 (overflow group-card), R2-F6 (focus-visible
+ hover) aplicados; D012/avatares publicos/mode login justificados no REVIEW.
R2 ✅ verify.sh re-executado TUDO VERDE: 130 testes core, py_compile, node --check,
19 node tests, greps, ≤300 linhas, zero TODO. CSS com chaves balanceadas (92 pares).
R3 ✅ contraste 5:1, empty-states e skeletons em todas as views, overflow-x no
group-card (360px ok), bracket com scroll proprio.
R4 ✅ tela de retry no boot + empty state com erro por view; sse.js degrada para
polling 30s e retenta SSE a cada 8s.
R5 ✅ grep: zero datetime.now() sem tz; unica fonte de "agora" e betlock.utcnow()
(tz-aware) usada por betting/matches; repos usam datetime.now(timezone.utc).
R6 ✅ README cobre deploy do zero (Fly passo a passo, Railway, Docker local,
Google OAuth, token football-data, admin, backup de 1 arquivo).

**PROJETO CONCLUIDO — ambas as rodadas verdes.**
Gate final independente: o primeiro `docker build` executa as suites core +
pytest HTTP (estagio test) — a imagem so nasce com tudo verde.

## Rodada 3 — migracao PostgreSQL (Supabase/Render) — criterios

P1. Suite core 100% verde com o adapter (caminho SQLite intacto + caminho
    Postgres exercitado por driver fake instrumentado: placeholders %s,
    RETURNING id, BEGIN/COMMIT/ROLLBACK, IntegrityError normalizada).
P2. DDL Postgres renderizado sem residuos SQLite (IDENTITY/BYTEA; sem PRAGMA/
    AUTOINCREMENT) — testado.
P3. DATABASE_URL: lida do ambiente, postgres:// normalizada, URL invalida
    derruba o boot — testado.
P4. Suite de integracao contra POSTGRES REAL entregue e executavel em 1 comando
    (make test-pg via docker compose; ou TEST_DATABASE_URL=...).
P5. Avatares migrados para o banco (BYTEA/BLOB) — roundtrip testado.
P6. verify.sh verde; <=300 linhas; README/env/render.yaml coerentes com Render+Supabase.

## Status — Rodada 3 (2026-06-11) ✅ COMPLETA (1 pendencia externa)

P1 ✅ 148 testes core verdes (test_db_adapter cobre o caminho pg via fake).
P2 ✅ TestDdlDialetos.
P3 ✅ TestSettingsDatabaseUrl.
P4 ✅ tests/pg/test_postgres_integration.py + docker-compose.test.yml + make
   test-pg. EXECUCAO real pendente do ambiente do usuario (sandbox sem rede p/
   PyPI/apt — registrado em CONTINUITY I000): rodar `make test-pg` na maquina
   local OU `TEST_DATABASE_URL=<supabase de teste> make verify`.
P5 ✅ test_avatars (SQLite real) + assert BYTEA na suite pg.
P6 ✅ verify.sh TUDO VERDE; maior arquivo 145 linhas (connection.py).
