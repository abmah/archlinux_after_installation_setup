#!/usr/bin/env python3
"""
Windows XP Start Menu - Python+GTK reimplementation.

Layout matches the original XP Start Menu:
    +-------------------------------+-------+
    |  [tile]  username             |       |
    |  ----- blue header strip -----|       |
    +-------------------------------+-------+
    | LEFT pane (white):            | RIGHT |
    |   - Pinned apps (top)         | pane  |
    |   - separator                 | (cream|
    |   - Recent / All Apps         |  bg)  |
    | All Programs >                |       |
    +-------------------------------+-------+
    | [Log Off]      [Turn Off Computer]    |
    +---------------------------------------+

Anchored to the bottom-left of the screen, just above the waybar.
"""

import gi, os, sys, subprocess, glob, re

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

XP_CSS = b"""
window.xp-start {
    background-color: #ECE9D8;
    border: 1px solid #0A246A;
}

/* Top blue header strip with avatar + username */
.xp-header {
    background-image:
        linear-gradient(180deg,
            #0A246A 0%, #0058E6 4%, #3A93FF 9%,
            #0F76E6 16%, #1E64DB 60%, #0050D2 100%);
    color: #FFFFFF;
    border-bottom: 1px solid #FFAA1A;
    min-height: 56px;
    padding: 6px 10px;
}
.xp-header label {
    color: #FFFFFF;
    font-family: "Trebuchet MS", "Tahoma", sans-serif;
    font-weight: bold;
    font-size: 13pt;
    text-shadow: 1px 1px 1px rgba(0,0,0,0.55);
    margin-left: 10px;
}

/* Two-pane body */
.xp-leftpane  { background-color: #FFFFFF; padding: 4px; }
.xp-rightpane { background-color: #D6E0EE; padding: 4px; }

/* App rows - left pane */
.xp-leftpane row {
    background-color: transparent;
    color: #000000;
    padding: 4px 8px;
    font-family: "Tahoma", sans-serif;
    font-size: 10pt;
}
.xp-leftpane row:hover,
.xp-leftpane row:selected {
    background-color: #316AC5;
    color: #FFFFFF;
}

/* Right pane (system shortcuts) */
.xp-rightpane row {
    background-color: transparent;
    color: #000000;
    padding: 4px 8px;
    font-family: "Tahoma", sans-serif;
    font-size: 10pt;
}
.xp-rightpane row:hover,
.xp-rightpane row:selected {
    background-color: #316AC5;
    color: #FFFFFF;
}

/* Section header label */
.xp-section {
    color: #0A246A;
    font-family: "Tahoma", sans-serif;
    font-size: 9pt;
    font-weight: bold;
    padding: 4px 8px 2px 8px;
}

/* Separator line */
.xp-sep {
    background-color: #316AC5;
    min-height: 1px;
    margin: 2px 8px;
}

/* All Programs row */
.xp-allprograms {
    background-color: transparent;
    color: #000000;
    padding: 6px 8px;
    font-family: "Tahoma", sans-serif;
    font-size: 10pt;
    font-weight: bold;
}

/* Footer with Log Off / Turn Off */
.xp-footer {
    background-image:
        linear-gradient(180deg, #5285DC 0%, #2E5FBC 100%);
    border-top: 1px solid #0A246A;
    padding: 6px 10px;
}
.xp-footer button {
    background-image:
        linear-gradient(180deg,
            #FFFFFF 0%, #ECE9D8 45%, #D8D2BD 100%);
    color: #000000;
    font-family: "Tahoma", sans-serif;
    font-size: 9pt;
    border: 1px solid #003C74;
    border-radius: 3px;
    padding: 4px 14px;
    margin: 0 6px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.9),
        inset -1px -1px 0 rgba(112,112,96,0.55);
}
.xp-footer button:hover {
    background-image:
        linear-gradient(180deg,
            #FFFFFF 0%, #F5F1E2 45%, #DAD5C2 100%);
    border-color: #0A246A;
}
"""


# ---- desktop-file loader (shared logic with xp-run.py) ---------------------

EXEC_PLACEHOLDER = re.compile(r"\s%[fFuUickdDnNvm]")


def parse_desktop_file(path):
    name = exec_ = icon = None
    no_display = False
    terminal = False
    in_main = False
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.rstrip("\n")
                if line.startswith("[") and line.endswith("]"):
                    in_main = (line == "[Desktop Entry]")
                    continue
                if not in_main:
                    continue
                if line.startswith("Name=") and name is None:
                    name = line[5:].strip()
                elif line.startswith("Exec=") and exec_ is None:
                    exec_ = EXEC_PLACEHOLDER.sub("", line[5:]).strip()
                elif line.startswith("Icon=") and icon is None:
                    icon = line[5:].strip()
                elif line.startswith("NoDisplay="):
                    no_display = line[10:].strip().lower() == "true"
                elif line.startswith("Hidden=") and line[7:].strip().lower() == "true":
                    no_display = True
                elif line.startswith("Terminal=") and line[9:].strip().lower() == "true":
                    terminal = True
                elif line.startswith("Type=") and line[5:].strip() != "Application":
                    return None
    except OSError:
        return None
    if not name or not exec_ or no_display:
        return None
    return (name, exec_, icon, terminal)


def load_apps():
    dirs = [
        os.path.expanduser("~/.local/share/applications"),
        "/usr/local/share/applications",
        "/usr/share/applications",
        "/var/lib/flatpak/exports/share/applications",
        os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
    ]
    seen = {}
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for path in glob.glob(os.path.join(d, "*.desktop")):
            entry = parse_desktop_file(path)
            if entry is None:
                continue
            name, exec_, icon, terminal = entry
            if name not in seen:
                seen[name] = (exec_, icon, terminal)
    return sorted([(n, *v) for n, v in seen.items()], key=lambda x: x[0].lower())


# ---- launcher --------------------------------------------------------------

def run_command(cmd, terminal=False):
    if not cmd or not cmd.strip():
        return False
    if terminal:
        cmd = f"wezterm start --always-new-process -- sh -c {repr(cmd)}"
    subprocess.Popen(
        ["/usr/bin/sh", "-c", f"setsid {cmd} >/dev/null 2>&1 &"],
        start_new_session=True,
    )
    return True


# ---- UI --------------------------------------------------------------------

PINNED = [
    # name regex (case insensitive)  - first match in apps used
    "Firefox",
    "Brave",
    "Google Chrome",
    "WezTerm",
    "Files",
    "Dolphin",
]


def find_app(apps, query):
    q = query.lower()
    for name, exec_, icon, terminal in apps:
        if q in name.lower():
            return (name, exec_, terminal)
    return None


def main():
    css = Gtk.CssProvider()
    css.load_from_data(XP_CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    apps = load_apps()

    win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    win.set_decorated(False)
    win.set_skip_taskbar_hint(True)
    win.set_keep_above(True)
    win.set_resizable(False)
    win.set_default_size(420, 480)
    win.set_title("Start")
    win.set_wmclass("XPMenu", "XPMenu")
    win.get_style_context().add_class("xp-start")

    def close_and(action=None):
        win.close()
        if action:
            action()

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    win.add(vbox)

    # ── Header ────────────────────────────────────────────────────────────
    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    header.get_style_context().add_class("xp-header")
    avatar = Gtk.Image()
    tile_path = os.path.expanduser("~/.config/hypr/xp-user-tile.png")
    if os.path.exists(tile_path):
        from gi.repository import GdkPixbuf
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_size(tile_path, 44, 44)
            avatar.set_from_pixbuf(pb)
        except Exception:
            avatar.set_from_icon_name("avatar-default", Gtk.IconSize.DIALOG)
    else:
        avatar.set_from_icon_name("avatar-default", Gtk.IconSize.DIALOG)
    header.pack_start(avatar, False, False, 0)
    user = os.environ.get("USER", "user")
    user_lbl = Gtk.Label(label=user, xalign=0.0)
    header.pack_start(user_lbl, True, True, 0)
    vbox.pack_start(header, False, False, 0)

    # ── Body: two columns ─────────────────────────────────────────────────
    body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    vbox.pack_start(body, True, True, 0)

    # Left pane - pinned + recent
    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    left.get_style_context().add_class("xp-leftpane")
    body.pack_start(left, True, True, 0)

    pinned_lbl = Gtk.Label(label="Pinned items", xalign=0.0)
    pinned_lbl.get_style_context().add_class("xp-section")
    left.pack_start(pinned_lbl, False, False, 0)

    pinned_list = Gtk.ListBox()
    pinned_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
    for keyword in PINNED:
        match = find_app(apps, keyword)
        if match is None:
            continue
        name, exec_, terminal = match
        row = Gtk.ListBoxRow()
        lbl = Gtk.Label(label=name, xalign=0.0)
        row.add(lbl)
        row._meta = (exec_, terminal)
        pinned_list.add(row)
    pinned_list.connect(
        "row-activated",
        lambda lb, row: close_and(lambda: run_command(*row._meta)) if hasattr(row, "_meta") else None,
    )
    left.pack_start(pinned_list, False, False, 0)

    # Separator
    sep = Gtk.Box()
    sep.get_style_context().add_class("xp-sep")
    sep.set_size_request(-1, 1)
    sep.set_margin_top(4); sep.set_margin_bottom(4)
    left.pack_start(sep, False, False, 0)

    recent_lbl = Gtk.Label(label="All programs", xalign=0.0)
    recent_lbl.get_style_context().add_class("xp-section")
    left.pack_start(recent_lbl, False, False, 0)

    # Recent / all programs (scrollable)
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.set_vexpand(True)
    all_list = Gtk.ListBox()
    all_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
    pinned_names = {find_app(apps, k)[0] for k in PINNED if find_app(apps, k)}
    for name, exec_, _icon, terminal in apps:
        if name in pinned_names:
            continue
        row = Gtk.ListBoxRow()
        lbl = Gtk.Label(label=name, xalign=0.0)
        row.add(lbl)
        row._meta = (exec_, terminal)
        all_list.add(row)
    all_list.connect(
        "row-activated",
        lambda lb, row: close_and(lambda: run_command(*row._meta)) if hasattr(row, "_meta") else None,
    )
    scrolled.add(all_list)
    left.pack_start(scrolled, True, True, 0)

    # Right pane - system shortcuts
    right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    right.get_style_context().add_class("xp-rightpane")
    right.set_size_request(180, -1)
    body.pack_start(right, False, False, 0)

    right_label = Gtk.Label(label="System", xalign=0.0)
    right_label.get_style_context().add_class("xp-section")
    right.pack_start(right_label, False, False, 0)

    right_list = Gtk.ListBox()
    right_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
    SYSTEM_ITEMS = [
        ("My Computer",        "xdg-open /"),
        ("My Documents",       "xdg-open " + os.path.expanduser("~")),
        ("Pictures",           "xdg-open " + os.path.expanduser("~/Pictures")),
        ("Network Connections","wezterm start --always-new-process -- nmtui"),
        ("Run...",             "/home/abd/.config/waybar/xp-run.py"),
        ("Search",             "/home/abd/.config/waybar/xp-run.py"),
        ("Help and Support",   "xdg-open https://wiki.archlinux.org/"),
        ("Lock Computer",      "hyprlock"),
    ]
    for label, cmd in SYSTEM_ITEMS:
        row = Gtk.ListBoxRow()
        lbl = Gtk.Label(label=label, xalign=0.0)
        row.add(lbl)
        row._cmd = cmd
        right_list.add(row)
    right_list.connect(
        "row-activated",
        lambda lb, row: close_and(lambda: run_command(row._cmd)) if hasattr(row, "_cmd") else None,
    )
    right.pack_start(right_list, True, True, 0)

    # ── Footer ────────────────────────────────────────────────────────────
    footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    footer.get_style_context().add_class("xp-footer")

    logoff_btn = Gtk.Button(label="Log Off")
    logoff_btn.connect(
        "clicked",
        lambda *_: close_and(lambda: run_command("hyprctl dispatch exit"))
    )
    footer.pack_start(logoff_btn, False, False, 0)

    spacer = Gtk.Label()
    spacer.set_hexpand(True)
    footer.pack_start(spacer, True, True, 0)

    shutdown_btn = Gtk.Button(label="Turn Off Computer")
    shutdown_btn.connect(
        "clicked",
        lambda *_: close_and(lambda: run_command("/home/abd/.config/waybar/shutdown-menu.sh"))
    )
    footer.pack_end(shutdown_btn, False, False, 0)
    vbox.pack_start(footer, False, False, 0)

    # Position: bottom-LEFT of primary monitor (above the waybar)
    def on_realize(_w):
        screen = win.get_screen()
        gdk_w = win.get_window()
        if gdk_w is None:
            return
        mon = screen.get_monitor_at_window(gdk_w) if screen.get_n_monitors() > 0 else 0
        geom = screen.get_monitor_geometry(mon)
        wbar_height = 44
        w, h = win.get_size()
        x = geom.x + 4
        y = geom.y + geom.height - wbar_height - h - 4
        win.move(x, y)
    win.connect("realize", on_realize)

    # Esc closes
    def on_key(widget, event):
        if event.keyval == Gdk.KEY_Escape:
            win.close()
    win.connect("key-press-event", on_key)
    win.connect("destroy", Gtk.main_quit)

    win.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
