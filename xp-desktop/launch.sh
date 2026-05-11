#!/usr/bin/env bash
# xp-desktop watchdog -- relaunches desktop.py if it crashes or exits.
# exec-once'd by Hyprland; safe to run as a singleton (uses a pid lock).

set -u

DIR="$(cd "$(dirname "$0")" && pwd)"
LOCK="${XDG_RUNTIME_DIR:-/tmp}/xp-desktop.lock"
LOG="${XDG_RUNTIME_DIR:-/tmp}/xp-desktop.log"

# Singleton check via flock so a second invocation (e.g. accidental
# double exec-once) exits cleanly without spawning a competing loop.
exec 9>"$LOCK"
flock -n 9 || { echo "[xp-desktop] already running"; exit 0; }

trap 'kill %% 2>/dev/null; exit 0' INT TERM

# Companion title-bar overlay. Same restart policy as the desktop.
spawn_titlebar() {
    python3 -u "$DIR/titlebar.py" >>"$LOG" 2>&1 &
    TITLEBAR_PID=$!
}

trap 'kill ${TITLEBAR_PID:-} 2>/dev/null; kill %% 2>/dev/null; exit 0' INT TERM

spawn_titlebar

while :; do
    echo "==== $(date '+%F %T') start desktop ====" >>"$LOG"
    python3 -u "$DIR/desktop.py" >>"$LOG" 2>&1 &
    pid=$!
    wait "$pid"
    rc=$?
    echo "==== $(date '+%F %T') desktop exited rc=$rc ====" >>"$LOG"

    # If the title bar manager has died too, bring it back
    if ! kill -0 "${TITLEBAR_PID:-0}" 2>/dev/null; then
        echo "==== $(date '+%F %T') restart titlebar ====" >>"$LOG"
        spawn_titlebar
    fi
    sleep 1
done
