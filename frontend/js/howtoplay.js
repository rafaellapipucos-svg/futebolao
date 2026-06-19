// howtoplay.js — modal "Como Jogar" + botão. Movido do Ranking para a aba Jogos
// (Rodada 16). Regra do mata-mata atualizada: vale o placar do FIM DA PRORROGAÇÃO.
import { h, icon, modal } from './ui.js';

export function howToPlayContent() {
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
      h('li', {}, 'No mata-mata vale o ', h('b', {}, 'placar ao fim da prorrogação'),
        ' (antes dos pênaltis). Empate é um resultado válido para a aposta; os pênaltis só definem quem avança.'),
      h('li', {}, 'Durante os jogos o ranking mostra ', h('b', {}, 'parciais ao vivo'),
        ' — os pontos só ficam definitivos no apito final.'),
      h('li', {}, 'Confrontos do mata-mata só abrem para apostas quando os dois classificados estão definidos.'),
    ),
  );
}

export function howToPlayButton() {
  return h('button', {
    class: 'btn btn-primary',
    type: 'button',
    'aria-label': 'Como Jogar',
    onClick: () => modal('Como Jogar', howToPlayContent()),
  }, icon('help', 18), 'Como Jogar');
}
