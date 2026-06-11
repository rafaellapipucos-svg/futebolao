// router.js — rotas por hash (#/dashboard), com guards de auth/admin.

export const ROUTES = {
  login: { auth: false },
  dashboard: { auth: true },
  jogos: { auth: true },
  chaveamento: { auth: true },
  ranking: { auth: true },
  apostas: { auth: true },
  perfil: { auth: true },
  admin: { auth: true, admin: true },
};

export function parseHash(hash) {
  const raw = (hash || '').replace(/^#\/?/, '');
  const [path, query = ''] = raw.split('?');
  const name = path.split('/')[0] || 'dashboard';
  const params = {};
  for (const pair of query.split('&')) {
    if (!pair) continue;
    const [k, v = ''] = pair.split('=');
    params[decodeURIComponent(k)] = decodeURIComponent(v);
  }
  return { name, params };
}

export function resolveRoute(hash, user) {
  const parsed = parseHash(hash);
  const def = ROUTES[parsed.name];
  if (!def) return { name: user ? 'dashboard' : 'login', params: {} };
  if (def.auth && !user) return { name: 'login', params: { next: parsed.name } };
  if (def.admin && !(user && user.is_admin)) return { name: 'dashboard', params: {} };
  if (parsed.name === 'login' && user) return { name: 'dashboard', params: {} };
  return parsed;
}

export function navigate(name, params = {}) {
  const query = Object.entries(params)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');
  window.location.hash = `#/${name}${query ? '?' + query : ''}`;
}

export function startRouter(onChange) {
  const handler = () => onChange(window.location.hash);
  window.addEventListener('hashchange', handler);
  handler();
  return () => window.removeEventListener('hashchange', handler);
}
