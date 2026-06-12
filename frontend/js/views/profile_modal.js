// views/profile_modal.js — modal de PERFIL PÚBLICO de qualquer jogador
// (nome, foto, descrição, posição/pontos, histórico). Sem email/Google.
import { ApiError, api } from '../api.js';
import { avatarEl, h, modal, toast } from '../ui.js';
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

export async function openProfile(userId) {
  let prof;
  try {
    prof = await api.get(`/api/users/${userId}`);
  } catch (err) {
    toast(err instanceof ApiError ? err.message : 'falha ao abrir perfil', 'err');
    return;
  }
  const pos = prof.position ? `#${prof.position} no ranking` : 'sem ranking';
  const head = h('div', { class: 'pubprof-head' },
    avatarEl(prof.avatar_url, prof.display_name, 68),
    h('div', {},
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
  modal(prof.display_name,
    h('div', { style: 'display:grid;gap:16px' },
      head,
      h('div', {},
        h('h3', {}, 'Histórico de palpites'),
        h('p', { class: 'muted small' },
          h('span', { class: 'dot-gold' }), ' cravada · ',
          h('span', { class: 'dot-green' }), ' resultado · ',
          h('span', { class: 'dot-red' }), ' erro'),
        hist),
    ),
  );
}
