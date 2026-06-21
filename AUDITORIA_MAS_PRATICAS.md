# Auditoria de Más Práticas — Bolão Copa 2026 (`futebolão`)

> Revisão crítica e completa do repositório em **2026-06-21**.
> Escopo: `backend/app/**`, `frontend/js/**`, `frontend/css/**`, infra (Docker/Render/Fly), seed e docs.
> Foco especial pedido pelo usuário: **hardcode indevido, violações SOLID e riscos futuros — sobretudo na fase de mata-mata.**

Antes de tudo, um reconhecimento honesto: este é um código **acima da média**. Núcleo de domínio puro e testável, SQL 100% parametrizado, segurança bem pensada (bcrypt+pepper, JWT rotacionado, CSRF double-submit, CSP restritiva, avatares recodificados por Pillow), 300 LOC respeitados em todos os arquivos e ~150 testes. As críticas abaixo são severas **de propósito** (foi o pedido), mas a base é sólida. O maior problema do projeto **não é a qualidade de cada peça — é o lixo arquitetural deixado por uma refatoração inacabada ("Rodada 16") e a contradição na regra mais importante do mata-mata.**

---

## 0. Índice por severidade

| # | Severidade | Achado | Onde |
|---|------------|--------|------|
| C1 | 🔴 Crítico | Regra do mata-mata contradiz a própria documentação canônica (90min × fim da prorrogação) | `CONTINUITY.md` vs código/UI |
| C2 | 🔴 Crítico | Modo manual (padrão) **não consegue registrar placar de pênaltis** | `api/schemas.py`, `views/admin.js` |
| A1 | 🟠 Alto | Dead code massivo de views/funções da "Rodada 16" inacabada | `frontend/js/views/*`, `bracket_svc.py` |
| A2 | 🟠 Alto | Sem connection pool: nova conexão Postgres por request/SSE/poll | `api/deps.py`, `api/sse.py` |
| A3 | 🟠 Alto | Reset de jogo de mata-mata não "des-propaga" o chaveamento | `services/bracket_svc.py` (D012) |
| A4 | 🟠 Alto | Estado global em memória quebra com >1 worker (SSE/rate-limit/cache) | `live_bus.py`, `ratelimit.py`, `leaderboard.py` |
| M1 | 🟡 Médio | Premissa **não confirmada** sobre `fullTime` da football-data | `providers/football_data.py` |
| M2 | 🟡 Médio | Casamento "fuzzy" de jogos do provider arrisca trocar partidas no mata-mata | `providers/sync.py` |
| M3 | 🟡 Médio | Fallbacks silenciosos na config contradizem o princípio declarado | `config.py` |
| M4 | 🟡 Médio | Dois relógios "ao vivo" divergentes + lógica de fase triplicada | `format.js`, `sync.py`, `football_data.py` |
| M5 | 🟡 Médio | Pins de dependência frouxos, sem lockfile (build não reproduzível) | `requirements.txt` |
| M6 | 🟡 Médio | Pênaltis nunca aparecem no chaveamento (só na aba Ao Vivo) | `views/bracket.js` |
| B1 | 🟢 Baixo | Tradução SQL `?`→`%s` e split de DDL por `;` são ingênuos (landmines) | `db/connection.py` |
| B2 | 🟢 Baixo | Hardcode de dados de times espalhado por 3 camadas + multiplicadores duplicados | vários |
| B3 | 🟢 Baixo | E-mail pessoal versionado no `.env.example` | `.env.example` |
| B4 | 🟢 Baixo | `store.set({})` como gambiarra de re-render; estado de UI fora do store | `views/*.js` |
| B5 | 🟢 Baixo | "Data clump": `set_score` com 14 parâmetros posicionais | `services/results.py` |
| B6 | 🟢 Baixo | Drift de comentários/constantes vs documentação (poller, tokens, schema_version) | vários |

---

## 1. 🔴 CRÍTICO

### C1 — A regra de pontuação do mata-mata se contradiz na documentação canônica

Este é o achado mais importante, porque envolve **a regra central de toda a fase eliminatória** e a fonte de verdade que deve sobreviver à compactação.

- `CONTINUITY.md` (Invariants e D005) afirma, em dois lugares:
  - *"Mata-mata: placar dos 90min."*
  - *"D005 ACTIVE: aposta em mata-mata = placar dos 90min (empate vale)."*
- Mas o **código, o teste e a tela do usuário** dizem o contrário — vale o **fim da prorrogação**:
  - `frontend/js/howtoplay.js:30` → *"No mata-mata vale o placar ao fim da prorrogação (antes dos pênaltis)."*
  - `backend/tests/core/test_scoring_knockout_et.py:1` → *"a aposta pontua pelo placar do FIM DA PRORROGAÇÃO (antes dos pênaltis)."*
  - `backend/app/providers/football_data.py:71-74` (`_score_pair`) usa `fullTime`, *"que já inclui a prorrogação"*.
  - `services/betting.py:bet_points` simplesmente usa `match.home_score/away_score` (campo único — ver abaixo), sem distinguir 90' de prorrogação.

**Por que é grave:** a regra real (fim da prorrogação) e a regra documentada (90min) são **incompatíveis e produzem pontuações diferentes**. Exemplo: jogo 1×1 nos 90', 2×1 na prorrogação. Pela regra real, quem apostou 2×1 crava; pela regra do ledger, quem apostou 1×1 crava. Como `CONTINUITY.md` é declaradamente *"a fonte canônica que sobrevive à compactação"*, um desenvolvedor futuro (ou você mesmo, daqui a semanas) pode "consertar" o código para a regra **errada** e quebrar o placar bem no meio da Copa.

**Risco estrutural associado:** existe **um único par de campos** `home_score`/`away_score` (`domain/entities.py:72-73`) que serve, ao mesmo tempo, para (a) decidir o vencedor do confronto (`winner_id()`, `entities.py:102`) e (b) pontuar a aposta. Hoje os dois usam "fim da prorrogação", então é consistente — mas **é impossível** exibir/pontuar o placar dos 90' separadamente sem adicionar um campo. Se algum dia a regra mudar, o modelo de dados não comporta.

**Recomendação:** decida a regra de uma vez, corrija `CONTINUITY.md` para bater com o produto (supersedendo D005 e o invariante explicitamente, como o próprio ledger manda) e adicione um teste que falhe se `MULTIPLIERS`/regra divergirem entre `entities.py` e `points.js`.

---

### C2 — No modo manual (o padrão), o admin não consegue registrar o placar de pênaltis

O deploy padrão roda **sem** `FOOTBALL_DATA_TOKEN` — o próprio `main.py:71` loga *"sem FOOTBALL_DATA_TOKEN - modo manual (admin)"* e o `CONTINUITY.md` trata o modo manual como o caminho principal.

Porém:

- `api/schemas.py:46-53` (`AdminScoreIn`) só tem `home_score, away_score, status, minute, winner_team_id, force, lock`. **Não há `home_pens`, `away_pens`, `pens_log`, `period`, `stoppage`.**
- `api/admin.py:35-40` chama `set_score(...)` sem repassar pênaltis (nem poderia — não estão no schema).
- `frontend/js/views/admin.js:26-49` tem inputs de gols, minuto e um `select` de "vencedor (pênaltis)", mas **nenhum campo para o placar dos pênaltis** (4×3).

Resultado: em modo manual, um jogo decidido nos pênaltis fica com `home_pens/away_pens = NULL` e `went_to_penalties = False` (`entities.py:98`). O admin marca o vencedor (o chaveamento propaga, isso funciona), mas:

- O painel de pênaltis da aba Ao Vivo (`views/live.js:93 pensBoard`) **nunca aparece** (a condição exige `home_pens`/`away_pens` ou `period === 'PENS'`).
- O placar "(pên. 4×3)" não é exibido em lugar nenhum.

Ou seja: **toda a infraestrutura de pênaltis (coluna no banco, `pens_log`, mini-placar com ✓/✗) só funciona com o provider pago ligado.** Na operação real, mais provável (manual), ela é morta. É um buraco funcional bem no clímax do torneio.

**Recomendação:** adicionar `home_pens`/`away_pens` (e opcionalmente `pens_log`) ao `AdminScoreIn` e à UI do admin, repassando para `set_score` (que **já aceita** esses parâmetros — `results.py:37-40`). O conserto é pequeno; o impacto é alto.

---

## 2. 🟠 ALTO

### A1 — Dead code massivo: a refatoração "Rodada 16" não foi limpa

A Rodada 16 fundiu as abas **Jogos + Ao Vivo + Apostas** numa só (`views/jogos.js`), reaproveitou as peças úteis (`matchCard`, `liveContent`) e **deixou os renderizadores de página antigos vivos no repositório, sem uso**. Confirmado por `grep` (nenhum `import` em `main.js` nem nas views ativas):

| Símbolo morto | Arquivo | Observação |
|---|---|---|
| `renderMyBets` | `views/mybets.js:40` | Arquivo inteiro (108 LOC) órfão; `tallyBets` **duplicado** em `jogos.js:23` |
| `renderMatches` | `views/matches.js:107` | Só `matchCard` é reutilizado; o resto da página é morto |
| `renderLive` | `views/live.js:148` | Só `liveContent`/`sortBettors`/`shortName`/`parsePensLog` são usados |
| `minuteLabel` | `format.js:54` | Referenciado **apenas pelo próprio teste** |
| `liveMinute` | `format.js:63` | Superado por `liveClock`; o ramo "live" só roda em `matchCard`, que nunca recebe jogo ao vivo |
| `bracket_payload` | `services/bracket_svc.py:74` | A rota `/api/bracket` usa `predicted_bracket_payload` (`game.py:77`); este é morto em produção |
| `TokenReuseError` | `core/tokens.py:29` | Classe definida e nunca lançada (a lógica mudou na Rodada 16) |
| `ScoreUpdate.period` + `_derive_period` | `providers/football_data.py:79` | Calculado em `parse_match`, **nunca lido**: `sync.py` recomputa tudo via `_next_period` |
| `TLA_FIXES` | `football_data.py:48` | Mapa identidade `{"KOR":"KOR",...}` — **não faz nada** |

**Por que importa (e não é "só estética"):** vários desses mortos estão **"protegidos" por testes** (`test_bracket_svc.py` testa `bracket_payload`; `betbox.test.js` importa `tallyBets` de `mybets.js`; `format.test.js` testa `minuteLabel`). Isso dá **falsa confiança**: a suíte fica verde testando código que o app não executa, e esconde que a versão *real* (ex.: `predicted_bracket_payload`, o `tallyBets` de `jogos.js`) pode divergir sem ninguém perceber. É dívida que **mascara risco**, não apenas peso morto.

**Recomendação:** apagar os renderizadores/funções órfãos e redirecionar os testes para os símbolos realmente usados. Se quiser manter `bracket_payload` como API "estável", então **use-o** na rota; senão, remova-o.

---

### A2 — Sem pool de conexões: cada request abre (e fecha) uma conexão nova

`api/deps.py:25-30` (`get_db`) faz `connect(...)` por request e `close()` no final. O mesmo padrão se repete em `api/sse.py:30` (a cada conexão SSE) e no endpoint de polling `/api/live/version` (`sse.py:19`).

- Em **SQLite** isso é aceitável (abrir arquivo é barato, e há WAL).
- Em **Postgres/Supabase** isso significa **um handshake TCP+TLS+auth a cada request**. Com o tempo-real do projeto (SSE + fallback de polling a cada 30s, multiplicado por N jogadores online durante um jogo), você gera um fluxo constante de conexões novas. O pooler do Supabase tem limite de conexões; sob carga de jogo, isso vira `too many connections` ou latência alta.

`connection.py` nem expõe um pool (psycopg3 tem `psycopg_pool`, não usado). Para um bolão de amigos pode passar; para qualquer pico (final, grupo do Brasil) é o gargalo mais provável.

**Recomendação:** introduzir um pool (psycopg_pool para PG; manter conexão única/arquivo para SQLite) atrás da mesma fábrica `connect`, sem mudar os repositórios.

---

### A3 — Corrigir um resultado de mata-mata **não desfaz** a propagação no chaveamento

Documentado como D012 no ledger, e implementado de propósito em `services/bracket_svc.py:44-59` (`persist_resolutions`): *"Nunca sobrescreve um time já definido com None (não 'des-resolve')."*

Consequência operacional na fase eliminatória: se o admin **errar** o vencedor de um jogo do R32 e depois corrigir (via `reset` + novo placar), os jogos de R16/QF que **já receberam** o time errado **não voltam atrás** automaticamente. O ledger admite isso ("reset de KO propagado exige correção manual"), mas:

- Não há ferramenta de admin para "limpar a jusante" — o admin teria que resetar manualmente cada confronto subsequente, na ordem certa, sem UI que mostre o que foi contaminado.
- `reset_match` (`results.py:93`) zera **um** jogo, mas o `persist_resolutions` chamado em seguida **não** reescreve com `None`, então o time errado **permanece** nos jogos seguintes.

Num torneio onde erros de digitação de placar acontecem ao vivo e sob pressão, isso é um pé-de-banana real. O custo de errar sobe a cada fase.

**Recomendação:** ou (a) permitir des-propagação controlada (recomputar o bracket inteiro a partir do zero quando um KO é resetado, respeitando jogos já encerrados como fonte de verdade), ou (b) ao menos um endpoint admin "recalcular bracket do zero" que limpe slots não-decididos. Hoje `/api/admin/recompute` (`admin.py:80`) só roda o mesmo `persist_resolutions` conservador, então **não resolve** este caso.

---

### A4 — Estado global em memória: SSE, rate-limit e cache do ranking quebram com mais de um worker

Três singletons de módulo guardam estado em RAM do processo:

- `services/live_bus.py:49` → `bus = LiveBus()` (assinantes SSE).
- `core/ratelimit.py` → instância única por app (`main.py:79`).
- `services/leaderboard.py:22-23` → `_cache` + `_cache_lock`.

Tudo bem **enquanto** rodar em **1 processo / 1 worker** (o `CONTINUITY.md` assume "container único"). Mas:

- Se algum dia subir `uvicorn --workers 2` (ou Gunicorn com vários workers, comum em produção), o **fanout de SSE silenciosamente para de funcionar entre workers**: um placar atualizado no worker A não notifica os assinantes SSE pendurados no worker B. O cliente só descobre pelo polling de 30s — a "experiência ao vivo" degrada sem erro nenhum.
- O rate-limit vira por-worker (limites efetivos multiplicados pelo nº de workers).
- O cache do ranking fica inconsistente entre workers até o próximo `data_version`.

`Dockerfile`/`render.yaml` precisam ser conferidos para garantir 1 worker — e isso vira um **acoplamento implícito e frágil** entre a arquitetura e o comando de boot.

**Recomendação:** documentar como **invariante de deploy** que é 1 worker (e travar no comando), ou externalizar esses estados (Postgres `LISTEN/NOTIFY` para SSE, rate-limit/cached no banco) se quiser escalar horizontalmente.

---

## 3. 🟡 MÉDIO

### M1 — Premissa não confirmada sobre `fullTime` da football-data afeta a pontuação do mata-mata

`providers/football_data.py:71-74` assume que `score.fullTime` *"já inclui a prorrogação"*. A football-data.org v4 também expõe `regularTime`, `extraTime` e `penalties`. **A semântica exata de `fullTime` em jogos de prorrogação não está verificada no código** — é uma suposição sobre uma API de terceiros que, se estiver errada, faz **toda a pontuação de mata-mata via provider** usar o placar errado (90' em vez de fim da prorrogação, ou vice-versa). Marcado no ledger? Não. Testado contra payload real? Não (o teste usa mocks).

**Recomendação:** confirmar contra um payload real de jogo com prorrogação **antes** dos mata-matas e registrar a conclusão como `[TOOL]` no ledger. Como o modo padrão é manual, o impacto é condicional a ligar o token — mas é exatamente nos mata-matas que tentarão ligar.

### M2 — Casamento "fuzzy" do provider pode atribuir um update ao jogo errado

`providers/sync.py:59-80` (`_find_local`): sem `external_id` conhecido, casa por janela de ±3h (`MATCH_WINDOW`) + códigos dos times; se isso falhar e **sobrar exatamente 1 candidato na janela, retorna esse candidato**. No mata-mata, os slots ainda não resolvidos têm `home_team_id = None`, então o casamento por código falha (códigos viram `None`) e a heurística do "1 candidato" assume o controle. A Copa tem vários jogos eliminatórios **no mesmo dia**, dentro de 3h um do outro. O `external_id` mitiga **depois** do primeiro sync, mas o primeiro sync de um jogo TBD é justamente o ponto cego.

**Recomendação:** exigir casamento forte (external_id **ou** dois códigos) e nunca cair no "único candidato" quando os times não estiverem definidos; logar e pular em vez de adivinhar (coerente com a regra do projeto "se falhar, falhe").

### M3 — Fallbacks silenciosos na config contradizem o princípio declarado

`config.py:1-3` afirma *"Sem fallbacks silenciosos: segredos obrigatórios ausentes/fracos derrubam o boot"* — e cumpre isso para `SECRET_KEY`/`PEPPER` (ótimo). Mas:

- `public_base_url` faz **fallback silencioso** para `http://localhost:8000` (`config.py:94`). Se esquecerem de setar em produção, o **redirect do OAuth do Google aponta para localhost** — quebra login social sem erro de boot.
- `cookie_secure` faz **default `false`** (`config.py:100`). Esquecer de ligar em produção = cookies de sessão **sem `Secure`** e **sem HSTS** (`main.py:86`), trafegando em texto se houver qualquer caminho HTTP.

São exatamente os "fallbacks silenciosos" que o módulo diz não ter. O `.env.example` ajuda, mas a regra do projeto ("não adicione fallbacks default na fase de dev; deixe falhar") está sendo violada nos dois pontos com maior consequência (segurança/OAuth).

**Recomendação:** em produção (quando `DATABASE_URL` presente, p.ex.), exigir `PUBLIC_BASE_URL` e `COOKIE_SECURE=true` explicitamente, derrubando o boot se ausentes.

### M4 — Lógica de "relógio ao vivo" duplicada/triplicada e divergente

Existem **três** implementações de "em que minuto está o jogo":

- `format.js:liveMinute` (estimativa pelo kickoff, ~15min de intervalo chutado) — usado por `matchCard`.
- `format.js:liveClock` (dirigido por `period`/`period_started_at` do backend) — usado por `liveContent`.
- Backend: `sync._next_period` (máquina de estado por status) **e** `football_data._derive_period` (heurística por minuto) — esta última **morta** (ver A1).

`liveMinute` e `liveClock` podem mostrar minutos diferentes para o mesmo jogo. Hoje o impacto é amortecido (jogos ao vivo são renderizados via `liveContent`/`liveClock`, e `matchCard` só pega scheduled/finished), mas a duplicação está lá, com **magic numbers** espalhados (`format.js:132` `e - 18`, `:141` `e - 15`, etc.). É frágil e confunde quem for mexer.

**Recomendação:** uma única fonte de relógio (a `liveClock`, dirigida pelo backend), apagando `liveMinute`/`minuteLabel` e a `_derive_period` morta.

### M5 — Dependências com pin frouxo e sem lockfile

`backend/requirements.txt`:

```
fastapi==0.115.*
bcrypt==4.*
requests==2.*
Pillow==11.*
psycopg[binary]==3.2.*
```

`bcrypt==4.*` e `requests==2.*` aceitam **qualquer minor/patch** futuro. Não há lockfile com hashes. Como o `Dockerfile` reinstala no build (e o gate de testes roda nesse build), **um rebuild meses depois pode puxar uma versão nova e quebrar o deploy** — justamente quando você precisar subir um hotfix durante a Copa. Isso colide com a meta "100% deploy-ready" e com a regra de "pensar à frente".

**Recomendação:** pinar versões exatas + gerar um `requirements.lock` (pip-tools/uv) com hashes; rebuilds passam a ser determinísticos.

### M6 — Pênaltis não aparecem no chaveamento

Mesmo com o provider ligado (quando os pênaltis existem), `views/bracket.js:matchBox` exibe só `home_score`/`away_score` + ✓ no vencedor. O payload `/api/bracket` (=`predicted_bracket_payload`) **traz** `home_pens`/`away_pens`/`pens_log` (`bracket_svc.py:169-171`), mas a view **ignora**. Então um jogo 2×2 (pên. 4×3) aparece como "2 × 2 ✓" sem indicar que foi nos pênaltis. Dado disponível, UI não usa.

---

## 4. 🟢 BAIXO (smells, landmines e drift)

### B1 — Adapter dual-dialeto ingênuo (`db/connection.py`)
- `_translate` faz `sql.replace("?", "%s")` (`:35`): um `?` literal dentro de string SQL, ou um `LIKE '%x%'` (o `%` quebra o parsing parametrizado do psycopg), passariam batido. Hoje não há `LIKE`/`?` literal (verificado), então é **landmine latente**, não bug ativo.
- `_split_statements` divide DDL por `;` (`:20-22`) com a justificativa "nosso DDL não tem `;` embutido". Verdadeiro hoje; quebra no dia que entrar um trigger, função, ou `CHECK` com literal contendo `;`.
- `_Psycopg2Conn.execute` (`:76-79`) cria um cursor novo a cada chamada e **nunca o fecha** — vazamento de cursores no fallback psycopg2 (o caminho principal é psycopg3).

### B2 — Hardcode de dados de domínio espalhado e duplicado
- Dados de seleção vivem em **três** lugares independentes: `seed/data/teams.json` (seed), `football_data.py:NAME_ALIASES` (provider), e `format.js:SIGLA_PT`/`SUBDIV_ABBR` (frontend). Uma seleção via repescagem que não esteja nos aliases vira `team_code = None` (não sincroniza) ou cai num fallback de sigla. São fontes que precisam ser mantidas em sincronia **na mão**.
- Os **multiplicadores de pontuação** estão duplicados em `domain/entities.py:21 MULTIPLIERS` e `frontend/js/points.js:4` — se um mudar e o outro não, o "feedback otimista" do front diverge do servidor. Sem teste que case os dois.
- IDs de jogos do mata-mata hardcoded em `entities.py:138 THIRD_SLOT_TO_MATCH` (`{"1A":79,...}`) — é dado oficial FIFA, aceitável, mas é conhecimento implícito acoplado ao número do jogo (frágil se a seed renumerar).

### B3 — E-mail pessoal versionado
`.env.example:` traz `ADMIN_EMAILS=rafaellapipucos@gmail.com` commitado no repositório. Não é segredo, mas é dado pessoal em arquivo de exemplo (deveria ser `voce@exemplo.com`).

### B4 — Estado de UI fora do store + re-render por gambiarra
`views/jogos.js`, `matches.js`, `bracket.js` guardam estado de aba/filtro em **variáveis de módulo** (`activeTab`, `selectedStage`, `closedPhase`, `activeFilter`...), fora do `store`. E forçam re-render com `store.set({})` (objeto vazio) — abusando do pub/sub como "invalida tudo". Funciona, mas é inconsistente com a arquitetura reativa do resto e dificulta testar/raciocinar sobre o estado.

### B5 — "Data clump": assinaturas longas demais
`services/results.py:set_score` tem **14 parâmetros**; `db/repos/matches.py:set_score`, idem. Lista de parâmetros longa é cheiro clássico (viola a ideia de coesão/Interface Segregation): deveria receber um DTO/dataclass (`MatchResult`) em vez de 14 posicionais opcionais — mais seguro contra troca de ordem e mais fácil de evoluir.

### B6 — Drift de comentários/constantes vs realidade
- `jobs/poller.py:6` (docstring) diz "15min fora" da janela; a constante é `IDLE_INTERVAL = 5*60` (`:23`, "5min"); o `CONTINUITY.md` D009 diz "15min". Três fontes, três valores.
- `core/tokens.py:1-5` (docstring) diz que reuso de refresh *"revoga TODAS as sessões"*; a implementação (`:78-84`, Rodada 16) **não** revoga mais a família. Docstring desatualizada.
- `db/schema.py:13 SCHEMA_VERSION = 5` é gravado uma vez com `ON CONFLICT DO NOTHING` (`:162`) e **nunca relido** para dirigir migração — a versão é decorativa; as migrações são por "existe a coluna?" (`_migrate`). Funciona, mas a constante engana.

### Observações menores
- `api.js:87` e `main.js:91` têm `catch` que engolem erro (com comentário). A regra do projeto proíbe `try-catch` **vazios**; estes têm comentário/tratamento, então passam — mas o swallow de JSON em `api.js:87` ainda é um silêncio.
- `console.warn` em `theme.js:28` e `live.js:82` — aceitável, mas é log de produção no client.
- `bump_data_version` (`schema.py:174`) guarda um inteiro como TEXT e faz `CAST` ida-e-volta — "type laundering" que funciona nos dois bancos, mas é cheiro.
- Rate-limit por `X-Forwarded-For` pegando o **primeiro** valor (`deps.py:33-37`): se o proxy não sanear o header, é spoofável (rotacionar XFF fura o limite por IP). Em Render/Fly atrás de proxy confiável, ok; mas é premissa não validada.

---

## 5. Leitura SOLID (resumo)

- **SRP:** em geral **bom** — domínio puro separado de I/O, repositórios finos, serviços orquestram. Pontos fracos: `format.js` mistura datas + relógio ao vivo + bandeiras + siglas (201 LOC, baixa coesão); `set_score` faz validação + transição + persistência + propagação + bump + publish numa função (`results.py:25-90`).
- **OCP:** `domain/bracket.py:resolve_source` é um mini-parser de strings (`"3:"`, `"W"/"L"`, `"1A"`) com `if/elif` por prefixo — adicionar um novo tipo de fonte exige editar a função (em vez de um registry extensível). Aceitável no escopo, mas é o ponto que mais cresceria.
- **LSP:** o adapter `Db` unifica SQLite/Postgres bem; o ponto frágil é o `_Psycopg2Conn` não honrar exatamente o contrato (cursor por execute, vazamento) — substituibilidade imperfeita no fallback.
- **ISP:** as assinaturas de 14 parâmetros (B5) são o oposto de interfaces enxutas.
- **DIP:** **exemplar** em alguns pontos — `Poller` recebe `connect_db`/`sync_once`/`list_matches` por injeção (`poller.py:42`), `FootballDataProvider` recebe `http_get` injetável. Mas os serviços importam repositórios concretos diretamente (`from ..db.repos import matches`), então a inversão é parcial (não há porta/interface de repositório).

---

## 6. Riscos concentrados na fase de mata-mata (visão única)

Reunindo o que mais dói **especificamente nos mata-matas**, que foi o pedido:

1. **C1** — regra 90' × prorrogação contraditória no ledger → disputa de pontuação no pior momento.
2. **C2** — modo manual não registra pênaltis → mini-placar/flag de pênaltis mortos.
3. **A3** — erro de placar em KO não se desfaz a jusante → bracket contaminado, correção manual penosa.
4. **M1** — semântica de `fullTime` não confirmada → pontuação de KO via provider pode estar errada.
5. **M2** — casamento fuzzy de jogos TBD no mesmo dia → update no jogo errado.
6. **M6** — pênaltis nunca exibidos no chaveamento.
7. (Suporte) `winner_id()`/`set_score` exigem `winner_team_id` em empate de KO (`results.py:65-73`) — **correto e bem feito**, mas depende do admin lembrar de preencher o `select` de vencedor; sem ele, o sync **pula** o jogo e loga warning (`sync.py:145-147`), deixando o bracket parado sem alarme visível ao usuário.

---

## 7. Plano de ação sugerido (prioridade)

1. **Resolver C1 já:** fixar a regra (fim da prorrogação) e **corrigir `CONTINUITY.md`** (supersedendo D005 + invariante). Adicionar teste de paridade de regra front/back.
2. **Resolver C2 já:** adicionar pênaltis ao `AdminScoreIn` + UI do admin (o serviço já aceita).
3. **A2/A4 antes de qualquer pico:** pool de Postgres + travar/declarar 1 worker (ou externalizar SSE via LISTEN/NOTIFY).
4. **A3:** endpoint "recalcular bracket do zero" que limpe slots não-decididos.
5. **A1:** limpar dead code e re-apontar testes (reduz risco mascarado).
6. **M1/M2:** validar `fullTime` real + endurecer o casamento do provider — **antes** de ligar o token nos mata-matas.
7. **M5:** pinar + lockfile para builds reproduzíveis.
8. Demais itens 🟢 conforme fôlego.

---

*Metodologia: leitura integral de `backend/app/**` e `frontend/js/**`, verificação cruzada por `grep` (usos/imports/dead code), conferência das premissas contra testes e contra `CONTINUITY.md`. Cada achado cita arquivo:linha para reprodução. As checagens de "código morto" foram confirmadas pela ausência de import nas views ativas (`main.js`) e nas rotas (`api/*.py`).*
