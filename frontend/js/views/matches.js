// views/matches.js — cartão de jogo (matchCard), reutilizado pela aba Jogos.
// O renderMatches antigo (página própria) saiu na Rodada 16 (fundido em Jogos);
// só o cartão permanece. Relógio ao vivo unificado em liveClock (M4).
import { renderBetBox } from '../betbox.js';
import { fmtTime, liveClock } from '../format.js';
import { flagContent, h, icon } from '../ui.js';


function teamSide(side, right = false) {
  if (side.team) {
    return h('div', { class: `team-side${right ? ' right' : ''}` },
      h('span', { class: 'team-flag' }, flagContent(side.team)),
      h('span', { class: 'team-name', title: side.team.name }, side.team.name),
    );
  }
  return h('div', { class: `team-side${right ? ' right' : ''}` },
    h('span', { class: 'flag-placeholder', 'aria-hidden': 'true' }),
    h('span', { class: 'team-tbd' }, side.label));
}

function scoreBox(match) {
  if (match.status === 'scheduled') {
    return h('div', { class: 'score-box' },
      h('span', { class: 'kick-time tnum' }, fmtTime(match.kickoff_utc)),
      h('span', { class: 'muted small' }, 'horário local'),
    );
  }
  return h('div', { class: 'score-box' },
    h('div', { class: 'score-line tnum' },
      h('span', {}, String(match.home_score ?? '–')),
      h('span', { class: 'score-x' }, 'x'),
      h('span', {}, String(match.away_score ?? '–')),
    ),
    match.status === 'live'
      ? h('span', { class: 'chip chip-live' }, h('span', { class: 'dot' }),
        liveClock(match))
      : h('span', { class: 'chip' }, 'Encerrado'),
  );
}

export function matchCard(store, match) {
  // Chip único de contexto: "Fase · Grupo X · J12" (em vez de 3 chips soltos).
  const context = [
    match.stage_label,
    match.group ? `Grupo ${match.group}` : null,
    `J${match.id}`,
  ].filter(Boolean).join(' · ');
  return h('div', { class: 'glass match-card' },
    h('div', { class: 'match-meta' },
      h('span', { class: 'chip chip-cyan' }, context),
      h('span', { class: 'venue', title: match.venue },
        icon('stadium', 12), match.venue),
    ),
    h('div', { class: 'match-grid' },
      teamSide(match.home),
      scoreBox(match),
      teamSide(match.away, true),
    ),
    renderBetBox(store, match),
  );
}
