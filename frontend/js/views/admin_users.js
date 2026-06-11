// views/admin_users.js — gestão de usuários no painel admin:
// redefinir senha, excluir perfil e editar apostas (com recálculo no servidor).
import { ApiError, api } from '../api.js';
import { h, modal, toast } from '../ui.js';

function refreshScores(store) {
  // força recarregar tudo que depende de apostas/usuários.
  store.set({ leaderboard: null, matches: null, standings: null, bracket: null });
}

function teamShort(side) {
  return side.team ? side.team.code : side.label;
}

function resetPwDialog(u) {
  const input = h('input', { class: 'input', type: 'text',
    placeholder: 'nova senha (mín. 8)' });
  const btn = h('button', { class: 'btn btn-primary', type: 'button' }, 'Redefinir');
  const dlg = modal(`Redefinir senha — ${u.display_name}`,
    h('div', { style: 'display:grid;gap:12px' },
      h('p', { class: 'muted small' }, u.email), input, btn));
  btn.addEventListener('click', async () => {
    try {
      await api.post(`/api/admin/users/${u.id}/reset-password`, { new_password: input.value });
      toast('Senha redefinida; sessões do usuário revogadas.');
      dlg.close();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'falha', 'err');
    }
  });
}

function deleteDialog(store, u, reload) {
  const btn = h('button', { class: 'btn btn-danger', type: 'button' },
    'Excluir definitivamente');
  const dlg = modal(`Excluir ${u.display_name}?`,
    h('div', { style: 'display:grid;gap:12px' },
      h('p', { class: 'muted small' },
        `${u.email} — apaga o perfil, as apostas e as sessões. Não dá pra desfazer.`),
      btn));
  btn.addEventListener('click', async () => {
    try {
      await api.del(`/api/admin/users/${u.id}`);
      toast('Perfil excluído.');
      dlg.close();
      refreshScores(store);
      reload();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'falha', 'err');
    }
  });
}

function betEditor(store, u, m) {
  const home = h('input', { class: 'input', type: 'number', min: '0', max: '20',
    value: String(m.my_bet.home_goals), style: 'width:54px' });
  const away = h('input', { class: 'input', type: 'number', min: '0', max: '20',
    value: String(m.my_bet.away_goals), style: 'width:54px' });
  const real = m.home_score != null ? `placar ${m.home_score}×${m.away_score}` : 'sem placar';
  const save = h('button', { class: 'btn btn-sm btn-primary', type: 'button' }, 'Salvar');
  save.addEventListener('click', async () => {
    try {
      await api.put(`/api/admin/users/${u.id}/bets/${m.id}`, {
        home_goals: parseInt(home.value, 10) || 0,
        away_goals: parseInt(away.value, 10) || 0,
      });
      toast(`J${m.id}: aposta atualizada · pontos recalculados`);
      refreshScores(store);
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'falha', 'err');
    }
  });
  return h('div', { class: 'row spread', style: 'gap:8px;border-bottom:1px solid var(--border);padding:8px 0;flex-wrap:wrap' },
    h('div', {}, h('b', {}, `${teamShort(m.home)} × ${teamShort(m.away)}`), ' ',
      h('span', { class: 'muted small' }, `${m.stage_label} · ${real}`)),
    h('div', { class: 'row', style: 'gap:6px' },
      home, h('span', { class: 'score-x' }, 'x'), away, save),
  );
}

async function editBetsDialog(store, u) {
  let resp;
  try {
    resp = await api.get(`/api/admin/users/${u.id}/bets`);
  } catch (err) {
    toast(err instanceof ApiError ? err.message : 'falha', 'err');
    return;
  }
  const rows = resp.bets.length
    ? resp.bets.map((m) => betEditor(store, u, m))
    : [h('p', { class: 'muted' }, 'Este usuário ainda não tem apostas.')];
  modal(`Apostas — ${u.display_name}`,
    h('div', { style: 'display:grid;gap:4px;max-height:60vh;overflow:auto' }, rows));
}

export function usersSection(store, users, reload) {
  return h('div', { class: 'glass', style: 'padding:16px;display:grid;gap:8px' },
    h('h3', {}, `Usuários (${users.length})`),
    users.map((u) => h('div', { class: 'row spread', style: 'border-bottom:1px solid var(--border);padding:6px 0;gap:8px;flex-wrap:wrap' },
      h('span', {}, u.display_name, ' ',
        h('span', { class: 'muted small' }, u.email),
        u.is_admin ? h('span', { class: 'chip chip-gold', style: 'margin-left:6px' }, 'admin') : null),
      h('div', { class: 'row', style: 'gap:6px;flex-wrap:wrap' },
        h('button', { class: 'btn btn-sm', type: 'button',
          onClick: () => editBetsDialog(store, u) }, 'Apostas'),
        h('button', { class: 'btn btn-sm', type: 'button',
          onClick: () => resetPwDialog(u) }, 'Senha'),
        h('button', { class: 'btn btn-sm btn-danger', type: 'button',
          onClick: () => deleteDialog(store, u, reload) }, 'Excluir'),
      ),
    )),
  );
}
