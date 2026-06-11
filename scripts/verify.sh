#!/usr/bin/env bash
# verify.sh — roda TODA a verificação possível no ambiente atual.
# Uso: bash scripts/verify.sh [core|front|all(default)]
set -u
cd "$(dirname "$0")/.."
MODE="${1:-all}"
FAIL=0

step() { printf '\n\033[1;36m== %s ==\033[0m\n' "$1"; }
ok()   { printf '\033[1;32m✔ %s\033[0m\n' "$1"; }
bad()  { printf '\033[1;31m✘ %s\033[0m\n' "$1"; FAIL=1; }

if [ "$MODE" != "front" ]; then
  step "Backend: testes core (stdlib)"
  if python3 backend/run_core_tests.py >/tmp/core.log 2>&1; then
    ok "core tests ($(grep -o 'Ran [0-9]* tests' /tmp/core.log | head -1))"
  else
    bad "core tests"; tail -20 /tmp/core.log
  fi

  step "Backend: py_compile em toda a árvore"
  if find backend -name '*.py' -not -path '*/__pycache__/*' -print0 \
      | xargs -0 python3 -m py_compile 2>/tmp/pyc.log; then
    ok "py_compile"
  else
    bad "py_compile"; cat /tmp/pyc.log
  fi

  step "Backend: integração Postgres real (tests/pg)"
  if [ -n "${TEST_DATABASE_URL:-}" ]; then
    if (cd backend && python3 -m pytest tests/pg -q -rs >/tmp/pg.log 2>&1); then
      ok "postgres integração ($(tail -1 /tmp/pg.log))"
    else
      bad "postgres integração"; tail -30 /tmp/pg.log
    fi
  else
    echo "… TEST_DATABASE_URL não definido — rode 'make test-pg' (Docker) ou aponte para um banco de teste Supabase"
  fi

  step "Backend: suíte HTTP (pytest) — requer fastapi instalado"
  if python3 -c "import fastapi" 2>/dev/null; then
    if (cd backend && python3 -m pytest tests/api -q >/tmp/pytest.log 2>&1); then
      ok "pytest api ($(tail -1 /tmp/pytest.log))"
    else
      bad "pytest api"; tail -30 /tmp/pytest.log
    fi
  else
    echo "… fastapi indisponível neste ambiente — gate roda no build do Docker (Dockerfile estágio test)"
  fi
fi

if [ "$MODE" != "core" ]; then
  step "Frontend: sintaxe (node --check)"
  JSFAIL=0
  while IFS= read -r f; do
    node --check "$f" 2>/tmp/nc.log || { JSFAIL=1; bad "sintaxe: $f"; cat /tmp/nc.log; }
  done < <(find frontend/js frontend/tests -name '*.js')
  [ $JSFAIL -eq 0 ] && ok "node --check"

  step "Frontend: testes (node:test)"
  if (cd frontend && node --test tests/*.test.js >/tmp/nt.log 2>&1); then
    ok "node tests ($(grep -o '# pass [0-9]*' /tmp/nt.log | tail -1))"
  else
    bad "node tests"; tail -30 /tmp/nt.log
  fi

  step "Frontend: greps de segurança"
  if grep -rn --include='*.js' -e 'innerHTML[[:space:]]*=' -e 'document\.write' -e '\beval(' frontend/js/ \
      | grep -v '^\S*:[0-9]*:\s*//'; then
    bad "padrão proibido encontrado acima"
  else
    ok "sem innerHTML=/eval/document.write"
  fi
fi

step "Limite de 300 linhas por arquivo de código"
BIG=$( (find backend -name '*.py' -not -path '*/__pycache__/*'; \
        find frontend -name '*.js' -o -name '*.css') | while IFS= read -r f; do
  lines=$(wc -l < "$f")
  [ "$lines" -gt 300 ] && echo "$lines $f"
done)
if [ -n "$BIG" ]; then bad "arquivos acima de 300 linhas:"; echo "$BIG"; else ok "todos ≤300 linhas"; fi

step "TODO/FIXME pendentes"
if grep -rn --include='*.py' --include='*.js' -e 'TODO' -e 'FIXME' backend/app frontend/js; then
  bad "pendências encontradas"
else
  ok "sem TODO/FIXME"
fi

printf '\n'
if [ $FAIL -eq 0 ]; then ok "VERIFICAÇÃO COMPLETA: TUDO VERDE"; else bad "VERIFICAÇÃO FALHOU"; fi
exit $FAIL
