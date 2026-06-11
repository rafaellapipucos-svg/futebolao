// betbox.js — editor/visualizador de aposta de um jogo (usado em Jogos e Minhas Apostas).
import { ApiError, api } from './api.js';
import { patchMatch } from './data.js';
import { countdown } from './format.js';
import { pointsChipClass, pointsText } from './points.js';
import { h, icon, toast } from './ui.js';

// Rascunhos sobrevivem a re-renders (atualizações ao vivo não apagam digitação).
const drafts = new Map();

function stepper(value, onChange) {
  const input = h('input', {
    class: 'bet-value', type: 'number', min: '0', max: '20',
    inputmode: 'numeric', value: String(value),
  });
  input.addEventListener('input', () => {
    const n = Math.max(0, Math.min(20, parseInt(input.value, 10) || 0));
    onChange(n);
  });
  const dec = h('button', { type: 'button', 'aria-label': 'menos um gol' }, '−');
  const inc = h('button', { type: 'button', 'aria-label': 'mais um gol' }, '+');
  dec.addEventListener('click', () => {
    input.value = String(Math.max(0, (parseInt(input.value, 10) || 0) - 1));
    onChange(parseInt(input.value, 10));
  });
  inc.addEventListener('click', () => {
    input.value = String(Math.min(20, (parseInt(input.value, 10) || 0) + 1));
    onChange(parseInt(input.value, 10));
  });
  return h('div', { class: 'bet-stepper' }, dec, input, inc);
}

function openEditor(store, match) {
  const existing = drafts.get(match.id)
    || (match.my_bet
      ? { h: match.my_bet.home_goals, a: match.my_bet.away_goals }
      : { h: 0, a: 0 });
  drafts.set(match.id, existing);

  const saveBtn = h('button', { class: 'btn btn-primary btn-sm', type: 'button' },
    match.my_bet ? 'Atualizar aposta' : 'Apostar');

  saveBtn.addEventListener('click', async () => {
    saveBtn.disabled = true;
    try {
      const draft = drafts.get(match.id);
      const saved = await api.put(`/api/bets/${match.id}`, {
        home_goals: draft.h, away_goals: draft.a,
      });
      drafts.delete(match.id);
      patchMatch(store, match.id, {
        my_bet: { home_goals: saved.home_goals, away_goals: saved.away_goals },
      });
      toast(`Aposta salva: ${saved.home_goals} x ${saved.away_goals} ⚽`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'falha ao salvar';
      toast(msg, 'err');
      if (err instanceof ApiError && err.status === 409) {
        store.set({ matches: null }); // trava bateu: força estado real
      }
      saveBtn.disabled = false;
    }
  });

  const cd = countdown(match.kickoff_utc);
  return h('div', { class: 'bet-area' },
    stepper(existing.h, (n) => { drafts.get(match.id).h = n; }),
    h('span', { class: 'score-x' }, 'x'),
    stepper(existing.a, (n) => { drafts.get(match.id).a = n; }),
    saveBtn,
    cd ? h('span', { class: 'countdown', title: 'tempo até o apito' },
      icon('clock', 12), ` fecha em ${cd}`) : null,
  );
}

function lockedView(match) {
  const parts = [];
  if (match.my_bet) {
    parts.push(h('span', { class: 'chip' },
      `Sua aposta: ${match.my_bet.home_goals} x ${match.my_bet.away_goals}`));
    if (match.my_points) {
      const cls = pointsChipClass(match.my_points);
      const extra = match.my_points.provisional ? ' chip-live' : '';
      parts.push(h('span', { class: `${cls}${extra} points-pill` },
        pointsText(match.my_points),
        match.my_points.provisional ? ' (parcial)' : ''));
    }
  } else {
    parts.push(h('span', { class: 'bet-locked' },
      icon('lock', 14), match.bet_lock_reason || 'apostas encerradas'));
  }
  return h('div', { class: 'bet-area' }, parts);
}

export function renderBetBox(store, match) {
  return match.bet_open ? openEditor(store, match) : lockedView(match);
}
