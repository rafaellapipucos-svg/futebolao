# Tabolão — Plano da Rodada 11 (organização antes de codar)

> Status: **AGUARDANDO APROVAÇÃO**. Nada de código até o "go".

## 1. Decisão de organização (reestruturei os "agentes")

Os 8 agentes que você descreveu **se cruzam muito** nos mesmos arquivos
(`schema`, `layout`, `tokens.css`, `api.js`, `profile`, endpoints novos). Rodar 8
agentes isolados em paralelo geraria conflito de merge e cada um re-descobriria
o contexto do zero (lento e caro). Então eu, como **um agente só**, vou executar
o trabalho em **fases ordenadas por dependência**: primeiro as *fundações*
compartilhadas, depois as features, depois o redesign, e por fim a crítica.
Isso entrega **exatamente** o que cada um dos seus 8 agentes pediria, sem
retrabalho. O mapeamento agente→fase está na seção 4.

Regras mantidas: arquivos de código ≤300 linhas (modular), SQL parametrizado,
sem fallback silencioso, testes a cada fase, `CONTINUITY.md` atualizado.

## 2. Fundações (FASE 0 — feita primeiro, destrava todo o resto)

**F0.1 — Migração de schema (descrição do usuário).**
- Nova coluna `users.bio TEXT` (descrição/sub-bio). `SCHEMA_VERSION = 3`.
- Migração **idempotente cross-dialeto**: helper que lê colunas existentes
  (`PRAGMA table_info` no SQLite, `information_schema.columns` no Postgres) e faz
  `ALTER TABLE users ADD COLUMN bio TEXT` só se faltar. Roda no `init_db` (que já
  roda a cada boot). Teste: criar DB v2 "na mão", migrar, garantir coluna.

**F0.2 — Perfil público (sem vazar dados privados).**
- `GET /api/users/{id}` → `{ id, display_name, avatar_url, bio, history }` —
  **sem** email e **sem** google_linked. `history` = só apostas **encerradas com
  resultado** (acerto/erro/cravada). `me` continua com email/bio/has_password.
- `bio` editável: `PATCH /api/profile` passa a aceitar `bio` (limite ~280).
- Teste: o payload público **não** contém `email` nem `google_linked`.

**F0.3 — Apostas públicas reveladas no apito.**
- `GET /api/matches/{id}/bets` → lista `{user_id, display_name, avatar_url,
  home_goals, away_goals, points}` **somente** se o jogo já começou
  (`bet_open == false`); antes disso retorna 403/vazio (apostas escondidas).
- `GET /api/live` → jogos com `status == live` + as apostas públicas de cada um.
- Teste: antes do kickoff o endpoint **não** revela apostas; depois, revela.

**F0.4 — Sistema definitivo anti-contraste (some o problema claro/escuro pra sempre).**
- Auditoria: **toda** cor sai de token (varredura por `rgb(`/`#xxx` fora de
  `tokens.css`). Hoje sobram: overlay de modal, glows do `#bg-glow`, etc.
- Novos tokens por tema: `--overlay`, `--modal-bg`, `--field-label`, etc., e
  `.modal`/`.input`/inputs do admin/"Como Jogar" passam a usá-los.
- **Trava no `verify.sh`**: um passo que **falha** se aparecer cor hardcoded fora
  de `tokens.css` (impede regressão de contraste no futuro).

**F0.5 — CSRF à prova de falha (some o "recarregue a página").**
- Causa-raiz: `logout` apaga o cookie `csrf_token` e a tela de login não reemite
  → próximo POST vai sem token. Fix duplo:
  1. Backend: `logout`/`clear_session_cookies` **reemite** um `csrf_token` novo
     (em vez de deletar).
  2. `api.js`: rede de segurança — num `403` de CSRF em request mutante, busca
     `GET /api/meta/config` (reemite o cookie) e **re-tenta 1x** automaticamente
     (igual ao retry de refresh no 401).
- Teste: simulação no node de que um 403-CSRF dispara o re-fetch + retry.

## 3. Estratégia de testes (a cada fase + no fim)

- Backend núcleo: `python run_core_tests.py` (stdlib, roda no sandbox) — novos
  testes de migração, perfil público, reveal de aposta, admin.
- Frontend: `node --test` (lógica pura: flags, format, reveal helper, csrf retry).
- `node --check` em todos os JS, `py_compile` na árvore, limite de 300 linhas.
- `scripts/verify.sh` com **logs em `mktemp -d`** (o `/tmp/*.log` do sandbox é de
  outro dono — bug do ambiente, não do código) + novo passo anti-cor-hardcoded.
- Visual (flags/redesign): screenshot via navegador no site publicado quando der.

## 4. Mapa Agente → Fase (ordem de execução)

| Sua descrição | Fase | Entregáveis principais |
|---|---|---|
| **Agente 1** (flags IN/SC iguais) | A | `.flag-abbr` redimensionada p/ parear com as outras (hoje ficou menor); teste de tamanho |
| **Agente 7** (bugs/contraste) | B | F0.5 (CSRF) + modal **singleton** (não empilha) + F0.4 (contraste definitivo) + caça a +bugs |
| **Agente 3** (perfil) | C | tirar aba "Perfil"; abrir perfil ao clicar na **foto**; botão **sair** = portinha com **círculo vermelho**, maior; caixa de **descrição**; **histórico** colorido (verde=resultado, vermelho=erro, dourado=cravada) |
| **Agente 2** (ao vivo + sub-bio) | D | nova aba **Ao Vivo** (jogos live + foto/nome/aposta pública dos jogadores); subtítulo real no perfil (não o email) |
| **Agente 4** (perfis clicáveis) | E | em todo lugar com avatar/nome → abre **modal de perfil público** (nome, foto, descrição, histórico; sem email/google) |
| **Agente 5** (gerais) | F | trocar **Futebolão→Tabolão** em tudo; opção **Live** na aba Apostas; subtítulos novos das abas |
| **Agente 6** (front-end 2x) | G | redesign quase total de **Ranking** e **Mata-mata**, animações/sombras no site todo (com tokens — sem quebrar contraste) |
| **Agente 8** (crítica) | H | revisão crítica + melhorias backend/UX + verificação final |

Ordem: **0 → A → B → C → D → E → F → G → H**. (Fundações antes; redesign G só
depois das features pra desenhar a estrutura final; H por último.)

## 5. Novos textos (Agente 5)
- Tabela: "Tabela atualizada em tempo real com os jogos em andamento."
- Mata-mata: "Escolha a fase para ver o chaveamento."
- Ranking: "Ranking com placar em tempo real com as parciais."
- Apostas: "Edite as apostas até o apito, confira o resultado das encerradas e
  acompanhe as ao vivo em tempo real."
- Marca "FUTEBOLÃO" → "TABOLÃO" (logo, `<title>`, textos). *Obs.: a pasta/repo/
  projeto GCP continuam `futebolao` — renomear isso quebraria o deploy; troco só
  o que é exibido.*

## 6. Decisões que preciso confirmar com você (seção 7 do chat)
1. Renomear só o **texto exibido** (marca/título) pra "Tabolão", certo? (não o
   repositório/deploy).
2. "Revelar aposta quando o jogo começar" = **no apito (kickoff)**, certo? Quem
   não apostou aparece como "não apostou".
3. Topo dos perfis públicos: mostro **posição no ranking + pontos** junto com
   nome/foto/descrição/histórico? (acho que fica bom).
