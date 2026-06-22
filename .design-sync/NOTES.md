# design-sync notes — Tabolão Copa 2026

## Why this is a styles-only sync (not a component sync)
- `frontend/` is a **no-build, imperative-DOM SPA** (`frontend/package.json`:
  *"SPA sem build - ES modules nativos servidos pelo FastAPI"*).
- "Components" are CSS classes (`css/*.css`) applied to DOM built imperatively by
  `frontend/js/ui.js` (`h()`, `modal()`, `toast()`, `avatarEl()`, …). There are
  **no importable/renderable components**, no `dist/`, no Storybook, no
  `*.stories.*`, no React.
- The design-sync converter targets compiled component libraries, so it does not
  apply here. Authoring React wrappers would be a reimplementation (forbidden by
  the skill and not code the engineers ship), so the user chose the **styles/
  tokens-only** path: upload `styles.css` + the CSS closure + a conventions
  header. Result: on-brand rendering and a real class vocabulary for the design
  agent, but **no component library / picker cards**.

## Bundle layout (hand-authored, off-script)
- `ds-bundle/styles.css` — entry; `@import`s the closure in `frontend/index.html`
  order: tokens → base → components → views → views-extra → match-bets.
- `ds-bundle/css/*.css` — verbatim copies of `frontend/css/*.css`.
- `ds-bundle/README.md` — copy of `.design-sync/conventions.md` (no generated
  body, since there are no components to index).
- No `_ds_bundle.js`, no `_vendor/`, no component dirs, no `fonts/` (system font
  stack), no `_ds_sync.json` (off-script — next sync re-verifies, which is cheap).

## Gotcha: dark theme requires `data-theme` on the document root
- Light is the `:root` default; the dark palette is `:root[data-theme="dark"]`.
  A wrapping `<div data-theme="dark">` will **not** trigger dark — the selector
  is `:root`, so it must be on `<html>`. Documented in the conventions header.
- The CSS closure is self-contained: **no `url()` asset references** (flags are
  set via JS `src` at runtime, not in CSS), so the closure renders standalone.

## Re-sync
- This is off-script: a future sync should re-run this hand path, not the standard
  converter. To refresh, re-copy `frontend/css/*.css` into `ds-bundle/css/`,
  re-validate the conventions header against the bundle, and re-upload.
- If `frontend/css/` files are renamed/added, update both `ds-bundle/styles.css`
  imports and this note.
