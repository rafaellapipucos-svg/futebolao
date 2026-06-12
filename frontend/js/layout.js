// layout.js — shell do app: topbar, navegação desktop, tab bar mobile.
import { api } from './api.js';
import { navigate } from './router.js';
import { avatarEl, h, icon, toast } from './ui.js';
import { getTheme, toggleTheme } from './theme.js';

const NAV_ITEMS = [
  { route: 'dashboard', label: 'Tabela', icon: 'table' },
  { route: 'jogos', label: 'Jogos', icon: 'ball' },
  { route: 'ao-vivo', label: 'Ao Vivo', icon: 'live' },
  { route: 'chaveamento', label: 'Mata-mata', icon: 'bracket' },
  { route: 'ranking', label: 'Ranking', icon: 'trophy' },
  { route: 'apostas', label: 'Apostas', icon: 'list' },
];

function brandLogo() {
  const svg = icon('ball', 26);
  svg.style.color = 'var(--green)';
  return h('a', { class: 'brand', href: '#/dashboard' },
    svg,
    h('span', { class: 'grad-text' }, 'TABOLÃO'),
    h('span', { class: 'year' }, '26'),
  );
}

async function doLogout(store) {
  try {
    await api.post('/api/auth/logout');
  } catch { /* sessão já podia estar inválida */ }
  store.set({ user: null, matches: null, standings: null, leaderboard: null, bracket: null });
  navigate('login');
  toast('Até logo! 👋');
}

export function renderShell(store, state, contentEl) {
  const items = [...NAV_ITEMS];
  if (state.user && state.user.is_admin) {
    items.push({ route: 'admin', label: 'Admin', icon: 'shield' });
  }
  const active = state.route.name;

  const topnav = h('nav', { class: 'topnav', 'aria-label': 'principal' },
    items.map((item) => h('a', {
      href: `#/${item.route}`,
      class: active === item.route ? 'active' : '',
    }, item.label)),
  );

  const profileBtn = h('button', {
    class: 'userchip', title: 'Meu perfil',
    onClick: () => navigate('perfil'),
  },
    avatarEl(state.user ? state.user.avatar_url : null,
      state.user ? state.user.display_name : '?', 32),
    h('span', { class: 'name' }, state.user ? state.user.display_name : ''),
  );
  const logoutBtn = h('button', {
    class: 'logoutbtn', title: 'Sair da conta', 'aria-label': 'sair da conta',
    onClick: () => doLogout(store),
  }, icon('logout', 19));

  const tabbar = h('nav', { class: 'tabbar', 'aria-label': 'abas' },
    items.map((item) => h('a', {
      href: `#/${item.route}`,
      class: active === item.route ? 'active' : '',
    }, icon(item.icon, 21), item.label)),
  );

  const themeBtn = h('button', {
    class: 'iconbtn', type: 'button',
    title: 'Alternar tema claro/escuro', 'aria-label': 'alternar tema',
    onClick: () => {
      const t = toggleTheme();
      themeBtn.replaceChildren(icon(t === 'dark' ? 'sun' : 'moon', 18));
    },
  }, icon(getTheme() === 'dark' ? 'sun' : 'moon', 18));

  return h('div', { class: 'shell' },
    h('header', { class: 'topbar' }, brandLogo(), topnav,
      h('div', { class: 'user-area' }, themeBtn, profileBtn, logoutBtn)),
    h('main', {}, contentEl),
    tabbar,
  );
}
