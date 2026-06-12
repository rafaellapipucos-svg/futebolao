// views/profile_modal.js — modal de PERFIL PÚBLICO de qualquer jogador.
// Abre INSTANTÂNEO (esqueleto) e preenche quando os dados chegam, pra não
// ficar sem feedback entre o clique e a resposta. Sem email/Google.
import { ApiError, api } from '../api.js';
import { avatarEl, h, modal, skeletonList, toast } from '../ui.js';
import { outcomeClass } from './profile.js';

function teamCode(side) {
  return side.team ? side.team.code : (side.label || '?');
}

function histItem(m) {
  const p = m.points;
  return h('div', { class: `hist-item ${outcomeClass(p)}` },
    h('div', { class: 'hist-main' },
      h('b', {}, `${teamCode(m.home)} ${m.home_score}×${m.away_score} ${teamCode(m.away)}`),
      h('span', { class: 'muted small' }, ` · palpite ${m.bet.home_goals}×${m.bet.away_goals}`)),
    h('span', { class: 'hist-pts' }, `${p.total} pt${p.total === 1 ? '' : 's'}`),
  );
}

function profileBody(prof) {
  const pos = prof.position ? `#${prof.position} no ranking` : 'sem ranking';
  const head = h('div', { class: 'pubprof-head' },
    avatarEl(prof.avatar_url, prof.display_name, 68),
    h('div', {},
      h('h2', { class: 'pubprof-name' }, prof.display_name),
      h('p', { class: 'pubprof-bio' }, prof.bio || 'Sem descrição.'),
      h('div', { class: 'row', style: 'gap:8px;margin-top:6px;flex-wrap:wrap' },
        h('span', { class: 'chip chip-gold' }, pos),
        h('span', { class: 'chip' }, `${prof.total_points} pts`)),
    ),
  );
  const hist = prof.history.length
    ? h('div', { class: 'hist-list' },
      prof.history.slice().sort((a, b) => b.match_id - a.match_id).map(histItem))
    : h('p', { class: 'muted small' }, 'Sem apostas encerradas ainda.');
  return h('div', { style: 'display:grid;gap:16px' },
    head,
    h('div', {},
      h('h3', {}, 'Histórico de palpites'),
      h('p', { class: 'muted small' },
        h('span', { class: 'dot-gold' }), ' cravada · ',
        h('span', { class: 'dot-green' }), ' resultado · ',
        h('span', { class: 'dot-red' }), ' erro'),
      hist),
  );
}

export async function openProfile(userId) {
  const body = h('div', {}, skeletonList(3, 56)); // feedback imediato
  modal('Perfil', body);
  try {
    const prof = await api.get(`/api/users/${userId}`);
    body.replaceChildren(profileBody(prof));
  } catch (err) {
    body.replaceChildren(h('p', { class: 'muted' }, 'Não consegui carregar este perfil.'));
    toast(err instanceof ApiError ? err.message : 'falha ao abrir perfil', 'err');
  }
}
