#!/usr/bin/env bash
# Fan-mode chooser — XP-styled yad list. Click the fan widget in waybar.

current=$(cat /tmp/fan-mode-current 2>/dev/null || echo auto)
fan_control=$(cat /sys/module/thinkpad_acpi/parameters/fan_control 2>/dev/null)
suffix=""
[ "$fan_control" = "N" ] && suffix=" — REBOOT NEEDED"

choice=$(/home/abd/.config/waybar/menu-xp.sh \
    "Fan Mode (now: $current)$suffix" \
    "Auto (BIOS controlled)" \
    "Quiet (level 1)" \
    "Normal (level 4)" \
    "Max (full speed)")

notify() { command -v notify-send >/dev/null && notify-send -t 3000 -i fan "Fan mode" "$1" 2>/dev/null; }

case "$choice" in
    "Auto"*)    sudo -n /usr/local/bin/fan-mode auto    && notify "Auto" ;;
    "Quiet"*)   sudo -n /usr/local/bin/fan-mode quiet   && notify "Quiet — level 1" ;;
    "Normal"*)  sudo -n /usr/local/bin/fan-mode normal  && notify "Normal — level 4" ;;
    "Max"*)     sudo -n /usr/local/bin/fan-mode max     && notify "Max — full disengaged speed" ;;
    *)          exit 0 ;;
esac

[ "$fan_control" = "N" ] && notify "Saved — but fan_control is disabled. Reboot to apply."
