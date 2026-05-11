#!/usr/bin/env bash
# ============================================================================
# install.sh - Bootstrap the XP / Frutiger Aero desktop on a fresh Arch box.
#
# Usage:
#   ./install.sh                # full install
#   ./install.sh <step>         # run a single step (see list_steps)
#   ./install.sh --list         # list available steps
#   ./install.sh --dry-run      # show what would happen
#
# Designed to be re-runnable: every step checks before acting, and
# config files are *templated* so no path is hard-coded to a specific user.
# ============================================================================

set -Eeuo pipefail

# ---------------------------------------------------------------------------
# 0. paths, colors, logging
# ---------------------------------------------------------------------------

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
CFG="$TARGET_HOME/.config"
DRY_RUN=0

c_reset='\033[0m';  c_bold='\033[1m'
c_red='\033[31m';   c_yel='\033[33m'
c_grn='\033[32m';   c_blu='\033[36m'
log()   { printf '%b==>%b %s\n'    "$c_grn$c_bold" "$c_reset" "$*"; }
warn()  { printf '%b!!%b  %s\n'    "$c_yel$c_bold" "$c_reset" "$*" >&2; }
die()   { printf '%bxx%b %s\n'     "$c_red$c_bold" "$c_reset" "$*" >&2; exit 1; }
step()  { printf '\n%b== %s ==%b\n' "$c_blu$c_bold" "$*" "$c_reset"; }

run() {
    if [ "$DRY_RUN" = 1 ]; then
        printf '%b[dry]%b %s\n' "$c_yel" "$c_reset" "$*"
    else
        eval "$@"
    fi
}

need_root() {
    [ "$DRY_RUN" = 1 ] && return 0
    if [ "$EUID" -eq 0 ]; then
        die "Run this as a regular user. Sudo is invoked only when needed."
    fi
    if ! sudo -v; then
        die "sudo is required and the password was not accepted."
    fi
}

# ---------------------------------------------------------------------------
# 1. package lists (one source of truth)
# ---------------------------------------------------------------------------

# Base + dev tooling required to build AUR packages
PKGS_BASE=(
    git base-devel curl wget unzip rsync jq sed gawk
)

# Hyprland desktop core
PKGS_HYPR=(
    hyprland hyprpaper hyprlock waybar dunst
    xdg-desktop-portal xdg-desktop-portal-hyprland
    polkit-kde-agent
    qt5-wayland qt6-wayland
    gtk-layer-shell  # required by the XP desktop background layer
)

# Terminal, file manager, browser-ish things
PKGS_DESKTOP=(
    wezterm
    thunar thunar-volman tumbler ffmpegthumbnailer
    gvfs gvfs-mtp gvfs-gphoto2
    udisks2 polkit-gnome
    ntfs-3g exfatprogs
    gwenview
    pavucontrol
    brightnessctl
    grim slurp swappy wl-clipboard
    fzf btop
    network-manager-applet
)

# Audio
PKGS_AUDIO=(
    pipewire pipewire-pulse pipewire-alsa pipewire-jack
    wireplumber
)

# Bluetooth
PKGS_BT=(
    bluez bluez-utils blueman
)

# Power & laptop sensors
PKGS_POWER=(
    power-profiles-daemon
    upower
    acpi
    lm_sensors
    keyd
)

# Fonts (Tahoma & Trebuchet come from ttf-ms-fonts in AUR)
PKGS_FONTS=(
    ttf-jetbrains-mono-nerd ttf-firacode-nerd
    noto-fonts noto-fonts-extra noto-fonts-emoji
    ttf-liberation
)

# AUR-only packages
PKGS_AUR=(
    ttf-ms-fonts            # Tahoma, Trebuchet MS for authentic XP look
    windows-xp-themes-git   # GTK XP-Luna theme used by Thunar etc.
    windows-xp-icon-theme   # icon set for Thunar
)

# ---------------------------------------------------------------------------
# 2. building blocks (small idempotent functions)
# ---------------------------------------------------------------------------

pacman_install() {
    local missing=()
    for p in "$@"; do
        pacman -Qq "$p" >/dev/null 2>&1 || missing+=("$p")
    done
    if [ ${#missing[@]} -gt 0 ]; then
        log "pacman -S ${missing[*]}"
        run "sudo pacman -S --needed --noconfirm ${missing[*]}"
    else
        log "all already installed: $*"
    fi
}

aur_install() {
    command -v paru >/dev/null 2>&1 || die "paru not installed; run step bootstrap first"
    local missing=()
    for p in "$@"; do
        pacman -Qq "$p" >/dev/null 2>&1 || missing+=("$p")
    done
    if [ ${#missing[@]} -gt 0 ]; then
        log "paru -S ${missing[*]}"
        run "paru -S --needed --noconfirm --skipreview ${missing[*]}"
    else
        log "AUR packages already installed: $*"
    fi
}

# Deploy a config tree from $REPO_DIR/$1 into $CFG/$2, with HOME templating.
# Hard-coded /home/abd/ paths inside text files are rewritten to $TARGET_HOME.
deploy_config_tree() {
    local src="$REPO_DIR/$1"
    local dst="$CFG/$2"
    [ -d "$src" ] || { warn "no source dir $src; skipping"; return 0; }
    log "deploy $1 -> $dst"
    run "mkdir -p '$dst'"
    run "rsync -a --exclude='__pycache__' --exclude='*.pyc' '$src/' '$dst/'"
    # Rewrite hard-coded user paths in text files (idempotent)
    if [ "$DRY_RUN" != 1 ]; then
        grep -rl --include='*.sh' --include='*.py' --include='*.conf' \
                 --include='*.css' --include='*.jsonc' --include='*.lua' \
                 --include='*.toml' --include='*.ini' \
                 '/home/abd' "$dst" 2>/dev/null \
            | xargs -r sed -i "s|/home/abd|$TARGET_HOME|g"
    fi
}

# ---------------------------------------------------------------------------
# 3. STEPS
# ---------------------------------------------------------------------------

step_bootstrap() {
    step "bootstrap: base-devel + paru (AUR helper)"
    pacman_install "${PKGS_BASE[@]}"
    if ! command -v paru >/dev/null 2>&1; then
        log "building paru from AUR"
        local tmp; tmp="$(mktemp -d)"
        run "git clone https://aur.archlinux.org/paru.git '$tmp/paru'"
        run "(cd '$tmp/paru' && makepkg -si --noconfirm)"
        run "rm -rf '$tmp'"
    else
        log "paru already installed"
    fi
}

step_packages() {
    step "packages: hyprland + desktop + audio + bluetooth + power + fonts"
    pacman_install "${PKGS_HYPR[@]}"
    pacman_install "${PKGS_DESKTOP[@]}"
    pacman_install "${PKGS_AUDIO[@]}"
    pacman_install "${PKGS_BT[@]}"
    pacman_install "${PKGS_POWER[@]}"
    pacman_install "${PKGS_FONTS[@]}"
    aur_install    "${PKGS_AUR[@]}"
}

step_services() {
    step "services: bluetooth, keyd, pipewire-pulse, NetworkManager, udisks2"
    run "sudo systemctl enable --now bluetooth.service"
    run "sudo systemctl enable --now keyd.service || true"
    run "sudo systemctl enable --now NetworkManager.service || true"
    run "sudo systemctl enable --now udisks2.service"
    run "systemctl --user enable --now pipewire-pulse.service || true"
    # storage group: lets the user mount removable drives without root
    run "sudo gpasswd -a '$TARGET_USER' storage 2>/dev/null || true"
}

# /etc/keyd/default.conf - rightalt → leftmeta (Win key on the laptop)
step_keyd() {
    step "keyd: remap Right Alt -> Super"
    local conf=/etc/keyd/default.conf
    if [ -f "$conf" ] && grep -q "rightalt = leftmeta" "$conf"; then
        log "keyd config already in place"
    else
        run "sudo mkdir -p /etc/keyd"
        run "echo -e '[ids]\n*\n\n[main]\nrightalt = leftmeta' | sudo tee '$conf' >/dev/null"
        run "sudo systemctl restart keyd.service || true"
    fi
}

step_system_files() {
    step "system files: /usr/local/bin helpers + systemd unit + modprobe + sudoers"
    local sys="$REPO_DIR/system"
    # power-mode / fan-mode
    run "sudo install -m 0755 -o root -g root '$sys/usr-local-bin/power-mode' /usr/local/bin/power-mode"
    run "sudo install -m 0755 -o root -g root '$sys/usr-local-bin/fan-mode'   /usr/local/bin/fan-mode"
    # thinkpad fan kernel module load with fan_control=1
    run "sudo install -m 0644 -o root -g root '$sys/etc-modprobe.d/thinkpad_acpi.conf' /etc/modprobe.d/thinkpad_acpi.conf"
    run "sudo install -m 0644 -o root -g root '$sys/etc-systemd-system/thinkpad-fan-control.service' /etc/systemd/system/thinkpad-fan-control.service"
    run "sudo systemctl daemon-reload"
    run "sudo systemctl enable thinkpad-fan-control.service || true"
    # sudoers drop-in - templated with deploying user's username; install via visudo for safety
    local sudoers_tmp; sudoers_tmp="$(mktemp)"
    sed "s|%USER%|$TARGET_USER|g" "$sys/etc-sudoers.d/xp-helpers" > "$sudoers_tmp"
    if [ "$DRY_RUN" = 1 ]; then
        run "sudo visudo -cf '$sudoers_tmp' && sudo install -m 0440 -o root -g root '$sudoers_tmp' /etc/sudoers.d/xp-helpers"
    elif sudo visudo -cf "$sudoers_tmp" >/dev/null; then
        run "sudo install -m 0440 -o root -g root '$sudoers_tmp' /etc/sudoers.d/xp-helpers"
    else
        warn "sudoers template failed visudo check; skipping"
    fi
    rm -f "$sudoers_tmp"
}

step_configs() {
    step "configs: deploy ~/.config trees from repo"
    deploy_config_tree hypr     hypr
    deploy_config_tree waybar   waybar
    deploy_config_tree wezterm  wezterm
    deploy_config_tree wofi     wofi
    deploy_config_tree dunst    dunst
    deploy_config_tree Thunar   Thunar
    deploy_config_tree xfce4    xfce4
    deploy_config_tree gtk-3.0     gtk-3.0
    deploy_config_tree kitty       kitty
    deploy_config_tree xp-desktop  xp-desktop
    # btop theme
    run "mkdir -p '$CFG/btop/themes'"
    run "cp -f '$REPO_DIR/btop/minimal_white.theme' '$CFG/btop/themes/'"
    # XP startup chime
    if [ -f "$REPO_DIR/sounds/xp-startup.wav" ]; then
        run "mkdir -p '$CFG/sounds'"
        run "cp -f '$REPO_DIR/sounds/xp-startup.wav' '$CFG/sounds/'"
    fi
    # font config for Arabic etc.
    if [ -f "$REPO_DIR/language/fonts.conf" ]; then
        run "mkdir -p '$CFG/fontconfig'"
        run "cp -f '$REPO_DIR/language/fonts.conf' '$CFG/fontconfig/fonts.conf'"
    fi
    # ensure scripts are executable
    run "find '$CFG/waybar' -maxdepth 2 -type f \\( -name '*.sh' -o -name '*.py' \\) -exec chmod +x {} +"
    run "chmod +x '$CFG/xp-desktop/desktop.py' 2>/dev/null || true"
}

step_mimes() {
    step "mimes: open images with Gwenview"
    local list="$CFG/mimeapps.list"
    run "mkdir -p '$CFG'"
    if ! grep -q '^\[Default Applications\]' "$list" 2>/dev/null; then
        run "echo '[Default Applications]' >> '$list'"
    fi
    for mt in image/png image/jpeg image/gif image/webp image/bmp image/tiff image/svg+xml image/x-portable-pixmap; do
        if ! grep -q "^${mt}=" "$list" 2>/dev/null; then
            run "sed -i '/^\\[Default Applications\\]/a ${mt}=org.kde.gwenview.desktop' '$list'"
        fi
    done
    command -v update-desktop-database >/dev/null \
        && run "update-desktop-database '$TARGET_HOME/.local/share/applications' 2>/dev/null || true"
}

step_wallpaper() {
    step "wallpaper: install cycler script"
    if [ -f "$REPO_DIR/wallpaper-cycler.sh" ]; then
        run "mkdir -p '$TARGET_HOME/scripts'"
        run "install -m 0755 '$REPO_DIR/wallpaper-cycler.sh' '$TARGET_HOME/scripts/wallpaper-cycler.sh'"
        # copy wallpapers if a bundled set exists
        if [ -d "$REPO_DIR/images" ]; then
            run "mkdir -p '$TARGET_HOME/Pictures/wallpapers'"
            run "rsync -a '$REPO_DIR/images/' '$TARGET_HOME/Pictures/wallpapers/'"
        fi
    fi
}

step_gtk_theme() {
    step "gtk: apply Windows XP Luna theme via gsettings"
    if command -v gsettings >/dev/null 2>&1; then
        run "gsettings set org.gnome.desktop.interface gtk-theme 'Windows XP Luna' 2>/dev/null || true"
        run "gsettings set org.gnome.desktop.interface icon-theme 'windows-xp-icon-theme' 2>/dev/null || true"
        run "gsettings set org.gnome.desktop.interface font-name 'Tahoma 10' 2>/dev/null || true"
    else
        warn "gsettings not available; settings.ini still in place"
    fi
}

step_lightdm_session() {
    step "lightdm: set hyprland as the default user session"
    local conf=/etc/lightdm/lightdm.conf
    if [ -f "$conf" ]; then
        if grep -q '^user-session=hyprland' "$conf"; then
            log "lightdm already targets hyprland"
        else
            run "sudo sed -i 's|^#\\?user-session=.*|user-session=hyprland|' '$conf'"
        fi
    else
        warn "no /etc/lightdm/lightdm.conf - greeter step skipped"
    fi
}

step_reload() {
    step "reload running services"
    pgrep -x waybar  >/dev/null && run "pkill -SIGUSR2 waybar"   || true
    pgrep -x hyprland>/dev/null && run "hyprctl reload || true"  || true
    pgrep -x dunst   >/dev/null && run "pkill dunst; setsid dunst >/dev/null 2>&1 &" || true
}

# ---------------------------------------------------------------------------
# 4. dispatcher
# ---------------------------------------------------------------------------

STEPS=(
    bootstrap
    packages
    services
    keyd
    system_files
    configs
    mimes
    wallpaper
    gtk_theme
    lightdm_session
    reload
)

list_steps() {
    printf 'Steps (run individually with: ./install.sh <name>):\n'
    for s in "${STEPS[@]}"; do printf '  - %s\n' "$s"; done
}

run_all() {
    need_root
    for s in "${STEPS[@]}"; do "step_$s"; done
    step "DONE"
    log "log out and back in (or reboot) so XDG env, services and key remaps apply."
}

main() {
    case "${1:-}" in
        ''|all)         run_all ;;
        --list|-l)      list_steps ;;
        --dry-run)      DRY_RUN=1; shift; main "$@" ;;
        -h|--help)
            sed -n '2,15p' "$0"
            echo
            list_steps
            ;;
        *)
            local s="$1"
            for known in "${STEPS[@]}"; do
                [ "$s" = "$known" ] && { need_root; "step_$s"; return; }
            done
            die "unknown step: $s   (try --list)"
            ;;
    esac
}

main "$@"
