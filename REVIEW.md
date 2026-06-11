# REVIEW — crítica honesta (Agente 9) e segunda rodada

Data: 2026-06-10. Revisor: o próprio pipeline (auto-crítica exigida pelo briefing).

## Críticas por área

### Domínio (nota: forte, 1 lacuna de teste)
A lógica de pontuação, standings FIFA, clinch conservador, Annex C exata (495
combos validados estruturalmente) e cascata do bracket estão cobertas por 127
testes que EXECUTARAM aqui. **Lacuna**: `services/matches.py` (payload da aba
Jogos) só era exercitado indiretamente via testes HTTP que não rodam neste
ambiente. → **R2-F4: teste core dedicado adicionado.**
O clinch é deliberadamente conservador (só pontos): nunca mente, mas demora a
"garantir" (ex.: 6 pts na 2ª rodada com rival a 5 de alcance não trava). Correto
matematicamente; comunicado na UI como "✓ garantido" apenas quando é fato.

### Segurança (nota: sólida, 1 erro CRÍTICO meu)
- **CRÍTICO R2-F1**: configurei `style-src 'self'` no CSP, mas as views usam
  atributos `style=` inline extensivamente. Em produção o navegador bloquearia
  todos → layout quebrado. Corrigido para `style-src 'self' 'unsafe-inline'`.
  Risco residual aceitável: injeção de *estilo* exigiria XSS prévio, e scripts
  continuam 100% bloqueados (`script-src 'self'`, zero innerHTML/eval, h() usa
  textContent). Alternativa futura: migrar estilos inline para classes.
- bcrypt+pepper, rotação de refresh com detecção de replay (revoga a família),
  CSRF double-submit + SameSite=Lax, scan AST anti-SQL-injection: acima do
  pedido. Mensagens de login neutras com custo equalizado (anti-enumeração).
- Avatares são públicos por URL (`/u/avatars/{id}.jpg`) sem auth — aceitável
  para bolão entre amigos; documentado.

### Backend HTTP (nota: boa, com débito de execução)
Camada fina como planejado. **Débito honesto**: a suíte pytest (§5) não pôde
ser EXECUTADA neste sandbox (PyPI bloqueado — registrado em CONTINUITY I000/
Receipts). Mitigação real: ela roda como **gate no build do Docker** (estágio
`test`): a imagem não nasce com teste vermelho. Primeiro `docker build` do
usuário é o juiz.
- **R2-F2**: HEALTHCHECK do Dockerfile tinha escaping frágil (f-string com
  aspas aninhadas). Substituído por `app/healthcheck.py` dedicado.
- **R2-F3**: rate limit `mutate` 60/min podia atrapalhar quem preenche as 72
  apostas da fase de grupos de uma vez → 120/min (continua rígido p/ abuso).

### Motor ao vivo (nota: boa)
Poller com janela inteligente (60s em jogo, 15min fora), manual_lock vence API,
sync idempotente testado. SSE com fallback automático para polling testável só
por leitura — o teste de integração do EventSource real fica para o navegador
do usuário (limitação de ambiente, documentada).
Limitação consciente: `persist_resolutions` nunca "des-resolve" um confronto.
Se um admin resetar um jogo de mata-mata JÁ propagado, os jogos seguintes mantêm
os times antigos até correção manual (decisão D012 — evita cascata destrutiva
por engano; operação documentada no README).

### Frontend (nota: boa, 2 deslizes meus corrigidos no caminho)
Durante a construção deixei código morto no dashboard (reescrito) e quebrei o
package.json com edit truncado (incidente I001 do FS — 3ª ocorrência; todas
pegas pelos testes, o que valida a estratégia de verificação contínua).
- Steppers de aposta guardam rascunho fora do store: atualização ao vivo NÃO
  apaga o que o usuário está digitando. ✓
- Countdown re-renderiza a cada 30s só nas abas relevantes. Ticker global nunca
  é destruído (singleton de módulo) — consciente, custo desprezível.
- Estado `mode` do login persiste após logout (pode reabrir em "Criar conta") —
  cosmético, aceito nesta rodada.
- Lista do admin recarrega usuários só ao reabrir a aba — aceitável p/ escala.

### Design/UX (nota: boa → polida na rodada 2)
- **R2-F5**: `.group-card` com tabela de 9 colunas podia estourar em 360px →
  `overflow-x: auto` no card.
- **R2-F6**: faltava feedback de foco para teclado e hover-lift nos cards →
  `:focus-visible` global + transição sutil nos cards glass.
- Contraste verificado: texto secundário #7e8ca6 sobre #04070f ≈ 5:1 (AA ✓);
  estados vazios e skeletons presentes em todas as views de dados.

### Deploy/docs (nota: boa)
README cobre do zero: Fly (com volume e secrets), Railway, Docker local, OAuth
no Google Console, token football-data, admin, backup de 1 arquivo. fly.toml com
`auto_stop_machines=false` (poller vivo) — custo ~US$2-4/mês, citado.

## Parâmetros finais — Rodada 2

R2-F1 CSP style-src corrigido e verificado por grep. ✅
R2-F2 healthcheck.py criado; Dockerfile simplificado. ✅
R2-F3 mutate 120/min (default_limiter) + teste de escopos segue verde. ✅
R2-F4 test_matches_service.py core: ordenação, my_bet/my_points, bet_open, labels. ✅
R2-F5/F6 CSS: overflow do group-card, focus-visible, hover-lift. ✅
R1..R6 (GOALS rodada 2): re-execução completa após os fixes — ver GOALS.md.

## O que eu faria com mais uma semana
Migrar estilos inline → classes e endurecer o CSP de volta; e2e Playwright no
navegador real; PWA (manifest + offline da tabela); notificação push "seu jogo
começa em 1h sem aposta"; i18n; tema claro; gráfico de evolução do ranking por
rodada; export CSV das apostas.

---

# Adendo — Rodada 3: migracao SQLite → PostgreSQL (2026-06-11)

**Motivo** [USER]: deploy no Render (disco efemero) com banco Supabase.

**Decisao tecnica**: driver psycopg 3 SEM SQLAlchemy. O usuario sugeriu
"asyncpg/psycopg2 com SQLAlchemy" como exemplo; adotar ORM agora descartaria a
camada de repositorios 100% testada. O adapter (`db/connection.py`, 145 linhas)
preserva todos os call-sites: traduz `?`→`%s`, normaliza IntegrityError,
RETURNING id, BEGIN/COMMIT explicitos, e mantem SQLite para dev/testes.
psycopg2 e suportado como fallback de driver. `prepare_threshold=None` evita
prepared statements (compativel com o pooler PgBouncer do Supabase).

**Critica honesta do processo**: o sed em massa que troquei hints
`sqlite3.Connection→Db` quase introduziu um bug grave (`row_factory = Any`) —
pego por inspecao de diff antes dos testes; os testes o pegariam de qualquer
forma (todo fetch explodiria). Licao mantida: mudancas mecanicas amplas exigem
revisao de diff linha a linha, nao so py_compile.

**Limitacao de verificacao**: sem rede p/ PyPI/apt no sandbox, a suite
tests/pg (Postgres real: constraints, RETURNING, BYTEA, rollback, trava de
aposta) foi entregue executavel em 1 comando (`make test-pg`) mas nao executada
aqui. O caminho pg do adapter foi validado por driver fake instrumentado
(SQL traduzido, transacoes, erros) + DDL por asserts. Riscos residuais reais:
detalhes do wire protocol/tipos do psycopg — exatamente o que `make test-pg`
cobre na sua maquina antes do deploy.

**Avatares**: movidos do disco para BYTEA/BLOB (Render free nao persiste
disco). URL e contrato do frontend inalterados.
