// views/jogos.js — Aba unificada "Jogos" (base: antiga Apostas). Funde Jogos +
// Ao Vivo + Apostas em 3 subdivisões: Futuros (filtro por fase + aposta),
// Ao vivo (= aba Ao Vivo: palpites de todos + relógio) e Encerrados (filtro por
// fase + ordenação + fundo por acerto). Rodada 16 (feature I).
import { ensureData } from '../data.js';
import { emptyState, h, icon, skeletonList } from '../ui.js';
import { matchCard } from './matches.js';
import { liveContent } from './live.js';
import { howToPlayButton } from '../howtoplay.js';

const PHASES = [
  ['ALL', 'Todos'], ['GROUP', 'Grupos'], ['R32', '16 avos'], ['R16', 'Oitavas'],
  ['QF', 'Quartas'], ['SF', 'Semis'], ['THIRD', '3º lugar'], ['FINAL', 'Grande Final'],
];

let activeTab = 'future';   // 'future' | 'live' | 'closed'
let futurePhase = 'ALL';
let closedPhase = 'ALL';
let closedSort = 'desc';     // 'desc' = mais recentes primeiro | 'asc' = mais antigos

// Pontos agregados das apostas pontuadas (puro/testável).
export function tallyBets(withBets) {
  let total = 0;
  let exact = 0;
  let results = 0;
  for (const m of withBets) {
    if (m.my_points) {
      total += m.my_points.total;
      if (m.my_points.hit_exact) exact += 1;
      else if (m.my_points.hit_result) results += 1;
    }
  }
  return { total, exact, results };
}

// Classe de fundo do cartão ENCERRADO (puro/testável): cravou=ouro, acertou=verde,
// errou=vermelho, não apostou=neutro.
export function closedCardClass(myPoints, hasBet) {
  if (!hasBet || !myPoints) return 'is-nobet';
  if (myPoints.hit_exact) return 'is-exact';
  if (myPoints.hit_result) return 'is-right';
  return 'is-wrong';
}

function statusBar(withBets) {
  const { total, exact, results } = tallyBets(withBets);
  const stat = (iconName, val, label, cls = '') => h('div', { class: 'status-item' },
    h('span', { class: `status-ico ${cls}` }, icon(iconName, 18)),
    h('div', { class: 'status-text' },
      h('span', { class: 'status-val tnum' }, String(val)),
      h('span', { class: 'status-lbl' }, label)));
  return h('div', { class: 'glass status-bar' },
    stat('trophy', total, 'Pontos', 'is-points'),
    stat('target', exact, 'Cravadas', 'is-exact'),
    stat('check', results, 'Resultados', 'is-result'),
  );
}

function phaseFilter(phase, setPhase, store) {
  return h('div', { class: 'filterbar' },
    PHASES.map(([value, label]) => h('button', {
      class: `chip ${phase === value ? 'active' : ''}`,
      type: 'button',
      onClick: () => { setPhase(value); store.set({}); },
    }, label)),
  );
}

function byPhase(list, phase) {
  return phase === 'ALL' ? list : list.filter((m) => m.stage === phase);
}

function futureView(store, matches) {
  const list = byPhase(matches.filter((m) => m.bet_open), futurePhase);
  return h('div', {},
    phaseFilter(futurePhase, (v) => { futurePhase = v; }, store),
    list.length
      ? h('div', { class: 'mybets-list' }, list.map((m) => matchCard(store, m)))
      : emptyState('ball', 'Nenhum jogo aberto para aposta nesta fase.',
        'Novos confrontos abrem assim que ficarem definidos.'),
  );
}

function sortToggle(store) {
  const opt = (val, label) => h('button', {
    class: `chip ${closedSort === val ? 'active' : ''}`,
    type: 'button',
    onClick: () => { closedSort = val; store.set({}); },
  }, label);
  return h('div', { class: 'closed-sort' },
    h('span', { class: 'closed-sort-lbl' }, 'Ordenar:'),
    opt('desc', 'Mais recentes'), opt('asc', 'Mais antigos'));
}

function closedView(store, matches) {
  const list = byPhase(matches.filter((m) => m.status === 'finished'), closedPhase)
    .slice()
    .sort((a, b) => (closedSort === 'desc'
      ? b.kickoff_utc.localeCompare(a.kickoff_utc)
      : a.kickoff_utc.localeCompare(b.kickoff_utc)));
  return h('div', {},
    phaseFilter(closedPhase, (v) => { closedPhase = v; }, store),
    sortToggle(store),
    list.length
      ? h('div', { class: 'mybets-list jogos-closed' }, list.map((m) =>
        h('div', { class: `closed-card ${closedCardClass(m.my_points, !!m.my_bet)}` },
          matchCard(store, m))))
      : emptyState('list', 'Nenhuma aposta encerrada nesta fase ainda.',
        'Suas apostas passadas e os pontos ganhos aparecem aqui.'),
  );
}

export function renderJogos(store) {
  const data = ensureData(store, 'matches');
  let summaryEl = null;
  let content;
  const counts = { future: 0, live: 0, closed: 0 };
  if (data === null) {
    content = skeletonList(4, 150);
  } else if (data.error) {
    content = emptyState('bolt', 'Não consegui carregar os jogos.', data.error);
  } else {
    const withBets = data.matches.filter((m) => m.my_bet);
    summaryEl = statusBar(withBets);
    counts.future = data.matches.filter((m) => m.bet_open).length;
    counts.live = data.matches.filter((m) => m.status === 'live').length;
    counts.closed = data.matches.filter((m) => m.status === 'finished').length;
    content = activeTab === 'future' ? futureView(store, data.matches)
      : activeTab === 'live' ? liveContent(store)
        : closedView(store, data.matches);
  }
  const tab = (key, label, opts = {}) => {
    const active = activeTab === key;
    const n = counts[key];
    return h('button', {
      class: `chip ${active ? 'active' : ''}`,
      type: 'button',
      'aria-pressed': active ? 'true' : 'false',
      onClick: () => { activeTab = key; store.set({}); },
    },
      opts.live ? h('span', { class: 'dot', 'aria-hidden': 'true' }) : null,
      label,
      n ? h('span', { class: 'count-badge tnum' }, String(n)) : null);
  };
  return h('div', { class: 'page' },
    h('div', { class: 'page-head' },
      h('div', {},
        h('h1', {}, 'Jogos ', h('span', { class: 'grad-text' }, '& apostas')),
        h('p', { class: 'sub' }, 'Aposte, acompanhe ao vivo e revise os resultados.'),
      ),
      howToPlayButton(),
    ),
    summaryEl,
    h('div', { class: 'filterbar', role: 'tablist', 'aria-label': 'Seções de jogos' },
      tab('future', 'Jogos futuros'),
      tab('live', 'Ao vivo', { live: true }),
      tab('closed', 'Encerrados'),
    ),
    content,
  );
}
