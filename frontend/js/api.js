// api.js — fetch wrapper: CSRF automático, refresh-em-401 com retry único.

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export function readCookie(name) {
  const found = document.cookie
    .split('; ')
    .find((row) => row.startsWith(name + '='));
  return found ? decodeURIComponent(found.slice(name.length + 1)) : '';
}

const MUTATING = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

async function rawRequest(path, { method = 'GET', json, formData } = {}) {
  const headers = {};
  let body;
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(json);
  } else if (formData !== undefined) {
    body = formData;
  }
  if (MUTATING.has(method)) {
    headers['X-CSRF-Token'] = readCookie('csrf_token');
  }
  const resp = await fetch(path, {
    method, headers, body, credentials: 'same-origin',
  });
  return resp;
}

let refreshing = null;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Renova INSISTINDO: falha de rede / 429 / 5xx (cold start, oscilacao, WiFi
// compartilhado) sao temporarias -> backoff e tenta de novo. So 401/403 (sessao
// realmente encerrada: logout/troca de senha) faz desistir = re-login de verdade.
async function refreshWithRetry() {
  const backoff = [400, 1200, 3000];
  for (let attempt = 0; ; attempt += 1) {
    let resp;
    try {
      resp = await rawRequest('/api/auth/refresh', { method: 'POST' });
    } catch (err) {
      if (attempt >= backoff.length) return false;
      await sleep(backoff[attempt]);
      continue;
    }
    if (resp.ok) return true;
    if (resp.status === 401 || resp.status === 403) return false;
    if (attempt >= backoff.length) return false;
    await sleep(backoff[attempt]);
  }
}

async function tryRefresh() {
  if (!refreshing) {
    refreshing = refreshWithRetry().finally(() => { refreshing = null; });
  }
  return refreshing;
}

let csrfReissuing = null;

async function reissueCsrf() {
  // (Re)emite o cookie csrf_token buscando o config público.
  if (!csrfReissuing) {
    csrfReissuing = rawRequest('/api/meta/config')
      .then((r) => r.ok)
      .finally(() => { csrfReissuing = null; });
  }
  return csrfReissuing;
}

const NO_REFRESH = new Set([
  '/api/auth/refresh', '/api/auth/login', '/api/auth/register', '/api/auth/logout',
]);

export async function request(path, opts = {}) {
  let resp = await rawRequest(path, opts);
  if (resp.status === 401 && !NO_REFRESH.has(path)) {
    const renewed = await tryRefresh();
    if (renewed) resp = await rawRequest(path, opts);
  }
  // CSRF ausente/expirado (ex.: após logout): reemite o cookie e tenta 1x.
  if (resp.status === 403 && MUTATING.has(opts.method || 'GET')) {
    let isCsrf = false;
    try {
      const data = await resp.clone().json();
      isCsrf = !!(data && typeof data.detail === 'string'
        && data.detail.includes('CSRF'));
    } catch (err) {
      isCsrf = false; // corpo não-JSON: não é o caso de CSRF
    }
    if (isCsrf && await reissueCsrf()) resp = await rawRequest(path, opts);
  }
  if (!resp.ok) {
    let detail = `erro ${resp.status}`;
    try {
      const data = await resp.json();
      if (data && data.detail) detail = String(data.detail);
    } catch { /* corpo não-JSON: mantém mensagem padrão */ }
    throw new ApiError(resp.status, detail);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

export const api = {
  get: (path) => request(path),
  post: (path, json) => request(path, { method: 'POST', json }),
  put: (path, json) => request(path, { method: 'PUT', json }),
  del: (path) => request(path, { method: 'DELETE' }),
  patch: (path, json) => request(path, { method: 'PATCH', json }),
  upload: (path, formData) => request(path, { method: 'POST', formData }),
};
