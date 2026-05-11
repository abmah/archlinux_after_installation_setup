# archlinux_after_installation_setup

Bootstraps the **Windows XP / Frutiger Aero** Hyprland desktop on a fresh Arch
Linux install.

## Quick start

On a freshly installed Arch box, log in as a normal user (with sudo rights)
and run:

```bash
git clone https://github.com/abmah/archlinux_after_installation_setup.git ~/setup
cd ~/setup
./install.sh
```

The script will:

1. Install `paru` (AUR helper)
2. Install all pacman + AUR packages
3. Enable services (Bluetooth, keyd, NetworkManager, pipewire-pulse)
4. Remap **Right Alt → Super** via keyd
5. Install the system helpers (`/usr/local/bin/{power-mode,fan-mode}`,
   systemd unit for ThinkPad fan control, modprobe option, sudoers drop-in)
6. Deploy every config tree under `~/.config/` and rewrite hard-coded
   `/home/abd/` paths to the current user's `$HOME`
7. Wire the image mime handlers to Gwenview
8. Install the wallpaper cycler script and copy bundled wallpapers
9. Apply the **Windows XP Luna** GTK theme via gsettings
10. Point lightdm at `user-session=hyprland`
11. Reload waybar / dunst / Hyprland in place

## Running individual steps

```bash
./install.sh --list             # show all step names
./install.sh configs            # only redeploy configs
./install.sh --dry-run packages # show what would be installed
```

## Updating the repo from your live config

When you tweak something in `~/.config/`, sync it back to the repo with:

```bash
./update-configs.sh
git commit -am "tweak"
git push
```

## What's inside

| Path             | Purpose                                                      |
|------------------|--------------------------------------------------------------|
| `install.sh`     | Modular installer (steps listed via `--list`)                |
| `update-configs.sh` | Pulls current `~/.config/*` back into the repo            |
| `hypr/`          | Hyprland, hyprpaper, hyprlock configs + XP login assets      |
| `waybar/`        | XP-Luna taskbar, sprites, and Python+GTK XP dialogs          |
| `wezterm/`       | Frutiger Aero terminal config + sky background               |
| `Thunar/`        | XP File Explorer styling                                     |
| `dunst/`         | XP-balloon notifications                                     |
| `gtk-3.0/`       | XP Luna theme + Tahoma 10 default font                       |
| `wofi/`, `kitty/`| Legacy launcher and terminal configs                         |
| `btop/`          | minimal_white btop theme                                     |
| `sounds/`        | `xp-startup.wav` chime played on login                       |
| `language/`      | fontconfig for Arabic + emoji fallback                       |
| `system/`        | Files copied to `/usr/local/bin`, `/etc/...` (root-owned)    |
