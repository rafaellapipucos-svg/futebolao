// views/bracket.js — Aba 3: mata-mata, UMA fase por vez (seletor) para não
// poluir a tela. Confrontos aparecem assim que ficam garantidos.
import { ensureData } from '../data.js';
import { fmtTime } from '../format.js';
import { emptyState, flagContent, h, skeletonList } from '../ui.js';

const PHASES = [
  ['R32', '16 avos'], ['R16', 'Oitavas'], ['QF', 'Quartas'],
  ['SF', 'Semifinais'], ['THIRD', '3º lugar'], ['FINAL', 'Grande Final'],
];

let selectedStage = 'R32';

// Pura/testável: rótulo curto "DD/MM HH:MM" para a tag do confronto. fmtTime
// cuida do fuso/formato da hora; aqui só montamos a data.
export function fmtMatchDate(iso) {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return '';
  const dd = String(dt.getDate()).padStart(2, '0');
  const mm = String(dt.getMonth() + 1).padStart(2, '0');
  return `${dd}/${mm} ${fmtTime(iso)}`;
}

// Lado do confronto: bandeira (ou placeholder circular se indefinido) + nome
// truncado com title + placar. Bandeira dimensionada por classe (--flag-sm),
// nunca por font-size inline.
function sideRow(side, score, isWinner, isLoser) {
  const cls = `bracket-team${isWinner ? ' winner' : ''}${isLoser ? ' loser' : ''}`
    + `${side.predicted ? ' predicted' : ''}`;
  if (!side.team) {
    return h('div', { class: cls },
      h('span', { class: 't' },
        h('span', { class: 'flag-placeholder flag-sm', 'aria-hidden': 'true' }),
        h('span', { class: 'nm tbd', title: side.label }, side.label),
      ),
      h('span', { class: 'sc' }, ''),
    );
  }
  // Times de previsão (ainda não garantidos) ganham marca sutil + dica no title.
  const nameTitle = side.predicted
    ? `${side.team.name} — previsão pelo ranking atual`
    : side.team.name;
  return h('div', { class: cls },
    h('span', { class: 't' },
      h('span', { class: 'team-flag flag-sm' }, flagContent(side.team)),
      h('span', { class: 'nm', title: nameTitle }, side.team.name),
      isWinner ? h('span', { class: 'win-check', 'aria-label': 'classificado' }, '✓') : null,
    ),
    h('span', { class: 'sc' }, score == null ? '' : String(score)),
  );
}

function matchBox(m) {
  const winId = m.winner_team_id;
  const homeWin = winId != null && m.home.team && m.home.team.id === winId;
  const awayWin = winId != null && m.away.team && m.away.team.id === winId;
  const extra = m.stage === 'FINAL' ? ' bracket-final'
    : m.stage === 'THIRD' ? ' bracket-third' : '';
  const isLive = m.status === 'live';
  const tag = m.stage === 'FINAL' ? '🏆 Grande Final'
    : m.stage === 'THIRD' ? '🥉 3º lugar' : `J${m.id}`;
  return h('div', { class: `glass bracket-match${extra}` },
    h('div', { class: 'bracket-head' },
      h('span', { class: 'mnum' }, tag),
      h('span', { class: 'mdate tnum' }, fmtMatchDate(m.kickoff_utc)),
      isLive
        ? h('span', { class: 'chip chip-live' }, h('span', { class: 'dot' }), 'AO VIVO')
        : (m.predicted
          ? h('span', { class: 'chip chip-pred', title: 'Confronto previsto pelo ranking atual' }, 'prev.')
          : null),
    ),
    h('div', { class: 'bracket-versus' },
      sideRow(m.home, m.home_score, homeWin, awayWin),
      h('span', { class: 'bracket-vs', 'aria-hidden': 'true' }, '×'),
      sideRow(m.away, m.away_score, awayWin, homeWin),
    ),
  );
}

function phaseBar(store, counts) {
  return h('div', { class: 'filterbar', role: 'tablist', 'aria-label': 'Fase do mata-mata' },
    PHASES.map(([stage, label]) => {
      const active = selectedStage === stage;
      return h('button', {
        class: `chip ${active ? 'active' : ''}`,
        type: 'button',
        role: 'tab',
        'aria-selected': active ? 'true' : 'false',
        onClick: () => { selectedStage = stage; store.set({}); },
      },
        label,
        counts[stage] ? h('span', { class: 'count-badge tnum' }, String(counts[stage])) : null,
      );
    }),
  );
}

export function renderBracket(store) {
  const data = ensureData(store, 'bracket');
  let bar = null;
  let content;
  if (data === null) {
    content = skeletonList(4, 120);
  } else if (data.error) {
    content = emptyState('bolt', 'Não consegui carregar o chaveamento.', data.error);
  } else {
    const byStage = {};
    for (const m of data.matches) {
      (byStage[m.stage] = byStage[m.stage] || []).push(m);
    }
    const counts = {};
    for (const [stage] of PHASES) counts[stage] = (byStage[stage] || []).length;
    bar = phaseBar(store, counts);

    const items = (byStage[selectedStage] || []).slice().sort((a, b) => a.id - b.id);
    const phaseLabel = (PHASES.find(([s]) => s === selectedStage) || ['', ''])[1];
    content = items.length
      ? h('div', { class: 'bracket-list' }, items.map(matchBox))
      : emptyState('bracket', `Ainda não há confrontos em ${phaseLabel}.`,
        'Os jogos surgem assim que ficam matematicamente garantidos.');
  }
  return h('div', { class: 'page' },
    h('div', { class: 'page-head' },
      h('div', {},
        h('h1', {}, 'Chaveamento ', h('span', { class: 'grad-text' }, 'do título')),
        h('p', { class: 'sub' }, 'Previsão com base no ranking atual.'),
      ),
    ),
    h('p', { class: 'bracket-note' },
      'Os times ainda não garantidos são projeção e mudam conforme a tabela; '
      + 'confrontos já decididos aparecem fixos.'),
    bar,
    content,
  );
}
