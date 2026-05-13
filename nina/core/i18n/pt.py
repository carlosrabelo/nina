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
        "Comandos disponiveis:\n\n"
        "/context — contexto atual\n"
        "/gmail_label — sugestoes remetente → etiqueta\n"
        "/health — status do daemon\n"
        "/lang — idioma atual\n"
        "/lang <codigo> — muda idioma (en|pt)\n"
        "/memo — notas e lembretes\n"
        "/presence — presenca atual\n"
        "/presence <status> — muda presenca (home|work|out|dnd)\n"
        "/profile — contas associadas por presenca\n"
        "/schedule — agendar evento no calendario\n"
        "/workdays — horario de trabalho\n"
        "/timezone — timezone atual\n\n"
        "/help <comando> — ver sub-opcoes de um comando"
    ),

    # ── presence ──────────────────────────────────────────────────────────────
    "presence.label.home":   "em casa",
    "presence.label.work": "no trabalho",
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
    "workdays.lunch":    "almoço: {start} → {end}",
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
    "context.label.lunch":        "horário de almoço",
    "context.label.weekend_work": "trabalhando no fim de semana",
    "context.label.overtime":     "hora extra",
    "context.label.home_office":  "home office",
    "context.label.office":       "no escritório",
    "context.label.off_hours":    "fora do horário",
    "context.flag.overtime":      "hora extra",
    "context.flag.weekend":       "fim de semana",
    "context.in_work_time":       "✓ horário de trabalho",
    "context.lunch_time":         "🍽️ horário de almoço",
    "context.off_hours":          "✗ fora do horário",
    "lunch.reminder":             "🍽️ Hora de almoçar! Não se esqueça de fazer uma pausa.",

    # ── gmail ─────────────────────────────────────────────────────────────────
    "unread.none":    "Nenhum email não lido.",
    "unread.error":   "Erro: {error}",
    "unread.item":    "[{account}]\nDe: {sender}\nAssunto: {subject}\nPreview: {snippet}",
    "latest.none":    "Nenhum email encontrado.",
    "latest.error":   "Erro: {error}",
    "latest.from":    "De: {sender}",
    "latest.subject": "Assunto: {subject}",

    # ── gmail label learning (por conta Gmail) ────────────────────────────────
    "gmail_label.suggest_telegram": (
        "Nina -- novo padrao de remetente\n"
        "Conta: {account}\n"
        "De: {sender}\n"
        "Assunto exemplo: {subject}\n"
        "Visto (~30d): {count}\n\n"
        "Defina a etiqueta (so nesta conta):\n"
        "/gmail_label {full_id} Sua/Etiqueta\n"
        "Ignorar esse remetente para sempre:\n"
        "/gmail_label dismiss {full_id}\n"
        "(id curto: {short_id}...)"
    ),
    "gmail_label.usage": (
        "/gmail_label — lista sugestões abertas\n"
        "/gmail_label <id> <etiqueta> — grava etiqueta para o remetente nessa conta\n"
        "/gmail_label rule add <conta> <remetente> <etiqueta> — adicionar regra manual\n"
        "/gmail_label dismiss <id> — ignora a sugestão (adiciona remetente à lista de ignorados)\n"
        "/gmail_label dismiss-all — ignora todas as sugestões abertas\n"
        "/gmail_label ignore list — listar remetentes ignorados\n"
        "/gmail_label ignore add <conta> <remetente> — adicionar à lista de ignorados\n"
        "/gmail_label ignore remove <conta> <remetente> — remover da lista de ignorados\n"
        "A etiqueta deve começar com @ (ex.: @Financeiro).\n"
        "Use pelo menos 8 caracteres do id da sugestão."
    ),
    "gmail_label.no_pending": "Nenhuma sugestão de remetente aberta.",
    "gmail_label.pending_header": "Sugestões abertas (regras por conta):",
    "gmail_label.pending_line": "· [{account}] {sender}\n  id: {full_id}\n  ocorrências: {hits}  exemplo: {subject}",
    "gmail_label.pending_not_found": "Nenhuma sugestão aberta com esse id.",
    "gmail_label.ambiguous_id": "Esse prefixo de id bate com mais de uma linha — cole mais caracteres.",
    "gmail_label.id_too_short": "Use pelo menos 8 caracteres do id da sugestão.",
    "gmail_label.label_empty": "O nome da etiqueta não pode ser vazio.",
    "gmail_label.dismiss_ok": (
        "Sugestão ignorada para {sender}.\n"
        "Emails futuros desse remetente não vão gerar sugestões."
    ),
    "gmail_label.dismiss_all_ok": (
        "{count} sugestão(ões) ignorada(s)."
    ),
    "gmail_label.label_must_at": (
        "A etiqueta deve começar com @ (ex.: @Financeiro)."
    ),
    "gmail_label.rule_added": (
        "✓ Regra adicionada: {sender} → [{label}] em {account}."
    ),
    "gmail_label.ignore_added": (
        "Remetente ignorado adicionado: [{account}] {sender}."
    ),
    "gmail_label.ignore_removed": (
        "Removido da lista de ignorados: [{account}] {sender}."
    ),
    "gmail_label.ignore_not_found": (
        "Remetente não encontrado na lista de ignorados."
    ),
    "gmail_label.ignore_header": "Remetentes ignorados (não vão gerar sugestões):",
    "gmail_label.ignore_empty": "Nenhum remetente ignorado.",
    "gmail_label.ignore_usage": (
        "/gmail_label ignore list — listar remetentes ignorados\n"
        "/gmail_label ignore add <conta> <remetente> — adicionar à lista de ignorados\n"
        "/gmail_label ignore remove <conta> <remetente> — remover da lista de ignorados"
    ),
    "gmail_label.taught_ok": (
        "✓ Regra gravada: {sender} → [{label}] em {account}.\n"
        "Aplicada em {applied} mensagem(ns) que a Nina já tinha registado."
    ),

    # ── calendar ──────────────────────────────────────────────────────────────
    "events.no_accounts": "Nenhuma conta autenticada.",
    "events.none":        "(sem eventos próximos)",
    "events.error":       "Erro em {account}: {error}",
    "events.not_found":   "Nenhum evento encontrado.",
    "events.location":    "Local: {location}",

    # ── calendar blocking ─────────────────────────────────────────────────────
    "calendar.no_events":  "Nenhum evento próximo encontrado.",
    "calendar.free_busy_header": "Intervalos livres (≥30 min):",
    "calendar.free_slot": "{start} → {end}",
    "calendar.no_free_slot": "Sem intervalos livres de pelo menos 30 minutos nesta janela.",
    "blocking.created":    "✓ {title}\n{date} · {start} → {end}\nConta: {account}",
    "blocking.conflict":   "⚠️ Conflito: {titles}",
    "blocking.no_account": "Nenhuma conta de calendar configurada para a presença atual. Configure com /profile.",

    # ── profile ───────────────────────────────────────────────────────────────
    "profile.title":            "Perfil de contas:",
    "profile.no_accounts":      "(não configurado)",
    "profile.gmail":            "gmail:    {accounts}",
    "profile.calendar":         "calendar: {accounts}",
    "profile.set_ok":           "Perfil atualizado.",
    "profile.empty":            "Nenhuma conta configurada ainda.\nEnvie algo como: \"no escritorio usar work@empresa.com\"",
    "cmd.profile":              "Ver perfil de contas por presenca",

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
    "console.context.presence": "  {work}  ·  presenca: {presence}",
    "cmd.timezone":           "Ver ou definir timezone",

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
    "cmd.schedule":  "Agendar evento no calendario diretamente",

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
    "notify.usage":          "  notify                       Ver configuracoes de notificacao\n  notify reminder <min>        Definir antecedencia do lembrete (minutos)\n  notify days <n>              Definir janela de monitoramento (dias)",
    "cmd.notify":            "Ver ou configurar notificacoes",

    # ── memo ──────────────────────────────────────────────────────────────────
    "memo.saved":       "✓ Memo salvo.",
    "memo.remind_set":  "✓ Lembrete para {date} — {subject}",
    "memo.done":        "✓ Memo marcado como concluído.",
    "memo.dismissed":   "✓ Memo descartado.",
    "memo.not_found":   "Memo não encontrado.",
    "memo.none_open":   "Nenhum memo aberto.",
    "memo.item":        "[{index}] {text}{due}",
    "memo.due":         "  Vence: {date}",
    "memo.usage":       "  memo <texto>             Salvar um novo memo\n  memo <texto> due <data>  Salvar com data de vencimento\n  memos                    Listar memos abertos\n  memo done <id>           Marcar como concluido\n  memo dismiss <id>        Descartar memo",
    "cmd.memo":         "Salvar ou listar memos",
    "cmd.memos":        "Listar memos abertos",
    "cmd.gmail_label":   "Ensinar etiquetas Gmail por conta",

    # ── dialogs ───────────────────────────────────────────────────────────────
    "dialogs.none":   "Nenhum chat encontrado.",
    "dialogs.error":  "Erro: {error}",
    "dialogs.unread": " ({count} nao lidas)",

    # ── /help <command> — per-command help (alphabetical) ──────────────────────
    "help.context": (
        "/context — contexto de trabalho atual"
    ),
    "help.gmail_label": (
        "/gmail_label — listar sugestoes abertas\n"
        "/gmail_label <id> <etiqueta> — gravar etiqueta para o remetente nessa conta\n"
        "/gmail_label rule add <conta> <remetente> <etiqueta> — adicionar regra manual\n"
        "/gmail_label dismiss <id> — ignorar sugestao (adiciona remetente aos ignorados)\n"
        "/gmail_label dismiss-all — ignorar todas as sugestoes abertas\n"
        "/gmail_label ignore list — listar remetentes ignorados\n"
        "/gmail_label ignore add <conta> <remetente> — adicionar aos ignorados\n"
        "/gmail_label ignore remove <conta> <remetente> — remover dos ignorados\n\n"
        "Etiquetas devem comecar com @ (ex.: @Financeiro).\n"
        "Use pelo menos 8 caracteres do id da sugestao."
    ),
    "help.health": (
        "/health — status e uptime do daemon"
    ),
    "help.lang": (
        "/lang — idioma atual\n"
        "/lang <codigo> — mudar idioma (en|pt)"
    ),
    "help.memo": (
        "/memo <texto> — salvar novo memo\n"
        "/memo <texto> due <data> — salvar com data de vencimento\n"
        "/memos — listar memos abertos\n"
        "/memo done <id> — marcar como concluido\n"
        "/memo dismiss <id> — descartar memo"
    ),
    "help.notify": (
        "/notify — ver configuracoes de notificacao\n"
        "/notify reminder <min> — definir antecedencia do lembrete (minutos)\n"
        "/notify days <n> — definir janela de monitoramento (dias)"
    ),
    "help.presence": (
        "/presence — presenca atual\n"
        "/presence <status> — definir presenca (home|work|out|dnd)\n"
        "/presence <status> <nota> — definir com nota"
    ),
    "help.profile": (
        "/profile — ver contas associadas a cada presenca\n"
        "/profile <presenca> — ver para uma presenca especifica"
    ),
    "help.schedule": (
        "/schedule HH:MM <titulo> [duracao]\n"
        "/schedule hoje|amanha HH:MM <titulo> [duracao]\n"
        "/schedule DD/MM HH:MM <titulo> [duracao]\n"
        "/schedule DD/MM/AAAA HH:MM <titulo> [duracao]\n\n"
        "Duracao: 1h  30min  1h30  (padrao: 60min)"
    ),
    "help.timezone": (
        "/timezone — timezone atual\n"
        "/timezone <tz> — definir timezone (ex.: America/Cuiaba)"
    ),
    "help.workdays": (
        "/workdays — horario de trabalho"
    ),
}
