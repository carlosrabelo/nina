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

O alvo **`make run`** e **`make console`** chamam Python como `python -m nina …`; o Python carrega o `.env` mais próximo (`load_project_dotenv` em `nina/cli/parser.py`). Fora do Docker, **`DATABASE_URL_HOST`** e **`*_HOST`** não vazios substituem os nomes canónicos para o mesmo `.env` servir Compose e host.

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
| `nina daemon [--dev]` | Processo em segundo plano: agendador interno (APScheduler), API HTTP e bot Telegram. **`--dev`** desliga só o bot (HTTP e scheduler mantêm-se). Exige variáveis como `DATABASE_URL`, `NINA_HTTP_HOST`, `NINA_HTTP_PORT` (ver README e `.env.example`). |
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
| `nina email-process` | `nina email process` | **Correr processamento:** ir buscar à inbox (consulta via env), upsert em **`email_messages`**, aplicar **`email_sender_rules`** existentes no Gmail, sugestões Telegram para remetentes de alto volume desconhecidos quando o fluxo daemon/Telegram está ativo; na **CLI** o Telegram fica desligado. |
| `nina email-rules [--account …]` | `nina email rules …` | **PostgreSQL:** lista as regras **aprendidas** remetente→etiqueta que a Nina aplica (`email_sender_rules`: conta, remetente normalizado, nome da etiqueta de utilizador no Gmail, arquivo na inbox, `created_at`). Não chama a API Gmail. |
| `nina email-infer-rules` | `nina email infer-rules [--days D] [--max-per-account N] [--min-messages M] [--verbose]` | **Só regras:** varre o Gmail com `newer_than:Dd` e **insere** novas linhas em **`email_sender_rules`** quando uma etiqueta de utilizador aparece sozinha em mensagens suficientes de um remetente (não substitui regra existente). **Não** grava `email_messages` nem altera a inbox — depois corra **`nina email process`** para ingerir e aplicar. **`--verbose`** (`-v`) imprime progresso no stderr. |

Ensinar ou listar etiquetas pendentes no **Telegram** (`/emailtag`) ou no **`nina console`** (`emailtag` ou `/emailtag` — omitido da lista `help` do console). Requer o scope OAuth `gmail.modify`.

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

O Compose sobe **nina** e **PostgreSQL** (`docker-compose.yml`). Copie `.env.example` → `.env` e defina `DATABASE_URL` e caminhos como no README.

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
nina email process
nina email rules
nina cal-events --limit 3
nina llm-ping
```

`make dev-start` abre `daemon --dev` e `console` na mesma sessão tmux.

## API HTTP

Movido para [API-PT.md](API-PT.md) (API HTTP, endpoints, exemplos MacroDroid).
