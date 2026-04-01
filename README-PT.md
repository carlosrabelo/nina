# nina

Assistente pessoal via CLI para gerenciar Gmail, Google Agenda e Telegram — projetado para crescer incrementalmente.

## Destaques

- Rastreie presença (home / office / out / dnd) e deixe a Nina adaptar a seleção de conta ao contexto
- Perfil mapeia cada status de presença para as contas Google certas (Gmail + Agenda)
- Console interativo e bot do Telegram — escreva livremente e a LLM interpreta sua intenção
- Roteador de intenção unificado: uma única chamada LLM classifica o domínio e extrai entidades; domínios simples não precisam de segunda chamada
- Bloqueio de agenda por texto livre ("estou em reunião por 1h") com resolução de data completa ("segunda-feira às 14h")
- Lembretes via linguagem natural ("me lembre na segunda às 10h") — armazenados como memos com data de vencimento
- Gerenciamento de memos: criar, listar, fechar e dispensar anotações pelo console ou Telegram
- Notificações de agenda via Telegram — lembretes, novos eventos, alterações, cancelamentos
- Interface bilíngue (inglês / português) — troque com `lang pt` ou `/lang pt`
- Autentica qualquer número de contas Google via OAuth — descobertas automaticamente pelos tokens
- Consulta qualquer provedor de LLM (Groq, OpenAI, Anthropic, Ollama) via interface unificada LiteLLM
- Agendador interno (APScheduler) — sem cron externo necessário
- Todos os segredos ficam locais: tokens, sessões e credenciais são ignorados pelo git

→ **[Referência de Comandos (GUIDE-PT.md)](GUIDE-PT.md)**

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Primeiros Passos](#primeiros-passos)
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

## Primeiros Passos

### 1. Autenticar contas Google

```bash
make auth-google   # abre o navegador — repita para cada conta
make status-google # ✓ voce@gmail.com  ✓ trabalho@gmail.com
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
make play-llm-ping   # verificar conectividade
```

### 3. Configurar o bot do Telegram

1. Converse com o [@BotFather](https://t.me/BotFather) → `/newbot` → copie o token para `TELEGRAM_BOT_TOKEN` no `.env`
2. Execute `make daemon`, depois envie `/start` para o seu bot
3. Copie o chat ID que ele responder para `TELEGRAM_OWNER_ID` no `.env`

### 4. Iniciar a Nina

```bash
make dev      # daemon + console em janelas tmux divididas (desenvolvimento — sem Telegram)
# ou
make daemon   # daemon de produção (bot do Telegram + API HTTP + agendador)
make console  # apenas o console (o daemon precisa estar rodando)
```

## Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `GOOGLE_CREDENTIALS_FILE` | `credentials/credentials.json` | Credenciais OAuth baixadas do Google Cloud Console |
| `TOKENS_DIR` | `tokens` | Diretório para todos os tokens e arquivos de sessão (ignorado pelo git) |
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
    cli.py                   # ponto de entrada da CLI
    errors.py                # exceções compartilhadas
    skills/
        memo/                # criação, listagem e gerenciamento de lembretes
        presence/            # rastreamento de presença
        workdays/            # horário de trabalho e timezone
        calendar/            # bloqueio via LLM, interpretador de intenção, parser de agenda
        notifications/       # configuração e estado das notificações
        profile/             # mapeamento de contas Google por presença
    integrations/
        google/
            auth.py          # fluxo OAuth, cache de tokens, descoberta automática
            gmail/client.py
            calendar/client.py  # CalendarClient (listar, criar eventos)
        telegram/bot.py      # Bot do Telegram (modo daemon)
    core/
        intent/              # roteador de domínio via LLM
        store/               # banco de dados SQLite (memos, actions, emails, events)
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
make/                        # setup.sh, test.sh, lint.sh
credentials/                 # credentials.json (ignorado pelo git)
tokens/                      # tokens OAuth, locale, profile, workdays, notifications (ignorados pelo git)
tests/                       # suite de testes pytest (235+ testes)
```

## Desenvolvimento

```bash
make setup      # criar .venv e instalar dependências
make test       # executar todos os testes
make lint       # lint com ruff
make fmt        # formatar código com ruff
make typecheck  # verificação de tipos com mypy
make dev        # iniciar daemon + console no tmux (sem Telegram)
```

## Licença

Este projeto está licenciado sob a Licença MIT — veja o arquivo [LICENSE](LICENSE) para detalhes.
