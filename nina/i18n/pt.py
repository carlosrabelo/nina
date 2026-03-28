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
        "/context — contexto atual\n"
        "/lang — idioma atual\n"
        "/lang <código> — muda idioma (en|pt)\n\n"
        "📧 Gmail\n"
        "/unread — emails não lidos\n"
        "/latest — últimos emails recebidos\n\n"
        "📅 Calendar\n"
        "/events — próximos eventos\n\n"
        "💬 Telegram\n"
        "/dialogs — chats recentes\n"
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

    # ── llm interpreter ───────────────────────────────────────────────────────
    "llm.presence_set":    "✓ {status} — {label}",
    "llm.schedule_set":    "✓ Horário atualizado.",
    "llm.not_understood":  "Não entendi. Tente /presence ou /workdays.",
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

    # ── dialogs ───────────────────────────────────────────────────────────────
    "dialogs.none":   "Nenhum chat encontrado.",
    "dialogs.error":  "Erro: {error}",
    "dialogs.unread": " ({count} não lidas)",
}
