// views/admin.js — placar manual, lock por jogo, sync da API e usuários.
import { ApiError, api } from '../api.js';
import { ensureData } from '../data.js';
import { fmtTime, fmtDayLong, teamFlag } from '../format.js';
import { emptyState, h, skeletonList, toast } from '../ui.js';
import { usersSection } from './admin_users.js';

async function call(path, json, okMsg, store) {
  try {
    const resp = await api.post(path, json);
    toast(okMsg);
    store.set({ matches: null, standings: null, leaderboard: null, bracket: null });
    return resp;
  } catch (err) {
    toast(err instanceof ApiError ? err.message : 'falha na operação', 'err');
    return null;
  }
}

function sideName(side) {
  if (!side.team) return side.label;
  const f = teamFlag(side.team);
  return f === side.team.code ? side.team.code : `${f} ${side.team.code}`;
}

function scoreControls(store, m) {
  const home = h('input', { class: 'input', type: 'number', min: '0', max: '99',
    value: String(m.home_score ?? 0), 'aria-label': 'gols mandante' });
  const away = h('input', { class: 'input', type: 'number', min: '0', max: '99',
    value: String(m.away_score ?? 0), 'aria-label': 'gols visitante' });
  const minute = h('input', { class: 'input', type: 'number', min: '0', max: '130',
    value: String(m.minute ?? ''), placeholder: "min'" });
  const winner = h('select', { class: 'input', 'aria-label': 'vencedor (se empate no mata-mata)' },
    h('option', { value: '' }, 'pênaltis: vencedor…'),
    m.home.team ? h('option', { value: String(m.home.team.id) }, m.home.team.code) : null,
    m.away.team ? h('option', { value: String(m.away.team.id) }, m.away.team.code) : null,
  );
  // C2: placar da disputa de pênaltis (mata-mata, modo manual) + sequência opcional.
  const hPens = h('input', { class: 'input', type: 'number', min: '0', max: '99',
    value: m.home_pens != null ? String(m.home_pens) : '', placeholder: 'pên M',
    'aria-label': 'pênaltis mandante' });
  const aPens = h('input', { class: 'input', type: 'number', min: '0', max: '99',
    value: m.away_pens != null ? String(m.away_pens) : '', placeholder: 'pên V',
    'aria-label': 'pênaltis visitante' });
  const pensLog = h('input', { class: 'input', type: 'text', value: m.pens_log || '',
    placeholder: 'sequência (opcional): [["home",true],["away",false]]',
    'aria-label': 'sequência de pênaltis (JSON, opcional)' });
  const payload = (status) => {
    const body = {
      home_score: parseInt(home.value, 10) || 0,
      away_score: parseInt(away.value, 10) || 0,
      status,
    };
    const min = parseInt(minute.value, 10);
    if (Number.isInteger(min)) body.minute = min;
    if (winner.value) body.winner_team_id = parseInt(winner.value, 10);
    const hp = parseInt(hPens.value, 10);
    const ap = parseInt(aPens.value, 10);
    if (Number.isInteger(hp) && Number.isInteger(ap)) {
      body.home_pens = hp;
      body.away_pens = ap;
    }
    if (pensLog.value.trim()) body.pens_log = pensLog.value.trim();
    if (m.status === 'finished') body.force = true;
    return body;
  };
  const showWinner = m.stage !== 'GROUP';
  const btn = (label, status, cls = 'btn btn-sm') => h('button', {
    class: cls,
    type: 'button',
    onClick: () => call(`/api/admin/matches/${m.id}/score`, payload(status),
      `J${m.id}: ${label} ✓`, store),
  }, label);
  return h('div', { class: 'admin-controls' },
    home, h('span', { class: 'score-x' }, 'x'), away, minute,
    showWinner ? winner : null,
    showWinner ? hPens : null,
    showWinner ? aPens : null,
    showWinner ? pensLog : null,
    btn('Ao vivo', 'live'),
    btn('Encerrar', 'finished', 'btn btn-sm btn-primary'),
    h('button', {
      class: 'btn btn-sm',
      type: 'button',
      title: m.manual_lock ? 'API liberada para este jogo' : 'Travar contra a API (modo manual)',
      onClick: async () => {
        try {
          await api.post(`/api/admin/matches/${m.id}/lock?lock=${!m.manual_lock}`, {});
          toast(`J${m.id}: lock ${!m.manual_lock ? 'ativado' : 'removido'}`);
          store.set({ matches: null });
        } catch (err) {
          toast(err instanceof ApiError ? err.message : 'falha', 'err');
        }
      },
    }, m.manual_lock ? '🔒 manual' : '🔓 api'),
    h('button', {
      class: 'btn btn-sm btn-danger',
      type: 'button',
      onClick: () => call(`/api/admin/matches/${m.id}/reset`, {},
        `J${m.id} resetado`, store),
    }, 'Reset'),
  );
}

function adminMatchRow(store, m) {
  return h('div', { class: 'glass admin-match' },
    h('div', { class: 'row spread' },
      h('div', { class: 'row', style: 'gap:8px;flex-wrap:wrap' },
        h('span', { class: 'chip chip-cyan' }, `J${m.id}`),
        h('span', { class: 'chip' }, m.stage_label, m.group ? ` · G${m.group}` : ''),
        h('b', {}, `${sideName(m.home)} × ${sideName(m.away)}`),
      ),
      h('span', { class: 'muted small' },
        `${fmtDayLong(m.kickoff_utc)} · ${fmtTime(m.kickoff_utc)}`,
        m.status === 'live' ? ' · 🔴 AO VIVO' : m.status === 'finished' ? ' · encerrado' : ''),
    ),
    scoreControls(store, m),
  );
}

let usersCache = null;

export function renderAdmin(store, state) {
  const data = ensureData(store, 'matches');
  if (usersCache === null) {
    usersCache = { loading: true };
    api.get('/api/admin/users')
      .then((resp) => { usersCache = resp.users; store.set({}); })
      .catch(() => { usersCache = []; store.set({}); });
  }
  let content;
  if (data === null) {
    content = skeletonList(4, 120);
  } else if (data.error) {
    content = emptyState('bolt', 'Falha ao carregar.', data.error);
  } else {
    const now = Date.now();
    const sorted = [...data.matches].sort((a, b) => {
      const rank = (m) => (m.status === 'live' ? 0 : m.status === 'scheduled' ? 1 : 2);
      if (rank(a) !== rank(b)) return rank(a) - rank(b);
      const da = Math.abs(new Date(a.kickoff_utc) - now);
      const db = Math.abs(new Date(b.kickoff_utc) - now);
      return da - db;
    }).slice(0, 14);
    content = h('div', { style: 'display:grid;gap:12px' },
      sorted.map((m) => adminMatchRow(store, m)));
  }
  return h('div', { class: 'page' },
    h('div', { class: 'page-head' },
      h('div', {},
        h('h1', {}, 'Painel ', h('span', { class: 'grad-text' }, 'admin')),
        h('p', { class: 'sub' }, 'Jogos ao vivo e próximos primeiro · placar manual vence a API com 🔒'),
      ),
      h('div', { class: 'row' },
        state.config.live_provider ? h('button', {
          class: 'btn',
          onClick: () => call('/api/admin/sync', {}, 'Sync com football-data feito', store),
        }, '⟳ Sync API') : h('span', { class: 'chip' }, 'modo manual (sem token de API)'),
        h('button', {
          class: 'btn',
          onClick: () => call('/api/admin/recompute', {}, 'Chaveamento recalculado', store),
        }, 'Recalcular chaveamento'),
      ),
    ),
    content,
    Array.isArray(usersCache)
      ? usersSection(store, usersCache, () => { usersCache = null; store.set({}); })
      : null,
  );
}
