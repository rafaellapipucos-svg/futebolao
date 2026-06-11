// views/bracket.js — Aba 3: árvore do mata-mata com preenchimento preditivo.
import { ensureData } from '../data.js';
import { fmtTime, dayKey } from '../format.js';
import { emptyState, h, skeletonList } from '../ui.js';

const COLUMNS = [
  ['R32', '16 avos'], ['R16', 'Oitavas'], ['QF', 'Quartas'],
  ['SF', 'Semifinais'], ['FINAL', 'Decisões'],
];

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
      h('span', { class: 'team-flag', style: 'font-size:1.05rem' }, side.team.flag),
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
  void dayKey;
  return h('div', { class: `glass bracket-match${extra}` },
    h('span', { class: 'mnum' },
      m.stage === 'FINAL' ? '🏆 FINAL' : m.stage === 'THIRD' ? '3º lugar' : `J${m.id}`,
      ' · ', dateLabel,
      m.status === 'live' ? ' · AO VIVO' : ''),
    sideRow(m.home, m.home_score, homeWin, awayWin),
    sideRow(m.away, m.away_score, awayWin, homeWin),
  );
}

export function renderBracket(store) {
  const data = ensureData(store, 'bracket');
  let content;
  if (data === null) {
    content = skeletonList(3, 200);
  } else if (data.error) {
    content = emptyState('bolt', 'Não consegui carregar o chaveamento.', data.error);
  } else {
    const byStage = {};
    for (const m of data.matches) {
      (byStage[m.stage] = byStage[m.stage] || []).push(m);
    }
    const cols = COLUMNS.map(([stage, label]) => {
      const items = stage === 'FINAL'
        ? [...(byStage.FINAL || []), ...(byStage.THIRD || [])]
        : (byStage[stage] || []).sort((a, b) => a.id - b.id);
      return h('div', { class: 'bracket-col' },
        h('h4', {}, label),
        items.map(matchBox),
      );
    });
    content = h('div', { class: 'bracket-scroll' },
      h('div', { class: 'bracket-cols' }, cols));
  }
  return h('div', { class: 'page' },
    h('div', { class: 'page-head' },
      h('div', {},
        h('h1', {}, 'Chaveamento ', h('span', { class: 'grad-text' }, 'do título')),
        h('p', { class: 'sub' },
          'Confrontos aparecem assim que ficam matematicamente garantidos — antes mesmo da fase terminar.'),
      ),
    ),
    content,
  );
}
