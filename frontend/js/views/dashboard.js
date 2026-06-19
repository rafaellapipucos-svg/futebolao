// views/dashboard.js — Aba 1: tabela de classificação ao vivo dos 12 grupos.
import { ensureData } from '../data.js';
import { siglaPt } from '../format.js';
import { emptyState, flagContent, h, skeletonList } from '../ui.js';

// Marca discreta de vaga MATEMATICAMENTE garantida (✓ verde, alto contraste).
// Detalhe completo no title; nada de pílula (evita ruído na célula do nome).
function clinchMark(row) {
  if (row.clinched_first) {
    return h('span', { class: 'clinch', title: '1º lugar garantido' }, '✓');
  }
  if (row.clinched_top2) {
    return h('span', { class: 'clinch', title: 'Classificação garantida' }, '✓');
  }
  return null;
}

// Zona de classificação (Rodada 16, feature D): 1º–2º = vaga direta (verde);
// 3º que está entre os 8 melhores 3ºs = repescagem (amarelo/dourado); 3º fora do
// corte + 4º = não se classificaria (vermelho). Pura/testável.
export function zoneFor(row) {
  if (row.position <= 2) return 'row-q';
  if (row.position === 3 && row.third_qualifying) return 'row-t';
  return 'row-out';
}

function standingRow(row) {
  // Zona indicada SÓ pela borda esquerda colorida (sem fundo de linha nem pílula).
  const zone = zoneFor(row);
  const tr = h('tr', { class: `${zone}${row.live ? ' row-live' : ''}`.trim() });
  const name = h('td', { class: 'tname' },
    h('span', { class: 'tname-wrap' },
      h('span', { class: 'pos' }, String(row.position)),
      h('span', { class: 'team-flag flag-sm' }, flagContent(row.team)),
      h('span', {
        class: 'nm',
        title: row.tie_unresolved
          ? `${row.team.name} — empate técnico, critérios FIFA esgotados`
          : row.team.name,
      }, row.team.name, row.tie_unresolved ? '*' : ''),
      // Sigla PT (só aparece quando o card é estreito — via container query no CSS);
      // assim o nome nunca é cortado e não precisa de rolagem horizontal.
      h('span', { class: 'sigla', title: row.team.name },
        siglaPt(row.team), row.tie_unresolved ? '*' : ''),
      clinchMark(row),
    ),
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
        h('p', { class: 'sub' }, 'Tabela atualizada em tempo real com os jogos em andamento.'),
      ),
    ),
    content,
    h('div', { class: 'legend' },
      h('span', {}, h('span', { class: 'bar q' }), '1º–2º: vaga direta'),
      h('span', {}, h('span', { class: 'bar t' }), '3º que passaria (8 melhores)'),
      h('span', {}, h('span', { class: 'bar out' }), 'não se classificaria'),
      h('span', {}, 'Pts pulsando = parcial · ✓ vaga garantida · * empate técnico'),
    ),
  );
}
