# nina

Assistente pessoal via CLI para gerenciar Gmail, Google Agenda e Telegram — projetado para crescer incrementalmente.

## Destaques

- Autentica qualquer número de contas Gmail via Google OAuth — sem necessidade de listar emails manualmente
- Descobre automaticamente as contas autenticadas pelos tokens salvos na inicialização
- Lista mensagens não lidas, pesquisa e exibe cabeçalhos recentes em todas as contas Gmail
- Lista próximos eventos da Agenda, com filtro por ID de calendário
- Lê e envia mensagens no Telegram agindo como sua conta pessoal (Telethon)
- Recebe comandos via Bot do Telegram em modo batch — sem loop em execução permanente
- Consulta qualquer provedor de LLM (Groq, OpenAI, Anthropic, Ollama) por meio de uma interface única LiteLLM — troca de provedor com uma linha no `.env`
- Renovação de tokens Google feita automaticamente; reautenticação apenas quando necessário
- Todos os segredos ficam locais: tokens, arquivos de sessão e credenciais são ignorados pelo git

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso — Google](#uso--google)
- [Uso — Cliente Telegram Pessoal](#uso--cliente-telegram-pessoal)
- [Uso — Bot do Telegram](#uso--bot-do-telegram)
- [Uso — LLM](#uso--llm)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Desenvolvimento](#desenvolvimento)
- [Licença](#licença)

## Pré-requisitos

- **Python 3.12+**
- **Projeto no Google Cloud** com as APIs Gmail e Google Agenda habilitadas e um cliente OAuth 2.0 Desktop — [console.cloud.google.com](https://console.cloud.google.com)
- **Credenciais da API do Telegram** (`api_id` / `api_hash`) em [my.telegram.org](https://my.telegram.org) → API Development Tools
- **Token de Bot do Telegram** do [@BotFather](https://t.me/BotFather) (necessário apenas para receber comandos via bot)

## Instalação

```bash
git clone https://github.com/carlosrabelo/nina.git
cd nina
make setup
cp .env.example .env
# Edite o .env — preencha as credenciais de cada serviço que quiser usar
```

## Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `GOOGLE_CREDENTIALS_FILE` | `credentials/credentials.json` | Credenciais OAuth baixadas do Google Cloud Console |
| `TOKENS_DIR` | `tokens` | Diretório para todos os tokens e arquivos de sessão (ignorado pelo git) |
| `TELEGRAM_API_ID` | — | API id do MTProto do Telegram (my.telegram.org) |
| `TELEGRAM_API_HASH` | — | API hash do MTProto do Telegram (my.telegram.org) |
| `TELEGRAM_BOT_TOKEN` | — | Token do bot fornecido pelo @BotFather |
| `TELEGRAM_OWNER_ID` | — | Seu chat ID pessoal no Telegram (o bot só responde a este ID) |
| `LLM_MODEL` | `groq/llama-3.3-70b-versatile` | String do modelo LiteLLM: `<provedor>/<modelo>` |
| `GROQ_API_KEY` | — | Chave de API do Groq (obrigatória ao usar Groq) |
| `OPENAI_API_KEY` | — | Chave de API da OpenAI (obrigatória ao usar OpenAI) |
| `ANTHROPIC_API_KEY` | — | Chave de API da Anthropic (obrigatória ao usar Anthropic) |
| `LLM_TEMPERATURE` | `0.3` | Temperatura de amostragem |
| `LLM_MAX_TOKENS` | `1024` | Número máximo de tokens na resposta |

## Uso — Google

### Autenticar uma conta Google

Execute uma vez por conta — abre o navegador para você escolher a conta:

```bash
make auth
```

Repita para cada conta. A Nina descobre automaticamente todas as contas autenticadas.

### Verificar status

```bash
make status
# ✓  voce@gmail.com
# ✓  trabalho@gmail.com
```

### Gmail

```bash
make gmail-latest                               # cabeçalhos recentes, todas as contas
make gmail-latest ACCOUNT=voce@gmail.com       # conta específica
make gmail-unread LIMIT=5                       # mensagens não lidas
make gmail-search QUERY="subject:fatura is:unread"
make gmail-search QUERY="from:chefe" ACCOUNT=trabalho@gmail.com
```

### Agenda

```bash
make cal-calendars                              # lista todos os calendários com seus IDs
make cal-events                                 # próximos eventos (calendário principal)
make cal-events LIMIT=5
make cal-events CAL=abc123@group.calendar.google.com   # calendário específico
make cal-events ACCOUNT=trabalho@gmail.com CAL=abc123@group.calendar.google.com
```

### Revogar uma conta Google

```bash
./nina.py revoke voce@gmail.com
```

## Uso — Cliente Telegram Pessoal

O cliente pessoal permite que a Nina leia e envie mensagens **como você** — agindo na sua conta Telegram pessoal.

### Autenticar

```bash
make tg-auth
# Número de telefone (com código do país): +5511...
# Código de verificação do Telegram: 12345
```

A sessão é salva em `tokens/telegram.session` — não precisa reautenticar na próxima vez.

### Verificar status

```bash
make tg-status
# ✓  Seu Nome (+5511...)
```

### Ler e enviar mensagens

```bash
make tg-dialogs                          # lista chats recentes
make tg-dialogs LIMIT=10
make tg-messages CHAT=@username          # mensagens de um chat
make tg-messages CHAT=+5511...           # por número de telefone
make tg-send CHAT=@username TEXT="Oi!"   # enviar uma mensagem
```

## Uso — Bot do Telegram

O bot permite que **você envie comandos para a Nina** pelo Telegram. Funciona em modo batch: cada execução busca os comandos pendentes, processa e encerra — sem processo em segundo plano.

### Configuração inicial (uma vez)

1. Converse com o [@BotFather](https://t.me/BotFather) → `/newbot` → copie o token para `TELEGRAM_BOT_TOKEN` no `.env`
2. Execute `make tg-bot` uma vez
3. Abra o Telegram e envie `/start` para o seu novo bot
4. Execute `make tg-bot` novamente — o bot responderá com seu chat ID
5. Copie esse número para `TELEGRAM_OWNER_ID` no `.env`

### Executar

```bash
make tg-bot
# Processed 1 command(s).
```

### Comandos disponíveis no bot

| Comando | Descrição |
|---|---|
| `/start` | Mensagem de boas-vindas e seu chat ID |
| `/help` | Lista todos os comandos |
| `/unread` | Emails não lidos em todas as contas Gmail |
| `/latest` | Cabeçalhos dos emails mais recentes |
| `/events` | Próximos eventos da Agenda |
| `/dialogs` | Chats recentes do Telegram |

### Automatizar com cron (opcional)

Para que a Nina verifique comandos a cada minuto, adicione ao crontab (`crontab -e`):

```
* * * * * cd /caminho/para/nina && make tg-bot >> /tmp/nina-bot.log 2>&1
```

## Uso — LLM

A Nina usa o [LiteLLM](https://github.com/BerriAI/litellm) como interface unificada para qualquer provedor de LLM. Trocar do Groq para OpenAI ou Anthropic é uma mudança de uma linha no `.env` — sem alterações no código.

### Configurar

Adicione ao `.env`:

```
LLM_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=gsk_...
```

Para usar outro provedor:

```
LLM_MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=sk_...

# ou Anthropic
LLM_MODEL=anthropic/claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=sk-ant-...

# ou Ollama local (sem chave)
LLM_MODEL=ollama/llama3.2
```

### Verificar conectividade

```bash
make llm-ping
#   ✓  groq/llama-3.3-70b-versatile  →  OK
```

## Estrutura do Projeto

```
nina.py              # Ponto de entrada CLI
gmail.py             # GmailClient + GmailMultiClient (N contas)
calendar_client.py   # CalendarClient (Google Agenda)
telegram_client.py   # TgClient — cliente Telethon pessoal (ler/enviar como você)
telegram_bot.py      # Processador batch do Bot do Telegram (receber comandos)
llm.py               # LLMClient — wrapper LiteLLM (Groq, OpenAI, Anthropic, Ollama)
auth.py              # Fluxo OAuth Google, cache de tokens, descoberta automática
errors.py            # NinaError, AuthError, GmailError, CalendarError, TelegramError, LLMError
make/                # setup.sh, test.sh, lint.sh
credentials/         # credentials.json do Google Cloud Console (ignorado pelo git)
tokens/              # Tokens OAuth, sessão Telegram, offset do bot (todos ignorados)
tests/               # Suite de testes pytest
```

## Desenvolvimento

```bash
make setup      # Cria o .venv e instala dependências (apenas na primeira vez)
make test       # Executa todos os testes
make lint       # Lint com ruff
make fmt        # Formata o código com ruff
make typecheck  # Verificação de tipos com mypy
```

## Licença

Este projeto está licenciado sob a Licença MIT — veja o arquivo [LICENSE](LICENSE) para detalhes.
