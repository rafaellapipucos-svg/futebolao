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

function sideRow(side, score, isWinner, isLoser) {
  const cls = `bracket-team${isWinner ? ' winner' : ''}${isLoser ? ' loser' : ''}`;
  if (!side.team) {
    return h('div', { class: cls },
      h('span', { class: 't' }, h('span', { class: 'lbl' }, side.label)),
      h('span', { class: 'sc' }, ''),
    );
  }
  return h('div', { class: cls },
    h('span', { class: 't' },
      h('span', { class: 'team-flag', style: 'font-size:1.05rem' }, flagContent(side.team)),
      h('span', { class: 'nm' }, side.team.name),
      isWinner ? '✓' : ''),
    h('span', { class: 'sc' }, score == null ? '' : String(score)),
  );
}

function matchBox(m) {
  const winId = m.winner_team_id;
  const homeWin = winId != null && m.home.team && m.home.team.id === winId;
  const awayWin = winId != null && m.away.team && m.away.team.id === winId;
  const extra = m.stage === 'FINAL' ? ' bracket-final'
    : m.stage === 'THIRD' ? ' bracket-third' : '';
  const dt = new Date(m.kickoff_utc);
  const dateLabel = `${String(dt.getDate()).padStart(2, '0')}/${String(dt.getMonth() + 1).padStart(2, '0')} ${fmtTime(m.kickoff_utc)}`;
  return h('div', { class: `glass bracket-match${extra}` },
    h('span', { class: 'mnum' },
      m.stage === 'FINAL' ? '🏆 GRANDE FINAL' : m.stage === 'THIRD' ? '🥉 3º lugar' : `J${m.id}`,
      ' · ', dateLabel,
      m.status === 'live' ? ' · AO VIVO' : ''),
    sideRow(m.home, m.home_score, homeWin, awayWin),
    sideRow(m.away, m.away_score, awayWin, homeWin),
  );
}

function phaseBar(store, counts) {
  return h('div', { class: 'filterbar' },
    PHASES.map(([stage, label]) => h('button', {
      class: `chip ${selectedStage === stage ? 'active' : ''}`,
      type: 'button',
      onClick: () => { selectedStage = stage; store.set({}); },
    },
      label,
      counts[stage] ? h('span', { class: 'count-badge' }, String(counts[stage])) : null,
    )),
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
        h('p', { class: 'sub' }, 'Escolha a fase para ver só aquele chaveamento.'),
      ),
    ),
    bar,
    content,
  );
}
