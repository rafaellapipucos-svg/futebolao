// views/matches.js — Aba 2: jogos por fase/dia/horário com apostas inline.
import { renderBetBox } from '../betbox.js';
import { ensureData } from '../data.js';
import { fmtTime, groupByDay, minuteLabel } from '../format.js';
import { emptyState, flagContent, h, skeletonList } from '../ui.js';

const STAGE_FILTERS = [
  ['ALL', 'Todos'], ['GROUP', 'Grupos'], ['R32', '16 avos'], ['R16', 'Oitavas'],
  ['QF', 'Quartas'], ['SF', 'Semis'], ['THIRD', '3º lugar'], ['FINAL', 'Grande Final'],
];

let activeFilter = 'ALL';
let ticker = null;

function ensureTicker(store) {
  if (ticker) return;
  ticker = setInterval(() => {
    const route = store.get().route.name;
    if (route === 'jogos' || route === 'apostas') store.set({}); // re-render p/ countdown
  }, 30000);
}

function teamSide(side, right = false) {
  if (side.team) {
    return h('div', { class: `team-side${right ? ' right' : ''}` },
      h('span', { class: 'team-flag' }, flagContent(side.team)),
      h('span', { class: 'team-name' }, side.team.name),
    );
  }
  return h('div', { class: `team-side${right ? ' right' : ''}` },
    h('span', { class: 'team-tbd' }, side.label));
}

function scoreBox(match) {
  if (match.status === 'scheduled') {
    return h('div', { class: 'score-box' },
      h('span', { class: 'kick-time' }, fmtTime(match.kickoff_utc)),
      h('span', { class: 'muted small' }, 'horário local'),
    );
  }
  return h('div', { class: 'score-box' },
    h('div', { class: 'score-line' },
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
  return h('div', { class: 'glass match-card' },
    h('div', { class: 'match-meta' },
      h('div', { class: 'row', style: 'gap:6px;flex-wrap:wrap' },
        h('span', { class: 'chip chip-cyan' }, match.stage_label),
        match.group ? h('span', { class: 'chip' }, `Grupo ${match.group}`) : null,
        h('span', { class: 'chip' }, `J${match.id}`),
      ),
      h('span', { class: 'venue' }, match.venue),
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

export function renderMatches(store) {
  ensureTicker(store);
  const data = ensureData(store, 'matches');
  let content;
  if (data === null) {
    content = skeletonList(5, 170);
  } else if (data.error) {
    content = emptyState('bolt', 'Não consegui carregar os jogos.', data.error);
  } else {
    const filtered = data.matches.filter(
      (m) => activeFilter === 'ALL' || m.stage === activeFilter,
    );
    if (filtered.length === 0) {
      content = emptyState('ball', 'Nenhum jogo nesta fase ainda.',
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
        h('h1', {}, 'Jogos & ', h('span', { class: 'grad-text' }, 'Apostas')),
        h('p', { class: 'sub' }, 'Aposte no placar exato até o apito inicial de cada partida.'),
      ),
    ),
    filterBar(store),
    content,
  );
}
