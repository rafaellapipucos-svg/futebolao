# TESTPLAN — catálogo de testes do projeto (referência)

> Documento de **referência** do que é testado e como. Não contém instruções para agentes.
> Os testes da rodada atual são definidos em `PLANO_RODADA16.md` (§2, Agente 0) e escritos
> antes da implementação (TDD).

Convenções: testes core = `unittest` puro em `backend/tests/core/` (executam no sandbox,
sem dependências externas). Testes api = `pytest` em `backend/tests/api/` (executam no
build do Docker e localmente). Front = `node:test` em `frontend/tests/` + `node --check`.

## §1 Domínio

**test_scoring.py**
- Cravada em grupo (2x1 vs 2x1) = 3; resultado certo não exato (2x1 vs 3x1) = 1; erro = 0.
- Empate cravado (1x1 vs 1x1) = 3; empate certo não exato (1x1 vs 2x2) = 1.
- Multiplicadores: mesma cravada vale 6 em R32, 9 em R16, 12 em QF, 15 em SF/THIRD, 30 em FINAL.
- Aposta inexistente/jogo sem placar → 0; pontos só com status finished (live = provisório sinalizado).
- **Mata-mata (Rodada 16):** o placar que pontua é o do **fim da prorrogação** (antes dos
  pênaltis); pênaltis são descartados; empate pós-prorrogação usa `winner_team_id`.

**test_standings.py**
- 3 vitórias = 9 pts; ordenação por pts > SG > GP.
- Empate total em pts/SG/GP entre 2 times → h2h decide; h2h também empatado → código (flag tie_unresolved).
- Live: jogo em andamento entra na tabela (1x0 ⇒ +3 provisórios) sem alterar jogos finished.
- Grupo sem jogos: 4 linhas zeradas em ordem alfabética de código.

**test_clinch.py**
- Time com 9 pts após 3 rodadas: 1º garantido (clinched_first).
- Time com 6 pts e adversários com máx 4: top-2 garantido antes da 3ª rodada.
- Time com 4 pts mas 2 rivais podem alcançar 6: NÃO clinched (conservador, só-pontos).
- Time com máx 3 pts e dois rivais já com 4+: eliminado do top-2.
- Grupo encerrado: posições exatas pelo standings (não pelo clinch).

**test_thirds_annexc.py**
- annex_c.txt tem exatamente 495 combos únicos = C(12,8); cada linha: 8 grupos válidos,
  atribuição é permutação dos 8, cada grupo atribuído pertence ao combo, e respeita o pool
  do slot: 1A∈{C,E,F,H,I} 1B∈{E,F,G,I,J} 1D∈{B,E,F,I,J} 1E∈{A,B,C,D,F} 1G∈{A,E,H,I,J}
  1I∈{C,D,F,G,H} 1K∈{D,E,I,J,L} 1L∈{E,H,I,J,K}.
- Lookup: combo "EFGHIJKL" → 1A:3E, 1B:3J, 1D:3I, 1E:3F, 1G:3H, 1I:3G, 1K:3L, 1L:3K (linha 1 oficial).
- Ranking dos 3ºs: pts > SG > GP > código; melhores 8 selecionados.
- **Preditivo (Rodada 16):** `mark_qualifying_thirds` escolhe os 8 melhores 3ºs com standings
  parciais (mid-torneio), expondo `third_qualifying` por linha de 3º colocado.

**test_bracket.py**
- Slots 1A/2B resolvem com grupo encerrado; antes, resolvem se clinch garante posição exata.
- Slot 3:ABCDF só resolve com os 12 grupos encerrados; usa Annex C.
- W73 resolve quando jogo 73 finished (placar fim-da-prorrogação decide; mata-mata empatado:
  vencedor indefinido pelo placar ⇒ exige winner_team_id explícito do admin/provider).
- L101/L102 (3º lugar) resolvem com semis encerradas.
- Cascata preditiva: grupos A..L todos encerrados + jogos 73..88 encerrados ⇒ R16 inteiro
  preenchido; QF/SF/Final permanecem com labels até decidíveis.
- Estrutura: 16+8+4+2+1+1 nós; refs corretas (89=W74×W77 … 104=W101×W102).
- **Preditivo (Rodada 16):** projeção do R32 a partir do ranking atual (`predicted=true`);
  clinched/encerrado vira `predicted=false`; vencedor real propaga ao slot seguinte mesmo com
  adversário TBD.

**test_betlock.py**
- now < kickoff ∧ scheduled ∧ times definidos ⇒ aberto.
- now == kickoff ⇒ fechado. now > kickoff ⇒ fechado. status live/finished ⇒ fechado.
- Times indefinidos (home_team_id NULL) ⇒ fechado mesmo antes do kickoff.

**test_repos_sqlite.py**
- CRUD users/teams/matches/bets em SQLite :memory:; UNIQUE(user_id,match_id) e UNIQUE(email)
  aplicados; FK ON; transação rollback em erro; data_version incrementa.
- Estático: nenhum arquivo de app/ contém f-string/`%`/`+` montando SQL (scan AST/regex).

**test_seed.py**
- Carga completa: 48 times, 12 grupos × 4, 104 jogos (72 GROUP + 16 R32 + 8 R16 + 4 QF + 2 SF + 1 THIRD + 1 FINAL).
- Kickoffs UTC válidos e crescentes por fase; jogo 1 = 2026-06-11 19:00Z MEX×RSA; 104 = final 2026-07-19 19:00Z.
- Sources do R32 conferem com tabela FIFA (73:2A×2B … 88:2D×2G); R16+ refs conferem.
- Reseed é idempotente (não duplica, preserva placares/apostas existentes).

**test_schema_v4_migration.py (Rodada 16)**
- DB v3 “na mão” migra e ganha `period/stoppage/home_pens/away_pens/pens_log`; idempotente;
  `SCHEMA_VERSION==4`.

## §2 Segurança & Auth

**test_passwords.py**: hash≠senha; verify ok/fail; pepper diferente ⇒ fail; política
(≥8 chars, rejeita só-dígitos e top-fracas tipo "12345678"); bytes longos (>72) ok via pré-hash.
**test_jwt.py**: roundtrip claims; exp vencido ⇒ rejeita; typ errado ⇒ rejeita; assinatura
adulterada ⇒ rejeita; header alg≠HS256 ⇒ rejeita; base64url sem padding ok.
**test_tokens.py**: refresh rotaciona (antigo revogado); reuse de jti revogado ⇒ rejeita
(e revoga família); logout revoga; expirado ⇒ rejeita.
**test_csrf_ratelimit.py**: csrf gera 32B url-safe; valida igual; rejeita ausente/diferente
(constant-time). Bucket: estoura no limite, reabastece com o tempo, chaves independentes.
**test_auth_service.py**: register cria user (email normalizado, invite respeitado quando
configurado); login ok/senha errada (mensagem neutra); change_password exige senha atual;
admin via ADMIN_EMAILS.
**test_oauth_google.py** (transporte fake): start gera URL com state/nonce; callback troca
code, valida state, exige email_verified, cria/loga/vincula por google_sub; e-mail já
existente com senha ⇒ vincula sem duplicar.

## §3 Serviços

**test_betting_service.py**: upsert cria e edita antes do kickoff; 0..20 gols; trava: editar
no/apos kickoff ⇒ BetLockedError (mesmo via chamada direta do serviço); aposta em jogo com
time indefinido ⇒ erro; minhas apostas separa futuras/encerradas com pontos.
**test_leaderboard.py**: 3 users, mix de cravadas/resultados/erros em fases distintas ⇒
totais, contadores e ordem exatos; jogo live altera parcial (flag live); cache invalida por
data_version; empate ordena por cravadas > nome.
- **Densa (Rodada 16):** três empatados ⇒ posições `1,1,1,2` (não `1,1,1,4`).
**test_standings_svc.py**: agrega 12 grupos; live=true inclui parciais; flags clinch expostas;
**(Rodada 16)** `third_qualifying` nas linhas de 3º colocado.
**test_results.py**: transições válidas (scheduled→live→finished; reabrir exige force admin);
placar negativo/absurdo rejeitado; finished sem winner em mata-mata empatado ⇒ exige
winner_team_id; bump data_version + publish; **(Rodada 16)** aceita `period/stoppage/
home_pens/away_pens/pens_log`.
**test_bracket_svc.py**: cenário integrado — simula copa inteira por resultados e confere
propagação até a final (matchups determinísticos do cenário); **(Rodada 16)** payload
preditivo com `predicted` por confronto.
**test_avatars.py**: PNG válido ⇒ JPEG 256px sem EXIF; >2MB ⇒ erro; bytes não-imagem ⇒ erro;
SVG/ZIP disfarçado ⇒ erro (Pillow verify).

## §4 Providers & jobs

**test_football_data.py**: parse fixture real-shape (IN_PLAY/PAUSED→live, FINISHED→finished,
TIMED/SCHEDULED→scheduled); aliases ("Korea Republic"→KOR etc.); casa por external_id e,
sem ele, por (kickoff±2h, par de codes); knockout: winner por fullTime+penalties.
- **(Rodada 16):** extrai `period`/`stoppage`/`penalties`; `_score_pair` devolve o placar
  **fim-da-prorrogação** (fullTime) para jogos com prorrogação.
**test_sync.py**: aplica updates; manual_lock ⇒ ignora aquele jogo; nada muda ⇒ data_version
estável (idempotente); mudança ⇒ bump+publish; placar regressivo da API com manual_lock=0 aplica.
- **(Rodada 16):** provider reporta horário diferente (>60s) em jogo scheduled ⇒ kickoff
  atualiza **sem input do admin** e bumpa data_version (SSE).
**test_poller_window.py**: janela ativa se ∃ jogo scheduled/live com kickoff-5min ≤ now ≤ kickoff+3h.

## §5 HTTP/pytest (roda no Docker build/local)

Auth: register/login set-cookies (HttpOnly, SameSite=Lax, Secure se prod), me 401 sem cookie,
refresh rotaciona, logout limpa+revoga, rate limit 429 no 6º login, register sem invite 403
(quando configurado), CSRF ausente ⇒ 403 em POST/PUT.
Bets: PUT antes do kickoff 200; no kickoff 409 (clock congelado via monkeypatch do serviço);
payload inválido 422; sem auth 401.
Admin: não-admin 403; set_score 200 e SSE versão muda; sync sem token 503.
Misc: headers de segurança presentes em todas as respostas; /api/health 200; SPA fallback
serve index.html para rota desconhecida não-/api; avatar multipart 413/415/200; SSE responde
text/event-stream com retry e primeiro evento {v}.

## §6 Frontend

node:test — **points.test.js** espelha §1 scoring (mesmos casos); **format.test.js** datas
UTC→local, agrupar por dia, countdown, **(Rodada 16)** `liveClock` (45+X/90+X/prorrogação/
pênaltis); **router.test.js** parse/navegação/guard; **store.test.js** subscribe/notify/derived.
- **(Rodada 16):** `theme.test.js` (reset + resolveTheme); `leaderboard.test.js` (`podiumSlots`
  com empates); `jogos.test.js` (`closedCardClass`, ordenação, filtro de fase); `dashboard.test.js`
  (`zoneFor`); `live.test.js` (`parsePensLog`, mini-placar); `bracket.test.js` (`predicted`).
Estáticos: `node --check` em todos os .js; grep proibindo `innerHTML=` com variável (permitido
apenas literais estáticos auditados), `eval(`, `document.write`, `dangerouslySetInnerHTML`-like.
Smoke: servir frontend/ + checar 200 e content-type de index.html, css e cada módulo js.

## Mapa exigência → teste
| Exigência | Cobertura |
|---|---|
| Pontuação 1/3 + multiplicadores | §1 scoring, §3 leaderboard, §6 points |
| Mata-mata = fim da prorrogação | §1 scoring, §4 provider, §3 results |
| Trava no apito (sem bypass) | §1 betlock, §3 betting, §5 bets 409 |
| Tabela ao vivo + 3ºs preditivos | §1 standings, §3 standings_svc, §5 SSE |
| Bracket preditivo antecipado | §1 clinch+thirds+bracket, §3 bracket_svc |
| Horário automático | §4 sync (kickoff) |
| Relógio/prorrogação/pênaltis | §4 provider, §6 format/live |
| Ranking denso + pódio com empate | §3 leaderboard, §6 leaderboard |
| Tema escuro padrão + reset | §6 theme |
| Aba Jogos unificada | §6 jogos |
| SQLi/XSS/CSRF/rate/senhas | §1 repos estático, §2 inteiro, §5 headers/429/403, §6 greps |
| OAuth Google + email/senha | §2 auth+oauth, §5 auth |
