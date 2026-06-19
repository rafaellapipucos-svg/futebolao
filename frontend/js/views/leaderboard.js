// views/leaderboard.js — Aba 4: ranking com parciais ao vivo + "Como Jogar".
import { ensureData } from '../data.js';
import { avatarEl, emptyState, h, icon, skeletonList } from '../ui.js';
import { openProfile } from './profile_modal.js';

// --- Helpers puros (testáveis em tests/leaderboard.test.js) ---
// Medalha por POSIÇÃO (não por índice): empates compartilham a mesma posição
// no backend (1,2,2,4…), então quem empata em 2º recebe a mesma medalha — o que
// mantém a conexão pódio↔tabela correta.
export function medalForPosition(position) {
  if (position === 1) return 'gold';
  if (position === 2) return 'silver';
  if (position === 3) return 'bronze';
  return null;
}

// Posições que aparecem em mais de uma linha = empate. Retorna um Set para
// marcar visualmente (sutil) o empate na tabela.
export function tiedPositions(rows) {
  const counts = new Map();
  for (const r of rows) counts.set(r.position, (counts.get(r.position) || 0) + 1);
  const ties = new Set();
  for (const [pos, n] of counts) if (n > 1) ties.add(pos);
  return ties;
}

const MEDAL_EMOJI = { gold: '🥇', silver: '🥈', bronze: '🥉' };

// Slots do pódio guiados por POSIÇÃO (não por índice de coluna): cada posição
// 1/2/3 vira um "tier" com TODOS os empatados nela e a medalha correta da posição.
// Empate em 2º ⇒ os dois recebem PRATA e o slot do 3º fica vazio (NENHUM bronze
// indevido — corrige o bug das imagens). Pura/testável.
export function podiumSlots(rows) {
  const tier = (pos, place) => {
    const entries = rows.filter((r) => r.position === pos);
    return entries.length
      ? { entries, position: pos, place, medal: medalForPosition(pos) }
      : null;
  };
  return { second: tier(2, 'second'), first: tier(1, 'first'), third: tier(3, 'third') };
}

function podium(rows) {
  const slots = podiumSlots(rows);
  const render = (t) => {
    if (!t) return h('div', { class: 'podium-slot podium-empty', 'aria-hidden': 'true' });
    const e = t.entries[0];
    const extra = t.entries.length - 1;  // empatados além do representante
    return h('div', { class: `glass podium-slot clickable ${t.place}`,
      title: 'Ver perfil', onClick: () => openProfile(e.user_id) },
      h('span', { class: 'medal' }, MEDAL_EMOJI[t.medal] || ''),
      avatarEl(e.avatar_url, e.display_name, t.place === 'first' ? 64 : 50),
      h('span', { class: 'podium-name', title: e.display_name }, e.display_name),
      h('span', { class: 'podium-pts tnum' },
        h('b', {}, String(e.total)), h('span', { class: 'unit' }, 'pts')),
      extra > 0
        ? h('span', { class: 'podium-tie', title: 'empate nesta posição' },
          `+${extra} empatado${extra > 1 ? 's' : ''}`)
        : null,
    );
  };
  return h('div', { class: 'podium' },
    render(slots.second), render(slots.first), render(slots.third));
}

function posCell(r) {
  const m = medalForPosition(r.position);
  // Conteúdo num wrapper flex (NÃO no <td>): td com display:flex quebra o
  // layout da linha da tabela. O <td> continua sendo célula de tabela normal.
  return h('td', { class: 'pos' },
    h('span', { class: 'pos-inner' },
      m ? h('span', { class: `pos-medal pos-${m}` }, icon('medal', 16)) : null,
      h('span', { class: 'pos-num tnum' }, String(r.position))));
}

function tableRows(rows) {
  const ties = tiedPositions(rows);
  return rows.map((r) => {
    const tied = ties.has(r.position);
    return h('tr', { class: `${r.is_me ? 'me' : ''}${tied ? ' tied' : ''}`.trim() || null },
      posCell(r),
      h('td', { class: 'player clickable', title: 'Ver perfil',
        onClick: () => openProfile(r.user_id) },
        h('span', { class: 'player-inner' },
          avatarEl(r.avatar_url, r.display_name, 30),
          h('span', { class: 'nm', title: r.display_name },
            r.display_name, r.is_me ? ' (você)' : ''),
          tied ? h('span', { class: 'tie-tag', title: 'Empate (desempate alfabético)' }, '=') : null)),
      h('td', { class: 'pts tnum' }, String(r.total),
        r.has_live && r.live_total > 0
          ? h('span', { class: 'live-delta' }, ` +${r.live_total} ao vivo`) : null),
      h('td', { class: 'tnum' }, String(r.exact_hits)),
      h('td', { class: 'tnum' }, String(r.result_hits)),
    );
  });
}

export function renderLeaderboard(store) {
  const data = ensureData(store, 'leaderboard');
  let content;
  if (data === null) {
    content = skeletonList(5, 64);
  } else if (data.error) {
    content = emptyState('bolt', 'Não consegui carregar o ranking.', data.error);
  } else if (data.leaderboard.length === 0) {
    content = emptyState('trophy', 'Ninguém no ranking ainda.', 'Chame os amigos!');
  } else {
    const rows = data.leaderboard;
    content = h('div', {},
      podium(rows),
      h('div', { class: 'glass lb-card' },
        h('table', { class: 'lb-table' },
          h('thead', {}, h('tr', {},
            h('th', { class: 'pos' }, '#'), h('th', { class: 'player' }, 'Jogador'),
            h('th', {}, 'Pts'),
            h('th', { title: 'placares exatos' }, '🎯 Cravadas'),
            h('th', { title: 'resultados certos (não exatos)' }, '✔ Resultados'))),
          h('tbody', {}, tableRows(rows)),
        ),
      ),
    );
  }
  return h('div', { class: 'page' },
    h('div', { class: 'page-head' },
      h('div', {},
        h('h1', {}, 'Ranking ', h('span', { class: 'grad-text' }, 'da galera')),
        h('p', { class: 'sub' }, 'Placar em tempo real, atualizado a cada lance.'),
      ),
    ),
    content,
  );
}
