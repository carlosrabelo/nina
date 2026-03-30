STRINGS: dict[str, str] = {
    # ── start / help ──────────────────────────────────────────────────────────
    "start.greeting": (
        "Olá! Sou a Nina, sua assistente pessoal.\n\n"
        "Use /help para ver os comandos disponíveis.\n\n"
        "Seu chat ID: {chat_id}"
    ),
    "start.lang_detected": "Idioma detectado: {lang}. Use /lang para alterar.",
    "lang.current":  "Idioma atual: {code}",
    "lang.set_ok":   "✓ Idioma alterado para: {code}",
    "lang.invalid":  "Idioma desconhecido '{code}'. Disponíveis: {supported}",
    "help.text": (
        "Comandos disponíveis:\n\n"
        "🤖 Nina\n"
        "/presence — presença atual\n"
        "/presence <status> — muda presença (home|office|out|dnd)\n"
        "/health — status do daemon\n"
        "/workdays — horário de trabalho\n"
        "/timezone — timezone atual\n"
        "/context — contexto atual\n"
        "/lang — idioma atual\n"
        "/lang <código> — muda idioma (en|pt)\n"
        "/profile — contas associadas por presença\n"
    ),

    # ── presence ──────────────────────────────────────────────────────────────
    "presence.label.home":   "em casa",
    "presence.label.office": "no escritório",
    "presence.label.out":    "na rua / em movimento",
    "presence.label.dnd":    "não perturbe",
    "presence.current":      "{status} — {label}\nDesde: {since}{note}",
    "presence.since_prefix": "desde",
    "presence.set_ok":       "✓ {status} — {label}",
    "presence.invalid":      "Status inválido. Use: {valid}",

    # ── health ────────────────────────────────────────────────────────────────
    "health.online": "✓ Nina online\nUptime: {uptime}",

    # ── workdays ──────────────────────────────────────────────────────────────
    "workdays.timezone":         "Timezone: {tz}",
    "workdays.timezone_set":     "✓ Timezone definido para: {tz}",
    "workdays.timezone_invalid": "Timezone desconhecido '{tz}'. Use um nome válido, ex: America/Cuiaba.",
    "workdays.hours":    "{start} → {end}",
    "workdays.off":      "—",
    "day.0": "Segunda",
    "day.1": "Terça",
    "day.2": "Quarta",
    "day.3": "Quinta",
    "day.4": "Sexta",
    "day.5": "Sábado",
    "day.6": "Domingo",

    # ── context ───────────────────────────────────────────────────────────────
    "context.label.dnd":          "foco total",
    "context.label.out":          "em movimento",
    "context.label.weekend_work": "trabalhando no fim de semana",
    "context.label.overtime":     "hora extra",
    "context.label.home_office":  "home office",
    "context.label.office":       "no escritório",
    "context.label.off_hours":    "fora do horário",
    "context.flag.overtime":      "hora extra",
    "context.flag.weekend":       "fim de semana",
    "context.in_work_time":       "✓ horário de trabalho",
    "context.off_hours":          "✗ fora do horário",

    # ── gmail ─────────────────────────────────────────────────────────────────
    "unread.none":    "Nenhum email não lido.",
    "unread.error":   "Erro: {error}",
    "unread.item":    "[{account}]\nDe: {sender}\nAssunto: {subject}\nPreview: {snippet}",
    "latest.none":    "Nenhum email encontrado.",
    "latest.error":   "Erro: {error}",
    "latest.from":    "De: {sender}",
    "latest.subject": "Assunto: {subject}",

    # ── calendar ──────────────────────────────────────────────────────────────
    "events.no_accounts": "Nenhuma conta autenticada.",
    "events.none":        "(sem eventos próximos)",
    "events.error":       "Erro em {account}: {error}",
    "events.not_found":   "Nenhum evento encontrado.",
    "events.location":    "Local: {location}",

    # ── calendar blocking ─────────────────────────────────────────────────────
    "calendar.no_events":  "Nenhum evento próximo encontrado.",
    "blocking.created":    "✓ {title}\n{date} · {start} → {end}\nConta: {account}",
    "blocking.conflict":   "⚠️ Conflito: {titles}",
    "blocking.no_account": "Nenhuma conta de calendar configurada para a presença atual. Configure com /profile.",

    # ── profile ───────────────────────────────────────────────────────────────
    "profile.title":            "Perfil de contas:",
    "profile.no_accounts":      "(não configurado)",
    "profile.gmail":            "gmail:    {accounts}",
    "profile.calendar":         "calendar: {accounts}",
    "profile.set_ok":           "✓ Perfil atualizado.",
    "profile.empty":            "Nenhuma conta configurada ainda.\nEnvie algo como: \"no escritório usar work@empresa.com\"",
    "help.profile":             "  profile   Ver contas associadas a cada presença\n  profile <presença>   Ver para uma presença específica",
    "cmd.profile":              "Ver perfil de contas por presença",

    # ── llm interpreter ───────────────────────────────────────────────────────
    "llm.presence_set":    "✓ {status} — {label}",
    "llm.schedule_set":    "✓ Horário atualizado.",
    "llm.not_understood":  "Não entendi.",
    "llm.unavailable":     "LLM não configurada. Defina LLM_MODEL e a chave de API no .env.",

    # ── console ───────────────────────────────────────────────────────────────
    "console.intro":          "Console Nina  —  digite 'help' para os comandos, 'exit' para sair.\nO daemon precisa estar rodando: nina daemon\n",
    "console.bye":            "Até logo.",
    "console.unknown_cmd":    "  Comando desconhecido: '{cmd}'. Digite 'help' para ver os comandos.",
    "console.health.status":  "  status   {value}",
    "console.health.uptime":  "  uptime   {value}",
    "console.context.presence": "  {work}  ·  presença: {presence}",
    "help.presence":          "  presence                    Ver presença atual\n  presence <status>           Definir presença  (home | office | out | dnd)\n  presence <status> <nota>    Definir com nota",
    "help.health":            "  health   Ver status e uptime do daemon",
    "help.workdays":          "  workdays   Ver horário de trabalho",
    "help.timezone":          "  timezone              Ver timezone atual\n  timezone <tz>         Definir timezone  (ex: America/Cuiaba)",
    "cmd.timezone":           "Ver ou definir timezone",
    "help.context":           "  context   Ver contexto de trabalho atual (presença × horário)",
    "help.lang":              "  lang              Ver idioma atual\n  lang <código>     Mudar idioma  (en | pt)",
    "help.exit":              "  exit / quit   Sair do console",

    # ── schedule command ──────────────────────────────────────────────────────
    "schedule.created":  "✓ {title}\n{date} · {start} → {end}\nConta: {account}",
    "schedule.conflict": "⚠️ Conflito: {titles}",
    "schedule.no_account": "Nenhuma conta de calendar configurada para a presença atual. Configure com /profile.",
    "schedule.parse_error": (
        "Não entendi o formato. Use:\n"
        "  schedule HH:MM <título> [duração]\n"
        "  schedule hoje 16:00 Reunião 1h\n"
        "  schedule amanhã 10:00 Consulta 30min\n"
        "  schedule 29/03 14:00 Treinamento 2h"
    ),
    "help.schedule": (
        "  schedule HH:MM <título> [duração]\n"
        "  schedule hoje|amanhã HH:MM <título> [duração]\n"
        "  schedule DD/MM HH:MM <título> [duração]\n"
        "  schedule DD/MM/AAAA HH:MM <título> [duração]\n"
        "\n"
        "  Duração: 1h  30min  1h30  (padrão: 60min)"
    ),
    "cmd.schedule":  "Agendar evento no calendário diretamente",

    # ── bot command descriptions (shown in Telegram autocomplete) ─────────────
    "cmd.start":     "Iniciar a Nina",
    "cmd.help":      "Listar comandos disponíveis",
    "cmd.lang":      "Ver ou mudar idioma",
    "cmd.presence":  "Ver ou definir presença",
    "cmd.health":    "Status e uptime do daemon",
    "cmd.workdays":  "Ver horário de trabalho",
    "cmd.context":   "Contexto de trabalho atual",
    "cmd.unread":    "Emails não lidos",
    "cmd.latest":    "Últimos emails recebidos",
    "cmd.events":    "Próximos eventos do calendário",
    "cmd.dialogs":   "Chats recentes do Telegram",

    # ── notifications ─────────────────────────────────────────────────────────
    "notify.config":         "Lembrete: {reminder_minutes} min antes  |  Monitorar: {watch_days} dias à frente",
    "notify.reminder_set":   "✓ Lembrete definido para {minutes} minutos antes.",
    "notify.days_set":       "✓ Janela de monitoramento definida para {days} dias.",
    "notify.invalid_value":  "Valor inválido '{value}'. Deve ser um número inteiro positivo.",
    "notify.usage":          "  notify                       Ver configurações de notificação\n  notify reminder <min>        Definir antecedência do lembrete (minutos)\n  notify days <n>              Definir janela de monitoramento (dias)",
    "help.notify":           "  notify                       Ver configurações de notificação\n  notify reminder <min>        Definir antecedência do lembrete (minutos)\n  notify days <n>              Definir janela de monitoramento (dias)",
    "cmd.notify":            "Ver ou configurar notificações",

    # ── memo ──────────────────────────────────────────────────────────────────
    "memo.saved":       "✓ Memo salvo.",
    "memo.remind_set":  "✓ Lembrete para {date} — {subject}",
    "memo.done":        "✓ Memo marcado como concluído.",
    "memo.dismissed":   "✓ Memo descartado.",
    "memo.not_found":   "Memo não encontrado.",
    "memo.none_open":   "Nenhum memo aberto.",
    "memo.item":        "[{index}] {text}{due}",
    "memo.due":         "  Vence: {date}",
    "memo.usage":       "  memo <texto>             Salvar um novo memo\n  memo <texto> due <data>  Salvar com data de vencimento\n  memos                    Listar memos abertos\n  memo done <id>           Marcar como concluído\n  memo dismiss <id>        Descartar memo",
    "help.memo":        "  memo <texto>             Salvar um novo memo\n  memo <texto> due <data>  Salvar com data de vencimento\n  memos                    Listar memos abertos\n  memo done <id>           Marcar como concluído\n  memo dismiss <id>        Descartar",
    "cmd.memo":         "Salvar ou listar memos",
    "cmd.memos":        "Listar memos abertos",

    # ── dialogs ───────────────────────────────────────────────────────────────
    "dialogs.none":   "Nenhum chat encontrado.",
    "dialogs.error":  "Erro: {error}",
    "dialogs.unread": " ({count} não lidas)",
}
