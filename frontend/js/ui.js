// ui.js — h() para DOM seguro (textContent, nunca innerHTML com dados),
// ícones SVG inline, toast, modal, avatar, skeleton.
import { flagIsAbbr, teamFlag } from './format.js';

export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value == null) continue;
    if (key === 'class') el.className = value;
    else if (key === 'dataset') Object.assign(el.dataset, value);
    else if (key.startsWith('on') && typeof value === 'function') {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === 'value') el.value = value;
    else if (key === 'checked' || key === 'disabled' || key === 'selected') {
      if (value) el.setAttribute(key, '');
      el[key] = Boolean(value);
    } else el.setAttribute(key, String(value));
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    el.appendChild(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

// Ícones — paths estáticos auditados (única fonte de markup não-textual).
const ICON_PATHS = {
  table: 'M3 5h18v4H3zM3 11h8v8H3zM13 11h8v8h-8z',
  ball: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 4 3.5 2.5-1.3 4H9.8L8.5 8.5zM5 9l3 1.5L7 14l-2.8.6A8 8 0 0 1 5 9zm3 9.5 1.6-2.6h4.8l1.6 2.6a8 8 0 0 1-8 0zM19.8 14.6 17 14l-1-3.5L19 9a8 8 0 0 1 .8 5.6z',
  bracket: 'M4 4h6v4H4zM4 16h6v4H4zM14 10h6v4h-6zM10 6h2v3h2v6h-2v3h-2z',
  trophy: 'M7 3h10v2h4v3a5 5 0 0 1-5 5 6 6 0 0 1-3 2.6V18h3v3H8v-3h3v-2.4A6 6 0 0 1 8 13a5 5 0 0 1-5-5V5h4zm12 4h-2v3.9A3 3 0 0 0 19 8zM5 7v1a3 3 0 0 0 2 2.9V7z',
  list: 'M4 5h2v2H4zM8 5h12v2H8zM4 11h2v2H4zM8 11h12v2H8zM4 17h2v2H4zM8 17h12v2H8z',
  user: 'M12 3a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm0 12c4.4 0 8 2.2 8 5v1H4v-1c0-2.8 3.6-5 8-5z',
  shield: 'M12 2l8 3v6c0 5-3.4 9.4-8 11-4.6-1.6-8-6-8-11V5z',
  logout: 'M10 3h6a2 2 0 0 1 2 2v3h-2V5h-6v14h6v-3h2v3a2 2 0 0 1-2 2h-6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zm-3 6 1.4 1.4L6.8 12H16v2H6.8l1.6 1.6L7 17l-4-4z',
  clock: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 5h-2v6l5 3 1-1.7-4-2.3z',
  lock: 'M12 2a5 5 0 0 1 5 5v3h1a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h1V7a5 5 0 0 1 5-5zm3 8V7a3 3 0 0 0-6 0v3z',
  check: 'M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z',
  target: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 4a6 6 0 1 1 0 12 6 6 0 0 1 0-12zm0 4a2 2 0 1 1 0 4 2 2 0 0 1 0-4z',
  camera: 'M9 3h6l1.5 2H20a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h3.5zM12 8a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm0 2.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5z',
  bolt: 'M13 2 4 14h6l-1 8 9-12h-6z',
  google: 'M12 11v3.6h5.1c-.5 2.3-2.4 3.9-5.1 3.9a5.5 5.5 0 1 1 0-11c1.4 0 2.6.5 3.6 1.3l2.6-2.6A9.4 9.4 0 0 0 12 3a9 9 0 1 0 0 18c5.2 0 8.7-3.7 8.7-8.9 0-.7-.1-1.4-.2-2.1z',
  sun: 'M12 17a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm0-15a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1zm0 18a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0v-1a1 1 0 0 1 1-1zm10-9a1 1 0 0 1-1 1h-1a1 1 0 1 1 0-2h1a1 1 0 0 1 1 1zM4 12a1 1 0 0 1-1 1H2a1 1 0 1 1 0-2h1a1 1 0 0 1 1 1zm14.95-6.95a1 1 0 0 1 0 1.41l-.71.71a1 1 0 1 1-1.41-1.41l.7-.71a1 1 0 0 1 1.42 0zM7.17 16.83a1 1 0 0 1 0 1.41l-.71.71a1 1 0 0 1-1.41-1.41l.7-.71a1 1 0 0 1 1.42 0zm11.78 1.41a1 1 0 0 1-1.41 0l-.71-.71a1 1 0 0 1 1.41-1.41l.71.7a1 1 0 0 1 0 1.42zM6.46 6.46a1 1 0 0 1-1.41 0l-.71-.71a1 1 0 0 1 1.41-1.41l.71.7a1 1 0 0 1 0 1.42z',
  moon: 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z',
  live: 'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM6.34 6.34 4.93 4.93a10 10 0 0 0 0 14.14l1.41-1.41a8 8 0 0 1 0-11.32zm11.32 0a8 8 0 0 1 0 11.32l1.41 1.41a10 10 0 0 0 0-14.14z',
};

export function icon(name, size = 20) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('width', size);
  svg.setAttribute('height', size);
  svg.setAttribute('fill', 'currentColor');
  svg.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', ICON_PATHS[name] || ICON_PATHS.ball);
  svg.appendChild(path);
  return svg;
}

// flagContent — emoji (texto) ou sigla pequena (.flag-abbr) p/ ENG/SCO.
export function flagContent(team) {
  return flagIsAbbr(team)
    ? h('span', { class: 'flag-abbr' }, teamFlag(team))
    : teamFlag(team);
}

export function toast(message, type = 'ok', ms = 3200) {
  const box = document.getElementById('toasts');
  const el = h('div', { class: `toast toast-${type}`, role: 'status' },
    icon(type === 'ok' ? 'check' : 'bolt', 16), message);
  box.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; }, ms - 300);
  setTimeout(() => el.remove(), ms);
}

export function modal(title, content) {
  // singleton: nunca empilha — fecha qualquer modal aberto antes de abrir.
  document.querySelectorAll('.modal-backdrop').forEach((el) => el.remove());
  const backdrop = h('div', { class: 'modal-backdrop' });
  const close = () => backdrop.remove();
  const card = h('div', { class: 'glass modal', role: 'dialog', 'aria-label': title },
    h('button', { class: 'btn btn-sm modal-close', onClick: close }, 'Fechar'),
    h('h2', {}, title),
    content,
  );
  backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(); });
  backdrop.appendChild(card);
  document.body.appendChild(backdrop);
  return { close };
}

export function avatarEl(url, name, size = 34) {
  const wrap = h('span', { class: 'avatar', style: `width:${size}px;height:${size}px;font-size:${size * 0.42}px` });
  if (url) {
    const img = h('img', { src: url, alt: name || 'avatar' });
    img.addEventListener('error', () => { img.remove(); wrap.append(initials(name)); });
    wrap.appendChild(img);
  } else {
    wrap.append(initials(name));
  }
  return wrap;
}

function initials(name) {
  const parts = String(name || '?').trim().split(/\s+/);
  return ((parts[0]?.[0] || '?') + (parts[1]?.[0] || '')).toUpperCase();
}

export function skeletonList(count = 4, height = 84) {
  return h('div', { style: 'display:grid;gap:12px' },
    Array.from({ length: count }, () => h('div', { class: 'skeleton', style: `height:${height}px` })));
}

export function emptyState(iconName, text, sub) {
  return h('div', { class: 'glass empty-state' },
    icon(iconName, 52), h('p', { style: 'font-weight:700' }, text),
    sub ? h('p', { class: 'small' }, sub) : null);
}
