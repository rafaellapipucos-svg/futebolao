# DESIGN SYSTEM — Tabolão Copa 2026 (referência)

Fonte da verdade de **design** do app. Mantém a paleta e a identidade (verde+turquesa,
glass leve, **tema escuro padrão** + tema claro). Não contém instruções para agentes — só
padroniza tokens, superfícies, tipografia, cores e componentes. Em conflito entre feedback
pontual e este documento sobre *aparência*, este documento vence.

## 0. Regras de ouro
- ≤300 LOC por arquivo de código. Se `views.css` estourar, use `frontend/css/views-extra.css`
  (já existe; adicione em seção comentada própria, com `<link>` após `views.css` no `index.html`).
- Sem `innerHTML` com dados, sem `eval`. DOM sempre via `h()` de `js/ui.js`.
- Rode os testes antes de entregar: `cd frontend && node --test tests/*.test.js` (e
  `node --check` nos js tocados).
- Tudo deve funcionar **nos dois temas** (testar `data-theme="dark"`, que é o padrão, e o claro).
- Contraste WCAG AA: texto normal ≥4.5:1, texto grande/bold ≥3:1. Nunca usar `--text-2` em
  fonte <0.72rem; para metadados pequenos preferir `--text-1`.
- Não remover tokens/classes existentes — apenas adicionar/ajustar valores.
- Cor **só** via token de `tokens.css` (a trava de contraste do `verify.sh` quebra o build se
  aparecer cor hardcoded fora de `tokens.css`).
- Hover/focus: manter `:focus-visible` global; elementos clicáveis precisam ser `<button>`/`<a>` reais.

## 1. Tokens (em `css/tokens.css`)
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

/* Bandeiras Twemoji */
--flag-sm: 18px;   /* tabelas, listas densas (standings, bracket, bettors) */
--flag-md: 24px;   /* padrão: match-card, live-head, mybets */
--flag-lg: 32px;   /* destaque (se necessário) */
```

## 2. Superfícies e cards
- **Card = branco puro sobre fundo cinza-claro** (claro) / superfície sólida (escuro). `.glass`
  usa `background: var(--card-bg)` + `box-shadow: var(--shadow-card)`; manter
  `border: 1px solid var(--border)` e `border-radius: var(--r-lg)` (20px; sub-itens `--r-md` 14px;
  pills `--r-full`).
- Sub-cards internos (`.live-bettor`, `.hist-item`): `background: var(--card-bg)`, borda `--border`,
  sombra leve opcional.
- Padding de card: mínimo `var(--sp-4)` (16px); cards principais de aba (`.group-card`,
  `.live-card`, `.match-card`) usam `var(--sp-4)` mobile e podem ir a `var(--sp-5)` em ≥880px.
- **Não usar borda tracejada** em conteúdo (placeholders de time, labels do bracket): use `solid`
  com `--border` ou fundo `--surface-2`. Único tracejado permitido: separador `.bet-area` (border-top).

## 3. Tipografia
- Família: system stack (`--font`); dados numéricos usam `--mono` **ou**
  `font-variant-numeric: tabular-nums` (utilitário `.tnum`). Aplicar tabular-nums em
  `.standings-table td`, `.score-line`, `.kick-time`, `.lb-table .pts`, `.podium-pts`,
  `.stat-card .val`, `.bet-value`, `.countdown`.
- Escala: xs .72 / sm .84 / md .95 / lg 1.12 / xl 1.45 / 2xl 2rem.
- Pesos: 800 só para H1, placares e números-chave; 700 para títulos de card e nomes de time;
  600 para botões/labels; 400/500 para corpo.
- **H1 das abas: padrão único** — primeira(s) palavra(s) em `--text-0` + UMA palavra de destaque
  com `.grad-text`. Esse padrão fica em todas as abas.
- Títulos de card (ex. "Grupo A"): `font-size: var(--fs-lg)`, `font-weight: 800`, cor `--text-0`;
  o identificador (letra do grupo) em `--accent`.
- Subtítulo `.sub`: `--fs-sm`, `--text-2`, `margin-top: 2px`.

## 4. Cores semânticas — uso obrigatório
| Significado | Token | Exemplos |
|---|---|---|
| Acerto de resultado / confirmação / classificado | `--success` (+ `--green-soft`) | chip ✓, linha 1º–2º do grupo, borda de bettor que pontua |
| Cravada (placar exato) / ouro / final | `--exact` (+ `--gold-soft`) | chip 🎯, 3º que se classifica, pódio 1º |
| Ao vivo | `--live` (+ `--red-soft`) | `.chip-live` com `.dot` pulsante |
| Destaque informativo | `--accent` (+ `--cyan-soft`) | letra do grupo, chip de fase, links |
| Erro/aposta perdida (no ranking/histórico) | NEUTRO | chip cinza `--surface-2` + ícone ✕ `--text-2` |

> Exceção (aba **Jogos encerrados**, Rodada 16): o **fundo** do cartão indica o resultado da
> sua aposta — errou = vermelho (`--red`/`--red-soft`), acertou = verde (`--success`),
> cravou = dourado (`--exact`), não apostou = neutro. É o único lugar onde "errou" é vermelho.
> Indicador AO VIVO: **sempre** `.chip-live` + `.dot` (base.css). Não criar variações.

## 5. Bandeiras (padrão Twemoji)
- Assets locais (sem CDN em runtime): `frontend/assets/flags/<codepoints>.svg`. Nome = codepoints
  hex minúsculos separados por hífen (BR `1f1e7-1f1f7.svg`; Inglaterra
  `1f3f4-e0067-e0062-e0065-e006e-e0067-e007f.svg`).
- `format.js`: `flagSrc(team)` (emoji → caminho do asset); `teamFlag`/`flagIsAbbr` só como fallback textual.
- `ui.js` `flagContent(team, size)`: `img.team-flag-img` com fallback `onerror` → `.flag-abbr`.
- CSS (`components.css`, seção "Flags"):
  ```css
  .team-flag-img { width: var(--flag-md); height: var(--flag-md); flex: none; object-fit: contain; }
  .flag-sm { width: var(--flag-sm); height: var(--flag-sm); }
  .flag-lg { width: var(--flag-lg); height: var(--flag-lg); }
  ```
- Tamanho por contexto (tabelas `--flag-sm`; cards `--flag-md`). **Proibido** dimensionar
  bandeira por `font-size`/style inline.
- Placeholder de time indefinido: círculo `--flag-sm/md` com `background: var(--surface-2);
  border: 1px solid var(--border); border-radius: 50%`.

## 6. Truncamento de nomes
Padrão: `overflow:hidden; text-overflow:ellipsis; white-space:nowrap;` no elemento do nome **+
atributo `title` com o nome completo**. Vale para `.team-name`, `.live-bettor-name`,
`.podium-name`, `.bracket-team .nm`, nomes na `.lb-table`.

## 7. Componentes padronizados
- **Filterbar/abas-pílula** (em `components.css`, consumida por Tabela/Jogos/Mata-mata):
  - chip: `padding: 8px 16px; font-size: var(--fs-sm);`
  - inativo: `background: var(--card-bg); border: 1px solid var(--border); color: var(--text-1);`
    (nada de opacity — não pode parecer desabilitado)
  - ativo: `background: var(--grad-brand); color: var(--text-on-accent);`
  - `.count-badge` em chip ativo: `background: rgba(255,255,255,.25); color: var(--text-on-accent);`
- **Feedback de aposta encerrada** (betbox `lockedView`): cravada = chip `--exact` 🎯 + "X pts";
  resultado = chip `--success` ✓ + "X pts"; erro = chip neutro ✕ + "0 pts"; parcial (live) com `.chip-live`.
- **Botões**: `.btn-primary` (gradiente brand) é o único botão de ação primária.
- **Tabelas**: cabeçalho `--fs-xs` 700 `--text-2`; colunas numéricas centradas com `tabular-nums`;
  coluna de nome à esquerda; divisor oficial `border-bottom: 1px solid var(--border)`; zebra
  opcional só na `.lb-table`.

## 8. Indicadores de zona (Tabela) e previsão (Mata-mata) — Rodada 16
- **Tabela de grupos** (`dashboard.js`): zona via **borda esquerda** colorida do nome.
  `pos 1–2` verde (`row-q`); `pos 3` que se classifica entre os 8 melhores → **amarelo/dourado**
  (`row-t`); `pos 3` que NÃO se classifica e `pos 4` → **vermelho** (`row-out`). Atualizar a legenda.
- **Mata-mata** (`bracket.js`): quando o confronto vem de projeção do ranking atual (`predicted`),
  marcar de forma sutil e exibir banner "Previsão com base no ranking atual". Confrontos já
  garantidos (clinched/encerrados) aparecem como definitivos.
