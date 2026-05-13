# nina — Guia de Comandos e Integrações

Documento complementar ao [README-PT.md](README-PT.md). Cobre a CLI, a API HTTP, os comandos slash e integrações como atualização automática de presença pelo MacroDroid. Ao alterar comportamento visível para o utilizador, mantenha este ficheiro e o [README-PT.md](README-PT.md) alinhados com [GUIDE.md](GUIDE.md) / [README.md](README.md) — ver [AGENTS.md](AGENTS.md).

## Sumário

- [Comandos da CLI](#comandos-da-cli)
- [Lista completa de comandos da CLI](#lista-completa-de-comandos-da-cli)
- [API HTTP](#api-http)
- [Estados de presença](#estados-de-presença)
- [MacroDroid: presença automática por localização](#macrodroid-presença-automática-por-localização)
- [Comandos slash](#comandos-slash)

## Comandos da CLI

### Como executar a `nina`

Na raiz do projeto, com o venv:

```bash
.venv/bin/python -m nina <comando> [argumentos...]
# ou, após `source .venv/bin/activate` e `pip install -e .`:
nina <comando> [argumentos...]
```

O alvo **`make run`** e **`make console`** chamam Python como `python -m nina …`; o Python carrega o `.env` mais próximo (`load_project_dotenv` em `nina/cli/parser.py`). Se `DATABASE_URL` estiver vazia, é montada a partir de `POSTGRES_*` (ver README). No Docker, valores relativos de `DATA_DIR` / `TOKENS_DIR` / `SESSIONS_DIR` / `GOOGLE_CREDENTIALS_FILE` recebem um `/` inicial para funcionarem como no host.

```bash
make run gmail latest --limit 5
make run migrate to-postgres    # o Makefile chama scripts/migrate_to_postgres.py (não é subcomando `nina`)
```

**`make console`** abre o console interativo (o daemon tem de estar a correr). Prefira `make console` a `make run console`.

Quando existem duas formas, este guia indica o **alias plano** (ex.: `nina gmail-latest`) e a forma **hierárquica** (`nina gmail latest`); são equivalentes.

### Ajuda integrada

```bash
.venv/bin/python -m nina --help
.venv/bin/python -m nina gmail --help
.venv/bin/python -m nina gmail latest -h
```

## Lista completa de comandos da CLI

### Ciclo de vida e consola

| Comando | Função |
|---------|--------|
| `nina daemon [--dev]` | Processo em segundo plano: agendador interno (APScheduler), API HTTP e bot Telegram. **`--dev`** desliga só o bot (HTTP e scheduler mantêm-se). Exige credenciais Postgres (ou `DATABASE_URL`), `NINA_HTTP_HOST`, `NINA_HTTP_PORT` (ver README e `.env.example`). |
| `nina console` | REPL interativo que fala com o **daemon já em execução** via HTTP (usa `NINA_HTTP_*`; envia `X-Api-Key` se `NINA_API_KEY` estiver definida). |

### Autenticação Google / Telegram (utilizador)

| Alias plano | Forma hierárquica | Função |
|-------------|-------------------|--------|
| `nina auth-google` | `nina auth google` | OAuth no browser; grava uma conta Google em `TOKENS_DIR`. Repita por conta. |
| `nina auth-telegram [--phone +…]` | `nina auth telegram [--phone +…]` | Login interativo da API **utilizador** Telegram (não o bot); sessão em `SESSIONS_DIR`. |
| `nina status-google` | `nina status google` | Lista contas Google descobertas e se o token parece válido. |
| `nina status-telegram` | `nina status telegram` | Indica se o cliente **utilizador** Telegram está autorizado. |
| — | `nina revoke <email>` | Remove o token OAuth Google dessa conta (sem alias plano). |

### Gmail (exploratório)

| Alias plano | Hierárquico | Função |
|-------------|-------------|--------|
| `nina gmail-latest [--account …] [--limit N]` | `nina gmail latest …` | Cabeçalhos das mensagens recentes por conta (ou uma conta). |
| `nina gmail-unread [--account …] [--limit N]` | `nina gmail unread …` | Mensagens não lidas (todas as contas se omitir `--account`). |
| `nina gmail-search "QUERY" [--account …] [--limit N]` | `nina gmail search "QUERY" …` | Pesquisa Gmail com [operadores de pesquisa](https://support.google.com/mail/answer/7190). |
| `nina gmail-labels [--account …] [--user-only]` | `nina gmail labels …` | **Só Gmail:** lista as etiquetas que **existem na conta Gmail** neste momento (API `users.labels.list`): id, tipo (`system` / `user`) e nome. **Não** são as regras remetente→etiqueta aprendidas pela Nina na PostgreSQL. **`--user-only`** limita às etiquetas criadas por si. |

### Etiquetas Gmail aprendidas (CLI)

| Alias plano | Hierárquico | Função |
|-------------|-------------|--------|
| `nina gmail-label-process [--verbose] [--days D] [--max-per-account N]` | `nina gmail_label process [--verbose] [--days D] [--max-per-account N]` | **Correr processamento:** ir buscar com **`NINA_EMAIL_SYNC_QUERY`**, upsert em **`email_messages`**, aplicar **`email_sender_rules`** no Gmail, sugestões Telegram no fluxo daemon; na **CLI** o Telegram fica desligado. Mensagens que já têm **`tagged_at`** em **`email_messages`** são ignoradas cedo (sem upsert de cabeçalho, sem regra/pending). **`--days`** define ou substitui o primeiro `newer_than:Dd` na consulta (backfill largo). **`--max-per-account`** limita quantas mensagens listar por conta (omissão: env, máx. 500; na CLI até **5000**). **`--verbose`** (`-v`) imprime progresso no stderr. |
| `nina gmail-label-rules` | `nina gmail_label rules list [--account …]` | **PostgreSQL:** lista as regras **aprendidas** remetente→etiqueta que a Nina aplica (`email_sender_rules`: conta, remetente normalizado, nome da etiqueta de utilizador no Gmail, arquivo na inbox, `created_at`). Nao chama a API Gmail. |
| | `nina gmail_label rules check` | **Validar regras:** verifica todas as regras para prefixo invalido, etiqueta ausente no Gmail, sem token OAuth, ou remetente tambem na lista de ignorados. |
| `nina gmail-label-infer` | `nina gmail_label infer-rules [--days D] [--max-per-account N] [--min-messages M] [--verbose]` | **So regras:** varre o Gmail com `newer_than:Dd` e **insere** novas linhas em **`email_sender_rules`** quando uma etiqueta de utilizador aparece sozinha em mensagens suficientes de um remetente (nao substitui regra existente). **Nao** grava `email_messages` nem altera a inbox — depois corra **`nina gmail_label process`** para ingerir e aplicar. **`--verbose`** (`-v`) imprime progresso no stderr. |
| `nina gmail_label rule add <conta> <remetente> <@etiqueta>` | (mesmo) | **Adicionar regra manualmente:** cria uma regra de remetente diretamente sem sugestao pendente. A etiqueta deve comecar com **`@`** ou **`!`**. Se ja existe uma regra para essa conta+remetente, a etiqueta e atualizada. |
| `nina gmail_label ignore list [--account …]` | (mesmo) | Lista remetentes ignorados que nunca vão gerar sugestões de etiquetas. |
| `nina gmail_label ignore add <conta> <remetente>` | (mesmo) | Adiciona um remetente à lista de ignorados. Também acontece automaticamente ao **descartar** uma sugestão pendente. |
| `nina gmail_label ignore remove <conta> <remetente>` | (mesmo) | Remove um remetente da lista de ignorados para que as sugestões possam aparecer novamente. |

Ensinar ou listar etiquetas pendentes no **Telegram** (`/gmail_label`) ou no **`nina console`** (`gmail_label`; ver `help` / `help gmail_label` no console). Descartar uma sugestao adiciona automaticamente o remetente a **lista de ignorados** (`email_ignored_senders`), impedindo sugestoes futuras. **`/gmail_label dismiss-all`** limpa todas as sugestoes abertas de uma vez. Etiquetas devem comecar com **`@`** ou **`!`** (ex.: `@Financeiro`, `!Importante`). **`/gmail_label rules check`** valida todas as regras para problemas comuns. Gerir os ignorados com **`/gmail_label ignore list|add|remove`** ou **`nina gmail_label ignore ...`**. Requer o scope OAuth `gmail.modify`.

### Google Agenda (CLI exploratório)

| Alias plano | Hierárquico | Função |
|-------------|-------------|--------|
| `nina cal-list [--account …]` | `nina calendar list …` | Lista nomes e IDs dos calendários. |
| `nina cal-events [--account …] [--calendar ID] [--limit N]` | `nina calendar events …` | Próximos eventos; `--calendar` por omissão é `primary`. |

**Linguagem natural (Telegram / console):** perguntas de agenda (janelas, palavra-chave, livre/ocupado) passam pelo bot ou `nina console` com o daemon — **só leitura**, usando a conta de calendário do perfil / presença (ou a melhor correspondência a palavras como “trabalho” vs “pessoal”). **Criar** tempo na agenda (bloqueios, “dentista às 9h”) usa o intent **`blocking`** / `POST /schedule`, não estes comandos exploratórios.

### Cliente Telegram utilizador (exploratório)

| Alias plano | Hierárquico | Função |
|-------------|-------------|--------|
| `nina tg-bot` | `nina tg bot` | Modo batch de comandos ligados ao bot a partir do ambiente (scripts / avançado). |
| `nina tg-setup` | `nina tg setup` | Ajuda a descobrir o `TELEGRAM_OWNER_ID` do bot. |
| `nina tg-dialogs [--limit N]` | `nina tg dialogs …` | Lista diálogos recentes da sessão **utilizador**. |
| `nina tg-messages CHAT [--limit N]` | `nina tg messages CHAT …` | Mensagens recentes; `CHAT` = id numérico, `@utilizador` ou telefone. |
| `nina tg-send CHAT TEXTO` | `nina tg send CHAT TEXTO` | Envia mensagem como cliente **utilizador**. |

### LLM

| Alias plano | Hierárquico | Função |
|-------------|-------------|--------|
| `nina llm-ping` | `nina llm ping` | Uma chamada a `LLM_MODEL` para validar chaves e conectividade. |

### Qualidade de código

| Comando | Função |
|---------|--------|
| `nina typecheck [caminhos…]` | Executa `mypy` (por omissão: pacote `nina` instalado). Equivale ao passo mypy do `make quality`. |

### Docker e Compose

O Compose sobe **nina** e **PostgreSQL** (`docker-compose.yml`). Copie `.env.example` → `.env`, defina `POSTGRES_*` (e caminhos como no README); `DATABASE_URL` é opcional.

- **`make docker-start`** — define `NINA_IMAGE` como `REGISTRY/IMAGE:<git curto>` e executa `docker compose up -d --build`.
- **`make docker-stop`** — `docker compose down`.
- **`make docker-restart`** — `docker-stop` e depois `docker-start`.
- **`make docker-migrate`** — executa `scripts/migrate_to_postgres.py` num container avulso (monta `./scripts`).

`docker compose up -d` sozinho usa o `NINA_IMAGE` do `.env`. Use `docker-compose.override.yml` com `build: .` para build local.

### Exemplos rápidos

```bash
nina auth-google && nina status-google
nina daemon --dev          # terminal A
make console               # terminal B — o `.env` no host deve apontar ao DB e ao daemon
nina gmail-unread --limit 5
nina gmail labels --user-only
nina gmail_label process
# opcional: janela larga, mais mensagens; linhas já etiquetadas são ignoradas cedo
nina gmail_label process --days 365 --max-per-account 2000 -v
nina gmail_label rules
nina cal-events --limit 3
nina llm-ping
```

`make dev-start` abre `daemon --dev` e `console` na mesma sessão tmux.

## API HTTP

Movido para [API-PT.md](API-PT.md) (API HTTP, endpoints, exemplos MacroDroid).
