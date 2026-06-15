// views/matches.js — Aba 2: jogos por fase/dia/horário com apostas inline.
import { renderBetBox } from '../betbox.js';
import { ensureData } from '../data.js';
import { fmtTime, groupByDay, minuteLabel } from '../format.js';
import { emptyState, flagContent, h, icon, skeletonList } from '../ui.js';

const STAGE_FILTERS = [
  ['ALL', 'Todos'], ['GROUP', 'Grupos'], ['R32', '16 avos'], ['R16', 'Oitavas'],
  ['QF', 'Quartas'], ['SF', 'Semis'], ['THIRD', '3º lugar'], ['FINAL', 'Grande Final'],
];

let activeFilter = 'ALL';
let searchQuery = '';
let ticker = null;

function ensureTicker(store) {
  if (ticker) return;
  ticker = setInterval(() => {
    const route = store.get().route.name;
    if (route === 'jogos' || route === 'apostas') store.set({}); // re-render p/ countdown
  }, 30000);
}

// Busca acento-insensível ("Japao" encontra "Japão"): remove marcas diacríticas.
const norm = (s) => String(s).normalize('NFD').replace(/\p{Mn}/gu, '').toLowerCase();

function matchesQuery(match, q) {
  if (!q) return true;
  return [match.home, match.away].some(
    (side) => side.team && norm(side.team.name).includes(q));
}

function teamSide(side, right = false) {
  if (side.team) {
    return h('div', { class: `team-side${right ? ' right' : ''}` },
      h('span', { class: 'team-flag' }, flagContent(side.team)),
      h('span', { class: 'team-name', title: side.team.name }, side.team.name),
    );
  }
  return h('div', { class: `team-side${right ? ' right' : ''}` },
    h('span', { class: 'flag-placeholder', 'aria-hidden': 'true' }),
    h('span', { class: 'team-tbd' }, side.label));
}

function scoreBox(match) {
  if (match.status === 'scheduled') {
    return h('div', { class: 'score-box' },
      h('span', { class: 'kick-time tnum' }, fmtTime(match.kickoff_utc)),
      h('span', { class: 'muted small' }, 'horário local'),
    );
  }
  return h('div', { class: 'score-box' },
    h('div', { class: 'score-line tnum' },
      h('span', {}, String(match.home_score ?? '–')),
      h('span', { class: 'score-x' }, 'x'),
      h('span', {}, String(match.away_score ?? '–')),
    ),
    match.status === 'live'
      ? h('span', { class: 'chip chip-live' }, h('span', { class: 'dot' }),
        minuteLabel(match.status, match.minute))
      : h('span', { class: 'chip' }, 'Encerrado'),
  );
}

export function matchCard(store, match) {
  // Chip único de contexto: "Fase · Grupo X · J12" (em vez de 3 chips soltos).
  const context = [
    match.stage_label,
    match.group ? `Grupo ${match.group}` : null,
    `J${match.id}`,
  ].filter(Boolean).join(' · ');
  return h('div', { class: 'glass match-card' },
    h('div', { class: 'match-meta' },
      h('span', { class: 'chip chip-cyan' }, context),
      h('span', { class: 'venue', title: match.venue },
        icon('stadium', 12), match.venue),
    ),
    h('div', { class: 'match-grid' },
      teamSide(match.home),
      scoreBox(match),
      teamSide(match.away, true),
    ),
    renderBetBox(store, match),
  );
}

function filterBar(store) {
  return h('div', { class: 'filterbar' },
    STAGE_FILTERS.map(([value, label]) => h('button', {
      class: `chip ${activeFilter === value ? 'active' : ''}`,
      type: 'button',
      onClick: () => { activeFilter = value; store.set({}); },
    }, label)),
  );
}

function searchBox(store) {
  const input = h('input', {
    id: 'match-search', class: 'input', type: 'search', autocomplete: 'off',
    placeholder: 'Buscar time…', value: searchQuery,
    'aria-label': 'Buscar jogos por nome de time',
  });
  input.addEventListener('input', () => {
    const pos = input.selectionStart;
    searchQuery = input.value;
    store.set({}); // re-render troca o input: restaura foco e cursor
    const el = document.getElementById('match-search');
    if (el) {
      el.focus();
      try { el.setSelectionRange(pos, pos); } catch { /* navegador sem suporte */ }
    }
  });
  return h('div', { class: 'match-search' }, icon('search', 16), input);
}

export function renderMatches(store) {
  ensureTicker(store);
  const data = ensureData(store, 'matches');
  const q = norm(searchQuery.trim());
  let content;
  if (data === null) {
    content = skeletonList(5, 170);
  } else if (data.error) {
    content = emptyState('bolt', 'Não consegui carregar os jogos.', data.error);
  } else {
    const filtered = data.matches.filter(
      (m) => (activeFilter === 'ALL' || m.stage === activeFilter) && matchesQuery(m, q),
    );
    if (filtered.length === 0) {
      content = q
        ? emptyState('search', `Nenhum jogo encontrado para “${searchQuery.trim()}”.`,
          'Tente outro nome de time ou limpe a busca.')
        : emptyState('ball', 'Nenhum jogo nesta fase ainda.',
          'Os confrontos aparecem assim que ficarem definidos.');
    } else {
      content = groupByDay(filtered).map((day) => [
        h('div', { class: 'day-sep' }, day.label),
        h('div', { style: 'display:grid;gap:14px' },
          day.items.map((m) => matchCard(store, m))),
      ]);
    }
  }
  return h('div', { class: 'page' },
    h('div', { class: 'page-head' },
      h('div', {},
        h('h1', { class: 'h1-ico' }, icon('ball', 26),
          h('span', {}, 'Jogos & ', h('span', { class: 'grad-text' }, 'Apostas'))),
        h('p', { class: 'sub' }, 'Aposte no placar exato até o apito inicial de cada partida.'),
      ),
      searchBox(store),
    ),
    filterBar(store),
    content,
  );
}
