#!/usr/bin/env bash
# Shutdown menu — XP-styled yad list. Click the waybar power button.

choice=$(/home/abd/.config/waybar/menu-xp.sh \
    "Turn off computer" \
    "Shutdown" \
    "Reboot" \
    "Suspend" \
    "Hibernate" \
    "Logout" \
    "Lock")

case "$choice" in
    Shutdown)  systemctl poweroff ;;
    Reboot)    systemctl reboot ;;
    Suspend)   systemctl suspend ;;
    Hibernate) systemctl hibernate ;;
    Logout)    pkill -KILL -u "$USER" ;;
    Lock)      command -v hyprlock >/dev/null && hyprlock || swaylock ;;
    *)         exit 0 ;;
esac
