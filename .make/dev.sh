#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SESSION="nina"
PY="$ROOT_DIR/.venv/bin/python -m nina"
PORT="${NINA_HTTP_PORT:-8765}"
HOST="${NINA_HTTP_HOST:-127.0.0.1}"

# 1) tmux session visible via socket → reattach (preserves daemon/console).
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "tmux session '$SESSION' exists — reattaching."
    exec tmux attach-session -t "$SESSION"
fi

# 2) tmux server visible only as a process (different socket/namespace).
tmux_pids=$(pgrep -f "tmux .*-s ${SESSION}([[:space:]]|$)" 2>/dev/null || true)
if [ -n "$tmux_pids" ]; then
    echo "ERROR: a tmux server for session '$SESSION' is running (pids: $tmux_pids)" >&2
    echo "       but cannot be reached from this shell (different socket)." >&2
    echo "       Reattach from the original shell, or run: make dev-stop" >&2
    exit 1
fi

# 3) No tmux session, but daemon port is busy → orphan process holding it.
if command -v ss >/dev/null 2>&1 && \
   ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "(^|:)${PORT}$"; then
    echo "ERROR: $HOST:$PORT is already in use, but no tmux '$SESSION' session." >&2
    echo "       Likely an orphan 'nina daemon'. Inspect:" >&2
    echo "         ss -ltnp | grep :$PORT" >&2
    echo "       Recover with:" >&2
    echo "         make dev-stop" >&2
    exit 1
fi

# 4) Stray daemon/console without the tmux wrapper.
strays=$(pgrep -f 'python -m nina (daemon|console)' 2>/dev/null || true)
if [ -n "$strays" ]; then
    echo "ERROR: nina daemon/console already running outside tmux (pids: $strays)" >&2
    echo "       Recover with: make dev-stop" >&2
    exit 1
fi

# 5) Fresh start — spawn detached tmux with daemon + console.
tmux new-session -d -s "$SESSION" -x 220 -y 50
tmux send-keys -t "$SESSION:0.0" "cd $ROOT_DIR && $PY daemon --dev" Enter
tmux split-window -v -t "$SESSION:0.0"
tmux send-keys -t "$SESSION:0.1" "cd $ROOT_DIR && sleep 2 && $PY console" Enter
tmux select-pane -t "$SESSION:0.1"
exec tmux attach-session -t "$SESSION"
