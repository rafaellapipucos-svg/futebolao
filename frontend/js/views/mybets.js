// views/mybets.js — Aba 5: histórico de apostas (futuras editáveis × encerradas).
import { ensureData } from '../data.js';
import { emptyState, h, icon, skeletonList } from '../ui.js';
import { matchCard } from './matches.js';

let activeTab = 'future'; // 'future' | 'live' | 'closed'
let ticker = null;

// Mantém o countdown/barra de progresso vivos mesmo se a aba Jogos nunca foi
// aberta. Só re-renderiza quando esta aba está na tela (evita trabalho à toa).
function ensureTicker(store) {
  if (ticker) return;
  ticker = setInterval(() => {
    if (store.get().route.name === 'apostas') store.set({});
  }, 30000);
}

// Agrega os pontos das apostas já pontuadas (puro/testável): total ganho,
// nº de cravadas (placar exato) e nº de resultados certos não exatos.
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

// Barra de status horizontal única (substitui os 3 cartões soltos): troféu =
// pontos, alvo = cravadas, tique = resultados. Ícones vetoriais (ICON_PATHS).
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

export function renderMyBets(store) {
  ensureTicker(store);
  const data = ensureData(store, 'matches');
  let content;
  let summaryEl = null;
  const counts = { future: 0, live: 0, closed: 0 };
  if (data === null) {
    content = skeletonList(4, 150);
  } else if (data.error) {
    content = emptyState('bolt', 'Não consegui carregar suas apostas.', data.error);
  } else {
    const withBets = data.matches.filter((m) => m.my_bet);
    summaryEl = statusBar(withBets);
    const future = data.matches.filter((m) => m.bet_open);
    const live = data.matches.filter((m) => m.status === 'live');
    // Encerradas = só jogos FINALIZADOS (os ao vivo ficam na aba Ao vivo);
    // inclui quem NÃO apostou (fica registrado como "não apostou").
    const closed = data.matches
      .filter((m) => m.status === 'finished')
      .sort((a, b) => b.kickoff_utc.localeCompare(a.kickoff_utc));
    counts.future = future.length;
    counts.live = live.length;
    counts.closed = closed.length;
    const list = activeTab === 'future' ? future
      : activeTab === 'live' ? live : closed;
    if (list.length === 0) {
      content = activeTab === 'future'
        ? emptyState('ball', 'Nenhum jogo aberto para aposta agora.',
          'Novos confrontos abrem assim que ficarem definidos.')
        : activeTab === 'live'
          ? emptyState('live', 'Nenhum jogo ao vivo agora.',
            'Quando rolar jogo, sua aposta dele aparece aqui em tempo real.')
          : emptyState('list', 'Nenhuma aposta encerrada ainda.',
            'Suas apostas passadas e os pontos ganhos aparecem aqui.');
    } else {
      content = h('div', { class: 'mybets-list' },
        list.map((m) => matchCard(store, m)));
    }
  }
  // Filtros na Filterbar canônica (Ag.5): chip ativo = gradiente brand; "Ao
  // vivo" ganha .dot pulsante; count-badge mostra quantos jogos em cada aba.
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
        h('h1', {}, 'Minhas ', h('span', { class: 'grad-text' }, 'apostas')),
        h('p', { class: 'sub' }, 'Edite até o apito e acompanhe seus pontos.'),
      ),
    ),
    summaryEl,
    h('div', { class: 'filterbar', role: 'tablist', 'aria-label': 'Filtrar apostas' },
      tab('future', 'Ativas'),
      tab('live', 'Ao vivo', { live: true }),
      tab('closed', 'Encerradas'),
    ),
    content,
  );
}
