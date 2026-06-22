# Tabolão · Copa 2026 — Design System (styles-only import)

> **Styles-only.** The source app is a no-build, imperative-DOM SPA, so no
> renderable JS/React components are bundled. This project ships the brand's
> CSS **tokens** and **class vocabulary** as the rendered look. Style designs by
> applying these classes and reading these custom properties — there is no
> component API.

## Setup / theming
- Two themes. **Light is the `:root` default; dark is the brand's primary look.**
  To get dark, set `data-theme="dark"` on the document root `<html>` — the dark
  palette lives under `:root[data-theme="dark"]`, so a wrapper
  `<div data-theme="dark">` will **not** trigger it; it must be on the root
  element. Light needs no attribute.
- Every design value is a CSS custom property in `css/tokens.css`. Never hardcode
  a color — use a token (`var(--…)`).
- `styles.css` is the entry and `@import`s the full closure in order; linking
  only `styles.css` is enough.

## Styling idiom — CSS classes + custom properties (no props, no CSS-in-JS)
Style by adding **classes** to elements and reading **`var(--token)`** for custom
values. Class families (real names):

- **Surfaces & layout:** `.glass` (card), `.shell`, `.topbar`, `.tabbar`,
  `.page`, `.page-head`, `.row`, `.spread`, `.center`, `.filterbar`.
- **Buttons:** `.btn`, `.btn-primary` (the single primary action, brand
  gradient), `.btn-danger`, `.btn-sm`, `.btn-block`, `.iconbtn`, `.logoutbtn`.
- **Inputs:** `.field`, `.input` (incl. `textarea.input`); bet fields
  `.bet-input`, `.bet-value`, `.bet-stepper`.
- **Chips/badges:** `.chip`, `.chip-green`, `.chip-cyan`, `.chip-gold`,
  `.chip-red`, `.chip-live` (+ pulsing `.dot`), `.count-badge`.
- **Feedback:** `.toast` (`.toast-ok` / `.toast-err`), `.modal` (+
  `.modal-backdrop`, `.modal-close`), `.skeleton`, `.empty-state`, `.boot-splash`.
- **Match / score:** `.match-card`, `.match-grid`, `.team-side`, `.team-name`,
  `.team-flag-img` (+ `.flag-sm` / `.flag-lg`), `.score-box`, `.score-line`,
  `.kick-time`, `.countdown`, `.countdown-bar`.
- **Tables / standings:** `.standings-table`, `.group-card`, `.group-letter`,
  `.legend`, `.lb-table`, `.pos-medal`, `.bracket-match`, `.podium`,
  `.status-bar`, `.status-item`.
- **Utilities:** `.tnum` (tabular numerals), `.muted`, `.small`, `.grad-text`
  (brand-gradient text).

**Key tokens** (`var(--…)`): text `--text-0/1/2`, `--text-on-accent`; background
`--bg-0/1/2`; surfaces `--surface`, `--surface-2`, `--surface-solid`, `--card-bg`;
borders `--border`, `--border-strong`; semantic `--success`, `--accent`, `--live`,
`--exact` (built on `--green`, `--cyan`, `--gold`, `--red`, `--violet` and their
`-soft` variants); gradients `--grad-brand`, `--grad-gold`; type `--font`,
`--mono`, `--fs-xs … --fs-2xl`; shape `--r-sm/md/lg/full`; space `--sp-1 … --sp-7`;
shadows `--shadow-card`, `--shadow-1`.

**Semantic color rules** (from the source design system):
- `--success` (+ `--green-soft`) — correct result / confirmation / qualified.
- `--exact` (+ `--gold-soft`) — exact score ("cravada") / gold / final / 1st.
- `--live` (+ `--red-soft`) — anything live; always `.chip-live` with pulsing `.dot`.
- `--accent` (+ `--cyan-soft`) — informational highlight (group letter, phase, links).

## Where the truth lives — read these before styling
- `css/tokens.css` — every token, both themes. **Start here.**
- `css/base.css` — primitives (`.glass`, `.btn*`, `.input`, `.chip*`, toasts, modal, utilities).
- `css/components.css` — shell, nav, match cards, filterbar pills, status bar, countdown.
- `css/views.css`, `css/views-extra.css`, `css/match-bets.css` — view-specific
  (standings, bracket, podium, leaderboard, bet modal).

## Build snippet (real, idiomatic)
```html
<html data-theme="dark">
<link rel="stylesheet" href="styles.css">
<div class="shell">
  <article class="glass match-card">
    <div class="match-meta">
      <span class="chip chip-live"><span class="dot"></span> AO VIVO</span>
      <span class="countdown">12:34</span>
    </div>
    <div class="match-grid">
      <div class="team-side"><span class="team-name">Brasil</span></div>
      <div class="score-box">
        <span class="score-line tnum"><span>2</span><span class="score-x">×</span><span>1</span></span>
      </div>
      <div class="team-side right"><span class="team-name">Argentina</span></div>
    </div>
    <button class="btn btn-primary btn-block">Apostar</button>
  </article>
</div>
</html>
```

Identity: green + turquoise, light glass, **dark theme by default**. H1 pattern:
plain words in `--text-0` + one highlight word with `.grad-text`. WCAG AA
contrast; numeric data uses `.tnum` / `--mono`. Full design rules live in
`frontend/DESIGN_SYSTEM.md` in the source repo.
