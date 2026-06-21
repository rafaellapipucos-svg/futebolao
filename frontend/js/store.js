// store.js — estado reativo minimalista (pub/sub) com setters parciais.

export function createStore(initial = {}) {
  let state = { ...initial };
  const listeners = new Set();

  return {
    get: () => state,
    set(partial) {
      state = { ...state, ...partial };
      for (const fn of listeners) fn(state);
    },
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}

export const store = createStore({
  booted: false,
  user: null,          // payload de /api/auth/me
  config: { google_oauth: false, invite_required: false, live_provider: false },
  route: { name: 'login', params: {} },
  liveVersion: 0,
  // caches de dados por view (preenchidos sob demanda)
  matches: null,
  standings: null,
  leaderboard: null,
  bracket: null,
  live: null,
  // estado de UI das views (B4): antes eram variáveis de módulo soltas. No store,
  // a troca de aba/filtro vira um delta real (sem a gambiarra store.set({})).
  ui: { jogosTab: 'future', closedPhase: 'ALL', closedSort: 'desc', bracketStage: 'R32' },
});

// Atualiza só o slice de UI e notifica (re-render). Centraliza o merge do `ui`.
export function setUi(partial) {
  store.set({ ui: { ...store.get().ui, ...partial } });
}
