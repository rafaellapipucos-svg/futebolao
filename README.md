# ⚽ Futebolão — Bolão da Copa do Mundo 2026

Site de bolão entre amigos: aposte no placar exato de cada um dos **104 jogos
oficiais** da Copa 2026, acompanhe a **tabela ao vivo**, o **chaveamento com
preenchimento preditivo** e o **ranking flutuando em tempo real**.

Stack: **FastAPI (Python)** + **SPA em JavaScript moderno sem build** +
**PostgreSQL (Supabase) em produção / SQLite em dev** — um único container.

## Funcionalidades

A aba *Tabela* mostra a classificação dos 12 grupos com placares parciais em
tempo real. *Jogos* lista os 104 confrontos por fase/dia com aposta inline —
trancada **no apito inicial**, no servidor. *Mata-mata* desenha a árvore
completa e preenche confrontos assim que ficam matematicamente garantidos
(clinch por pontos + tabela Annex C oficial da FIFA). *Ranking* tem pódio,
cravadas e parciais ao vivo, com o modal "Como Jogar". *Minhas Apostas* separa
futuras de encerradas. *Perfil* tem foto (armazenada no banco), nome e senha.
Admins ganham aba própria: placar manual, lock anti-API, sync e usuários.

**Pontuação**: resultado certo = 1 pt; placar exato = 3 pts. Multiplicadores:
grupos ×1, 16 avos ×2, oitavas ×3, quartas ×4, semis ×5, 3º lugar ×5, final ×10.
Mata-mata vale o placar ao **fim da prorrogação** (antes dos pênaltis); empate é
resultado válido para a aposta e os pênaltis só definem quem avança.

## Banco de dados

`DATABASE_URL` definido → **PostgreSQL** (Supabase, RDS, local…).
`DATABASE_URL` vazio → **SQLite** em `DATA_DIR` (dev/testes).
Drivers: psycopg 3 (binário, instalado via requirements). Avatares ficam em
BYTEA no banco — sobrevivem a discos efêmeros (Render free).

## Deploy: Supabase + Render (recomendado p/ você)

1. **Supabase** — crie um projeto (região sa-east-1). Em
   *Project Settings → Database → Connection string → URI*, copie a string do
   **Session Pooler (porta 5432)** — é IPv4, funciona no Render. A do
   Transaction Pooler (6543) também funciona (o app não usa prepared statements).
   Troque `[YOUR-PASSWORD]` pela senha do banco.
2. **Render** — *New → Web Service*, conecte o repositório (runtime **Docker**,
   detecta o Dockerfile sozinho; ou use o `render.yaml` como Blueprint).
   Em *Environment*, defina:
   - `DATABASE_URL` = a connection string do Supabase
   - `SECRET_KEY` e `PEPPER` = gere com `python3 -c "import secrets;print(secrets.token_urlsafe(48))"`
   - `ADMIN_EMAILS` = seu e-mail
   - `PUBLIC_BASE_URL` = https://SEU-APP.onrender.com
   - `COOKIE_SECURE` = `true`
   - opcionais: `GOOGLE_CLIENT_ID/SECRET`, `FOOTBALL_DATA_TOKEN`, `INVITE_CODE`
3. Deploy. O schema é criado e o seed dos 104 jogos roda **automaticamente no
   boot** (idempotente). Crie sua conta com o e-mail de `ADMIN_EMAILS` e pronto.

**Render free dorme** após ~15min sem tráfego: o poller de placares para junto
e o primeiro acesso demora ~30s. Durante os jogos, deixe alguém com a aba
aberta (o SSE mantém o serviço acordado) ou crie um ping a cada 10min no
[cron-job.org](https://cron-job.org) / UptimeRobot para `/api/health`.
O plano Starter elimina isso.

### Alternativas

**Fly.io**: `fly launch` + `fly secrets set DATABASE_URL=...` (sem volume — o
banco é o Supabase). **Docker local**: `cp .env.example .env` (preencha
segredos; DATABASE_URL vazio = SQLite) e `docker compose up --build`.

## Deploy: Google Cloud Run

O disco do Cloud Run e **efemero** — some a cada deploy e a cada cold start. Logo
o banco **tem que ser externo** (Supabase) e os segredos **fixos** no Secret
Manager; senao cada deploy zera contas, apostas e sessoes (todo mundo reloga). O
boot agora **recusa** subir no Cloud Run sem `DATABASE_URL` (trava em `config.py`;
escape so p/ teste descartavel: `ALLOW_EPHEMERAL_DB=true`).

1. **Supabase** — a mesma connection string do passo do Render (Session Pooler,
   porta 5432).
2. **Segredos fixos** — gere UMA vez e nunca troque (trocar `SECRET_KEY` desloga
   todo mundo; trocar `PEPPER` quebra TODAS as senhas):
   ```bash
   python3 -c "import secrets;print(secrets.token_urlsafe(48))" | tr -d '\n' \
     | gcloud secrets create SECRET_KEY --data-file=-
   python3 -c "import secrets;print(secrets.token_urlsafe(48))" | tr -d '\n' \
     | gcloud secrets create PEPPER --data-file=-
   printf '%s' 'postgresql://...supabase...' \
     | gcloud secrets create DATABASE_URL --data-file=-
   ```
3. **Deploy** referenciando os segredos:
   ```bash
   gcloud run deploy futebolao --source . --region southamerica-east1 \
     --min-instances 1 --max-instances 1 --allow-unauthenticated \
     --set-secrets SECRET_KEY=SECRET_KEY:latest,PEPPER=PEPPER:latest,DATABASE_URL=DATABASE_URL:latest \
     --set-env-vars COOKIE_SECURE=true,PUBLIC_BASE_URL=https://SEU-SERVICO.run.app,ADMIN_EMAILS=seu@email
   ```
   `--max-instances 1` e obrigatorio: SSE, rate-limit e cache do ranking vivem na
   memoria do processo. `--min-instances 1` mantem o poller de placares de pe e
   evita cold start (a **sessao** sobrevive ao cold start de qualquer jeito — ela
   vive no Supabase + cookie; quem nao sobrevive e o poller e os caches em memoria).
4. Nos logs do boot, confira a linha `boot fingerprints: SECRET_KEY=... PEPPER=...`:
   se o fingerprint **mudar** entre dois deploys, a chave nao esta fixa — e essa a
   causa de "caiu todo mundo no deploy".

## Testes

```bash
make test-core   # 145 testes (domínio/segurança/serviços/adapter) — sem deps externas
make test-api    # camada HTTP (FastAPI TestClient, SQLite)
make test-pg     # >>> integração contra POSTGRES REAL (sobe postgres:16 no Docker) <<<
bash scripts/verify.sh   # verificação completa
```

Para rodar a suíte Postgres direto contra um banco Supabase **de teste**
(ela DERRUBA e recria as tabelas!):
`cd backend && TEST_DATABASE_URL=postgresql://... python3 -m pytest tests/pg -q`

O `docker build` roda as suítes core+HTTP como **gate**: imagem só nasce verde.

## Integrações opcionais

**Placares automáticos** — token gratuito em
[football-data.org](https://www.football-data.org/client/register) →
`FOOTBALL_DATA_TOKEN`. Poller a cada 60s durante jogos; SSE empurra para os
navegadores. Sem token: modo manual pela aba Admin (lock 🔒 por jogo faz o
manual vencer a API).

**Login com Google** — Google Cloud Console → *Credentials → OAuth Client ID*
(tipo Web), redirect `https://SEU-DOMINIO/api/oauth/google/callback` →
`GOOGLE_CLIENT_ID/SECRET`. O botão aparece sozinho.

## Operação

Backup: Supabase faz backup diário (plano free: 7 dias) — ou
`pg_dump "$DATABASE_URL" > backup.sql`. Reset de senha: aba Admin → usuários →
Redefinir (ou `python -m app.cli reset-password email@x.com`). Placar errado da
API: ative o 🔒 do jogo e corrija manualmente. `python -m app.cli recompute`
recalcula o chaveamento. CLI usa o mesmo `DATABASE_URL` do ambiente.

## Segurança (resumo)

bcrypt+pepper (custo 12), JWT HS256 com sessão de 90 dias e renovação tolerante (logout e troca de senha encerram na hora), cookies HttpOnly SameSite=Lax Secure, CSRF double-submit,
rate limiting por IP/escopo, SQL 100% parametrizado (scan AST no CI) com
tradução de placeholders no adapter, uploads re-codificados via Pillow direto
para o banco, CSP sem CDNs, HSTS. Detalhes: ARCHITECTURE.md §7 e TESTPLAN.md.

## Estrutura

`ARCHITECTURE.md` (arquitetura e papel de cada arquivo), `AGENTS.md` (pipeline),
`TESTPLAN.md` (testes planejados), `GOALS.md` (critérios de aceite por rodada),
`REVIEW.md` (crítica + correções), `CONTINUITY.md` (ledger de decisões).
