// main.js — boot da SPA: config → sessão → router → render → live updates.
import { api } from './api.js';
import { renderShell } from './layout.js';
import { resolveRoute, startRouter } from './router.js';
import { connectLive } from './sse.js';
import { prefetch, markStale, refreshData } from './data.js';
import { startCountdownTicker } from './countdown_ticker.js';
import { store } from './store.js';
import { initTheme } from './theme.js';
import { h } from './ui.js';
import { renderAdmin } from './views/admin.js';
import { renderBracket } from './views/bracket.js';
import { renderDashboard } from './views/dashboard.js';
import { renderLeaderboard } from './views/leaderboard.js';
import { renderLogin } from './views/login.js';
import { renderJogos } from './views/jogos.js';
import { renderProfile } from './views/profile.js';

const VIEWS = {
  login: { render: renderLogin, shell: false },
  dashboard: { render: renderDashboard, shell: true },
  chaveamento: { render: renderBracket, shell: true },
  jogos: { render: renderJogos, shell: true },
  ranking: { render: renderLeaderboard, shell: true },
  perfil: { render: renderProfile, shell: true },
  admin: { render: renderAdmin, shell: true },
};

const root = document.getElementById('app');
let disconnectLive = null;
let rendering = false;

function renderApp(state) {
  if (rendering) return; // evita reentrância de store.set durante render
  rendering = true;
  try {
    const view = VIEWS[state.route.name] || VIEWS.login;
    const content = view.render(store, state);
    root.replaceChildren(
      view.shell ? renderShell(store, state, content) : content,
    );
  } finally {
    rendering = false;
  }
}

// Chaves de cache afetadas por updates ao vivo + a chave que cada rota exibe.
const LIVE_KEYS = ['matches', 'standings', 'leaderboard', 'bracket', 'live'];
const ROUTE_DATA_KEY = {
  dashboard: 'standings', jogos: 'matches', chaveamento: 'bracket',
  ranking: 'leaderboard',
};
let liveVersion = 0;

function ensureLiveConnection(state) {
  if (state.user && !disconnectLive) {
    disconnectLive = connectLive((version) => {
      if (version === liveVersion) return;
      liveVersion = version;
      // Revalida SEM piscar: marca tudo como stale (revalida ao visitar) e
      // atualiza só a view ativa em 2º plano, trocando o dado quando chega —
      // sem zerar caches (que derrubava a tela para o skeleton a cada update).
      markStale(LIVE_KEYS);
      const activeKey = ROUTE_DATA_KEY[store.get().route.name];
      if (activeKey) refreshData(store, activeKey);
    });
  } else if (!state.user && disconnectLive) {
    disconnectLive();
    disconnectLive = null;
  }
}

async function boot() {
  initTheme(); // crava o tema certo (e roda o reset) mesmo se o index.html vier de cache
  let config = store.get().config;
  try {
    config = await api.get('/api/meta/config'); // também emite cookie CSRF
  } catch {
    root.replaceChildren(
      h('div', { class: 'boot-splash' },
        h('p', {}, 'Servidor indisponível no momento.'),
        h('button', { class: 'btn btn-primary', onClick: () => window.location.reload() },
          'Tentar de novo'),
      ),
    );
    return;
  }
  let user = null;
  try {
    user = await api.get('/api/auth/me');
  } catch { /* sem sessão: segue para login */ }

  store.set({ booted: true, config, user });
  store.subscribe((state) => {
    ensureLiveConnection(state);
    renderApp(state);
  });

  startRouter((hash) => {
    const route = resolveRoute(hash, store.get().user);
    const wanted = `#/${route.name}`;
    if (!hash.startsWith(wanted)) {
      window.location.hash = wanted; // normaliza (dispara novo evento)
      return;
    }
    store.set({ route });
  });

  ensureLiveConnection(store.get());
  renderApp(store.get());
  startCountdownTicker(); // countdowns atualizam in-place (sem re-render do app)

  // Aquece as abas principais em 2º plano (após o 1º paint) p/ navegação
  // instantânea. SSE mantém tudo fresco depois.
  if (store.get().user) {
    setTimeout(
      () => prefetch(store, ['matches', 'standings', 'leaderboard', 'bracket']),
      600,
    );
  }
}

boot();
