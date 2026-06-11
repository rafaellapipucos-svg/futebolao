// views/profile.js — Aba 6: foto, nome de exibição e senha.
import { ApiError, api } from '../api.js';
import { avatarEl, h, icon, toast } from '../ui.js';

async function uploadAvatar(store, file) {
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  try {
    const resp = await api.upload('/api/profile/avatar', fd);
    const user = { ...store.get().user, avatar_url: resp.avatar_url };
    store.set({ user, leaderboard: null });
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
  const cam = h('span', { class: 'cam' }, icon('camera', 15));
  const wrap = h('div', {
    class: 'avatar-edit', title: 'Trocar foto de perfil',
    onClick: () => fileInput.click(),
  }, avatarEl(user.avatar_url, user.display_name, 96), cam, fileInput);
  return h('div', { class: 'glass profile-card', style: 'justify-items:center' },
    wrap,
    h('p', { class: 'muted small center' },
      'PNG/JPG até 2MB — a imagem é reduzida e recortada em quadrado.'),
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
      if (!user.has_password) {
        store.set({ user: { ...user, has_password: true } });
      }
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
      : h('p', { class: 'muted small' }, 'Você entrou pelo Google e ainda não tem senha. Defina uma para também entrar por e-mail.'),
    h('div', { class: 'field' }, h('label', {}, 'Nova senha (mín. 8 caracteres)'), next),
    btn,
  );
}

export function renderProfile(store, state) {
  const user = state.user;
  return h('div', { class: 'page' },
    h('div', { class: 'page-head' },
      h('div', {},
        h('h1', {}, 'Meu ', h('span', { class: 'grad-text' }, 'perfil')),
        h('p', { class: 'sub' }, user.email),
      ),
    ),
    h('div', { class: 'profile-grid' },
      avatarSection(store, user),
      nameSection(store, user),
      passwordSection(store, user),
    ),
  );
}
