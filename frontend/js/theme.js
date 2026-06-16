// theme.js — alterna entre escuro (padrão) e claro e lembra a escolha.
// A aplicação inicial (antes da 1ª pintura) é feita por um script inline no
// index.html para evitar "flash" de tema errado.
const KEY = 'theme';

function read() {
  try {
    return localStorage.getItem(KEY);
  } catch (err) {
    console.warn('theme: leitura do localStorage falhou', err);
    return null;
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
  // Padrão = ESCURO; só fica claro se o usuário escolheu explicitamente.
  return read() === 'light' ? 'light' : 'dark';
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
