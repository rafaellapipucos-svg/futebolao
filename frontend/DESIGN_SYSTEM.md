# DESIGN SYSTEM — Tabolão Copa 2026 (pipeline de polish, Agentes 1–7)

Fonte da verdade para TODOS os agentes. Mantém a paleta e a identidade atuais
(verde+turquesa, glass leve, tema claro padrão + tema escuro). Nada aqui muda a
visão do produto — só padroniza. Em conflito entre feedback de aba e este
documento, **este documento vence**.

## 0. Regras de ouro (valem para todos)
- ≤300 LOC por arquivo. Se `views.css` for estourar, crie `frontend/css/views-extra.css`
  (o primeiro agente que precisar cria e adiciona o `<link>` no `index.html` após
  `views.css`); os demais apenas anexam em seção comentada própria.
- Sem `innerHTML` com dados, sem `eval`. DOM sempre via `h()` de `js/ui.js`.
- Todo agente roda os testes antes de entregar:
  `cd frontend && node --test tests/*.test.js` (e `node --check` nos js tocados).
- Tudo deve funcionar **nos dois temas** (testar `data-theme="dark"` também).
- Contraste WCAG AA: texto normal ≥4.5:1, texto grande/bold ≥3:1. Nunca usar
  `--text-2` em fonte <0.72rem; para metadados pequenos preferir `--text-1`.
- Não remover tokens/classes existentes — apenas adicionar/ajustar valores.
- Hover/focus: manter `:focus-visible` global; elementos clicáveis novos precisam
  ser `<button>`/`<a>` reais.

## 1. Tokens novos (criar em `css/tokens.css`)
O **Agente 2** cria todos os tokens abaixo (nos DOIS temas). Agentes seguintes
só consomem. O Agente 1 cria apenas os de bandeira (roda antes).

```css
/* Semânticos (alias — claro e escuro herdam automaticamente) */
--success: var(--green);     /* acerto de resultado, confirmações, vaga */
--accent:  var(--cyan);      /* turquesa: destaque informativo (letra do grupo, links, fase) */
--live:    var(--red);       /* tudo "ao vivo": dot pulsante, parciais */
--exact:   var(--gold);      /* cravada/placar exato, 1º lugar, final */

/* Card sólido (substitui o vidro translúcido como fundo de card) */
--card-bg: #ffffff;                                  /* claro */
--card-bg: #0d1830;                                  /* escuro (= surface-solid) */
--shadow-card: 0 1px 3px rgba(17,25,45,.07), 0 8px 24px rgba(17,25,45,.08);  /* claro */
--shadow-card: 0 4px 24px rgba(0,0,0,.45);           /* escuro */

/* Bandeiras Twemoji (Agente 1) */
--flag-sm: 18px;   /* tabelas, listas densas (standings, bracket, bettors) */
--flag-md: 24px;   /* padrão: match-card, live-head, mybets */
--flag-lg: 32px;   /* destaque (se necessário) */
```

## 2. Superfícies e cards
- **Card = branco puro sobre fundo cinza-claro.** `.glass` (base.css) passa a usar
  `background: var(--card-bg)` + `box-shadow: var(--shadow-card)`; manter
  `border: 1px solid var(--border)` e `border-radius: var(--r-lg)` (20px — raio
  padrão de card; sub-itens internos usam `--r-md` 14px; pills `--r-full`).
  O backdrop-filter pode ficar (inócuo em fundo sólido). Implementação: Agente 2,
  uma única vez — os demais NÃO reestilizam `.glass`.
- Sub-cards internos (ex.: `.live-bettor`, `.hist-item`): `background: var(--card-bg)`,
  borda `--border`, sombra leve opcional `0 1px 2px rgba(17,25,45,.06)`.
- Padding de card: mínimo `var(--sp-4)` (16px); cards principais de aba
  (`.group-card`, `.live-card`, `.match-card`) usam `var(--sp-4)` mobile e
  podem ir a `var(--sp-5)` em ≥880px. Nada de padding <12px em card raiz.
- **Não usar borda tracejada** em elementos de conteúdo (placeholders de time,
  labels do bracket): trocar `dashed` por `solid` com `--border` ou fundo
  `--surface-2`. Único tracejado permitido: separador `.bet-area` (border-top).

## 3. Tipografia
- Família: manter system stack (`--font`); dados numéricos usam `--mono` **ou**
  `font-variant-numeric: tabular-nums`. Regra única: criar utilitário em base.css
  (Agente 2):
  ```css
  .tnum { font-variant-numeric: tabular-nums; letter-spacing: 0; }
  ```
  e aplicar `tabular-nums` também em `.standings-table td`, `.score-line`,
  `.kick-time`, `.lb-table .pts`, `.podium-pts`, `.stat-card .val`, `.bet-value`,
  `.countdown` (a maioria já usa `--mono`; garantir o variant).
- Escala (já existe, não criar nova): xs .72 / sm .84 / md .95 / lg 1.12 / xl 1.45 / 2xl 2rem.
- Pesos: 800 só para H1, placares e números-chave; 700 para títulos de card e
  nomes de time; 600 para botões/labels; 400/500 para corpo.
- **H1 das abas: padrão único do site** — primeira(s) palavra(s) em `--text-0` +
  UMA palavra de destaque com `.grad-text`. Esse padrão FICA em todas as abas
  (resolve os feedbacks de "cor unificada" por consistência, não por remoção).
  Nenhum agente troca o estilo do título da sua aba.
- Títulos de card (ex. "Grupo A"): `font-size: var(--fs-lg)`, `font-weight: 800`,
  cor `--text-0`; o identificador (letra do grupo) em `--accent`.
- Subtítulo `.sub`: `--fs-sm`, `--text-2`, `margin-top: 2px` (colado ao título).

## 4. Cores semânticas — uso obrigatório
| Significado | Token | Exemplos |
|---|---|---|
| Acerto de resultado / confirmação / classificado | `--success` (+ `--green-soft` p/ fundo) | chip ✓, linha 1º–2º do grupo, borda de bettor que pontua |
| Cravada (placar exato) / ouro / final | `--exact` (+ `--gold-soft`) | chip 🎯, linha do 3º do grupo, pódio 1º |
| Ao vivo | `--live` (+ `--red-soft`) | `.chip-live` com `.dot` pulsante (animação `pulse` existente) |
| Destaque informativo | `--accent` (+ `--cyan-soft`) | letra do grupo, chip de fase, links |
| Erro/aposta perdida | NEUTRO (não vermelho) | chip cinza `--surface-2` + ícone ✕ `--text-2`; vermelho é reservado p/ "ao vivo" e ações destrutivas |

- Indicador AO VIVO: **sempre** `.chip-live` + `.dot` (base.css). Proibido criar
  variações novas. Agente 4 pode reforçar o dot (8px, `box-shadow: 0 0 0 3px var(--red-soft)`).

## 5. Bandeiras (padrão Twemoji — Agente 1)
- Assets locais (sem CDN em runtime): `frontend/assets/flags/<codepoints>.svg`,
  baixados do Twemoji (jsdelivr, jdecked/twemoji v15+). Nome = codepoints hex
  minúsculos separados por hífen (ex.: BR `1f1e7-1f1f7.svg`,
  Inglaterra `1f3f4-e0067-e0062-e0065-e006e-e0067-e007f.svg`,
  Escócia `1f3f4-e0067-e0062-e0073-e0063-e0074-e007f.svg`).
- `format.js`: nova função pura `flagSrc(team)` (emoji → caminho do asset);
  manter `teamFlag`/`flagIsAbbr` apenas como fallback textual.
- `ui.js` `flagContent(team, size)`: retorna
  `h('img', { class:'team-flag-img', src: flagSrc(team), alt:'', 'aria-hidden':'true', width:…, height:… })`
  com fallback `onerror` → span `.flag-abbr` atual. Nome do time fica no texto
  adjacente (por isso `alt=""`).
- CSS (Agente 1 adiciona em components.css, seção "Flags"):
  ```css
  .team-flag-img { width: var(--flag-md); height: var(--flag-md);
    flex: none; object-fit: contain; }
  .flag-sm { width: var(--flag-sm); height: var(--flag-sm); }
  .flag-lg { width: var(--flag-lg); height: var(--flag-lg); }
  ```
- Tamanho fixo por contexto: tabelas/listas densas `--flag-sm`; cards de jogo
  `--flag-md`. **Proibido** dimensionar bandeira via `font-size`/style inline —
  os `style:'font-size:…'` existentes nas views são removidos pelo agente da aba.
- Placeholder de time indefinido (bracket/jogos): círculo `--flag-sm/md` com
  `background: var(--surface-2); border: 1px solid var(--border); border-radius: 50%`.

## 6. Truncamento de nomes
Padrão único: `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;`
no elemento do nome **+ atributo `title` com o nome completo** (tooltip nativo).
Vale para `.team-name`, `.live-bettor-name`, `.podium-name`, `.bracket-team .nm`,
nomes na `.lb-table`. Quem tocar num desses garante o `title`.

## 7. Componentes padronizados
- **Filterbar/abas-pílula** (spec única — implementada pelo Agente 5 em
  components.css, consumida por Jogos, Mata-mata e Apostas):
  - chip: `padding: 8px 16px; font-size: var(--fs-sm);`
  - inativo: `background: var(--card-bg); border: 1px solid var(--border);
    color: var(--text-1);` (não pode parecer desabilitado: nada de opacity)
  - ativo: `background: var(--grad-brand); color: var(--text-on-accent);` (já existe)
  - `.count-badge` dentro de chip ativo: `background: rgba(255,255,255,.25);
    color: var(--text-on-accent);`
- **Feedback de aposta encerrada** (rodapé do match-card, betbox.js `lockedView`):
  cravada = chip `--exact` com 🎯/ícone target + "X pts"; resultado = chip
  `--success` com ✓ + "X pts"; erro = chip neutro com ✕ + "0 pts"; parcial (live)
  adiciona `.chip-live`. Sempre na MESMA posição (rodapé, após separador).
- **Botões**: `.btn-primary` (gradiente brand) é o único botão de ação primária.
  Sombra/elevação já existem; não inventar novos estilos de botão.
- **Tabelas**: cabeçalho `--fs-xs` 700 `--text-2`; colunas numéricas centradas
  com `tabular-nums` e mesma largura de th/td; coluna de nome à esquerda.
  Zebra/divisórias: `border-bottom: 1px solid var(--border)` (padrão atual) é o
  divisor oficial; zebra striping é opcional APENAS na `.lb-table`
  (`tbody tr:nth-child(even) td { background: var(--surface); }`).

## 8. Mapa de propriedade de arquivos (evitar conflito)
| Arquivo | Dono(s) — seções |
|---|---|
| `css/tokens.css` | Ag.1 (só `--flag-*`) · Ag.2 (todos os demais tokens novos) |
| `css/base.css` | Ag.2 (`.glass`, `.tnum`) · Ag.4 (só `.chip-live .dot`) |
| `css/components.css` | Ag.1 (seção Flags) · Ag.3 (match-card/bet-area/busca) · Ag.5 (filterbar) · Ag.7 (bet-inputs/countdown-bar/status-bar) — seções comentadas separadas |
| `css/views.css` | Ag.2 (Dashboard) · Ag.4 (Ao Vivo) · Ag.5 (Bracket) · Ag.6 (Ranking) · Ag.7 (Minhas apostas) — cada um SÓ na sua seção |
| `js/format.js` + `tests/format.test.js` | Ag.1 |
| `js/ui.js` | Ag.1 (`flagContent`) · Ag.3/6 (apenas ADICIONAR paths em `ICON_PATHS`) |
| `js/betbox.js` | Ag.3 (`lockedView`) · Ag.7 (`stepper`/`openEditor`/countdown) |
| `js/views/matches.js` (exporta `matchCard` usado por mybets) | Ag.3 |
| `js/views/{dashboard,live,bracket,leaderboard,mybets}.js` | Ag.2/4/5/6/7 respectivamente |

Pipeline é sequencial (1→7): quem roda depois NÃO desfaz decisão de quem rodou
antes; divergência → registrar em CONTINUITY.md e seguir este documento.
