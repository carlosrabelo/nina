#!/bin/bash
set -euo pipefail

SESSION="nina"
PORT="${NINA_HTTP_PORT:-8765}"

# tmux: prefer process inspection (works under restricted/sandboxed shells too).
tmux_pids=$(pgrep -f "tmux .*-s ${SESSION}([[:space:]]|$)" 2>/dev/null || true)
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "tmux session : running  (attach with: tmux attach -t $SESSION)"
elif [ -n "$tmux_pids" ]; then
    echo "tmux session : running (server PID(s): $tmux_pids — different socket)"
else
    echo "tmux session : not running"
fi

if command -v ss >/dev/null 2>&1 && \
   ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "(^|:)${PORT}$"; then
    echo "port $PORT    : in use"
else
    echo "port $PORT    : free"
fi

daemon_pids=$(pgrep -f 'python -m nina daemon' 2>/dev/null || true)
console_pids=$(pgrep -f 'python -m nina console' 2>/dev/null || true)
echo "daemon procs : ${daemon_pids:-none}"
echo "console procs: ${console_pids:-none}"
