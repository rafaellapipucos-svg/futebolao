// betbox.js — editor/visualizador de aposta de um jogo (usado em Jogos e Minhas Apostas).
import { ApiError, api } from './api.js';
import { patchMatch } from './data.js';
import { countdown } from './format.js';
import { h, icon, toast } from './ui.js';

// Rascunhos sobrevivem a re-renders (atualizações ao vivo não apagam digitação).
const drafts = new Map();

// Placar válido: inteiro 0–20 (clamp). Puro/testável — usado pelos campos de
// gol e mantém a mesma regra do backend. Entrada vazia/inválida vira 0.
const MAX_GOALS = 20;
export function clampScore(raw) {
  const n = parseInt(raw, 10);
  if (Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(MAX_GOALS, n));
}

// Fração 0..1 de proximidade do apito dentro de uma janela de urgência (24h por
// padrão): 0 = ainda longe, 1 = no apito. A barra de progresso abaixo do
// countdown cresce conforme o jogo se aproxima. Pura/testável.
const URGENCY_WINDOW_MS = 24 * 60 * 60 * 1000;
export function kickoffProgress(kickoffIso, nowMs = Date.now(), windowMs = URGENCY_WINDOW_MS) {
  const diff = new Date(kickoffIso).getTime() - nowMs;
  if (Number.isNaN(diff)) return 0;
  if (diff <= 0) return 1;
  if (diff >= windowMs) return 0;
  return 1 - diff / windowMs;
}

// Um campo de gol: input numérico limpo (sem setas), acessível via aria-label.
// Atualiza o rascunho e reescreve o valor saneado ao sair do campo (blur).
function goalField(value, ariaLabel, onChange) {
  const input = h('input', {
    class: 'bet-input tnum', type: 'text', inputmode: 'numeric',
    pattern: '[0-9]*', maxlength: '2', autocomplete: 'off',
    'aria-label': ariaLabel, value: String(value),
  });
  input.addEventListener('input', () => {
    input.value = input.value.replace(/[^0-9]/g, '').slice(0, 2);
    onChange(clampScore(input.value));
  });
  input.addEventListener('blur', () => {
    const n = clampScore(input.value);
    input.value = String(n);
    onChange(n);
  });
  return input;
}

function openEditor(store, match) {
  const existing = drafts.get(match.id)
    || (match.my_bet
      ? { h: match.my_bet.home_goals, a: match.my_bet.away_goals }
      : { h: 0, a: 0 });
  drafts.set(match.id, existing);

  const homeName = match.home.team ? match.home.team.name : 'mandante';
  const awayName = match.away.team ? match.away.team.name : 'visitante';

  const saveBtn = h('button', { class: 'btn btn-primary btn-block', type: 'button' },
    icon('check', 16), match.my_bet ? 'Atualizar aposta' : 'Confirmar aposta');

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
  const progress = kickoffProgress(match.kickoff_utc);
  const urgent = progress >= 0.5; // <12h p/ o apito: countdown ganha cor de alerta
  const countdownEl = cd
    ? h('div', { class: `countdown-bar${urgent ? ' is-urgent' : ''}`, title: 'tempo até o apito' },
      h('div', { class: 'countdown-head' },
        icon('clock', 13),
        h('span', { class: 'countdown-label' }, 'Fecha em '),
        h('span', { class: 'countdown-time tnum' }, cd)),
      h('div', { class: 'countdown-track', 'aria-hidden': 'true' },
        h('div', { class: 'countdown-fill', style: `width:${Math.round(progress * 100)}%` })))
    : null;

  return h('div', { class: 'bet-area' },
    h('div', { class: 'bet-inputs' },
      goalField(existing.h, `Gols do ${homeName}`, (n) => { drafts.get(match.id).h = n; }),
      h('span', { class: 'bet-x', 'aria-hidden': 'true' }, '×'),
      goalField(existing.a, `Gols do ${awayName}`, (n) => { drafts.get(match.id).a = n; }),
    ),
    saveBtn,
    countdownEl,
  );
}

// Feedback padronizado do rodapé (DESIGN_SYSTEM §7): cravada = chip dourado
// (--exact) + alvo; resultado = chip verde (--success) + ✓; erro = chip NEUTRO
// + ✕ (nunca vermelho — vermelho é só "ao vivo"); parcial mantém .chip-live.
// Aceita os dois formatos de my_points: snake_case (API) e camelCase (points.js).
function outcomeChip(p) {
  if (!p) return null;
  const live = p.provisional ? ' chip-live' : '';
  const suffix = p.provisional ? ' (parcial)' : '';
  if (p.hit_exact ?? p.hitExact) {
    return h('span', { class: `chip chip-gold points-pill${live}`, title: 'Cravada: placar exato!' },
      icon('target', 12), `+${p.total} pts${suffix}`);
  }
  if (p.hit_result ?? p.hitResult) {
    return h('span', { class: `chip chip-green points-pill${live}`, title: 'Acertou o resultado' },
      icon('check', 12), `+${p.total} pts${suffix}`);
  }
  return h('span', { class: `chip points-pill${live}`, title: 'Não pontuou nesta partida' },
    h('span', { 'aria-hidden': 'true' }, '✕'), `0 pts${suffix}`);
}

function lockedView(match) {
  const parts = [];
  if (match.my_bet) {
    parts.push(h('span', { class: 'chip tnum' },
      `Sua aposta: ${match.my_bet.home_goals} x ${match.my_bet.away_goals}`));
    parts.push(outcomeChip(match.my_points));
  } else {
    parts.push(h('span', { class: 'bet-locked' },
      icon('lock', 14), 'Você não apostou'));
    parts.push(h('span', { class: 'chip points-pill', title: 'Sem aposta nesta partida' },
      h('span', { 'aria-hidden': 'true' }, '✕'), '0 pts'));
  }
  return h('div', { class: 'bet-area bet-result' }, parts);
}

export function renderBetBox(store, match) {
  return match.bet_open ? openEditor(store, match) : lockedView(match);
}
