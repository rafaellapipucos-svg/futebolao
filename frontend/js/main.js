// main.js — boot da SPA: config → sessão → router → render → live updates.
import { api } from './api.js';
import { renderShell } from './layout.js';
import { resolveRoute, startRouter } from './router.js';
import { connectLive } from './sse.js';
import { store } from './store.js';
import { h } from './ui.js';
import { renderAdmin } from './views/admin.js';
import { renderBracket } from './views/bracket.js';
import { renderDashboard } from './views/dashboard.js';
import { renderLeaderboard } from './views/leaderboard.js';
import { renderLogin } from './views/login.js';
import { renderMatches } from './views/matches.js';
import { renderMyBets } from './views/mybets.js';
import { renderProfile } from './views/profile.js';

const VIEWS = {
  login: { render: renderLogin, shell: false },
  dashboard: { render: renderDashboard, shell: true },
  jogos: { render: renderMatches, shell: true },
  chaveamento: { render: renderBracket, shell: true },
  ranking: { render: renderLeaderboard, shell: true },
  apostas: { render: renderMyBets, shell: true },
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

function ensureLiveConnection(state) {
  if (state.user && !disconnectLive) {
    disconnectLive = connectLive((version) => {
      const current = store.get();
      if (version !== current.liveVersion) {
        // invalida caches: a view ativa refaz o fetch e re-renderiza
        store.set({
          liveVersion: version,
          matches: null, standings: null, leaderboard: null, bracket: null,
        });
      }
    });
  } else if (!state.user && disconnectLive) {
    disconnectLive();
    disconnectLive = null;
  }
}

async function boot() {
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
}

boot();
