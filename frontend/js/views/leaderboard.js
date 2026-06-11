// views/leaderboard.js — Aba 4: ranking com parciais ao vivo + "Como Jogar".
import { ensureData } from '../data.js';
import { avatarEl, emptyState, h, modal, skeletonList } from '../ui.js';

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
          h('td', {}, label), h('td', {}, `×${mult}`),
          h('td', {}, String(1 * mult)), h('td', {}, String(3 * mult)))),
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
    ? h('div', { class: `glass podium-slot ${cls}` },
      h('span', { class: 'medal' }, medal),
      avatarEl(entry.avatar_url, entry.display_name, cls === 'first' ? 64 : 50),
      h('span', { class: 'podium-name' }, entry.display_name),
      h('span', { class: 'podium-pts grad-text' }, `${entry.total}`),
      h('span', { class: 'muted small' }, 'pts'),
    )
    : h('div', {}));
  return h('div', { class: 'podium' },
    slot(second, 'second', '🥈'), slot(first, 'first', '🥇'), slot(third, 'third', '🥉'));
}

function tableRows(rows) {
  return rows.map((r) => h('tr', { class: r.is_me ? 'me' : '' },
    h('td', {}, String(r.position)),
    h('td', { class: 'player' },
      avatarEl(r.avatar_url, r.display_name, 30),
      h('span', {}, r.display_name, r.is_me ? ' (você)' : '')),
    h('td', { class: 'pts' }, String(r.total),
      r.has_live && r.live_total > 0
        ? h('span', { class: 'live-delta' }, ` +${r.live_total} ao vivo`) : null),
    h('td', {}, String(r.exact_hits)),
    h('td', {}, String(r.result_hits)),
  ));
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
      h('div', { class: 'glass', style: 'padding:8px 16px' },
        h('table', { class: 'lb-table' },
          h('thead', {}, h('tr', {},
            h('th', {}, '#'), h('th', { class: 'player' }, 'Jogador'),
            h('th', {}, 'Pts'), h('th', { title: 'placares exatos' }, '🎯 Cravadas'),
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
        h('p', { class: 'sub' }, 'Flutuando em tempo real com os placares parciais.'),
      ),
      h('button', {
        class: 'btn btn-primary',
        onClick: () => modal('Como Jogar', howToPlayContent()),
      }, '❓ Como Jogar'),
    ),
    content,
  );
}
