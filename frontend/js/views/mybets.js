// views/mybets.js — Aba 5: histórico de apostas (futuras editáveis × encerradas).
import { ensureData } from '../data.js';
import { emptyState, h, skeletonList } from '../ui.js';
import { matchCard } from './matches.js';

let activeTab = 'future'; // 'future' | 'closed'

function summary(withBets) {
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
  const card = (val, lbl, cls = '') => h('div', { class: 'glass stat-card' },
    h('span', { class: `val ${cls}` }, String(val)),
    h('span', { class: 'lbl' }, lbl));
  return h('div', { class: 'mybets-summary' },
    card(total, 'Pontos', 'grad-text'),
    card(exact, '🎯 Cravadas'),
    card(results, '✔ Resultados'),
  );
}

export function renderMyBets(store) {
  const data = ensureData(store, 'matches');
  let content;
  let summaryEl = null;
  if (data === null) {
    content = skeletonList(4, 150);
  } else if (data.error) {
    content = emptyState('bolt', 'Não consegui carregar suas apostas.', data.error);
  } else {
    const withBets = data.matches.filter((m) => m.my_bet);
    summaryEl = summary(withBets);
    const future = data.matches.filter((m) => m.bet_open);
    const closed = withBets.filter((m) => !m.bet_open)
      .sort((a, b) => b.kickoff_utc.localeCompare(a.kickoff_utc));
    const list = activeTab === 'future' ? future : closed;
    if (list.length === 0) {
      content = activeTab === 'future'
        ? emptyState('ball', 'Nenhum jogo aberto para aposta agora.',
          'Novos confrontos abrem assim que ficarem definidos.')
        : emptyState('list', 'Nenhuma aposta encerrada ainda.',
          'Suas apostas passadas e os pontos ganhos aparecem aqui.');
    } else {
      content = h('div', { style: 'display:grid;gap:14px' },
        list.map((m) => matchCard(store, m)));
    }
  }
  const tab = (key, label) => h('button', {
    class: `chip ${activeTab === key ? 'active' : ''}`,
    type: 'button',
    onClick: () => { activeTab = key; store.set({}); },
  }, label);
  return h('div', { class: 'page' },
    h('div', { class: 'page-head' },
      h('div', {},
        h('h1', {}, 'Minhas ', h('span', { class: 'grad-text' }, 'apostas')),
        h('p', { class: 'sub' }, 'Edite as futuras até o apito; confira os pontos das encerradas.'),
      ),
    ),
    summaryEl,
    h('div', { class: 'filterbar' },
      tab('future', '🟢 Futuras (editáveis)'),
      tab('closed', '🔒 Encerradas'),
    ),
    content,
  );
}
