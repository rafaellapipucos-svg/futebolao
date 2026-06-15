// views/live.js — Aba "Ao Vivo": jogos em andamento agora + os palpites
// publicos de todos os jogadores (revelados a partir do apito). Clicar num
// jogador abre o perfil publico.
import { ensureData } from '../data.js';
import { avatarEl, emptyState, flagContent, h, skeletonList } from '../ui.js';
import { openProfile } from './profile_modal.js';

// Acento-insensível para desempate alfabético estável ("Ávila" ~ "Avila").
const norm = (s) => String(s || '').normalize('NFD').replace(/\p{Mn}/gu, '').toLowerCase();

// Pontos do palpite (parcial ao vivo). null = jogo sem placar / sem cálculo.
function bettorPoints(b) {
  return b.points && typeof b.points.total === 'number' ? b.points.total : 0;
}

// Ordenação dinâmica (gamificação): quem está pontuando vai ao topo; empate
// resolvido por mais pontos e depois alfabeticamente. Estável e pura (testável).
export function sortBettors(bets) {
  return [...bets].sort((a, b) => {
    const pa = bettorPoints(a);
    const pb = bettorPoints(b);
    if (pa !== pb) return pb - pa; // mais pontos primeiro
    return norm(a.display_name).localeCompare(norm(b.display_name));
  });
}

// Nome curto: primeiro + último sobrenome (resto vira inicial implícita pelo
// truncamento/title). Pura/testável; o nome completo fica no title do elemento.
export function shortName(full) {
  const parts = String(full || '').trim().split(/\s+/).filter(Boolean);
  if (parts.length <= 2) return parts.join(' ');
  return `${parts[0]} ${parts[parts.length - 1]}`;
}

// Lado do time no bloco de placar (mesmo padrão de matches.js: bandeira via
// flagContent sem font-size inline; nome truncado com title).
function teamSide(side, right = false) {
  const cls = `live-team${right ? ' right' : ''}`;
  if (side.team) {
    return h('div', { class: cls },
      h('span', { class: 'team-flag' }, flagContent(side.team)),
      h('span', { class: 'live-team-name', title: side.team.name }, side.team.name),
    );
  }
  return h('div', { class: cls },
    h('span', { class: 'flag-placeholder', 'aria-hidden': 'true' }),
    h('span', { class: 'live-team-name muted', title: side.label }, side.label),
  );
}

function bettor(b) {
  const pts = bettorPoints(b);
  const scoring = pts > 0;
  const exact = scoring && b.points && b.points.hit_exact;
  // Card de sucesso só para quem está pontuando (borda --success / --exact).
  const cardCls = `live-bettor${scoring ? (exact ? ' is-exact' : ' is-scoring') : ''}`;
  return h('button', { class: cardCls, title: `Ver perfil de ${b.display_name}`,
    onClick: () => openProfile(b.user_id) },
    h('span', { class: 'live-bettor-id' },
      avatarEl(b.avatar_url, b.display_name, 32),
      h('span', { class: 'live-bettor-name', title: b.display_name }, shortName(b.display_name)),
    ),
    h('span', { class: 'live-bettor-meta' },
      // Palpite em pílula NEUTRA — separado da pontuação.
      h('span', { class: 'live-guess tnum', title: 'Palpite' }, `${b.home_goals}×${b.away_goals}`),
      // Pontuação destacada apenas para quem pontua; quem zerou fica discreto.
      h('span', { class: `live-bettor-pts tnum${scoring ? ' scoring' : ''}` },
        `${pts} pt${pts === 1 ? '' : 's'}`),
    ),
  );
}

function liveMatch(m) {
  return h('div', { class: 'glass live-card' },
    h('div', { class: 'live-head' },
      teamSide(m.home),
      h('div', { class: 'live-score' },
        h('b', { class: 'tnum' }, `${m.home_score ?? 0} × ${m.away_score ?? 0}`),
        h('span', { class: 'chip chip-live' }, h('span', { class: 'dot' }),
          m.minute != null ? `${m.minute}'` : 'AO VIVO')),
      teamSide(m.away, true)),
    h('div', { class: 'live-bettors' },
      m.bets.length
        ? sortBettors(m.bets).map(bettor)
        : h('p', { class: 'muted small live-empty-bettors' }, 'Ninguém apostou neste jogo.')),
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
    content = h('div', { class: 'live-grid' }, data.matches.map(liveMatch));
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
