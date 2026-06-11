// views/dashboard.js — Aba 1: tabela de classificação ao vivo dos 12 grupos.
import { ensureData } from '../data.js';
import { teamFlag } from '../format.js';
import { emptyState, h, skeletonList } from '../ui.js';

function clinchBadge(row) {
  if (row.clinched_first) {
    return h('span', { class: 'chip chip-green', title: '1º lugar garantido' }, '1º ✓');
  }
  if (row.clinched_top2) {
    return h('span', { class: 'chip chip-green', title: 'Classificação direta garantida' }, '✓');
  }
  if (row.eliminated_top2) {
    return h('span', { class: 'chip', title: 'Sem chance de terminar no top-2' }, '–');
  }
  return null;
}

function standingRow(row) {
  const tr = h('tr', { class: row.live ? 'row-live' : '' });
  const name = h('td', { class: 'tname' },
    h('span', {
      class: `pos-badge ${row.position <= 2 ? 'q' : row.position === 3 ? 't' : ''}`,
    }, String(row.position)),
    h('span', { class: 'team-flag', style: 'font-size:1.1rem' }, teamFlag(row.team)),
    h('span', { title: row.tie_unresolved ? 'Empate técnico — critérios FIFA esgotados' : '' },
      row.team.name, row.tie_unresolved ? '*' : ''),
    clinchBadge(row),
  );
  tr.append(
    name,
    h('td', {}, String(row.played)),
    h('td', {}, String(row.won)),
    h('td', {}, String(row.drawn)),
    h('td', {}, String(row.lost)),
    h('td', {}, String(row.gf)),
    h('td', {}, String(row.ga)),
    h('td', {}, (row.gd > 0 ? '+' : '') + row.gd),
    h('td', { class: 'pts' }, String(row.points)),
  );
  return tr;
}

function groupCard(group) {
  const isLive = group.rows.some((r) => r.live);
  return h('div', { class: 'glass group-card' },
    h('h3', {},
      h('span', {}, 'Grupo ', h('span', { class: 'group-letter' }, group.group)),
      isLive
        ? h('span', { class: 'chip chip-live' }, h('span', { class: 'dot' }), 'AO VIVO')
        : group.finished ? h('span', { class: 'chip chip-green' }, 'Encerrado') : null,
    ),
    h('table', { class: 'standings-table' },
      h('thead', {}, h('tr', {},
        h('th', { class: 'tname' }, 'Seleção'),
        ...['J', 'V', 'E', 'D', 'GP', 'GC', 'SG', 'Pts'].map((c) => h('th', {}, c)),
      )),
      h('tbody', {}, group.rows.map(standingRow)),
    ),
  );
}

export function renderDashboard(store) {
  const data = ensureData(store, 'standings');
  let content;
  if (data === null) {
    content = skeletonList(6, 220);
  } else if (data.error) {
    content = emptyState('bolt', 'Não consegui carregar a tabela.', data.error);
  } else {
    content = h('div', { class: 'groups-grid' }, data.groups.map(groupCard));
  }
  return h('div', { class: 'page' },
    h('div', { class: 'page-head' },
      h('div', {},
        h('h1', {}, 'Tabela ', h('span', { class: 'grad-text' }, 'ao vivo')),
        h('p', { class: 'sub' }, 'Jogos em andamento já contam pontos e saldo — em tempo real.'),
      ),
    ),
    content,
    h('div', { class: 'legend' },
      h('span', {}, h('span', { class: 'dot', style: 'background:var(--green)' }), '1º–2º: vaga direta'),
      h('span', {}, h('span', { class: 'dot', style: 'background:var(--gold)' }), '3º: concorre entre os 8 melhores'),
      h('span', {}, h('span', { class: 'dot', style: 'background:var(--red)' }), 'linha pulsando: placar parcial'),
      h('span', {}, '✓ vaga garantida · * empate técnico'),
    ),
  );
}
