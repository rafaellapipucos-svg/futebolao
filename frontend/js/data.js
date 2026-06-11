// data.js — carregamento sob demanda com dedupe de requisições por chave.
import { api } from './api.js';

const ENDPOINTS = {
  standings: '/api/standings',
  matches: '/api/matches',
  leaderboard: '/api/leaderboard',
  bracket: '/api/bracket',
};

const inflight = new Set();

/**
 * Retorna o cache atual da chave; se vazio, dispara o fetch (uma vez) e o
 * store.set posterior re-renderiza a view. Erro vira {error: msg}.
 */
export function ensureData(store, key) {
  const cached = store.get()[key];
  if (cached !== null && cached !== undefined) return cached;
  if (!inflight.has(key)) {
    inflight.add(key);
    api.get(ENDPOINTS[key])
      .then((data) => store.set({ [key]: data }))
      .catch((err) => store.set({ [key]: { error: err.message || 'falha ao carregar' } }))
      .finally(() => inflight.delete(key));
  }
  return null;
}

/** Atualiza uma partida dentro do cache de matches (pós-aposta, sem refetch). */
export function patchMatch(store, matchId, patch) {
  const cache = store.get().matches;
  if (!cache || !cache.matches) return;
  const matches = cache.matches.map(
    (m) => (m.id === matchId ? { ...m, ...patch } : m),
  );
  store.set({ matches: { matches } });
}
