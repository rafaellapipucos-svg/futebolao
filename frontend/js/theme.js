// theme.js — alterna entre escuro (padrão) e claro e lembra a escolha.
// A aplicação inicial (antes da 1ª pintura) é feita por um script inline no
// index.html para evitar "flash" de tema errado.
const KEY = 'theme';
const RESET_KEY = 'theme_reset';
const RESET_TOKEN = 'r16-dark-default';

// Pura/testável: resolve o tema a partir de um storage, aplicando o RESET único
// (Rodada 16): se o reset ainda não rodou, zera a preferência antiga e marca-o.
// Resultado: todos voltam ao ESCURO neste deploy; só fica claro quem escolher
// claro DEPOIS do reset.
export function resolveTheme(storage) {
  try {
    if (storage.getItem(RESET_KEY) !== RESET_TOKEN) {
      storage.removeItem(KEY);
      storage.setItem(RESET_KEY, RESET_TOKEN);
    }
    return storage.getItem(KEY) === 'light' ? 'light' : 'dark';
  } catch (err) {
    return 'dark';
  }
}

function write(value) {
  try {
    localStorage.setItem(KEY, value);
  } catch (err) {
    console.warn('theme: persistência falhou (segue sem lembrar)', err);
  }
}

export function getTheme() {
  // Fonte da verdade = o data-theme JÁ aplicado (pelo inline do index.html, que
  // roda antes da 1ª pintura). Ler dele garante que o BOTÃO nunca discorde da
  // TELA. Sem DOM (testes), cai no resolveTheme (reset + leitura da preferência).
  if (typeof document !== 'undefined' && document.documentElement) {
    const applied = document.documentElement.getAttribute('data-theme');
    if (applied === 'light' || applied === 'dark') return applied;
  }
  return resolveTheme(localStorage);
}

// Reaplica o tema no boot (rede de segurança caso o index.html venha de cache
// antigo sem o reset): roda o reset idempotente e crava o data-theme correto.
export function initTheme() {
  const t = resolveTheme(localStorage);
  applyTheme(t);
  return t;
}

export function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', theme === 'dark' ? '#04070f' : '#e9eef6');
}

export function toggleTheme() {
  const next = getTheme() === 'dark' ? 'light' : 'dark';
  write(next);
  applyTheme(next);
  return next;
}
