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
- Todos os segredos ficam locais: tokens, sessões e credenciais em ficheiros; o estado da aplicação fica no PostgreSQL

→ **[Referência de Comandos (GUIDE-PT.md)](GUIDE-PT.md)** (tabela completa: [Lista completa de comandos da CLI](GUIDE-PT.md#lista-completa-de-comandos-da-cli)) · [AGENTS.md](AGENTS.md) (sincronizar README/GUIDE ao mudar o produto)

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
.venv/bin/python -m nina auth-google   # abre o navegador — repita para cada conta
.venv/bin/python -m nina status-google # ✓ voce@gmail.com  ✓ trabalho@gmail.com
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
.venv/bin/python -m nina llm-ping   # verificar conectividade
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

Copie [`.env.example`](.env.example) para `.env`. O exemplo traz **caminhos canónicos para Docker** (`DATA_DIR=/data/db`, `DATABASE_URL` com host `postgres`, etc.) e variáveis **`*_HOST`** para os mesmos caminhos/URL na sua máquina — `make run` e `make console` exportam os overrides do host automaticamente.

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | — | URL PostgreSQL para **containers** (ex.: host `postgres`) — obrigatória no daemon/CLI dentro do Compose |
| `DATABASE_URL_HOST` | — | URL PostgreSQL para **`make run` / `make console`** no host (ex.: `localhost` com a porta do DB publicada) |
| `NINA_IMAGE` | (ver `.env.example`) | Imagem do serviço `nina` no Compose; `make docker-start` sobrescreve com `REGISTRY/IMAGE:<git sha>` e `--build` |
| `GOOGLE_CREDENTIALS_FILE`, `TOKENS_DIR`, `SESSIONS_DIR`, `DATA_DIR` | — | Caminhos canónicos no **container**; use `*_HOST` para `make run` / `make console` no host |
| `NINA_HTTP_HOST` | `0.0.0.0` | Interface para bind/publicação da porta HTTP |
| `NINA_HTTP_PORT` | `8765` | Porta HTTP |
| `NINA_API_KEY` | — | Se setada, protege a API HTTP via header `X-Api-Key` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_PORT` | — | Serviço Postgres no Docker Compose (ver `.env.example`) |
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
    cli/                     # parser + handlers da CLI (auth, status, daemon,
                             # console, gmail, calendar, tg, llm)
    skills/
        memo/                # criação, listagem e gerenciamento de lembretes
        presence/            # rastreamento de presença
        workdays/            # horário de trabalho e timezone
        calendar/            # execute.py (leitura), blocking (escrita), interpretador, parser de agenda
        notifications/       # configuração e estado das notificações
        profile/             # mapeamento de contas Google por presença
        activity_log/        # log de atividades passadas no Google Calendar
    integrations/
        google/
            auth.py          # fluxo OAuth, cache de tokens, descoberta automática
            gmail/client.py
            calendar/client.py  # CalendarClient (listar, criar eventos)
        telegram/bot.py      # Bot do Telegram (modo daemon)
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
        console/runner.py    # REPL interativo
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
