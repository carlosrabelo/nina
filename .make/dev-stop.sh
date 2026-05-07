#!/bin/bash
set -euo pipefail

SESSION="nina"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux kill-session -t "$SESSION"
    echo "tmux session '$SESSION' killed."
fi

# Fallback: tmux server visible only as a process (different socket / namespace).
tmux_pids=$(pgrep -f "tmux .*-s ${SESSION}([[:space:]]|$)" 2>/dev/null || true)
if [ -n "$tmux_pids" ]; then
    echo "killing stray tmux pids: $tmux_pids"
    # shellcheck disable=SC2086
    kill $tmux_pids 2>/dev/null || true
fi

# Mop up any nina daemon/console process not under tmux.
strays=$(pgrep -f 'python -m nina (daemon|console)' 2>/dev/null || true)
if [ -n "$strays" ]; then
    echo "killing stray nina pids: $strays"
    # shellcheck disable=SC2086
    kill $strays 2>/dev/null || true
fi

echo "done."
