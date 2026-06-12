// views/profile.js — conta do usuário: foto, nome, descrição, senha e
// histórico de palpites encerrados (verde=resultado, dourado=cravada, vermelho=erro).
import { ApiError, api } from '../api.js';
import { ensureData } from '../data.js';
import { avatarEl, h, icon, toast } from '../ui.js';

function teamCode(side) {
  return side.team ? side.team.code : (side.label || '?');
}

async function uploadAvatar(store, file) {
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  try {
    const resp = await api.upload('/api/profile/avatar', fd);
    store.set({ user: { ...store.get().user, avatar_url: resp.avatar_url }, leaderboard: null });
    toast('Foto atualizada! 📸');
  } catch (err) {
    toast(err instanceof ApiError ? err.message : 'falha no upload', 'err');
  }
}

function avatarSection(store, user) {
  const fileInput = h('input', {
    type: 'file', accept: 'image/png,image/jpeg,image/webp,image/gif',
    style: 'display:none',
  });
  fileInput.addEventListener('change', () => uploadAvatar(store, fileInput.files[0]));
  const wrap = h('div', {
    class: 'avatar-edit', title: 'Trocar foto de perfil',
    onClick: () => fileInput.click(),
  }, avatarEl(user.avatar_url, user.display_name, 96),
    h('span', { class: 'cam' }, icon('camera', 15)), fileInput);
  return h('div', { class: 'glass profile-card', style: 'justify-items:center' },
    wrap,
    h('p', { class: 'muted small center' }, user.email),
    h('p', { class: 'muted small center' }, 'PNG/JPG até 2MB, recortada em quadrado.'),
  );
}

function nameSection(store, user) {
  const input = h('input', { class: 'input', value: user.display_name, maxlength: '40' });
  const btn = h('button', { class: 'btn btn-primary' }, 'Salvar nome');
  btn.addEventListener('click', async () => {
    btn.disabled = true;
    try {
      const updated = await api.patch('/api/profile', { display_name: input.value });
      store.set({ user: updated, leaderboard: null });
      toast('Nome atualizado!');
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'falha ao salvar', 'err');
    }
    btn.disabled = false;
  });
  return h('div', { class: 'glass profile-card' },
    h('h3', {}, 'Nome de exibição'),
    h('div', { class: 'field' }, h('label', {}, 'Como aparece no ranking'), input),
    btn,
  );
}

function bioSection(store, user) {
  const ta = h('textarea', {
    class: 'input', rows: '3', maxlength: '280',
    placeholder: 'Conte algo sobre você — time do coração, fama de palpiteiro...',
  });
  ta.value = user.bio || '';
  const btn = h('button', { class: 'btn btn-primary' }, 'Salvar descrição');
  btn.addEventListener('click', async () => {
    btn.disabled = true;
    try {
      const updated = await api.patch('/api/profile', { bio: ta.value });
      store.set({ user: updated });
      toast('Descrição salva! ✍️');
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'falha ao salvar', 'err');
    }
    btn.disabled = false;
  });
  return h('div', { class: 'glass profile-card' },
    h('h3', {}, 'Descrição'),
    h('div', { class: 'field' },
      h('label', {}, 'Aparece no seu perfil público'), ta),
    btn,
  );
}

function passwordSection(store, user) {
  const current = h('input', { class: 'input', type: 'password', autocomplete: 'current-password' });
  const next = h('input', { class: 'input', type: 'password', autocomplete: 'new-password' });
  const btn = h('button', { class: 'btn btn-primary' },
    user.has_password ? 'Alterar senha' : 'Definir senha');
  btn.addEventListener('click', async () => {
    btn.disabled = true;
    try {
      await api.post('/api/profile/password', {
        current_password: user.has_password ? current.value : null,
        new_password: next.value,
      });
      current.value = '';
      next.value = '';
      if (!user.has_password) store.set({ user: { ...user, has_password: true } });
      toast('Senha atualizada! 🔒');
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'falha ao alterar senha', 'err');
    }
    btn.disabled = false;
  });
  return h('div', { class: 'glass profile-card' },
    h('h3', {}, 'Senha'),
    user.google_linked
      ? h('p', { class: 'muted small' }, icon('google', 13), ' Conta vinculada ao Google.')
      : null,
    user.has_password
      ? h('div', { class: 'field' }, h('label', {}, 'Senha atual'), current)
      : h('p', { class: 'muted small' }, 'Você entrou pelo Google. Defina uma senha para também entrar por e-mail.'),
    h('div', { class: 'field' }, h('label', {}, 'Nova senha (mín. 8 caracteres)'), next),
    btn,
  );
}

export function outcomeClass(points) {
  if (!points) return '';
  if (points.hit_exact) return 'hist-gold';
  if (points.hit_result) return 'hist-green';
  return 'hist-red';
}

function historyItem(m) {
  const p = m.my_points;
  return h('div', { class: `hist-item ${outcomeClass(p)}` },
    h('div', { class: 'hist-main' },
      h('b', {}, `${teamCode(m.home)} ${m.home_score}×${m.away_score} ${teamCode(m.away)}`),
      h('span', { class: 'muted small' }, ` · palpite ${m.my_bet.home_goals}×${m.my_bet.away_goals}`)),
    h('span', { class: 'hist-pts' }, `${p.total} pt${p.total === 1 ? '' : 's'}`),
  );
}

function historySection(store) {
  const data = ensureData(store, 'matches');
  let body;
  if (data === null || data.error) {
    body = h('p', { class: 'muted small' }, 'Carregando seu histórico…');
  } else {
    const done = data.matches
      .filter((m) => m.status === 'finished' && m.my_bet && m.my_points)
      .sort((a, b) => b.kickoff_utc.localeCompare(a.kickoff_utc));
    body = done.length
      ? h('div', { class: 'hist-list' }, done.map(historyItem))
      : h('p', { class: 'muted small' }, 'Você ainda não tem apostas encerradas.');
  }
  return h('div', { class: 'glass profile-card profile-history' },
    h('h3', {}, 'Histórico de palpites'),
    h('p', { class: 'muted small' },
      h('span', { class: 'dot-gold' }), ' cravada · ',
      h('span', { class: 'dot-green' }), ' resultado · ',
      h('span', { class: 'dot-red' }), ' erro'),
    body,
  );
}

export function renderProfile(store, state) {
  const user = state.user;
  return h('div', { class: 'page' },
    h('div', { class: 'page-head' },
      h('div', {},
        h('h1', {}, 'Meu ', h('span', { class: 'grad-text' }, 'perfil')),
        h('p', { class: 'sub' }, 'Sua conta, descrição e histórico de palpites.'),
      ),
    ),
    h('div', { class: 'profile-grid' },
      avatarSection(store, user),
      nameSection(store, user),
      bioSection(store, user),
      passwordSection(store, user),
    ),
    historySection(store),
  );
}
