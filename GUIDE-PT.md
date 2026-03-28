# Nina — Guia de Comandos

Referência completa de todos os comandos da Nina, disponíveis tanto no **console** quanto no **bot do Telegram**.

Os comandos podem ser digitados diretamente no console (ex: `presence office`) ou enviados ao bot com `/` no início (ex: `/presence office`). No console, a sintaxe `/comando` também funciona.

Texto livre (linguagem natural) é interpretado pela LLM em ambas as interfaces.

---

## presence

Ver ou definir seu status de presença atual.

```
presence
presence <status>
presence <status> <nota>
```

| Status | Significado |
|---|---|
| `home` | Trabalhando em casa |
| `office` | No escritório |
| `out` | Na rua / em movimento |
| `dnd` | Não perturbe — foco total |

**Exemplos:**
```
presence
# office — no escritório  (desde 09:30)

presence home
# ✓ home — em casa

presence dnd "finalizando o relatório"
```

**Efeito nas notificações:** Quando `dnd` está ativo, as notificações ficam em fila e são entregues quando você sair do `dnd`.

---

## schedule

Cria um evento na agenda diretamente, sem LLM. Instantâneo e confiável.

```
schedule <quando> <título> [duração]
```

**Formatos de data/hora:**

| Formato | Exemplo | Significado |
|---|---|---|
| `HH:MM` | `16:00` | Hoje às 16:00 |
| `hoje HH:MM` | `hoje 16:00` | Hoje às 16:00 |
| `amanhã HH:MM` | `amanhã 09:00` | Amanhã às 09:00 |
| `DD/MM HH:MM` | `29/03 14:00` | 29 de março às 14:00 |
| `DD/MM/AAAA HH:MM` | `15/04/2024 10:00` | 15 de abril de 2024 às 10:00 |

**Formatos de duração:** `1h` · `30min` · `1h30` · `1h30min` · `90min` (padrão: 60min)

**Exemplos:**
```
schedule 16:00 Reunião com Sandra 1h
schedule hoje 16:00 Consultoria 30min
schedule amanhã 09:00 Consulta médica
schedule 29/03 14:00 Treinamento 2h
schedule 15/04/2024 10:00 Reunião anual 1h30
```

O horário de início é arredondado para baixo até o bloco de 15 minutos mais próximo. O horário de término é arredondado para cima. O evento é criado na conta de calendário associada à sua presença atual (`profile`).

---

## workdays

Mostra seu horário de trabalho configurado.

```
workdays
```

**Exemplo de saída:**
```
  Timezone: America/Cuiaba

  Segunda     09:00 → 18:00
  Terça       09:00 → 18:00
  Quarta      09:00 → 18:00
  Quinta      09:00 → 18:00
  Sexta       09:00 → 18:00
  Sábado      —
  Domingo     —
```

Para alterar o horário, use texto livre: `"meu horário de trabalho é de segunda a sexta das 9h às 18h"`.

---

## timezone

Ver ou definir o timezone usado para o horário de trabalho e eventos de calendário.

```
timezone
timezone <tz>
```

**Exemplos:**
```
timezone
# Timezone: America/Cuiaba

timezone America/Sao_Paulo
# ✓ Timezone definido para: America/Sao_Paulo
```

Usa nomes de timezone IANA. Lista completa em [iana.org/time-zones](https://www.iana.org/time-zones).

---

## context

Mostra seu contexto de trabalho atual — combina status de presença e horário de trabalho.

```
context
```

**Exemplo de saída:**
```
  no escritório
  ✓ horário de trabalho  ·  presença: office
```

Possíveis rótulos de contexto: `no escritório` · `home office` · `em movimento` · `foco total` · `hora extra` · `trabalhando no fim de semana` · `fora do horário`.

---

## profile

Ver ou configurar quais contas Google ficam ativas para cada status de presença.

```
profile
profile <status>
```

**Exemplos:**
```
profile
# Perfil de contas:
#
# home — em casa
#   gmail:    pessoal@gmail.com
#   calendar: pessoal@gmail.com
#
# office — no escritório
#   gmail:    trabalho@empresa.com
#   calendar: trabalho@empresa.com

profile office
```

Para configurar os mapeamentos, use texto livre:
```
no escritório usar trabalho@empresa.com para o calendário
em casa usar pessoal@gmail.com
```

---

## notify

Ver ou configurar as notificações de calendário.

```
notify
notify reminder <minutos>
notify days <n>
```

| Sub-comando | Descrição |
|---|---|
| `notify` | Ver configurações atuais |
| `notify reminder 10` | Definir lembrete para 10 minutos antes do evento |
| `notify days 14` | Monitorar novos eventos até 14 dias à frente |

**Exemplos:**
```
notify
# Lembrete: 15 min antes  |  Monitorar: 7 dias à frente

notify reminder 10
# ✓ Lembrete definido para 10 minutos antes.

notify days 30
# ✓ Janela de monitoramento definida para 30 dias.
```

**O que a Nina notifica:**
- 🔔 **Lembrete** — X minutos antes de um evento começar (todas as contas)
- 📅 **Novo evento** — alguém agendou algo na sua agenda
- ✏️ **Evento alterado** — um evento foi movido ou renomeado
- ❌ **Evento cancelado** — um evento foi removido

As notificações são suprimidas durante `dnd` e fora do horário de trabalho. Ao retornar ao trabalho ou sair do `dnd`, as notificações em fila são entregues em lote.

---

## lang

Ver ou definir o idioma da interface.

```
lang
lang <código>
```

Códigos suportados: `en` · `pt`

**Exemplos:**
```
lang
# Idioma atual: pt

lang en
# ✓ Language changed to: en
```

Alterar o idioma atualiza tanto as mensagens do console quanto as descrições dos comandos do bot no Telegram.

---

## health

Mostra o status e uptime do daemon.

```
health
```

**Exemplo de saída:**
```
  status   ok
  uptime   02:14:35
```

---

## Texto livre (LLM)

No console e no bot do Telegram, você pode digitar qualquer coisa em linguagem natural. A Nina tenta entender sua intenção nesta ordem:

1. **Bloqueio de agenda** — cria um evento no calendário
2. **Mudança de presença** — atualiza seu status de presença
3. **Mudança de horário de trabalho** — atualiza workdays ou timezone
4. **Mapeamento de perfil** — associa contas a uma presença

**Exemplos:**
```
acabei de chegar no escritório
→ ✓ office — no escritório

estou em reunião com a Sandra por 1 hora
→ ✓ Reunião com Sandra  10:00 → 11:00

preciso atender a professora Vera Lucia às 16:00 por uma hora
→ ✓ Atendimento Vera Lucia  16:00 → 17:00

meu horário de trabalho é de segunda a sexta das 9h às 18h
→ ✓ Horário atualizado.

no escritório usar trabalho@empresa.com para o calendário
→ ✓ Perfil atualizado.
```

Uma única mensagem pode conter múltiplos eventos de calendário:
```
estou em reunião agora por 30 minutos e às 16:00 tenho uma consultoria por 1 hora
→ ✓ Reunião  10:15 → 10:45
→ ✓ Consultoria  16:00 → 17:00
```

---

## Comandos exclusivos do console

### exit / quit

Sair do console interativo.

```
exit
quit
```

### help

Mostrar comandos disponíveis.

```
help
help <comando>
```

---

## Comandos exclusivos do bot

### /start

Exibe uma mensagem de boas-vindas e seu chat ID do Telegram (necessário para `TELEGRAM_OWNER_ID` no `.env`).

### /help

Lista todos os comandos disponíveis no bot.
