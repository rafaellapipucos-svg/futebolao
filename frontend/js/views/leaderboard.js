// views/leaderboard.js — Aba 4: ranking com parciais ao vivo + "Como Jogar".
import { ensureData } from '../data.js';
import { avatarEl, emptyState, h, icon, modal, skeletonList } from '../ui.js';
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

function howToPlayContent() {
  return h('div', {},
    h('p', {}, 'Você aposta no placar exato de cada jogo. A pontuação base é:'),
    h('ul', { class: 'rules-list' },
      h('li', {}, h('b', {}, '1 ponto'), ' — acertar o resultado (vitória A, vitória B ou empate).'),
      h('li', {}, h('b', {}, '+2 pontos extras'), ' — cravar o placar exato (total de ',
        h('b', {}, '3 pontos'), ' na partida).'),
    ),
    h('p', {}, 'Nas fases eliminatórias os pontos são multiplicados:'),
    h('table', { class: 'rules-table' },
      h('thead', {}, h('tr', {},
        h('th', {}, 'Fase'), h('th', {}, 'Multiplicador'),
        h('th', {}, 'Resultado'), h('th', {}, 'Cravada'))),
      h('tbody', {},
        [['Fase de Grupos', 1], ['16 avos de final', 2], ['Oitavas de final', 3],
          ['Quartas de final', 4], ['Semifinais', 5], ['Disputa de 3º lugar', 5],
          ['Grande Final', 10]].map(([label, mult]) => h('tr', {},
          h('td', {}, label), h('td', { class: 'tnum' }, `×${mult}`),
          h('td', { class: 'tnum' }, String(1 * mult)),
          h('td', { class: 'tnum' }, String(3 * mult)))),
      ),
    ),
    h('ul', { class: 'rules-list', style: 'margin-top:16px' },
      h('li', {}, 'As apostas de cada jogo fecham ', h('b', {}, 'no apito inicial'),
        '. Depois disso, nada muda — nem pra você, nem pra ninguém.'),
      h('li', {}, 'No mata-mata vale o ', h('b', {}, 'placar dos 90 minutos'),
        ' (+acréscimos). Empate é um resultado válido para a aposta; prorrogação e pênaltis só definem quem avança.'),
      h('li', {}, 'Durante os jogos o ranking mostra ', h('b', {}, 'parciais ao vivo'),
        ' — os pontos só ficam definitivos no apito final.'),
      h('li', {}, 'Confrontos do mata-mata só abrem para apostas quando os dois classificados estão definidos.'),
    ),
  );
}

function podium(rows) {
  const [first, second, third] = rows;
  const slot = (entry, cls, medal) => (entry
    ? h('div', { class: `glass podium-slot clickable ${cls}`,
      title: 'Ver perfil', onClick: () => openProfile(entry.user_id) },
      h('span', { class: 'medal' }, medal),
      avatarEl(entry.avatar_url, entry.display_name, cls === 'first' ? 64 : 50),
      h('span', { class: 'podium-name', title: entry.display_name }, entry.display_name),
      h('span', { class: 'podium-pts tnum' },
        h('b', {}, String(entry.total)), h('span', { class: 'unit' }, 'pts')),
    )
    : h('div', { class: 'podium-slot podium-empty', 'aria-hidden': 'true' }));
  return h('div', { class: 'podium' },
    slot(second, 'second', '🥈'), slot(first, 'first', '🥇'), slot(third, 'third', '🥉'));
}

function posCell(r) {
  const m = medalForPosition(r.position);
  return h('td', { class: 'pos' },
    m ? h('span', { class: `pos-medal pos-${m}` }, icon('medal', 16)) : null,
    h('span', { class: 'pos-num tnum' }, String(r.position)));
}

function tableRows(rows) {
  const ties = tiedPositions(rows);
  return rows.map((r) => {
    const tied = ties.has(r.position);
    return h('tr', { class: `${r.is_me ? 'me' : ''}${tied ? ' tied' : ''}`.trim() || null },
      posCell(r),
      h('td', { class: 'player clickable', title: 'Ver perfil',
        onClick: () => openProfile(r.user_id) },
        avatarEl(r.avatar_url, r.display_name, 30),
        h('span', { class: 'nm', title: r.display_name },
          r.display_name, r.is_me ? ' (você)' : ''),
        tied ? h('span', { class: 'tie-tag', title: 'Empate (desempate alfabético)' }, '=') : null),
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
      podium(rows.slice(0, 3)),
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
      h('button', {
        class: 'btn btn-primary',
        'aria-label': 'Como Jogar',
        onClick: () => modal('Como Jogar', howToPlayContent()),
      }, icon('help', 18), 'Como Jogar'),
    ),
    content,
  );
}
