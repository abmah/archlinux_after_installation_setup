#!/usr/bin/env python3
"""
Windows XP Run dialog with an integrated app launcher.

  - Win+R pops the dialog. Type a name -> the list filters live.
  - Click a row, or press Enter, to launch the highlighted app.
  - Type a raw command (anything that doesn't match an app) and Enter
    runs it via /bin/sh -c, exactly like the XP Run dialog.
  - History is saved in ~/.local/share/xp-run-history.txt.
  - Esc closes.

The dialog is intentionally styled like the XP "Run" window: blue
Luna title bar, gear icon + explanatory text, "Open:" entry, then
the app list below it (a Start-Menu / All Programs feel), with
OK / Cancel / Browse buttons at the bottom.
"""

import gi, os, sys, subprocess, glob, re

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

HISTORY_PATH = os.path.expanduser("~/.local/share/xp-run-history.txt")
HISTORY_LIMIT = 25

XP_CSS = b"""
window.xp-run {
    background-color: #ECE9D8;
    border: 1px solid #0A246A;
}

.xp-titlebar {
    background-image:
        linear-gradient(180deg,
            #0A246A 0%, #0058E6 4%, #3A93FF 9%,
            #0F76E6 16%, #1E64DB 60%, #0050D2 100%);
    color: #FFFFFF;
    padding: 0 6px;
    min-height: 24px;
    border-bottom: 1px solid #0A246A;
}
.xp-titlebar label {
    color: #FFFFFF;
    font-family: "Trebuchet MS", "Tahoma", "Verdana", sans-serif;
    font-weight: bold;
    font-size: 11pt;
    text-shadow: 1px 1px 1px rgba(0,0,0,0.55);
}

.xp-close {
    background-image:
        linear-gradient(180deg, #FF8E70 0%, #E73E1A 50%, #B92500 51%, #DD3B16 100%);
    color: #FFFFFF;
    border: 1px solid #6E0F00;
    border-radius: 3px;
    min-width: 22px;
    min-height: 18px;
    padding: 0 2px;
    margin: 3px;
    font-weight: bold;
    text-shadow: 0 1px 1px rgba(0,0,0,0.6);
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.65),
        inset -1px -1px 0 rgba(0,0,0,0.30);
}
.xp-close:hover {
    background-image:
        linear-gradient(180deg, #FFA98E 0%, #F25531 50%, #C92F0F 51%, #EE5128 100%);
}

.xp-body { background-color: #ECE9D8; padding: 12px; }
.xp-explain, .xp-prompt {
    color: #000000;
    font-family: "Tahoma", "Verdana", sans-serif;
    font-size: 10pt;
}

.xp-entry {
    background-color: #FFFFFF;
    color: #000000;
    border: 1px solid #7F9DB9;
    border-radius: 0;
    padding: 3px 5px;
    font-family: "Tahoma", "Verdana", sans-serif;
    font-size: 10pt;
    box-shadow: inset 1px 1px 0 rgba(112,112,96,0.35);
}
.xp-entry:focus { border-color: #0A246A; }

/* App list - XP file-list look, sunken bezel */
.xp-applist {
    background-color: #FFFFFF;
    color: #000000;
    border: 1px solid #7F9DB9;
    box-shadow:
        inset  1px  1px 0 rgba(112,112,96,0.35),
        inset -1px -1px 0 rgba(255,255,255,0.7);
}

.xp-applist row {
    background-color: transparent;
    color: #000000;
    padding: 3px 6px;
    font-family: "Tahoma", "Verdana", sans-serif;
    font-size: 10pt;
}
.xp-applist row:hover {
    background-color: #316AC5;
    color: #FFFFFF;
}
.xp-applist row:selected {
    background-color: #316AC5;
    color: #FFFFFF;
}

.xp-buttons { background-color: #ECE9D8; padding: 4px 12px 12px 12px; }

.xp-btn {
    background-image:
        linear-gradient(180deg,
            #FFFFFF 0%, #ECE9D8 45%, #D8D2BD 100%);
    color: #000000;
    font-family: "Tahoma", "Verdana", sans-serif;
    font-size: 10pt;
    border: 1px solid #003C74;
    border-radius: 3px;
    padding: 3px 14px;
    margin: 0 4px;
    min-width: 75px;
    text-shadow: none;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.9),
        inset -1px -1px 0 rgba(112,112,96,0.55);
}
.xp-btn:hover {
    background-image:
        linear-gradient(180deg,
            #FFFFFF 0%, #F5F1E2 45%, #DAD5C2 100%);
    border-color: #0A246A;
}
.xp-btn:active {
    background-image:
        linear-gradient(180deg,
            #D4D0C8 0%, #ECE9D8 100%);
    box-shadow:
        inset 1px 1px 0 rgba(112,112,96,0.55),
        inset -1px -1px 0 rgba(255,255,255,0.6);
}
.xp-btn:focus { outline: 1px dotted #000000; outline-offset: -4px; }
"""


# ---- desktop-file loader ---------------------------------------------------

EXEC_PLACEHOLDER = re.compile(r"\s%[fFuUickdDnNvm]")


def parse_desktop_file(path):
    """Return (name, exec, icon, no_display, is_terminal) or None."""
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
            # Earlier paths win (user > local > system) due to our dirs order
            if name not in seen:
                seen[name] = (exec_, icon, terminal)
    apps = sorted(seen.items(), key=lambda kv: kv[0].lower())
    return [(n, *v) for n, v in apps]


# ---- history ---------------------------------------------------------------

def load_history():
    try:
        with open(HISTORY_PATH) as f:
            return [line.rstrip("\n") for line in f if line.strip()][:HISTORY_LIMIT]
    except FileNotFoundError:
        return []


def save_history(cmd):
    items = load_history()
    if cmd in items:
        items.remove(cmd)
    items.insert(0, cmd)
    items = items[:HISTORY_LIMIT]
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        f.write("\n".join(items) + "\n")


# ---- launcher --------------------------------------------------------------

def run_command(cmd, terminal=False):
    if not cmd.strip():
        return False
    save_history(cmd)
    if terminal:
        cmd = f"wezterm start --always-new-process -- sh -c {repr(cmd)}"
    subprocess.Popen(
        ["/usr/bin/sh", "-c", f"setsid {cmd} >/dev/null 2>&1 &"],
        start_new_session=True,
    )
    return True


# ---- UI --------------------------------------------------------------------

def main():
    css = Gtk.CssProvider()
    css.load_from_data(XP_CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    apps = load_apps()                         # [(name, exec, icon, terminal)]

    win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    win.set_decorated(False)
    win.set_skip_taskbar_hint(True)
    win.set_keep_above(True)
    win.set_position(Gtk.WindowPosition.CENTER)
    win.set_default_size(420, 380)
    win.set_resizable(False)
    win.set_title("Run")
    win.set_wmclass("XPMenu", "XPMenu")
    win.get_style_context().add_class("xp-run")

    chosen = {"cmd": None, "terminal": False}

    def submit(cmd, terminal=False):
        chosen["cmd"] = cmd
        chosen["terminal"] = terminal
        win.close()

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    win.add(vbox)

    # Title bar
    titlebar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    titlebar.get_style_context().add_class("xp-titlebar")
    title_lbl = Gtk.Label(label="Run", xalign=0.0)
    title_lbl.set_hexpand(True)
    title_lbl.set_margin_start(8)
    titlebar.pack_start(title_lbl, True, True, 0)
    close_btn = Gtk.Button(label="✕")
    close_btn.get_style_context().add_class("xp-close")
    close_btn.set_focus_on_click(False)
    close_btn.connect("clicked", lambda *_: submit(None))
    titlebar.pack_end(close_btn, False, False, 0)
    vbox.pack_start(titlebar, False, False, 0)

    def begin_move(widget, event):
        if event.button == 1:
            win.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
        return False
    titlebar.connect("button-press-event", begin_move)

    # Body
    body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    body.get_style_context().add_class("xp-body")
    vbox.pack_start(body, True, True, 0)

    # icon + explainer
    explain_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    icon = Gtk.Image.new_from_icon_name("system-run", Gtk.IconSize.DIALOG)
    explain_row.pack_start(icon, False, False, 0)
    explain_lbl = Gtk.Label(
        label="Type the name of a program, folder, document, or\n"
              "Internet resource, and the system will open it for you.",
        xalign=0.0)
    explain_lbl.get_style_context().add_class("xp-explain")
    explain_row.pack_start(explain_lbl, True, True, 0)
    body.pack_start(explain_row, False, False, 0)

    # Open: + entry
    open_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    open_lbl = Gtk.Label(label="Open:", xalign=0.0)
    open_lbl.get_style_context().add_class("xp-prompt")
    open_lbl.set_size_request(50, -1)
    open_row.pack_start(open_lbl, False, False, 0)
    entry = Gtk.Entry()
    entry.get_style_context().add_class("xp-entry")
    entry.set_hexpand(True)
    open_row.pack_start(entry, True, True, 0)
    body.pack_start(open_row, False, False, 0)

    # App list (filterable)
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.set_min_content_height(180)
    scrolled.set_vexpand(True)
    listbox = Gtk.ListBox()
    listbox.get_style_context().add_class("xp-applist")
    listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    scrolled.add(listbox)
    body.pack_start(scrolled, True, True, 0)

    # Helper that builds a row
    def make_row(name, exec_, terminal):
        row = Gtk.ListBoxRow()
        h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        # tiny icon column - just the name now (icon lookup is slow)
        lbl = Gtk.Label(label=name, xalign=0.0)
        lbl.set_margin_top(1); lbl.set_margin_bottom(1)
        lbl.set_margin_start(4); lbl.set_margin_end(4)
        h.pack_start(lbl, True, True, 0)
        row.add(h)
        row._meta = (name, exec_, terminal)
        return row

    def populate(filter_str=""):
        for child in listbox.get_children():
            listbox.remove(child)
        f = filter_str.lower().strip()
        # History entries get a "*" prefix label (so user sees their custom commands)
        for h in load_history():
            if not f or f in h.lower():
                row = Gtk.ListBoxRow()
                lbl = Gtk.Label(label=f"  ↻  {h}", xalign=0.0)
                lbl.set_margin_top(1); lbl.set_margin_bottom(1)
                row.add(lbl)
                row._meta = (h, h, False)  # exec the raw text
                listbox.add(row)
        for name, exec_, _icon, terminal in apps:
            if not f or f in name.lower():
                listbox.add(make_row(name, exec_, terminal))
        listbox.show_all()
        first = listbox.get_row_at_index(0)
        if first:
            listbox.select_row(first)

    populate()

    def on_entry_changed(_e):
        populate(entry.get_text())
    entry.connect("changed", on_entry_changed)

    def submit_selection():
        row = listbox.get_selected_row()
        text = entry.get_text().strip()
        if row is not None and hasattr(row, "_meta"):
            name, exec_, terminal = row._meta
            submit(exec_, terminal)
        elif text:
            submit(text, False)
        else:
            submit(None)

    def on_entry_activate(*_):
        submit_selection()
    entry.connect("activate", on_entry_activate)

    listbox.connect(
        "row-activated",
        lambda lb, row: submit(row._meta[1], row._meta[2]) if hasattr(row, "_meta") else None,
    )

    # Button row
    btnrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    btnrow.get_style_context().add_class("xp-buttons")
    spacer = Gtk.Label()
    spacer.set_hexpand(True)
    btnrow.pack_start(spacer, True, True, 0)

    ok_btn = Gtk.Button(label="OK")
    ok_btn.get_style_context().add_class("xp-btn")
    ok_btn.connect("clicked", lambda *_: submit_selection())
    btnrow.pack_start(ok_btn, False, False, 0)

    cancel_btn = Gtk.Button(label="Cancel")
    cancel_btn.get_style_context().add_class("xp-btn")
    cancel_btn.connect("clicked", lambda *_: submit(None))
    btnrow.pack_start(cancel_btn, False, False, 0)

    def on_browse(*_):
        chooser = Gtk.FileChooserDialog(
            title="Browse",
            parent=win,
            action=Gtk.FileChooserAction.OPEN,
            buttons=("Cancel", Gtk.ResponseType.CANCEL,
                     "Open", Gtk.ResponseType.ACCEPT),
        )
        chooser.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        if chooser.run() == Gtk.ResponseType.ACCEPT:
            entry.set_text(chooser.get_filename())
        chooser.destroy()
    browse_btn = Gtk.Button(label="Browse...")
    browse_btn.get_style_context().add_class("xp-btn")
    browse_btn.connect("clicked", on_browse)
    btnrow.pack_start(browse_btn, False, False, 0)
    vbox.pack_start(btnrow, False, False, 0)

    # Keyboard navigation: arrow keys move list selection while focus is in entry
    def on_key(widget, event):
        if event.keyval == Gdk.KEY_Escape:
            submit(None)
            return True
        if event.keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            row = listbox.get_selected_row()
            i = row.get_index() if row else 0
            count = len(listbox.get_children())
            if count == 0:
                return True
            i = (i + (1 if event.keyval == Gdk.KEY_Down else -1)) % count
            new = listbox.get_row_at_index(i)
            listbox.select_row(new)
            new.grab_focus()
            entry.grab_focus()  # keep typing focus
            return True
        return False
    win.connect("key-press-event", on_key)
    win.connect("destroy", Gtk.main_quit)

    entry.grab_focus()
    win.show_all()
    Gtk.main()

    if chosen["cmd"]:
        run_command(chosen["cmd"], chosen["terminal"])
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
