// data.js — carregamento sob demanda com dedupe + revalidação SEM "piscar".
import { api } from './api.js';

const ENDPOINTS = {
  standings: '/api/standings',
  matches: '/api/matches',
  leaderboard: '/api/leaderboard',
  bracket: '/api/bracket',
  live: '/api/live/matches',
};

const inflight = new Set();
const stale = new Set(); // chaves já carregadas que precisam revalidar (sem skeleton)

function fetchInto(store, key) {
  if (inflight.has(key)) return;
  inflight.add(key);
  api.get(ENDPOINTS[key])
    .then((data) => store.set({ [key]: data }))
    .catch((err) => {
      // 1ª carga (cache vazio) mostra o erro; numa REVALIDAÇÃO mantém o dado
      // atual na tela (atualização ao vivo não derruba o que já está visível).
      if (store.get()[key] == null) {
        store.set({ [key]: { error: err.message || 'falha ao carregar' } });
      }
    })
    .finally(() => inflight.delete(key));
}

/**
 * Retorna o cache da chave. Vazio → dispara o fetch (1x) e devolve null (a view
 * mostra skeleton até o store.set). Se marcado "stale" (chegou update ao vivo),
 * revalida em 2º plano e DEVOLVE o dado atual — sem piscar para o skeleton.
 */
export function ensureData(store, key) {
  const cached = store.get()[key];
  if (cached !== null && cached !== undefined) {
    if (stale.has(key)) { stale.delete(key); fetchInto(store, key); }
    return cached;
  }
  fetchInto(store, key);
  return null;
}

/** Marca chaves p/ revalidar na próxima leitura (sem piscar). */
export function markStale(keys) {
  for (const key of keys) stale.add(key);
}

/** Revalida já: refaz o fetch e troca o dado quando chegar (sem skeleton). */
export function refreshData(store, key) {
  stale.delete(key);
  fetchInto(store, key);
}

/** Aquece o cache das abas principais em segundo plano (tabs ficam instantâneas). */
export function prefetch(store, keys) {
  for (const key of keys) ensureData(store, key);
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
