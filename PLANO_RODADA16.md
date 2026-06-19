# PLANO RODADA 16 — Agentes, Contratos e Loop (Tabolão Copa 2026)

> **Este é o ÚNICO documento de instruções para agentes do projeto.** Os antigos
> (`AGENTS.md`, `PLAN_RODADA11.md`) foram removidos. `DESIGN_SYSTEM.md` e
> `TESTPLAN.md` viraram referências neutras (sem numeração de agentes).
>
> **Como rodar:** o orquestrador executa os agentes **em ordem estrita** (0 → 10),
> em **loop** (`/loop` ou `/goal`), e só encerra quando a *Definição de Pronto*
> (§ Loop) estiver 100% verde. Nenhum agente avança com teste vermelho.

---

## 0. Regras de ouro (valem para TODOS os agentes)

1. **Arquivos de código ≤ 300 LOC.** Estourou? Quebre em módulos. Docs podem ser longas.
2. **Pense à frente:** mantenha entrypoints estáveis; isole lógica em funções pequenas.
3. **Sem fallback silencioso** e **sem `try/except`/`try-catch` vazio.** Se falhar, falhe alto.
4. **Não reinventar a roda:** use o que já existe no projeto (helpers `h()`, `format.js`,
   `rank_thirds`, `compute_group`, `resolve_all`, padrão de migração de `schema.py`).
5. **UI para o usuário final**, não para o schema.
6. **SQL 100% parametrizado** (o scanner anti-injeção quebra o build se houver interpolação).
7. **Dois temas sempre:** tudo precisa funcionar em `data-theme="dark"` (padrão) e claro.
   Cor SÓ via token de `tokens.css` (trava de contraste no `verify.sh`).
8. **Atualize `CONTINUITY.md`** ao terminar cada agente (delta de Decisão/State/Receipts).
9. **TDD de verdade:** os testes do Agente 0 vêm primeiro e **não podem ser editados**
   pelos agentes de implementação. Se um teste estiver errado, registre em
   `CONTINUITY.md` (Incidente) e escale — não “conserte” o teste para passar.

### Ambiente (incidentes conhecidos — não relativize)
- **Sem PyPI/npm no sandbox:** a suíte `pytest` de `backend/tests/api/**` roda como
  **gate no build do Docker** e na máquina local — **não** no sandbox. No sandbox roda
  `python3 backend/run_core_tests.py` (unittest stdlib) e `node --test` (frontend).
- **I010 — mount trunca arquivo recém-escrito:** o `bash` (virtiofs) às vezes serve
  versões truncadas de arquivos acabados de gravar. **A verdade é o file tool
  (Read/Write).** Verifique build/sintaxe reconstruindo o arquivo em `/tmp` a partir
  do conteúdo do file tool antes de confiar em `node --check`/`py_compile` no mount.

---

## 1. Contratos compartilhados (fonte da verdade — Agente 0 escreve testes contra isto)

> Estes contratos travam nomes de função, formato de payload, classes CSS e chaves de
> `localStorage`. Os testes (Agente 0) e a implementação (Agentes 1–9) **têm que** bater.

### 1.1 Modelo de dados — `matches` (schema v4, migração idempotente)
Novas colunas (NULL-safe; migração igual ao padrão de `schema.py` `_migrate`):
- `period TEXT` — fase do relógio ao vivo. Domínio:
  `'1H' | 'HT' | '2H' | 'ET1' | 'ET_HT' | 'ET2' | 'PENS' | 'FT'` ou `NULL` (agendado).
- `stoppage INTEGER` — minutos de acréscimo **na fase atual** (ex.: `3` ⇒ `45+3`, `90+3`,
  `105+3`, `120+3`). `NULL`/`0` = sem acréscimo.
- `home_pens INTEGER`, `away_pens INTEGER` — placar da **disputa de pênaltis** (NULL se não houve).
- `pens_log TEXT` — sequência chute-a-chute (opcional, p/ o mini-placar). JSON:
  `[["home",true],["away",false],...]` na ordem das cobranças. Vazio/NULL ⇒ mostrar só o tally.
- **Semântica de `home_score`/`away_score` MUDA no mata-mata:** passam a ser o **placar ao
  fim da prorrogação (antes dos pênaltis)**. Em jogo decidido nos 90' (sem prorrogação),
  é o placar dos 90'. Em fase de grupos, segue o placar dos 90'. (Supersede D005.)
- `SCHEMA_VERSION = 4`.

### 1.2 Pontuação (backend)
- `score_bet(...)` **não muda** (compara aposta × placar real). O que muda é **qual placar
  real** entra: agora o de 1.1 (fim da prorrogação no mata-mata).
- `Match.winner_id()`: com `home_score == away_score` (empate após prorrogação) usa
  `winner_team_id` (vencedor nos pênaltis). Adicionar propriedade
  `Match.went_to_penalties` ⇔ `home_pens is not None`.

### 1.3 Ranking (backend `leaderboard.py`)
- **Posição DENSA** (`1,1,1,2`, não `1,1,1,4`). Algoritmo:
  ```python
  position, last_key = 0, None
  for r in rows_sorted:
      key = (r["total"], r["exact_hits"], r["result_hits"])
      if key != last_key:
          position += 1          # densa: +1, NÃO o índice i
          last_key = key
      r["position"] = position
  ```
- Empate = mesma `key` ⇒ mesma `position`. Ordenação de exibição mantém o desempate
  alfabético, mas **não** afeta a posição.

### 1.4 Pódio / medalhas com empate (frontend `leaderboard.js`)
- `medalForPosition(position)`: 1→`gold`, 2→`silver`, 3→`bronze`, senão `null` (já existe).
- **NOVO** `podiumSlots(rows)` (puro/testável): retorna os slots do pódio guiados por
  **posição**, nunca por índice de slot. Regras:
  - medalha de cada entrada = `medalForPosition(entrada.position)`.
  - mostra entradas das posições 1, 2 e 3 (layout: 2ª à esquerda, 1ª ao centro, 3ª à direita).
  - **empate em 2º ⇒ os dois recebem PRATA; ninguém recebe bronze** indevidamente.
  - empate em 1º ⇒ todos ouro; e assim por diante.
  - nunca atribuir uma medalha que contradiga a posição (o bug das imagens: 2º empatado
    recebendo bronze **não pode** acontecer).

### 1.5 Tema (frontend `theme.js` + script inline do `index.html`)
- Chaves: `PREF_KEY='theme'`, `RESET_KEY='theme_reset'`, `RESET_TOKEN='r16-dark-default'`.
- **Reset único na carga** (inline e `theme.js`): se `localStorage[RESET_KEY] !== RESET_TOKEN`,
  então `removeItem(PREF_KEY)` e `setItem(RESET_KEY, RESET_TOKEN)`. (zera a preferência de
  todos uma vez ⇒ todos voltam ao escuro neste deploy.)
- `getTheme()` = `localStorage[PREF_KEY] === 'light' ? 'light' : 'dark'`.
- Escolher claro grava `PREF_KEY='light'` (persiste, pois o reset já rodou).
- Função pura testável `resolveTheme(storage)` (recebe um storage fake) aplicando as regras.

### 1.6 Relógio ao vivo (frontend `format.js`)
- **NOVO** `liveClock(match, nowMs = Date.now())` → string. Usa `match.period`/`stoppage`/
  `minute`/`kickoff_utc`/`status`. Regras:
  - `status !== 'live'` ⇒ `''`.
  - Com `period` (dado do servidor):
    - `'1H'` ⇒ `45+{stoppage}'` se `minute>45` (ou stoppage>0), senão `{minute}'`.
    - `'HT'` ⇒ `'Intervalo'`.
    - `'2H'` ⇒ `90+{stoppage}'` se `minute>90`, senão `{minute}'`.
    - `'ET1'` ⇒ `{minute}'` (90–105); `105+{stoppage}'` se passar de 105.
    - `'ET_HT'` ⇒ `'Intervalo da prorrogação'`.
    - `'ET2'` ⇒ `{minute}'` (105–120); `120+{stoppage}'` se passar de 120.
    - `'PENS'` ⇒ `'Pênaltis'`.
  - **Sem `period`** (sem provider): estima pelo relógio **ancorado no kickoff real**
    (que o Agente 2 mantém correto). Mantém os “45+”/“90+” por janela de tempo.
- `liveMinute` antigo pode delegar para `liveClock` (compat) — não quebrar `matches.js`.

### 1.7 Mini-placar de pênaltis (frontend)
- Exibido **somente** se `match.home_pens != null` **ou** `match.period === 'PENS'`.
- Mostra tally `home_pens × away_pens`; se `match.pens_log` existir, renderiza os marcadores
  por time em ordem (✓ converteu / ✗ perdeu). Helper puro `parsePensLog(str)` → array.
- **Fonte de dados:** o tier grátis da football-data dá só o tally; o chute-a-chute é
  entrada **manual do admin** (opcional). Sem `pens_log`, mostrar só o tally (comportamento real).

### 1.8 Terceiros que se classificam (backend `standings_svc`)
- **NOVO** helper puro `mark_qualifying_thirds(third_rows_by_group)` → `set` das letras dos
  grupos cujo 3º **se classificaria agora** (8 melhores, via `rank_thirds`).
- Payload de `standings(...)`: cada linha de **posição 3** ganha `third_qualifying: bool`.
  Demais linhas: campo ausente/`null`.
- Zona de exibição (frontend calcula): `pos<=2 → 'row-q'` (verde) · `pos==3 && third_qualifying
  → 'row-t'` (amarelo) · `pos==3 && !third_qualifying → 'row-out'` (vermelho) · `pos==4 →
  'row-out'` (vermelho).

### 1.9 Mata-mata preditivo (backend `bracket_svc`)
- **NOVO** `predicted_bracket_payload(conn)` (ou `bracket_payload(conn, predict=True)`):
  mesmo shape de `bracket_payload`, mais `predicted: bool` por confronto.
  - Preenche o **R32** com 1º/2º provisórios (standings `include_live`) e os **8 melhores
    3ºs provisórios** (via `mark_qualifying_thirds` + Annex C) ⇒ `predicted=true` nessas vagas.
  - Time **matematicamente classificado** (clinch) ou jogo já decidido ⇒ `predicted=false`.
  - **Vencedor de jogo de mata-mata já encerrado propaga** para o slot seguinte
    (`predicted=false`) **mesmo que o adversário ainda seja TBD** (usar `resolve_all`, que já
    resolve cada lado de forma independente).
  - **Não inventar** vencedor de jogo de mata-mata ainda não jogado (sem base no ranking):
    esse lado fica TBD até o jogo acontecer.
- Endpoint `/api/bracket` passa a devolver o payload preditivo (campo `predicted` por confronto).

### 1.10 Aba “Jogos” unificada (frontend) — rota e subdivisões
- **Ordem das abas:** Tabela · Mata-mata · **Jogos** · Ranking · (Admin). Some “Ao Vivo” e
  “Apostas” como abas próprias; some a “Jogos” antiga (vira subdivisão).
- Rota `jogos` renderiza a view unificada (base = a antiga **Apostas**/`mybets`). Rotas
  `ao-vivo` e `apostas` viram **redirect** para `jogos` (não quebrar hash/links antigos).
- Subdivisões (filterbar): `future` (Jogos futuros) · `live` (Ao vivo) · `closed` (Jogos encerrados).
  - **future:** filtro por **fase** (`STAGE_FILTERS`) + cartões de aposta (betbox) como hoje.
  - **live:** **idêntico** à aba Ao Vivo de hoje (palpite público de todos + relógio do jogo).
    Reusar a renderização de `live.js` (não duplicar).
  - **closed:** filtro por **fase** + **ordenação** (mais recente↔mais antigo) + **fundo
    colorido** do cartão: errou→`is-wrong` (vermelho), acertou resultado→`is-right` (verde),
    cravou→`is-exact` (dourado), não apostou→`is-nobet` (neutro).
- Helper puro `closedCardClass(my_points, has_bet)` → `'is-exact'|'is-right'|'is-wrong'|'is-nobet'`.
- Botão **“Como Jogar”** vive aqui (movido do Ranking). Conteúdo em **novo** `js/howtoplay.js`
  (módulo compartilhado), com a regra atualizada (1.11).

### 1.11 Texto “Como Jogar” (regra do mata-mata atualizada)
- Trocar “vale o placar dos 90 minutos (+acréscimos)… prorrogação e pênaltis só definem quem
  avança” por: **“No mata-mata vale o placar ao fim da prorrogação (antes dos pênaltis).
  Empate é um resultado válido para a aposta; os pênaltis só definem quem avança.”**

---

## 2. Agente 0 — Testes primeiro (TDD, roda ANTES de todos)

**Objetivo:** escrever **todos** os testes de cada feature, **contra os Contratos (§1)**,
antes de qualquer implementação, e provar que eles **falham pelo motivo certo** (vermelho).
Isso garante que os testes não estão “viciados” (escritos para passar no código atual).

**Não faça:** não implemente nenhuma feature; não relaxe asserts; não dependa de detalhes de
implementação (teste comportamento observável/contratos).

**Entregáveis (backend core — `backend/tests/core/`, unittest stdlib):**
- `test_scoring_knockout_et.py` — placar de mata-mata = fim da prorrogação; pênaltis
  descartados; empate pós-prorrogação usa `winner_team_id`; `went_to_penalties`.
- `test_schema_v4_migration.py` — DB v3 “na mão” migra e ganha `period/stoppage/home_pens/
  away_pens/pens_log`; idempotente; `SCHEMA_VERSION==4`.
- `test_results_penalties.py` — `set_score` aceita `period/stoppage/home_pens/away_pens/
  pens_log` e persiste; valida domínio de `period`; mata-mata empatado pós-prorrogação exige winner.
- `test_sync_kickoff.py` — provider reporta horário diferente (>60s) em jogo `scheduled` ⇒
  kickoff atualiza no banco **e** `data_version` sobe (SSE); jogo em andamento/encerrado não muda.
- `test_provider_live_state.py` — `parse_match` extrai `period`/`stoppage`/`penalties` do shape
  da football-data v4 (`score.duration`, `score.penalties`, acréscimos); `_score_pair` passa a
  devolver o placar **fim-da-prorrogação** (fullTime) p/ jogos com prorrogação.
- `test_thirds_predictive.py` — `mark_qualifying_thirds` escolhe os 8 melhores 3ºs por
  `pts>SG>GP>código` com standings parciais; payload marca `third_qualifying`.
- `test_bracket_predictive.py` — cenário mid-torneio: líderes provisórios entram no R32 com
  `predicted=true`; time clinched entra `predicted=false`; vencedor de R32 encerrado propaga
  ao R16 (`predicted=false`) com adversário TBD.
- `test_leaderboard_dense.py` — três empatados ⇒ `1,1,1,2` (densa); chaves e contadores certos.

**Entregáveis (frontend — `frontend/tests/`, node:test):**
- `theme.test.js` — `resolveTheme`: legado `light` sem reset ⇒ `dark` (e aplica reset);
  `light` explícito após reset ⇒ `light`; nada salvo ⇒ `dark`.
- `format.test.js` (estender) — `liveClock`: `1H/47'+stoppage2 ⇒ "45+2'"`; `2H ⇒ "90+X'"`;
  `ET2 ⇒ "120+X'"`; `PENS ⇒ "Pênaltis"`; sem `period` cai na estimativa por kickoff.
- `live.test.js` (estender) — `parsePensLog` e a regra de exibição do mini-placar.
- `leaderboard.test.js` (estender) — `podiumSlots`: empate em 2º ⇒ duas pratas, zero bronze;
  empate em 1º ⇒ ouros; caso 1-2-3 distinto ⇒ ouro/prata/bronze.
- `jogos.test.js` (novo) — `closedCardClass`: cravou→exact, acertou→right, errou→wrong,
  não apostou→nobet; ordenação asc/desc; filtro por fase.
- `dashboard.test.js` (novo ou estender) — `zoneFor(row)`: 1º–2º q, 3º qualificado t, 3º não
  qualificado out, 4º out.
- `bracket.test.js` (estender) — render/flag de `predicted` (helper puro de rótulo/estado).

**Done:** todos os arquivos acima existem; rodando agora, **falham** (import ausente / asserт
quebrado) — registrar o “red run” em `CONTINUITY.md` (Receipts). Nenhum teste vacila (cada um
faz pelo menos um assert significativo do contrato).

---

## 3. Agentes de implementação (ordem estrita; mapa de arquivos evita conflito)

> Regra: cada agente torna **verdes** os testes do Agente 0 da sua feature **sem editar os
> testes**. Roda a verificação da sua área antes de passar o bastão.

### Agente 1 — Pontuação do mata-mata (fim da prorrogação) + schema [BACKEND]
**Resolve:** “contar até o placar final da prorrogação, antes dos pênaltis” (+ fundação de dados de B).
**Arquivos:** `db/schema.py` (migração v4), `domain/entities.py` (`went_to_penalties`,
comentário do `winner_id`), `services/results.py` (`set_score` aceita período/acréscimo/pênaltis),
`db/repos/matches.py` (persistir colunas novas), `providers/football_data.py` **só** o
`_score_pair` (fullTime). **Não** mexa em frontend.
**Passos:**
1. Migração: adicionar as 5 colunas (§1.1) no padrão idempotente; `SCHEMA_VERSION=4`.
2. `set_score(...)` ganha params `period, stoppage, home_pens, away_pens, pens_log` (todos
   opcionais), validando `period` no domínio e `pens` inteiros ≥0; persistir via repo.
3. `_score_pair`: devolver **fullTime** (placar fim-da-prorrogação) — não mais `regularTime`.
4. `entities`: `went_to_penalties`; `winner_id` segue usando `winner_team_id` no empate.
**Aceite:** `test_scoring_knockout_et`, `test_schema_v4_migration`, `test_results_penalties` verdes;
`run_core_tests.py` 100% verde (sem regressão).

### Agente 2 — Sync de horário automático + estado ao vivo [BACKEND]
**Resolve:** C (horário muda e o site não atualiza sozinho) + dados de B (período/acréscimo/pênaltis).
**Arquivos:** `providers/football_data.py` (`parse_match`, `ScoreUpdate` em `providers/base.py`),
`providers/sync.py`, `jobs/poller.py`, `services/matches.py` e `services/public_bets.py`
(expor `period/stoppage/home_pens/away_pens/pens_log` nos payloads de jogos/live).
**Passos:**
1. **Diagnóstico de C:** confirmar por que o kickoff não atualiza hoje (token ausente?
   `manual_lock`? matching por `external_id`/janela? cadência). Registrar achado em CONTINUITY.
2. Tornar o update de kickoff **robusto e suficientemente frequente**: o `sync.py` já atualiza
   kickoff de jogo `scheduled` (>60s) — garanta que dispara **sem input do admin** e que o
   `poller` (idle 15min; ativo 60s) cobre mudança no mesmo dia (ex.: 22:00→21:30). Considere
   reduzir o idle e/ou reavaliar a janela quando o provider antecipar o horário.
3. `parse_match`: extrair `period` (de `score.duration` + `status` PAUSED/IN_PLAY ⇒ HT/2H etc.),
   `stoppage` (acréscimo, se disponível) e `penalties` (`score.penalties`). `_score_pair` já é do Agente 1.
4. `sync.apply_updates`: aplicar período/acréscimo/pênaltis (respeitando `manual_lock`).
5. Expor os campos novos em `services/matches.py` (lista de jogos) e `public_bets`/live.
**Aceite:** `test_sync_kickoff`, `test_provider_live_state` verdes; sem regressão no core.

### Agente 3 — Terceiros preditivos + mata-mata preditivo [BACKEND]
**Resolve:** D (quais 8 terceiros passam) + E (simular o mata-mata pela tabela atual).
**Arquivos:** `services/standings_svc.py` (+ `mark_qualifying_thirds`), `services/bracket_svc.py`
(`predicted_bracket_payload`), `api/bracket.py` e `api/standings.py` se preciso expor flags.
**Passos:**
1. `mark_qualifying_thirds(third_rows_by_group)` (puro) usando `rank_thirds`; marcar top-8.
2. `standings(...)`: para a linha de posição 3 de cada grupo, setar `third_qualifying`.
3. `predicted_bracket_payload(conn)` (§1.9): standings provisórios → 1º/2º/8 melhores 3ºs →
   Annex C → `resolve_all`; mesclar com resoluções reais (real vence provisório);
   `predicted` por confronto; vencedores reais propagam mesmo com adversário TBD.
4. `/api/bracket` passa a devolver `predicted`.
**Aceite:** `test_thirds_predictive`, `test_bracket_predictive` verdes; sem regressão.

### Agente 4 — Ranking denso + empates [BACKEND]
**Resolve:** F (1,1,1,2) e a base de G.
**Arquivos:** `services/leaderboard.py` (só o cálculo de `position`).
**Passos:** trocar a posição por **densa** (§1.3).
**Aceite:** `test_leaderboard_dense` verde; `test_leaderboard` existente sem regressão.

### Agente 5 — Tema escuro padrão + reset de preferência [FRONTEND]
**Resolve:** A (escuro default p/ todos; reset; só fica claro se apertarem claro após o deploy).
**Arquivos:** `js/theme.js`, `index.html` (script inline de tema).
**Passos:** implementar §1.5 (reset único + `resolveTheme`). O botão de tema continua gravando
`light`/`dark` em `PREF_KEY`.
**Aceite:** `theme.test.js` verde; `node --check`.

### Agente 6 — Relógio ao vivo + prorrogação + mini-placar de pênaltis [FRONTEND]
**Resolve:** B (dessincronia; “45+X”/“90+X”; prorrogação no mata-mata; mini-placar de pênaltis).
**Arquivos:** `js/format.js` (`liveClock`), `js/views/live.js` (relógio + mini-placar),
`css/views.css`/`views-extra.css` (seção “Ao Vivo”/pênaltis), `js/ui.js` (só **adicionar**
ícones se preciso). **Não** edite `matches.js` (é do Agente 9).
**Passos:**
1. `liveClock(match, now)` por §1.6 (servidor manda; estimativa ancorada no kickoff como fallback).
2. `live.js`: usar `liveClock`; exibir prorrogação; **mini-placar de pênaltis** (§1.7), só em shootout.
**Aceite:** `format.test.js`, `live.test.js` verdes; `node --check`; trava de contraste verde.

### Agente 7 — Tabela (cor dos 3ºs) + Mata-mata preditivo (UI) [FRONTEND]
**Resolve:** D (listrinha amarela só nos 3ºs que passam; flair vermelho nos que não passam) +
E (UI da previsão).
**Arquivos:** `js/views/dashboard.js` (+ `zoneFor`), `js/views/bracket.js` (consumir `predicted`),
`css/views.css`/`views-extra.css` (seções Dashboard e Bracket).
**Passos:**
1. `dashboard.js`: zona por `zoneFor(row)` (§1.8). Verde 1º–2º, **amarelo** só nos 3ºs que
   passam, **vermelho** nos demais (3ºs fora + 4ºs). Atualizar a legenda.
2. `bracket.js`: banner **“Previsão com base no ranking atual”**; marcar confrontos
   `predicted` de forma sutil (sem competir com os definitivos); vencedores já propagados aparecem.
**Aceite:** `dashboard.test.js`, `bracket.test.js` verdes; contraste verde; `node --check`.

### Agente 8 — Ranking: pódio/medalhas/densa + tirar “Como Jogar” [FRONTEND]
**Resolve:** F (exibição densa), G (pódio/medalhas com empate), e remove o botão “Como Jogar”
(ele vai para a aba Jogos).
**Arquivos:** `js/views/leaderboard.js` (+ `podiumSlots`), `css` do ranking.
**Passos:**
1. `podiumSlots(rows)` (§1.4) guiado por posição; empate em 2º ⇒ duas pratas, **zero bronze**.
2. Tabela mostra a posição densa (já vem do Agente 4).
3. **Remover** o botão “Como Jogar” daqui (passa a viver na aba Jogos — Agente 9).
**Aceite:** `leaderboard.test.js` verde (inclui `podiumSlots`); contraste verde; `node --check`.

### Agente 9 — Unificar Jogos/Ao Vivo/Apostas na aba “Jogos” [FRONTEND]
**Resolve:** I (fusão das 3 abas) + mover o botão “Como Jogar” + texto novo da regra (§1.11).
**Arquivos:** `js/views/jogos.js` (NOVO, base = `mybets.js`), `js/howtoplay.js` (NOVO),
`js/layout.js` (NAV + ordem), `js/router.js` (rota `jogos`; `ao-vivo`/`apostas`→redirect),
`js/main.js` (wire da nova view), reuso de `js/views/matches.js` (`matchCard`) e
`js/views/live.js` (render ao vivo). Aposentar `mybets.js` (conteúdo migra para `jogos.js`);
manter `matches.js`/`live.js` como módulos reutilizados. **Quebre em ≤300 LOC** (ex.: helpers
de “encerrados” em `jogos_closed.js`).
**Passos:**
1. NAV/ordem (§1.10): Tabela · Mata-mata · **Jogos** · Ranking · Admin. Remover abas “Ao Vivo”/“Apostas”.
2. `jogos.js` com subdivisões `future`/`live`/`closed`:
   - future: filtro por fase + betbox (como a Apostas de hoje).
   - live: **idêntico** ao Ao Vivo (reusar `live.js`).
   - closed: filtro por fase + **ordenação** asc/desc + **fundo** `closedCardClass` (§1.10).
3. `howtoplay.js`: conteúdo + botão “Como Jogar” no head da aba Jogos, com a regra nova (§1.11).
4. `router.js`: `ao-vivo`/`apostas` → `jogos` (compat).
**Aceite:** `jogos.test.js` verde; `node --check`; contraste verde; todos os arquivos ≤300 LOC.

---

## 4. Agente 10 — Integração, verificação e loop [VERIFY]

**Objetivo:** rodar a verificação completa, em **loop**, até a *Definição de Pronto*; revisão
crítica independente; atualizar `CONTINUITY.md` e `GOALS.md` (Rodada 16).

**Verificação (sandbox):**
- `python3 backend/run_core_tests.py` ⇒ 100% verde.
- `cd frontend && node --test tests/*.test.js` ⇒ 100% verde.
- `node --check` em todo `.js` tocado; `py_compile` na árvore backend.
- Trava de contraste (0 cor hardcoded fora de `tokens.css`) e limite **≤300 LOC**.
- (Reconstruir em `/tmp` quando o mount truncar — I010.)
**Verificação (fora do sandbox / quando possível):**
- `pytest backend/tests/api` roda no **build do Docker**/local (gate).
- Visual via Chrome MCP no site servido/deploy: dois temas; relógio “45+X/90+X”, prorrogação,
  mini-placar de pênaltis; tabela (amarelo só nos 3ºs que passam, vermelho nos demais);
  mata-mata preditivo com banner; pódio com empates corretos; aba **Jogos** com as 3 subdivisões.
**Revisão crítica:** subagente independente revisa diffs (regressões, contratos, segurança).

### Definição de Pronto (o loop só encerra quando TUDO for verdade)
1. Todos os testes do Agente 0 **verdes** (e foram **vermelhos** antes da implementação).
2. As 9 features abaixo atendem aos critérios de aceite e foram conferidas (lógica + visual):
   A tema escuro default+reset · B relógio/prorrogação/pênaltis · C horário automático ·
   D 3ºs na tabela · E mata-mata preditivo · F ranking denso · G pódio/medalhas ·
   H pontuação fim-da-prorrogação + botão movido · I aba Jogos unificada.
3. `run_core_tests.py` + `node --test` + `node --check` + contraste + ≤300 LOC ⇒ verdes.
4. `CONTINUITY.md` e `GOALS.md` (Rodada 16) atualizados; zero `TODO`/`try/except` vazio.

---

## 5. Mapa de propriedade de arquivos (evitar conflito; ordem 1→9)

| Arquivo | Dono |
|---|---|
| `backend/app/db/schema.py`, `db/repos/matches.py` | Ag.1 |
| `backend/app/domain/entities.py`, `services/results.py` | Ag.1 |
| `backend/app/providers/football_data.py` | Ag.1 (`_score_pair`) · Ag.2 (`parse_match`) |
| `backend/app/providers/sync.py`, `jobs/poller.py`, `providers/base.py` | Ag.2 |
| `backend/app/services/matches.py`, `services/public_bets.py` | Ag.2 |
| `backend/app/services/standings_svc.py`, `services/bracket_svc.py` | Ag.3 |
| `backend/app/api/bracket.py`, `api/standings.py` | Ag.3 |
| `backend/app/services/leaderboard.py` | Ag.4 |
| `frontend/js/theme.js`, `index.html` (inline) | Ag.5 |
| `frontend/js/format.js`, `js/views/live.js` | Ag.6 |
| `frontend/js/views/dashboard.js`, `js/views/bracket.js` | Ag.7 |
| `frontend/js/views/leaderboard.js` | Ag.8 |
| `frontend/js/views/jogos.js`(novo), `js/howtoplay.js`(novo), `layout.js`, `router.js`, `main.js` | Ag.9 |
| `frontend/js/views/matches.js`, `js/views/mybets.js` | Ag.9 (merge) |
| `frontend/css/{views,views-extra,components,tokens}.css` | seção por dono; sem sobrescrever decisão alheia |
| `backend/tests/**`, `frontend/tests/**` | **Ag.0 (somente)** — impl não edita |

Conflito/divergência ⇒ registrar em `CONTINUITY.md` e seguir este documento.
