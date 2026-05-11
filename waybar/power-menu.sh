#!/usr/bin/env bash
# Power-mode chooser — XP-styled yad list dialog. Click waybar battery to invoke.

current=$(cat /tmp/power-mode-current 2>/dev/null || echo "balanced")

choice=$(/home/abd/.config/waybar/menu-xp.sh \
    "Power Mode (now: $current)" \
    "Ultra Saver" \
    "Balanced" \
    "Performance")

apply_user_tweaks() {
    case "$1" in
        ultra)
            rfkill block bluetooth 2>/dev/null || true
            hyprctl --batch "keyword animations:enabled 0 ; keyword decoration:blur:enabled false ; keyword decoration:shadow:enabled false ; keyword misc:vrr 2" >/dev/null 2>&1
            ;;
        balanced)
            rfkill unblock bluetooth 2>/dev/null || true
            hyprctl --batch "keyword animations:enabled 1 ; keyword decoration:blur:enabled true ; keyword decoration:blur:size 3 ; keyword decoration:blur:passes 1 ; keyword decoration:shadow:enabled true ; keyword misc:vrr 0" >/dev/null 2>&1
            ;;
        performance)
            rfkill unblock bluetooth 2>/dev/null || true
            hyprctl --batch "keyword animations:enabled 1 ; keyword decoration:blur:enabled true ; keyword decoration:blur:size 5 ; keyword decoration:blur:passes 2 ; keyword decoration:shadow:enabled true ; keyword misc:vrr 0" >/dev/null 2>&1
            ;;
    esac
}

notify() { command -v notify-send >/dev/null && notify-send -t 3000 -i battery "Power mode" "$1" 2>/dev/null; }

case "$choice" in
    "Ultra Saver")
        sudo -n /usr/local/bin/power-mode ultra && apply_user_tweaks ultra && \
            notify "Ultra Saver — CPU 25%, no turbo, BT off, no effects"
        ;;
    "Balanced")
        sudo -n /usr/local/bin/power-mode balanced && apply_user_tweaks balanced && \
            notify "Balanced — CPU 85%, turbo on, BT on, effects on"
        ;;
    "Performance")
        sudo -n /usr/local/bin/power-mode performance && apply_user_tweaks performance && \
            notify "Performance — full CPU, max effects"
        ;;
    *) exit 0 ;;
esac
