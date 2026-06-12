// views/live.js — Aba "Ao Vivo": jogos em andamento agora + os palpites
// públicos de todos os jogadores (revelados a partir do apito). Clicar num
// jogador abre o perfil público.
import { ensureData } from '../data.js';
import { avatarEl, emptyState, flagContent, h, skeletonList } from '../ui.js';
import { openProfile } from './profile_modal.js';

function teamSide(side, right = false) {
  return h('div', { class: `live-team${right ? ' right' : ''}` },
    h('span', { class: 'team-flag', style: 'font-size:1.2rem' }, flagContent(side.team)),
    h('span', { class: 'team-name' }, side.team ? side.team.name : side.label),
  );
}

function bettor(b) {
  const p = b.points;
  const cls = p && p.hit_exact ? 'chip chip-gold'
    : p && p.hit_result ? 'chip chip-green' : 'chip';
  return h('button', { class: 'live-bettor', title: 'Ver perfil',
    onClick: () => openProfile(b.user_id) },
    avatarEl(b.avatar_url, b.display_name, 30),
    h('span', { class: 'live-bettor-name' }, b.display_name),
    h('span', { class: cls }, `${b.home_goals}×${b.away_goals}`),
    p ? h('span', { class: 'live-bettor-pts' }, `${p.total} pt${p.total === 1 ? '' : 's'}`) : null,
  );
}

function liveMatch(m) {
  return h('div', { class: 'glass live-card' },
    h('div', { class: 'live-head' },
      teamSide(m.home),
      h('div', { class: 'live-score' },
        h('b', {}, `${m.home_score ?? 0} × ${m.away_score ?? 0}`),
        h('span', { class: 'chip chip-live' }, h('span', { class: 'dot' }),
          m.minute != null ? `${m.minute}'` : 'AO VIVO')),
      teamSide(m.away, true)),
    h('div', { class: 'live-bettors' },
      m.bets.length
        ? m.bets.map(bettor)
        : h('p', { class: 'muted small' }, 'Ninguém apostou neste jogo.')),
  );
}

export function renderLive(store) {
  const data = ensureData(store, 'live');
  let content;
  if (data === null) {
    content = skeletonList(2, 170);
  } else if (data.error) {
    content = emptyState('bolt', 'Não consegui carregar os jogos ao vivo.', data.error);
  } else if (!data.matches.length) {
    content = emptyState('ball', 'Nenhum jogo ao vivo agora.',
      'Volte na hora dos jogos para ver os palpites de todo mundo em tempo real.');
  } else {
    content = h('div', { style: 'display:grid;gap:16px' }, data.matches.map(liveMatch));
  }
  return h('div', { class: 'page' },
    h('div', { class: 'page-head' },
      h('div', {},
        h('h1', {}, 'Jogos ', h('span', { class: 'grad-text' }, 'ao vivo')),
        h('p', { class: 'sub' }, 'Os palpites de todo mundo, revelados a partir do apito.'),
      ),
    ),
    content,
  );
}
