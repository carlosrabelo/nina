# Nina — skills (domínios de comportamento)

Este documento descreve os **pacotes de comportamento** em [`nina/skills/`](nina/skills/): o que cada domínio faz, como é acionado e onde está o código. Complementa a [referência de comandos](GUIDE-PT.md) (CLI, HTTP, integrações).

A versão em inglês está em [SKILL.md](SKILL.md).

---

## Como as skills ligam ao produto

- O **bot Telegram** e o **`nina console`** (com o daemon a correr) interpretam texto livre num pipeline partilhado: gates por padrões locais → **router LLM** opcional → execução por domínio.
- Os **comandos exploratórios da CLI** (`nina gmail …`, `nina calendar …`, etc.) vivem em [`nina/cli/`](nina/cli/) e **não** são o mesmo que estas skills — são utilitários de desenvolvimento.

---

## Roteamento de intenções (resumo)

Ver [`nina/core/intent/router.py`](nina/core/intent/router.py) para a lista completa de domínios.

Pipeline em traços gerais:

1. **Camada 1** — `try_action` por skill (ex.: memo), quando existir.
2. **Camada 2** — [`local_router.py`](nina/core/intent/local_router.py): regex e NLP leve, sem LLM.
3. **Camada 3** — LLM devolve um `RouterIntent` (domínio + campos).
4. **Camada 4** — segunda passagem LLM só para **blocking** e **workdays** quando necessário.

Domínios frequentemente resolvidos cedo (quando os padrões batem) incluem **presence**, **memo**, **calendar** (leitura), **notifications** e partes de **profile**. **Blocking** e **workdays** costumam precisar do interpretador dedicado.

---

## Catálogo de skills

Ordem alfabética pelo id do domínio (ver [AGENTS.md](AGENTS.md)).

### `activity_log` — atividades estruturadas na agenda

- **Objetivo:** Registar ou consultar atividades passadas apoiadas no Google Calendar (distinto de “listar os meus eventos” genérico).
- **Acionadores:** Domínio `activity_log` no router; sinais locais em [`activity_log/patterns.py`](nina/skills/activity_log/patterns.py).
- **Código:** [`nina/skills/activity_log/`](nina/skills/activity_log/) (`interpreter`, `google_reader`, `google_writer`, `models`).
- **Armazenamento:** Lê/escreve no **Google Calendar**; usa as contas de calendário do perfil como nos outros fluxos de agenda.

---

### `blocking` — ocupar tempo na agenda

- **Objetivo:** Criar um evento de bloqueio / foco no Google Calendar quando há hora ou duração explícita (“bloquear 14h”, “reunião por 1 hora”).
- **Acionadores:** Domínio `blocking` no router; segunda chamada LLM em [`blocking.py`](nina/skills/calendar/blocking.py); HTTP [`POST /schedule`](nina/core/daemon/http.py) no daemon.
- **Código:** [`nina/skills/calendar/blocking.py`](nina/skills/calendar/blocking.py), [`schedule_parser.py`](nina/skills/calendar/schedule_parser.py) quando aplicável.
- **Armazenamento:** Escrita via **API Google Calendar** (mesma stack que a leitura).

---

### `calendar` (leitura) — perguntas à agenda

- **Objetivo:** Só leitura: listar eventos numa janela, pesquisar por palavra-chave, sugerir **intervalos livres** (não cria eventos aqui).
- **Acionadores:** Linguagem natural (ex.: “o que tenho amanhã”, “eventos com dentista”, “livre à tarde”); domínio `calendar` no router; padrões locais em [`try_calendar`](nina/core/intent/local_router.py).
- **Código:** [`nina/skills/calendar/execute.py`](nina/skills/calendar/execute.py), [`interpreter.py`](nina/skills/calendar/interpreter.py), e o cliente Google [`nina/integrations/google/calendar/client.py`](nina/integrations/google/calendar/client.py).
- **Escolha de conta:** Usa [`Profile.best_calendar_accounts`](nina/skills/profile/models.py) com a mensagem e a presença atual.
- **Armazenamento:** Lê o **Google Calendar**; a base Nina não é a fonte de verdade dos eventos em tempo real.

---

### `gmail_label` — etiquetas Gmail por remetente

- **Objetivo:** Manter regras por conta que associam um remetente (dominio ou endereco) a uma etiqueta de **utilizador** do Gmail; **`nina gmail_label process`** ingere metadados da inbox em **`email_messages`**, aplica essas regras no Gmail e pode mostrar pedidos no Telegram para remetentes novos de alto volume. O **`nina gmail_label infer-rules`** so varre o correio para inserir novas **`email_sender_rules`** a partir de etiquetas de utilizador no Gmail (sem escrita em `email_messages`). Na CLI, **`process`** e **`infer-rules`** aceitam **`-v` / `--verbose`** (progresso no stderr); o **`process`** tambem aceita **`--days`** e **`--max-per-account`** para backfill. Linhas com **`tagged_at`** definido sao ignoradas cedo (sem upsert de cabecalho). Etiquetas devem comecar com **`@`** ou **`!`**. O **`dismiss-all`** limpa todas as sugestoes abertas de uma vez.
- **Acionadores:** Dominio do router LLM `gmail_label`. Corre pelo **agendador** (job `gmail_label` quando o bot Telegram esta configurado), **`nina gmail_label process`** (CLI ou daemon), **`nina gmail_label infer-rules`**, **`nina gmail_label rules`** (listar regras gravadas), **`/gmail_label`** no Telegram e **`gmail_label`** no `nina console`.
- **Codigo:** [`nina/skills/gmail_label/`](nina/skills/gmail_label/) (`execute.py`, [`interpreter.py`](nina/skills/gmail_label/interpreter.py)); tarefas em [`nina/tasks/`](nina/tasks/) ([`email_process.py`](nina/tasks/email_process.py), [`email_infer_rules.py`](nina/tasks/email_infer_rules.py)); integracao Gmail em [`nina/integrations/google/gmail/client.py`](nina/integrations/google/gmail/client.py).
- **Armazenamento:** Tabelas PostgreSQL em [`nina/core/store/repos/email_label.py`](nina/core/store/repos/email_label.py) — `email_messages`, `email_sender_rules`, `email_pending_labels`, `email_ignored_senders` (esquema em [`nina/core/store/db.py`](nina/core/store/db.py)).

---

### `health` — status e uptime do daemon

- **Objetivo:** Informar se o daemon esta a correr e ha quanto tempo.
- **Acionadores:** **`/health`** no Telegram, **`health`** no `nina console`, HTTP **`GET /health`**.
- **Codigo:** [`nina/skills/health/execute.py`](nina/skills/health/execute.py).
- **Armazenamento:** Nenhum (stateless — uptime calculado a partir do inicio do processo).

---

### `memo` — notas e lembretes

- **Objetivo:** Criar, listar, fechar ou dispensar memos; lembretes com data/hora resolvida.
- **Acionadores:** Frases tipo “memo …”, “me lembra …”; interpretador memo na camada 1; domínio `memo` no router.
- **Código:** [`nina/skills/memo/`](nina/skills/memo/) (`interpreter`).
- **Armazenamento:** Tabelas PostgreSQL em [`nina/core/store/repos/memo.py`](nina/core/store/repos/memo.py).

---

### `notifications` — com quanta antecedência avisar

- **Objetivo:** Configurar minutos antes dos eventos para lembrete e quantos dias à frente monitorizar a agenda por alterações.
- **Acionadores:** Linguagem natural (“avisa 30 minutos antes”, “dois dias de antecedência”); rotas HTTP do daemon onde existirem.
- **Código:** [`nina/skills/notifications/`](nina/skills/notifications/) (`store`, `interpreter`, `models`).
- **Armazenamento:** PostgreSQL `kv_state`.

---

### `presence` — onde está agora

- **Objetivo:** Estados `home` / `work` / `out` / `dnd` e uma `note` curta opcional (ex.: campus vs escritório).
- **Acionadores:** Linguagem natural no Telegram/console; HTTP `PUT /presence`, `POST /presence/{status}`; integrações tipo MacroDroid.
- **Código:** [`nina/skills/presence/`](nina/skills/presence/) (`models`, `store`, `interpreter`).
- **Armazenamento:** PostgreSQL `kv_state` (via `open_db` / helpers KV), não ficheiros JSON em produção.

---

### `profile` — que contas Google vão com cada presença

- **Objetivo:** Associar emails de Gmail e Calendar a cada estado de presença para a Nina escolher a conta certa nas ações Google.
- **Acionadores:** Linguagem natural (“no escritório usar work@empresa.com”); domínio `profile` no router.
- **Código:** [`nina/skills/profile/`](nina/skills/profile/) (`store`, `interpreter`, `models`).
- **Armazenamento:** PostgreSQL `kv_state`.

---

### `workdays` — horário semanal e fuso

- **Objetivo:** Definir horário de trabalho, almoço, folgas e fuso para contexto (não confundir com “cheguei ao trabalho”, que é `presence`).
- **Acionadores:** Domínio `workdays`; frases sobre “segunda a sexta 9–18”, mudança de timezone; interpretador LLM dedicado quando necessário.
- **Código:** [`nina/skills/workdays/`](nina/skills/workdays/) (`store`, `interpreter`, `checker`, `models`).
- **Armazenamento:** PostgreSQL `kv_state`.

---

## Pacotes relacionados (fora de `nina/skills/`)

- **Store core:** [`nina/core/store/`](nina/core/store/) — ligação PostgreSQL, migrações, repositórios para memos, actions, emails e `calendar_events` usados pelo daemon/agendador.
- **HTTP do daemon:** [`nina/core/daemon/http.py`](nina/core/daemon/http.py) — API REST que pode tocar em presence, workdays, schedule (`blocking`), notifications, etc.

Ao alterar comportamento, mantenha este ficheiro alinhado com [SKILL.md](SKILL.md), [GUIDE-PT.md](GUIDE-PT.md) e [README-PT.md](README-PT.md) — ver [AGENTS.md](AGENTS.md).
