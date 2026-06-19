// views/live.js — Aba "Ao Vivo": jogos em andamento agora + os palpites
// publicos de todos os jogadores (revelados a partir do apito). Clicar num
// jogador abre o perfil publico.
import { ensureData } from '../data.js';
import { liveClock } from '../format.js';
import { avatarEl, emptyState, flagContent, h, icon, skeletonList } from '../ui.js';
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

// Mini-placar de pênaltis (Rodada 16): pens_log = JSON [["home",true],...].
// Inválido/vazio ⇒ [] (mostra só o tally). Puro/testável.
export function parsePensLog(raw) {
  if (!raw) return [];
  try {
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch (err) {
    console.warn('pens_log inválido', err);
    return [];
  }
}

function sideName(side) {
  if (!side) return '';
  return side.team ? side.team.name : (side.label || '');
}

// Mostrado SÓ quando o jogo foi/está nos pênaltis (tally definido ou period PENS).
function pensBoard(m) {
  if (m.home_pens == null && m.away_pens == null && m.period !== 'PENS') return null;
  const log = parsePensLog(m.pens_log);
  const marks = (team) => {
    const kicks = log.filter((k) => Array.isArray(k) && k[0] === team);
    if (!kicks.length) return null;
    return h('span', { class: 'pens-marks' },
      kicks.map((k) => h('span', {
        class: `pens-kick ${k[1] ? 'scored' : 'missed'}`,
        title: k[1] ? 'converteu' : 'perdeu', 'aria-hidden': 'true',
      }, k[1] ? '✓' : '✗')));
  };
  const row = (side, pens, team) => h('div', { class: 'pens-row' },
    h('span', { class: 'pens-team', title: sideName(side) }, sideName(side)),
    h('b', { class: 'pens-score tnum' }, String(pens ?? 0)),
    marks(team));
  return h('div', { class: 'pens-board' },
    h('div', { class: 'pens-title' }, icon('target', 14), 'Pênaltis'),
    row(m.home, m.home_pens, 'home'),
    row(m.away, m.away_pens, 'away'),
  );
}

function liveMatch(m) {
  return h('div', { class: 'glass live-card' },
    h('div', { class: 'live-head' },
      teamSide(m.home),
      h('div', { class: 'live-score' },
        h('b', { class: 'tnum' }, `${m.home_score ?? 0} × ${m.away_score ?? 0}`),
        h('span', { class: 'chip chip-live' }, h('span', { class: 'dot' }),
          liveClock(m))),
      teamSide(m.away, true)),
    pensBoard(m),
    h('div', { class: 'live-bettors' },
      m.bets.length
        ? sortBettors(m.bets).map(bettor)
        : h('p', { class: 'muted small live-empty-bettors' }, 'Ninguém apostou neste jogo.')),
  );
}

// Conteúdo da seção "ao vivo" (sem o cabeçalho da página) — reusado IGUAL na
// subdivisão "Ao vivo" da aba Jogos (Rodada 16). Garante que fique idêntico.
export function liveContent(store) {
  const data = ensureData(store, 'live');
  if (data === null) return skeletonList(2, 170);
  if (data.error) {
    return emptyState('bolt', 'Não consegui carregar os jogos ao vivo.', data.error);
  }
  if (!data.matches.length) {
    return emptyState('ball', 'Nenhum jogo ao vivo agora.',
      'Volte na hora dos jogos para ver os palpites de todo mundo em tempo real.');
  }
  return h('div', { class: 'live-grid' }, data.matches.map(liveMatch));
}

export function renderLive(store) {
  return h('div', { class: 'page' },
    h('div', { class: 'page-head' },
      h('div', {},
        h('h1', {}, 'Jogos ', h('span', { class: 'grad-text' }, 'ao vivo')),
        h('p', { class: 'sub' }, 'Os palpites de todo mundo, revelados a partir do apito.'),
      ),
    ),
    liveContent(store),
  );
}
