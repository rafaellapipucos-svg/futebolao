// views/match_bets_modal.js — modal com os palpites de TODOS num jogo (encerrado
// ou ao vivo), coloridos pelo acerto: cravou=ouro, acertou=verde, errou=vermelho
// (a mesma lógica de cores dos cartões). Abre instantâneo (esqueleto) e preenche.
import { ApiError, api } from '../api.js';
import { avatarEl, flagContent, h, modal, skeletonList, toast } from '../ui.js';
import { outcomeClass } from './profile.js';
import { openProfile } from './profile_modal.js';

function side(s) {
  const flag = s.team
    ? h('span', { class: 'team-flag flag-sm' }, flagContent(s.team))
    : h('span', { class: 'flag-placeholder flag-sm', 'aria-hidden': 'true' });
  const name = s.team ? s.team.name : (s.label || '?');
  return h('span', { class: 'mb-team' }, flag,
    h('span', { class: 'mb-nm', title: name }, name));
}

function matchHead(m) {
  const pens = (m.home_pens != null && m.away_pens != null)
    ? h('span', { class: 'muted small' }, ` (pên. ${m.home_pens}×${m.away_pens})`)
    : null;
  return h('div', { class: 'mb-head' },
    side(m.home),
    h('span', { class: 'mb-score tnum' }, `${m.home_score ?? 0} × ${m.away_score ?? 0}`, pens),
    side(m.away));
}

// Uma linha de palpite (reusa .hist-item + outcomeClass p/ a cor; clicável → perfil).
function bettorRow(b) {
  const pts = b.points ? b.points.total : 0;
  return h('button', {
    class: `hist-item betrow ${outcomeClass(b.points)}`, type: 'button',
    title: `Ver perfil de ${b.display_name}`, onClick: () => openProfile(b.user_id),
  },
    h('span', { class: 'betrow-main' },
      avatarEl(b.avatar_url, b.display_name, 28),
      h('span', { class: 'betrow-name', title: b.display_name }, b.display_name),
      h('span', { class: 'betrow-guess tnum' }, `${b.home_goals}×${b.away_goals}`)),
    h('span', { class: 'hist-pts' }, `${pts} pt${pts === 1 ? '' : 's'}`),
  );
}

export async function openMatchBets(match) {
  const body = h('div', {}, skeletonList(4, 46)); // feedback imediato
  modal('Palpites de todos', h('div', { class: 'mb-modal' }, matchHead(match), body));
  try {
    const data = await api.get(`/api/matches/${match.id}/bets`);
    const bets = (data && data.bets) || [];
    body.replaceChildren(
      bets.length
        ? h('div', { class: 'hist-list' }, bets.map(bettorRow))
        : h('p', { class: 'muted small' }, 'Ninguém apostou neste jogo.'),
    );
  } catch (err) {
    body.replaceChildren(h('p', { class: 'muted small' }, 'Não consegui carregar os palpites.'));
    toast(err instanceof ApiError ? err.message : 'falha ao abrir os palpites', 'err');
  }
}
