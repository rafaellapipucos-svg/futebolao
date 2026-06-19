// views/jogos.js — Aba unificada "Jogos" (base: antiga Apostas). Funde Jogos +
// Ao Vivo + Apostas em 3 subdivisões: Futuros (apostar), Ao vivo (= aba Ao Vivo:
// palpites de todos + relógio) e Encerrados (filtro de fase + ordenação + fundo
// por acerto). Rodada 16 (feature I).
import { ensureData } from '../data.js';
import { emptyState, h, icon, skeletonList } from '../ui.js';
import { matchCard } from './matches.js';
import { liveContent } from './live.js';
import { howToPlayButton } from '../howtoplay.js';
import { openMatchBets } from './match_bets_modal.js';

const PHASES = [
  ['ALL', 'Todas as fases'], ['GROUP', 'Fase de grupos'], ['R32', '16 avos'],
  ['R16', 'Oitavas'], ['QF', 'Quartas'], ['SF', 'Semifinais'],
  ['THIRD', '3º lugar'], ['FINAL', 'Grande Final'],
];

let activeTab = 'future';   // 'future' | 'live' | 'closed'
let closedPhase = 'ALL';    // filtro de fase — só na subdivisão Encerrados
let closedSort = 'desc';    // 'desc' = mais recentes primeiro | 'asc' = mais antigos

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

function byPhase(list, phase) {
  return phase === 'ALL' ? list : list.filter((m) => m.stage === phase);
}

function futureView(store, matches) {
  const list = matches.filter((m) => m.bet_open);
  return list.length
    ? h('div', { class: 'mybets-list' }, list.map((m) => matchCard(store, m)))
    : emptyState('ball', 'Nenhum jogo aberto para aposta agora.',
      'Novos confrontos abrem assim que ficarem definidos.');
}

// Menu suspenso de fase (só nos Encerrados): 1 controle no lugar de 8 botões.
function phaseSelect(store) {
  const sel = h('select', {
    class: 'fase-select', 'aria-label': 'Filtrar por fase',
    onChange: () => { closedPhase = sel.value; store.set({}); },
  }, PHASES.map(([value, label]) => h('option', { value }, label)));
  sel.value = closedPhase;
  return h('label', { class: 'fase-field' },
    h('span', { class: 'fase-lbl' }, 'Fase'), sel);
}

// Botão ↕ (à direita) que inverte a ordem — padrão de sites, no lugar de 2 botões.
function sortButton(store) {
  const desc = closedSort === 'desc';
  return h('button', {
    class: 'sortbtn', type: 'button',
    title: desc ? 'Mais recentes primeiro (tocar para inverter)'
      : 'Mais antigos primeiro (tocar para inverter)',
    'aria-label': 'Inverter a ordem dos jogos encerrados',
    onClick: () => { closedSort = desc ? 'asc' : 'desc'; store.set({}); },
  }, icon('sort', 18),
    h('span', { class: 'sortbtn-lbl' }, desc ? 'Mais recentes' : 'Mais antigos'));
}

// Cartão encerrado: fundo pela SUA aposta + CLICÁVEL → modal com os palpites de
// todos (mesma lógica de cores). lockedView não tem botões, então clicar o cartão
// inteiro é seguro.
function closedCard(store, m) {
  return h('div', {
    class: `closed-card clickable-card ${closedCardClass(m.my_points, !!m.my_bet)}`,
    role: 'button', tabindex: '0', title: 'Ver os palpites de todos',
    onClick: () => openMatchBets(m),
    onKeydown: (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openMatchBets(m); }
    },
  },
    matchCard(store, m),
    h('span', { class: 'closed-hint' }, 'Toque para ver os palpites de todos →'),
  );
}

function closedView(store, matches) {
  const list = byPhase(matches.filter((m) => m.status === 'finished'), closedPhase)
    .slice()
    .sort((a, b) => (closedSort === 'desc'
      ? b.kickoff_utc.localeCompare(a.kickoff_utc)
      : a.kickoff_utc.localeCompare(b.kickoff_utc)));
  return h('div', {},
    h('div', { class: 'closed-controls' }, phaseSelect(store), sortButton(store)),
    list.length
      ? h('div', { class: 'mybets-list jogos-closed' }, list.map((m) => closedCard(store, m)))
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
