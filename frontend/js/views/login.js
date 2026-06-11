// views/login.js — entrar / criar conta (+Google quando configurado).
import { ApiError, api } from '../api.js';
import { navigate } from '../router.js';
import { h, icon, toast } from '../ui.js';

let mode = 'login'; // 'login' | 'register'

function oauthErrorMessage(params) {
  if (params.error === 'oauth_state') return 'Sessão do Google expirou, tente de novo.';
  if (params.error === 'oauth') return 'Não foi possível entrar com o Google.';
  return null;
}

export function renderLogin(store, state) {
  const { config } = state;
  const errorBox = h('div', { class: 'auth-error', style: 'display:none' });
  const oauthMsg = oauthErrorMessage(state.route.params);
  if (oauthMsg) { errorBox.textContent = oauthMsg; errorBox.style.display = ''; }

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.style.display = '';
  }

  const email = h('input', { class: 'input', type: 'email', placeholder: 'voce@email.com', autocomplete: 'email' });
  const password = h('input', { class: 'input', type: 'password', placeholder: '••••••••', autocomplete: mode === 'login' ? 'current-password' : 'new-password' });
  const name = h('input', { class: 'input', type: 'text', placeholder: 'Como te chamam no grupo', maxlength: '40' });
  const invite = h('input', { class: 'input', type: 'text', placeholder: 'Código do bolão' });
  const submitBtn = h('button', { class: 'btn btn-primary btn-block', type: 'submit' },
    mode === 'login' ? 'Entrar' : 'Criar conta');

  async function onSubmit(event) {
    event.preventDefault();
    errorBox.style.display = 'none';
    submitBtn.disabled = true;
    try {
      let user;
      if (mode === 'login') {
        user = await api.post('/api/auth/login', {
          email: email.value, password: password.value,
        });
      } else {
        const payload = {
          email: email.value, password: password.value, display_name: name.value,
        };
        if (config.invite_required) payload.invite_code = invite.value;
        user = await api.post('/api/auth/register', payload);
      }
      store.set({ user });
      toast(`Bem-vindo, ${user.display_name}! ⚽`);
      navigate('dashboard');
    } catch (err) {
      showError(err instanceof ApiError ? err.message : 'Falha de conexão, tente novamente.');
      submitBtn.disabled = false;
    }
  }

  function switchMode(next) {
    mode = next;
    store.set({}); // re-render
  }

  const form = h('form', { class: 'field', style: 'display:grid;gap:14px', onSubmit },
    mode === 'register' ? h('div', { class: 'field' }, h('label', {}, 'Nome de exibição'), name) : null,
    h('div', { class: 'field' }, h('label', {}, 'E-mail'), email),
    h('div', { class: 'field' }, h('label', {}, 'Senha'), password),
    (mode === 'register' && config.invite_required)
      ? h('div', { class: 'field' }, h('label', {}, 'Código de convite'), invite)
      : null,
    submitBtn,
  );

  const googleBtn = config.google_oauth
    ? [
      h('div', { class: 'auth-divider' }, 'ou'),
      h('a', { class: 'btn btn-block', href: '/api/oauth/google/start' },
        icon('google', 18), 'Continuar com Google'),
    ]
    : null;

  const logo = icon('ball', 54);
  logo.style.color = 'var(--green)';

  return h('div', { class: 'auth-wrap' },
    h('div', { class: 'glass auth-card' },
      h('div', { class: 'auth-logo' },
        logo,
        h('h1', { class: 'grad-text' }, 'TABOLÃO 26'),
        h('p', { class: 'muted small' }, 'O bolão da Copa entre amigos'),
      ),
      h('div', { class: 'auth-tabs' },
        h('button', { class: mode === 'login' ? 'active' : '', onClick: () => switchMode('login'), type: 'button' }, 'Entrar'),
        h('button', { class: mode === 'register' ? 'active' : '', onClick: () => switchMode('register'), type: 'button' }, 'Criar conta'),
      ),
      errorBox,
      form,
      googleBtn,
    ),
  );
}
