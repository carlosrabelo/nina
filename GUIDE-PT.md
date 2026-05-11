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

O alvo **`make run`** carrega o `.env` e aplica os overrides de host (`*_HOST`, `DATABASE_URL_HOST`, …) para usar Postgres e ficheiros na sua máquina:

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

O Compose sobe **nina** e **PostgreSQL** (`docker-compose.yml`). Copie `.env.example` → `.env` e defina `DATABASE_URL`, `DATABASE_URL_HOST` e caminhos como no README.

- **`make docker-start`** — define `NINA_IMAGE` como `REGISTRY/IMAGE:<git curto>` e executa `docker compose up -d --build`.
- **`make docker-stop`** — `docker compose down`.
- **`make docker-restart`** — `docker-stop` e depois `docker-start`.
- **`make docker-migrate`** — executa `scripts/migrate_to_postgres.py` num container avulso (monta `./scripts`).

`docker compose up -d` sozinho usa o `NINA_IMAGE` do `.env`. Use `docker-compose.override.yml` com `build: .` para build local.

### Exemplos rápidos

```bash
nina auth-google && nina status-google
nina daemon --dev          # terminal A
make console               # terminal B — `.env` / *_HOST no host devem apontar ao DB e ao daemon
nina gmail-unread --limit 5
nina cal-events --limit 3
nina llm-ping
```

`make dev-start` abre `daemon --dev` e `console` na mesma sessão tmux.

## API HTTP

Quando o daemon está rodando, a API HTTP responde na porta `8765`. Padrões:

| Variável          | Valor típico |
|-------------------|--------------|
| `NINA_HTTP_HOST`  | `0.0.0.0` (ver `.env` / `.env.example`) |
| `NINA_HTTP_PORT`  | `8765`       |
| `NINA_API_KEY`    | vazio (auth desligada) |

Para aceitar conexões de outros aparelhos (celular com MacroDroid, scripts em outra máquina), coloque no `.env`:

```
NINA_HTTP_HOST=0.0.0.0
NINA_HTTP_PORT=8765
NINA_API_KEY=escolha-uma-chave-forte
```

Reinicie o daemon (`make dev-stop && make dev-start` ou reinicie seu processo `nina daemon`). Quando `NINA_API_KEY` está definida, todas as requisições precisam levar o header `X-API-Key: <chave>`.
O console envia automaticamente `X-Api-Key` quando `NINA_API_KEY` está setada localmente.

### Endpoints

| Método | Caminho                    | Função                                       |
|--------|----------------------------|----------------------------------------------|
| GET    | `/`                        | Info do serviço, uptime, presença atual      |
| GET    | `/health`                  | Liveness probe                               |
| GET    | `/status`                  | Presença + contexto de horário de trabalho   |
| GET    | `/presence`                | Estado de presença atual                     |
| PUT    | `/presence`                | Define presença (corpo JSON)                 |
| POST   | `/presence/{status}`       | Define presença (path-style; MacroDroid)     |
| POST   | `/command`                 | Comando slash (ver abaixo)                   |
| GET    | `/notifications/config`    | Config de lembretes                          |
| ...    | ...                        | Lista completa em `/docs` (Swagger UI)       |

Abra `http://127.0.0.1:8765/docs` no navegador com o daemon ativo para inspecionar todas as rotas interativamente.

### Definir presença — exemplos

PUT com JSON:

```bash
curl -X PUT http://127.0.0.1:8765/presence \
  -H "X-API-Key: $NINA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status": "work", "note": "office"}'
```

POST com path + query (sem corpo — mais simples no MacroDroid):

```bash
curl -X POST "http://127.0.0.1:8765/presence/work?note=office" \
  -H "X-API-Key: $NINA_API_KEY"
```

Ler de volta:

```bash
curl -s -H "X-API-Key: $NINA_API_KEY" http://127.0.0.1:8765/presence
# {"status":"work","since":"...","note":"office"}
```

## Estados de presença

Quatro estados em `nina/skills/presence/models.py`:

| status  | significado                                                  |
|---------|--------------------------------------------------------------|
| `home`  | em casa — disponibilidade normal                             |
| `work`  | trabalhando presencialmente (escritório, campus, cliente…)   |
| `out`   | na rua / em movimento — resumos curtos                       |
| `dnd`   | não perturbe — silêncio total                                |

O campo `note` é texto livre que viaja junto com o estado. Use ele para sub-contexto (`office` vs `campus`) sem mudar o status canônico.

## MacroDroid: presença automática por localização

Objetivo: o celular atualiza a presença sozinho, baseado em onde você está. Definimos **três geofences** (home, campus, office) e usamos o campo `note` para distinguir "no prédio do escritório" de "no campus mas fora do escritório".

### Tabela de estados

| local                                              | status | note     |
|----------------------------------------------------|--------|----------|
| dentro da cerca HOME                               | `home` | —        |
| dentro da cerca OFFICE (também dentro de CAMPUS)   | `work` | `office` |
| dentro de CAMPUS, fora de OFFICE                   | `work` | `campus` |
| fora das três cercas                               | `out`  | —        |

OFFICE fica totalmente dentro de CAMPUS (o prédio do escritório está no campus). O campo `note` carrega a distinção office/campus; o roteamento de contas usa o `status`, então as duas zonas de trabalho roteiam igual.

### 1. Pré-requisitos

- Daemon acessível pelo celular:
  - `NINA_HTTP_HOST=0.0.0.0` e `NINA_API_KEY=...` no `.env`
  - Celular na mesma Wi-Fi ou VPN do host
  - IP da máquina no LAN (Linux): `ip -4 addr show | grep inet`
- MacroDroid instalado no Android com permissão de localização **"Permitir o tempo todo"** e otimização de bateria **desligada** para o app
- Teste rápido do celular: abra `http://<IP_HOST>:8765/health` num cliente HTTP que mande o header `X-API-Key`; deve retornar `{"status":"ok",...}`

### 2. Crie as 3 cercas

No MacroDroid → **Configurações → Geofences → +**:

1. **HOME** — centrada na sua casa, raio ~80–150 m
2. **CAMPUS** — centrada no local de trabalho, raio largo o suficiente para cobrir o campus inteiro (geralmente 300–800 m)
3. **OFFICE** — centrada no prédio do seu escritório, raio 30–80 m (fica dentro de CAMPUS)

Use exatamente esses nomes — as macros abaixo referenciam considerando maiúsculas/minúsculas.

### 3. Variáveis reutilizáveis (recomendado)

Crie duas variáveis globais no MacroDroid para não chumbar valor em toda macro:

- `nina_host` (string) — ex.: `192.168.1.10:8765`
- `nina_api_key` (string) — sua `NINA_API_KEY`

Em toda action HTTP a URL fica `http://[nina_host]/presence/<status>?note=<note>` e o header fica `X-API-Key: [nina_api_key]`.

### 4. Modelo de action HTTP

Toda macro usa a mesma action: **Conectividade → Requisição HTTP**.

- **Método**: POST
- **URL**: `http://[nina_host]/presence/<status>?note=<note>`
- **Headers**: `X-API-Key: [nina_api_key]`
- **Corpo**: vazio
- Marque "Aguardar resposta" só se quiser ser notificado de falha

### 5. As seis macros

Crie uma macro para cada transição. Cada uma tem um único gatilho, restrição opcional, e a action HTTP acima.

#### Nina presence — Home in

- **Gatilho**: Geofence → Entrou → HOME
- **Action**: POST `http://[nina_host]/presence/home`

#### Nina presence — Home out

- **Gatilho**: Geofence → Saiu → HOME
- **Restrição**: Fora de CAMPUS, Fora de OFFICE
- **Action**: POST `http://[nina_host]/presence/out`

#### Nina presence — Office in

- **Gatilho**: Geofence → Entrou → OFFICE
- **Action**: POST `http://[nina_host]/presence/work?note=office`

#### Nina presence — Office out

- **Gatilho**: Geofence → Saiu → OFFICE
- **Restrição**: Dentro de CAMPUS
- **Action**: POST `http://[nina_host]/presence/work?note=campus`

#### Nina presence — Campus in

- **Gatilho**: Geofence → Entrou → CAMPUS
- **Restrição**: Fora de OFFICE
- **Action**: POST `http://[nina_host]/presence/work?note=campus`

#### Nina presence — Campus out

- **Gatilho**: Geofence → Saiu → CAMPUS
- **Restrição**: Fora de HOME
- **Action**: POST `http://[nina_host]/presence/out`

As restrições resolvem a sobreposição: quando você sai do OFFICE você ainda está no CAMPUS, então mantém `work` (a note só flipa de `office` para `campus`). Quando sai do CAMPUS, cai para `out` — a menos que HOME já tenha assumido.

### 6. Verificação

Com o daemon rodando:

```bash
watch -n 2 'curl -s -H "X-API-Key: $NINA_API_KEY" http://127.0.0.1:8765/presence'
```

Atravesse as cercas e veja o status + note virarem em tempo real. A mesma checagem do celular (abrir `/presence` num cliente HTTP) também serve.

### 7. Dicas

- **Bootstrap inicial** — o Android às vezes não dispara o "enter" para uma cerca onde você já estava quando ela foi criada. Saia e volte uma vez para semear.
- **Otimização de bateria** — o Android pode estrangular callbacks de geofence. Libere o MacroDroid em **Configurações → Apps → MacroDroid → Bateria → Sem restrições**.
- **Override manual** — deixe `nina presence work` no console ou `/presence dnd` no Telegram à mão, para os casos em que a automação erra (ex.: trabalhando do café).
- **DND por localização** — `dnd` foi deixado de fora deliberadamente; ele funciona melhor como sinal explícito (comando no Telegram, Modo de Foco do Android, ou macro disparada por evento da agenda).

## Comandos slash

O daemon expõe `/command` para comandos textuais, espelhando o que o bot do Telegram aceita. Útil para integrações pontuais e scripts.

```bash
curl -X POST http://127.0.0.1:8765/command \
  -H "X-API-Key: $NINA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command": "/presence work note:campus"}'
```

Comandos suportados:

| Comando                          | Efeito                                       |
|----------------------------------|----------------------------------------------|
| `/presence <status> [note:...]`  | Define presença (mesmos status do enum)      |
| `/status`                        | Retorna presença + contexto do dia útil      |
| `/health`                        | Liveness check                               |
| `/memo <texto>`                  | Cria um memo                                 |
| `/activity <texto>`              | Registra atividade passada                   |

Os mesmos comandos funcionam no bot do Telegram — basta enviar como mensagem normal.
