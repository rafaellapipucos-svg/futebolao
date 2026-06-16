// countdown_ticker.js — atualiza os countdowns (.countdown-bar) NO LUGAR, a
// cada segundo, SEM re-render do app. Antes isso era feito com setInterval +
// store.set({}) (re-render total → recarregava imagens e reiniciava animações,
// causando "piscadas"). Aqui só mexemos no texto/largura dos próprios nós.
import { countdown } from './format.js';
import { kickoffProgress } from './betbox.js';

let started = false;

function tick() {
  const bars = document.querySelectorAll('.countdown-bar[data-kickoff]');
  for (const bar of bars) {
    const iso = bar.dataset.kickoff;
    const cd = countdown(iso);
    const prog = kickoffProgress(iso);
    const timeEl = bar.querySelector('.countdown-time');
    const fillEl = bar.querySelector('.countdown-fill');
    if (timeEl) timeEl.textContent = cd == null ? 'Fechando…' : cd;
    if (fillEl) fillEl.style.width = `${Math.round(prog * 100)}%`;
    bar.classList.toggle('is-urgent', prog >= 0.5);
  }
}

/** Liga o ticker global de 1s (idempotente). */
export function startCountdownTicker() {
  if (started) return;
  started = true;
  setInterval(tick, 1000);
}
