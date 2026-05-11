#!/bin/bash
# update-configs.sh
# Script to backup configs to ~/setup/

# Set the base backup directory
BACKUP_DIR=~/setup

# Copy Hyprland config
echo "Copying Hyprland config..."
mkdir -p "$BACKUP_DIR/hypr"
cp -r ~/.config/hypr/* "$BACKUP_DIR/hypr/"

# Copy Kitty config
echo "Copying Kitty config..."
mkdir -p "$BACKUP_DIR/kitty"
cp -r ~/.config/kitty/* "$BACKUP_DIR/kitty/"

# Copy Waybar config
echo "Copying Waybar config..."
mkdir -p "$BACKUP_DIR/waybar"
cp -r ~/.config/waybar/* "$BACKUP_DIR/waybar/"

# Copy Wofi config
echo "Copying Wofi config..."
mkdir -p "$BACKUP_DIR/wofi"
cp -r ~/.config/wofi/* "$BACKUP_DIR/wofi/"

# Copy btop theme
echo "Copying btop theme..."
mkdir -p "$BACKUP_DIR/btop"
cp ~/.config/btop/themes/minimal_white.theme "$BACKUP_DIR/btop/"

# Copy WezTerm config (XP / Frutiger Aero terminal)
if [ -d ~/.config/wezterm ]; then
    echo "Copying WezTerm config..."
    mkdir -p "$BACKUP_DIR/wezterm"
    cp -r ~/.config/wezterm/* "$BACKUP_DIR/wezterm/" 2>/dev/null || true
fi

# Copy Thunar config (file manager)
if [ -d ~/.config/Thunar ]; then
    echo "Copying Thunar config..."
    mkdir -p "$BACKUP_DIR/Thunar"
    cp -r ~/.config/Thunar/* "$BACKUP_DIR/Thunar/" 2>/dev/null || true
fi

# Copy Dunst config (XP-themed notifications)
if [ -d ~/.config/dunst ]; then
    echo "Copying Dunst config..."
    mkdir -p "$BACKUP_DIR/dunst"
    cp -r ~/.config/dunst/* "$BACKUP_DIR/dunst/" 2>/dev/null || true
fi

# Copy GTK3 theme settings (XP Luna)
if [ -d ~/.config/gtk-3.0 ]; then
    echo "Copying GTK3 settings..."
    mkdir -p "$BACKUP_DIR/gtk-3.0"
    cp ~/.config/gtk-3.0/settings.ini "$BACKUP_DIR/gtk-3.0/" 2>/dev/null || true
fi

# Copy XP startup sound if present
if [ -f ~/.config/sounds/xp-startup.wav ]; then
    echo "Copying XP startup sound..."
    mkdir -p "$BACKUP_DIR/sounds"
    cp ~/.config/sounds/xp-startup.wav "$BACKUP_DIR/sounds/" 2>/dev/null || true
fi

# Drop Python bytecode caches that shouldn't be in git
find "$BACKUP_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo "All configs copied to $BACKUP_DIR ✅"
