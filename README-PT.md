# nina

Assistente pessoal via CLI para gerenciar Gmail, Google Agenda e Telegram — projetado para crescer incrementalmente.

## Destaques

- **PostgreSQL** para estado em tempo de execução (memos, actions, emails, fila de notificações de agenda, presence/workdays/notifications/profile/locale em `kv_state`) — tokens OAuth, sessões e credenciais Google continuam em ficheiros
- Roteamento de contas por presença — rastreia home/work/out/dnd e mapeia cada status para as contas Google certas (Gmail + Agenda)
- Console interativo e bot do Telegram com roteador de intenção LLM unificado — uma única chamada classifica o domínio e extrai entidades
- **Agenda (leitura)** em linguagem natural no Telegram/console — hoje/amanhã/próximos N dias, busca por palavra-chave, intervalos livres; **escritas** (bloquear horário) usam o fluxo **`blocking`** e `POST /schedule`
- Bloqueio de agenda por texto livre ("estou em reunião por 1h") com resolução de data completa ("segunda-feira às 14h")
- Memos e lembretes via linguagem natural ("me lembre na segunda às 10h") — criar, listar, fechar e dispensar pelo console ou Telegram
- Notificações de agenda via Telegram — lembretes, novos eventos, alterações, cancelamentos
- Interface bilíngue (inglês / português) — troque com `lang pt` ou `/lang pt`
- Autentica qualquer número de contas Google via OAuth — descobertas automaticamente pelos tokens
- Consulta qualquer provedor de LLM (Groq, OpenAI, Anthropic, Ollama) via interface unificada LiteLLM
- Agendador interno (APScheduler) e comandos HTTP slash para integrações externas (MacroDroid, scripts) — sem cron externo necessário
- **Etiquetas Gmail aprendidas (por conta):** **`nina gmail_label process`** vai a inbox, grava cabecalhos na PostgreSQL, aplica etiquetas aprendidas no Gmail e pode sugerir remetentes novos no Telegram pelo daemon; opcionalmente **`--days`** e **`--max-per-account`** alargam a consulta Gmail e sobem o limite por conta (ate 5000); mensagens com **`tagged_at`** ja definido em **`email_messages`** sao ignoradas cedo (sem upsert de cabecalho); **`nina gmail_label infer-rules`** so acrescenta **`email_sender_rules`** a partir de etiquetas de utilizador ja no Gmail (sem gravar `email_messages`); ambos aceitam **`-v` / `--verbose`** para progresso no stderr; **`nina gmail_label rules`** lista as regras gravadas; ensinar com `/gmail_label` ou `gmail_label` no `nina console`; **`/gmail_label dismiss-all`** limpa todas as sugestoes abertas; etiquetas devem comecar com **`@`** ou **`!`**; remetentes ignorados (**`nina gmail_label ignore ...`**) ficam excluidos permanentemente das sugestoes.
- Todos os segredos ficam locais: tokens, sessões e credenciais em ficheiros; o estado da aplicação fica no PostgreSQL

→ **[Referência de Comandos (GUIDE-PT.md)](GUIDE-PT.md)** (tabela completa: [Lista completa de comandos da CLI](GUIDE-PT.md#lista-completa-de-comandos-da-cli)) · **[API HTTP (API-PT.md)](API-PT.md)** / [API.md](API.md) · **[Skills (SKILL-PT.md)](SKILL-PT.md)** / [SKILL.md](SKILL.md) (domínios em `nina/skills/`) · [AGENTS.md](AGENTS.md) (manter docs em sync ao mudar o produto)

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Uso](#uso)
- [Configuração](#configuração)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Desenvolvimento](#desenvolvimento)
- [Licença](#licença)

## Pré-requisitos

- **Python 3.12+**
- **Projeto no Google Cloud** com as APIs Gmail e Google Agenda habilitadas e um cliente OAuth 2.0 Desktop — [console.cloud.google.com](https://console.cloud.google.com)
- **Token de Bot do Telegram** do [@BotFather](https://t.me/BotFather) (necessário para a interface bot)
- **Chave de API de LLM** (Groq, OpenAI, Anthropic) ou Ollama local — necessária para comandos em texto livre

## Instalação

```bash
git clone https://github.com/carlosrabelo/nina.git
cd nina
make setup
cp .env.example .env
# Edite o .env — preencha as credenciais de cada serviço que quiser usar
```

## Uso

### 1. Autenticar contas Google

```bash
.venv/bin/python -m nina google auth    # abre o navegador — repita para cada conta
.venv/bin/python -m nina google status  # ✓ voce@gmail.com  ✓ trabalho@gmail.com
```

O escopo OAuth inclui leitura e escrita na Agenda — necessário para bloqueio e notificações.

### 2. Configurar a LLM

Adicione ao `.env`:

```
LLM_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=gsk_...
```

Outros provedores: `openai/gpt-4o-mini`, `anthropic/claude-haiku-4-5-20251001`, `ollama/llama3.2`.

```bash
.venv/bin/python -m nina llm ping   # verificar conectividade
```

### 3. Configurar o bot do Telegram

1. Converse com o [@BotFather](https://t.me/BotFather) → `/newbot` → copie o token para `TELEGRAM_BOT_TOKEN` no `.env`
2. Execute `.venv/bin/python -m nina daemon`, depois envie `/start` para o seu bot
3. Copie o chat ID que ele responder para `TELEGRAM_OWNER_ID` no `.env`

### 4. Iniciar a Nina

```bash
make dev-start  # daemon + console em janelas tmux divididas (desenvolvimento — sem Telegram)
# ou
.venv/bin/python -m nina daemon   # daemon de produção (bot do Telegram + API HTTP + agendador)
make console     # apenas o console (o daemon precisa estar rodando)
```

## Configuração

Copie [`.env.example`](.env.example) para `.env`. **Recomendado:** defina só `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` e `POSTGRES_PORT`; o `nina` monta `DATABASE_URL` depois de carregar o `.env` (host `127.0.0.1` na máquina, host `postgres` dentro do contentor). Defina `DATABASE_URL` manualmente só se precisar de opções extra na URL (ex.: `?sslmode=require`). Use **caminhos relativos ao repositório** (`DATA_DIR=data/db`, …) para a CLI local; dentro do Docker, o `load_project_dotenv` acrescenta um `/` inicial a esses valores quando ainda não são absolutos (ex.: `data/db` passa a `/data/db` no volume `./data:/data`).

Ao correr **`nina`** ou **`make run` / `make console`**, o Python carrega o `.env` mais próximo (`load_project_dotenv` em `nina/cli/_env.py`). Não há variáveis separadas `*_HOST`.

| Variável | Padrão | Descrição |
|---|---|---|
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_PORT` | — | **Principal:** credenciais Postgres; `DATABASE_URL` é derivada quando vazia (ver acima). |
| `POSTGRES_HOST` | — | Hostname opcional da BD (senão `127.0.0.1` no host, `postgres` no Docker). |
| `DATABASE_URL` | (derivada de `POSTGRES_*`) | URL PostgreSQL explícita opcional (parâmetros não padrão). |
| `NINA_IMAGE` | (ver `.env.example`) | Imagem do serviço `nina` no Compose; `make docker-start` sobrescreve com `REGISTRY/IMAGE:<git sha>` e `--build` |
| `GOOGLE_CREDENTIALS_FILE`, `TOKENS_DIR`, `SESSIONS_DIR`, `DATA_DIR` | — | Caminhos: relativos ao repo no host; no Docker, acrescenta-se `/` no início se o valor não for já absoluto (ver acima). |
| `NINA_HTTP_HOST` | `0.0.0.0` | Interface para bind/publicação da porta HTTP |
| `NINA_HTTP_PORT` | `8765` | Porta HTTP |
| `NINA_API_KEY` | — | Se setada, protege a API HTTP via header `X-Api-Key` |
| `TZ` / `PGTZ` | — | Timezone nos containers e TZ compatível com libpq |
| `TELEGRAM_BOT_TOKEN` | — | Token do bot fornecido pelo @BotFather |
| `TELEGRAM_OWNER_ID` | — | Seu chat ID pessoal no Telegram (o bot só responde a este ID) |
| `LLM_MODEL` | `groq/llama-3.3-70b-versatile` | String do modelo LiteLLM: `<provedor>/<modelo>` |
| `GROQ_API_KEY` | — | Chave de API do Groq (obrigatória ao usar Groq) |
| `OPENAI_API_KEY` | — | Chave de API da OpenAI (obrigatória ao usar OpenAI) |
| `ANTHROPIC_API_KEY` | — | Chave de API da Anthropic (obrigatória ao usar Anthropic) |
| `LLM_TEMPERATURE` | `0.3` | Temperatura de amostragem |
| `LLM_MAX_TOKENS` | `1024` | Número máximo de tokens na resposta |

## Estrutura do Projeto

```
nina/
    __main__.py              # ponto de entrada do `python -m nina`
    errors.py                # exceções compartilhadas
    cli/                     # parser + handlers da CLI (google, telegram, daemon,
                             # console, gmail, calendar, llm)
    tasks/
        email_process.py         # ingestão da inbox, aplicar regras, sugestões Telegram
        email_infer_rules.py     # varrer etiquetas Gmail → inserir regras de remetente
    skills/
        memo/                # criação, listagem e gerenciamento de lembretes
        presence/            # rastreamento de presença
        workdays/            # horário de trabalho e timezone
        calendar/            # execute.py (leitura), blocking (escrita), interpretador, parser de agenda
        notifications/       # configuração e estado das notificações
        profile/             # mapeamento de contas Google por presença
        activity_log/        # log de atividades passadas no Google Calendar
        gmail_label/         # ensinar/descartar etiquetas, ignorados, execute + interpreter
    integrations/
        google/
            auth.py          # fluxo OAuth, cache de tokens, descoberta automática
            gmail/client.py
            calendar/client.py  # CalendarClient (listar, criar eventos)
        telegram/
            bot.py                 # fábrica da app, comandos com /, runner em batch
            command_registry.py    # /setMyCommands + bot_lang(ctx)
            constants.py           # MAX_MSG
            free_text_handler.py   # linguagem natural + router LLM (mensagens sem comando)
            offset_store.py        # persistência do offset do getUpdates (batch)
    core/
        intent/
            router.py          # roteador LLM unificado (4 camadas)
            local_router.py    # pattern matching local — zero LLM
        nlp/                   # parser local de data/hora/duração
        store/               # banco de dados PostgreSQL (memos, actions, emails, events) + kv_state
        llm/                 # LLMClient — wrapper LiteLLM
        i18n/                # strings bilíngues (en / pt)
        locale/              # configuração de idioma
        scheduler/
            jobs/
                calendar_notifications.py  # lembretes + detecção de mudanças (a cada 5 min)
        daemon/
            runner.py        # daemon com APScheduler + servidor HTTP
            http.py          # API HTTP (presence, workdays, schedule, notifications)
            client.py        # cliente HTTP console → daemon
        console/
            runner.py              # REPL interativo (cmd.Cmd)
            paths.py               # DATA_DIR, TOKENS_DIR, idioma do console
            intent_executors.py    # memo / notificações / activity_log → print
            freeform_dispatch.py   # linguagem natural + router LLM para linhas livres
scripts/                     # ex.: migrate_to_postgres.py (SQLite/JSON legado → Postgres)
.make/                       # setup.sh, test.sh, lint.sh, quality.sh, clean.sh, dev.sh
credentials/                 # credentials.json (ignorado pelo git)
tokens/                      # tokens OAuth (ignorados pelo git)
tests/                       # suite de testes pytest
```

## Desenvolvimento

```bash
make help       # listar alvos do make e comandos da CLI nina
make setup      # criar .venv e instalar dependências
make test       # executar todos os testes
make lint       # lint com ruff
make fmt        # formatar código com ruff
make quality    # fmt + lint + typecheck (mypy) em um único alvo
.venv/bin/python -m nina typecheck   # apenas mypy no pacote nina
make dev-start  # iniciar daemon + console no tmux (sem Telegram)
make console    # abrir o console (daemon precisa estar rodando)
make run …      # CLI com .env e caminhos do host (ex.: `make run migrate to-postgres`)
make docker-start   # compose up com imagem etiquetada pelo commit + build
make docker-stop    # compose down
make docker-restart # docker-stop depois docker-start
make docker-migrate # script de migração num container one-off (monta ./scripts)
```

Nota para contribuidores: manter a documentação de utilizador alinhada — ver [AGENTS.md](AGENTS.md).

## Licença

Este projeto está licenciado sob a Licença MIT — veja o arquivo [LICENSE](LICENSE) para detalhes.
