#!/usr/bin/env python3
"""
xp-desktop - Windows XP-style desktop layer for Hyprland (Wayland).

Renders icons from ~/Desktop on a gtk-layer-shell background layer:
  - 48x48 XP icons (uses the installed windows-xp-icon-theme)
  - White Tahoma 9pt labels with the classic XP black drop shadow
  - Click to select, double-click to open, drag to reposition
  - XP-styled right-click context menus on icons AND on empty desktop
  - Live ~/Desktop file-watching so new/removed files appear instantly
  - Positions persisted to ~/.config/xp-desktop/positions.json

Run me:
    ./desktop.py
Hyprland: add  exec-once = ~/.config/xp-desktop/desktop.py
"""

import gi, os, json, subprocess, mimetypes, shutil, time, sys, html
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GdkPixbuf, GtkLayerShell, GLib, Gio, Pango


# ==========================================================================
# paths + state
# ==========================================================================

HOME        = os.path.expanduser("~")
DESKTOP_DIR = os.path.join(HOME, "Desktop")
STATE_DIR   = os.path.join(HOME, ".config", "xp-desktop")
POS_FILE    = os.path.join(STATE_DIR, "positions.json")

os.makedirs(DESKTOP_DIR, exist_ok=True)
os.makedirs(STATE_DIR,   exist_ok=True)

ICON_W   = 76          # cell width
ICON_H   = 92          # cell height
ICON_PX  = 48          # actual pixmap size
GRID_DX  = 88
GRID_DY  = 96
MARGIN_X = 16          # left margin of the icon grid
MARGIN_Y = 16          # top margin

WAYBAR_RESERVE_BOTTOM = 50  # don't drop icons under the taskbar


# ==========================================================================
# XP CSS
# ==========================================================================

XP_CSS = b"""
/* Desktop background is transparent - wallpaper shows through */
window.xp-desktop { background-color: rgba(0,0,0,0); }

/* Icon labels - white Tahoma with the classic XP black drop shadow.
   We render the shadow ourselves via Pango markup; this CSS just sets the
   font + transparent background. */
.xp-icon-label { background-color: transparent; }

/* Cell wraps the icon + label, gets the selection rectangle + focus ring */
.xp-icon-cell {
    background-color: transparent;
    border: 1px dotted transparent;
    padding: 2px;
}
.xp-icon-cell.selected {
    /* XP-blue translucent fill, exactly like XP "selected" item */
    background-color: rgba(49, 106, 197, 0.40);
    /* Classic XP focus ring: 1px dotted dark-gray "marching ants" */
    border: 1px dotted #1A1A1A;
}

/* ----- Context menu (authentic Windows XP look) ---------------------- */
/* Outer chrome: thin gray border, white interior, with a 24px CREAM
   icon gutter on the left exactly like Explorer's context menu. The
   gutter is painted via a left-to-right linear gradient on the menu
   background, then each item is padded so its label clears the gutter. */
menu.xp-menu {
    background-color: #FFFFFF;
    background-image: linear-gradient(
        to right,
        #ECE9D8 0px,
        #ECE9D8 24px,
        #D4D0C8 24px,
        #D4D0C8 25px,
        #FFFFFF 25px,
        #FFFFFF 100%);
    border: 1px solid #6D6D6D;
    padding: 2px 0;
    color: #000000;
}

menu.xp-menu separator {
    background-color: #D4D0C8;
    min-height: 1px;
    margin: 3px 2px 3px 28px;   /* don't cross into the icon gutter */
    padding: 0;
}

menu.xp-menu menuitem {
    background-color: transparent;
    background-image: none;
    padding: 4px 28px 4px 4px;  /* room for submenu arrow on right */
    color: #000000;
    font-family: "Tahoma";
    font-size: 9pt;
    border: none;
    text-shadow: none;
}

/* HOVER = full XP-blue row, white text. Solid color, not gradient. */
menu.xp-menu menuitem:hover,
menu.xp-menu menuitem:selected {
    background-color: #316AC5;
    background-image: none;
    color: #FFFFFF;
}
menu.xp-menu menuitem:hover label,
menu.xp-menu menuitem:selected label {
    color: #FFFFFF;
}

menu.xp-menu menuitem:disabled {
    color: #888888;
}
menu.xp-menu menuitem:disabled label { color: #888888; }

menu.xp-menu menuitem label {
    color: #000000;
    background-color: transparent;
}

/* Submenu indicator (the little right-pointing arrow) */
menu.xp-menu menuitem arrow {
    min-width: 8px;
    min-height: 8px;
    color: #000000;
    -gtk-icon-source: -gtk-icontheme("pan-end-symbolic");
}
menu.xp-menu menuitem:hover arrow,
menu.xp-menu menuitem:selected arrow {
    color: #FFFFFF;
}
"""


# ==========================================================================
# helpers
# ==========================================================================

def run_detached(cmd):
    """Spawn cmd (string) without waiting; cmd is shell-parsed by Popen=False."""
    try:
        subprocess.Popen(cmd, start_new_session=True,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL)
    except Exception as e:
        print(f"[xp-desktop] run failed: {cmd!r}: {e}", file=sys.stderr)


def load_positions():
    try:
        with open(POS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_positions(d):
    try:
        with open(POS_FILE, "w") as f:
            json.dump(d, f, indent=2)
    except Exception as e:
        print(f"[xp-desktop] save positions: {e}", file=sys.stderr)


def parse_desktop_file(path):
    """Return dict with Name, Exec, Icon, Terminal for a .desktop file."""
    info = {"Name": os.path.basename(path), "Exec": "", "Icon": "", "Terminal": False}
    try:
        in_entry = False
        with open(path) as f:
            for line in f:
                s = line.strip()
                if s.startswith("[") and s.endswith("]"):
                    in_entry = (s == "[Desktop Entry]")
                    continue
                if not in_entry or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                if k in ("Name", "Exec", "Icon"):
                    info[k] = v
                elif k == "Terminal":
                    info["Terminal"] = (v.lower() == "true")
    except Exception:
        pass
    return info


def icon_name_for(path):
    """Decide the icon-theme name for any filesystem path."""
    name = os.path.basename(path).lower()
    if os.path.isdir(path):
        special = {
            "documents":  "folder-documents",
            "pictures":   "folder-pictures",
            "music":      "folder-music",
            "videos":     "folder-videos",
            "downloads":  "folder-download",
            "desktop":    "user-desktop",
            "trash":      "user-trash",
        }
        return special.get(name, "folder")
    if name.endswith(".desktop"):
        info = parse_desktop_file(path)
        if info["Icon"]:
            return info["Icon"]
        return "application-x-executable"

    mime, _ = mimetypes.guess_type(path)
    if mime:
        major, _, minor = mime.partition("/")
        if major == "image":  return "image-x-generic"
        if major == "video":  return "video-x-generic"
        if major == "audio":  return "audio-x-generic"
        if major == "text":   return "text-x-generic"
        if minor in ("pdf", "x-pdf"):     return "application-pdf"
        if "zip" in minor or "tar" in minor: return "package-x-generic"
    return "text-x-generic"


def pixbuf_for(icon_name, size=ICON_PX):
    """Look up an icon by name in the system theme, falling back through
    common synonyms before returning a generic placeholder."""
    theme = Gtk.IconTheme.get_default()
    candidates = [icon_name]
    # Common fallback chains - XP icon theme sometimes uses old names
    if icon_name == "folder":
        candidates += ["folder", "gnome-fs-directory", "inode-directory"]
    elif icon_name == "user-trash":
        candidates += ["edittrash", "user-trash-full", "gnome-stock-trash"]
    elif icon_name == "image-x-generic":
        candidates += ["image", "gnome-mime-image"]
    elif icon_name == "text-x-generic":
        candidates += ["text-x-generic", "txt", "gnome-mime-text-plain"]
    candidates += ["text-x-generic", "unknown"]
    for c in candidates:
        if not c:
            continue
        try:
            pb = theme.load_icon(c, size, Gtk.IconLookupFlags.FORCE_SIZE)
            if pb:
                return pb
        except Exception:
            continue
    # last resort: blank pixmap
    return GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, size, size)


def open_path(path):
    """Open a file/folder/.desktop the right way."""
    if path.endswith(".desktop") and os.path.isfile(path):
        info = parse_desktop_file(path)
        exec_line = info.get("Exec", "")
        if exec_line:
            # Strip .desktop %f/%F/%u/%U field codes
            import re as _re
            cmd = _re.sub(r"\s*%[fFuUdDnNickvm]\s*", " ", exec_line).strip()
            if info.get("Terminal"):
                cmd = f"wezterm start -- bash -lc {GLib.shell_quote(cmd)}"
            try:
                subprocess.Popen(["sh", "-c", cmd], start_new_session=True,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 stdin=subprocess.DEVNULL)
                return
            except Exception as e:
                print(f"[xp-desktop] exec {cmd!r}: {e}", file=sys.stderr)
        # Fallback to gtk-launch by app id
        name = os.path.basename(path)[:-len(".desktop")]
        run_detached(["gtk-launch", name])
        return
    if os.path.isdir(path):
        run_detached(["thunar", path])
        return
    run_detached(["xdg-open", path])


def trash_path(path):
    """Move to ~/.local/share/Trash; fall back to outright delete if it fails."""
    try:
        gfile = Gio.File.new_for_path(path)
        gfile.trash(None)
        return True
    except GLib.Error:
        return False


# ==========================================================================
# XP-styled context menu builder
# ==========================================================================

class XPMenu(Gtk.Menu):
    def __init__(self):
        super().__init__()
        self.get_style_context().add_class("xp-menu")

    def add_item(self, label, callback=None, bold=False, enabled=True, icon=None):
        item = Gtk.MenuItem()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        # 16x16 icon centred in the 24px cream gutter
        img = Gtk.Image()
        if icon:
            try:
                pb = Gtk.IconTheme.get_default().load_icon(
                    icon, 16, Gtk.IconLookupFlags.FORCE_SIZE)
                img.set_from_pixbuf(pb)
            except Exception:
                pass
        img.set_size_request(20, 16)            # leaves ~4px breathing room
        img.set_margin_start(2)
        img.set_margin_end(8)                   # clears the 24px gutter
        box.pack_start(img, False, False, 0)

        # Tahoma label, optionally bold for the default action
        lbl = Gtk.Label()
        weight = "bold" if bold else "normal"
        # Use Pango markup so colour can't be flipped by the system theme
        lbl.set_markup(
            f'<span font_desc="Tahoma 9" weight="{weight}" foreground="#000000">'
            f'{GLib.markup_escape_text(label)}</span>')
        lbl.set_xalign(0.0)
        lbl.set_hexpand(True)
        box.pack_start(lbl, True, True, 0)
        item.add(box)
        item.set_sensitive(enabled)
        if callback:
            item.connect("activate", lambda *_: callback())

        # Flip label colour on hover (Pango fixes the foreground, so we have
        # to re-render the markup when the item enters/leaves state).
        def _on_state(_w, _flags):
            on = bool(item.get_state_flags() & (Gtk.StateFlags.PRELIGHT |
                                                Gtk.StateFlags.SELECTED))
            fg = "#FFFFFF" if on else ("#888888" if not enabled else "#000000")
            lbl.set_markup(
                f'<span font_desc="Tahoma 9" weight="{weight}" foreground="{fg}">'
                f'{GLib.markup_escape_text(label)}</span>')
        item.connect("state-flags-changed", _on_state)

        self.append(item)
        return item

    def add_separator(self):
        self.append(Gtk.SeparatorMenuItem())

    def popup_at(self, event):
        self.show_all()
        try:
            self.popup_at_pointer(event)
        except Exception:
            self.popup(None, None, None, None,
                       event.button if event else 0,
                       event.time if event else 0)


# ==========================================================================
# Icon widget
# ==========================================================================

class XPIcon(Gtk.EventBox):
    def __init__(self, desktop, path):
        super().__init__()
        self.desktop = desktop
        self.path = path
        self.selected = False
        self._drag_start = None
        self._dragging = False
        self.set_size_request(ICON_W, ICON_H)
        # CSS background/border on EventBox is only painted when the widget
        # owns a real GDK window -- visible_window=False disables this and
        # was hiding the XP selection rectangle entirely.
        self.set_visible_window(True)
        # Allow rgba background -> transparent until selected
        self.set_app_paintable(True)
        self.get_style_context().add_class("xp-icon-cell")
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        v.set_halign(Gtk.Align.CENTER)
        self.add(v)

        # Icon image
        self.img = Gtk.Image()
        v.pack_start(self.img, False, False, 0)

        # Label - white Tahoma w/ XP black shadow via Pango markup
        self.label = Gtk.Label()
        self.label.get_style_context().add_class("xp-icon-label")
        self.label.set_justify(Gtk.Justification.CENTER)
        self.label.set_max_width_chars(12)
        self.label.set_line_wrap(True)
        self.label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.label.set_lines(2)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        v.pack_start(self.label, False, False, 0)

        self.refresh()

        self.connect("button-press-event",   self._on_press)
        self.connect("motion-notify-event",  self._on_motion)
        self.connect("button-release-event", self._on_release)

    # ---- visuals ---------------------------------------------------------

    def refresh(self):
        # display name
        name = os.path.basename(self.path)
        if name.endswith(".desktop"):
            info = parse_desktop_file(self.path)
            if info["Name"]:
                name = info["Name"]
        self._set_label_markup(name)
        # icon pixbuf
        self.img.set_from_pixbuf(pixbuf_for(icon_name_for(self.path)))

    def _set_label_markup(self, text, selected=False):
        """Match real XP icon labels:
          unselected -> white Tahoma text over a translucent black tile
                        (readable on any wallpaper)
          selected   -> white Tahoma text over a SOLID XP-blue tile,
                        exactly like Windows XP's icon-selection paint."""
        safe = GLib.markup_escape_text(text)
        if selected:
            self.label.set_markup(
                f'<span font_desc="Tahoma 9" foreground="#FFFFFF" '
                f'background="#316AC5">  {safe}  </span>')
        else:
            self.label.set_markup(
                f'<span font_desc="Tahoma 9" foreground="#FFFFFF" '
                f'background="#00000080">  {safe}  </span>')

    def set_selected(self, sel):
        if sel == self.selected:
            return
        self.selected = sel
        ctx = self.get_style_context()
        if sel:
            ctx.add_class("selected")
        else:
            ctx.remove_class("selected")
        # Re-render label tile so it matches selection state
        name = os.path.basename(self.path)
        if name.endswith(".desktop"):
            info = parse_desktop_file(self.path)
            if info.get("Name"):
                name = info["Name"]
        self._set_label_markup(name, selected=sel)

    # ---- input -----------------------------------------------------------

    def _on_press(self, _w, event):
        if event.button == 1:
            self._drag_start = (event.x_root, event.y_root,
                                self.desktop.icon_pos.get(self.path, (0, 0)))
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                self.activate()
                return True
            self.desktop.select_only(self)
            return True
        if event.button == 3:
            self.desktop.select_only(self)
            self._show_menu(event)
            return True
        return False

    def _on_motion(self, _w, event):
        if not self._drag_start:
            return False
        dx = event.x_root - self._drag_start[0]
        dy = event.y_root - self._drag_start[1]
        if not self._dragging and (abs(dx) > 4 or abs(dy) > 4):
            self._dragging = True
        if self._dragging:
            x0, y0 = self._drag_start[2]
            self.desktop.move_icon(self, x0 + dx, y0 + dy)
        return False

    def _on_release(self, _w, event):
        if self._dragging:
            self.desktop.snap_icon(self)
            self.desktop.save_positions()
        self._drag_start = None
        self._dragging = False
        return False

    # ---- ops -------------------------------------------------------------

    def activate(self):
        open_path(self.path)

    def rename(self):
        dialog = Gtk.Dialog(title="Rename", modal=True)
        dialog.set_default_size(320, 60)
        entry = Gtk.Entry()
        entry.set_text(os.path.basename(self.path))
        entry.set_activates_default(True)
        dialog.get_content_area().pack_start(entry, True, True, 6)
        dialog.add_button("OK", Gtk.ResponseType.OK)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        resp = dialog.run()
        new_name = entry.get_text().strip()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK and new_name and new_name != os.path.basename(self.path):
            new_path = os.path.join(os.path.dirname(self.path), new_name)
            try:
                os.rename(self.path, new_path)
            except Exception as e:
                print(f"[xp-desktop] rename: {e}", file=sys.stderr)

    def delete_to_trash(self):
        if trash_path(self.path):
            return
        # ask before hard-delete
        d = Gtk.MessageDialog(
            modal=True, message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"Couldn't move to trash. Permanently delete '{os.path.basename(self.path)}'?")
        if d.run() == Gtk.ResponseType.OK:
            try:
                if os.path.isdir(self.path) and not os.path.islink(self.path):
                    shutil.rmtree(self.path)
                else:
                    os.remove(self.path)
            except Exception as e:
                print(f"[xp-desktop] delete: {e}", file=sys.stderr)
        d.destroy()

    def copy_path_to_clipboard(self):
        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        cb.set_text(self.path, -1)

    def show_in_thunar(self):
        run_detached(["thunar", os.path.dirname(self.path)])

    def show_properties(self):
        try:
            stat = os.stat(self.path)
            size_mb = stat.st_size / 1024
            unit = "KB" if size_mb < 1024 else "MB"
            if size_mb >= 1024: size_mb = size_mb / 1024
            mtime = time.strftime("%Y-%m-%d %H:%M:%S",
                                  time.localtime(stat.st_mtime))
            msg = (f"Name:     {os.path.basename(self.path)}\n"
                   f"Type:     {'Folder' if os.path.isdir(self.path) else 'File'}\n"
                   f"Location: {os.path.dirname(self.path)}\n"
                   f"Size:     {size_mb:.1f} {unit}\n"
                   f"Modified: {mtime}")
            d = Gtk.MessageDialog(
                modal=True, message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK, text="Properties")
            d.format_secondary_text(msg)
            d.run(); d.destroy()
        except Exception as e:
            print(f"[xp-desktop] properties: {e}", file=sys.stderr)

    # ---- right-click menu -----------------------------------------------

    def _show_menu(self, event):
        m = XPMenu()
        is_dir = os.path.isdir(self.path)
        m.add_item("Open", self.activate, bold=True,
                   icon="folder-open" if is_dir else "document-open")
        if is_dir:
            m.add_item("Explore", self.activate, icon="folder")
            m.add_item("Search...",
                       lambda: run_detached(["thunar", self.path]),
                       icon="system-search")
        else:
            m.add_item("Open With...",
                       lambda: run_detached(
                           ["xdg-mime", "query", "default",
                            mimetypes.guess_type(self.path)[0] or "text/plain"]),
                       icon="document-open")
        m.add_separator()
        m.add_item("Cut",  lambda: self.copy_path_to_clipboard(), icon="edit-cut")
        m.add_item("Copy", lambda: self.copy_path_to_clipboard(), icon="edit-copy")
        m.add_separator()
        m.add_item("Create Shortcut",
                   lambda: self._make_shortcut(), icon="emblem-symbolic-link")
        m.add_item("Delete",  self.delete_to_trash, icon="edit-delete")
        m.add_item("Rename", self.rename, icon="document-edit")
        m.add_separator()
        m.add_item("Show in File Manager", self.show_in_thunar, icon="system-file-manager")
        m.add_item("Properties", self.show_properties, icon="document-properties")
        m.popup_at(event)

    def _make_shortcut(self):
        link = self.path + " - Shortcut"
        try:
            os.symlink(self.path, link)
        except Exception as e:
            print(f"[xp-desktop] symlink: {e}", file=sys.stderr)


# ==========================================================================
# Main desktop window (gtk-layer-shell BACKGROUND layer)
# ==========================================================================

class XPDesktop(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.get_style_context().add_class("xp-desktop")

        # Make this a Wayland layer-shell BACKGROUND surface that fills the screen.
        GtkLayerShell.init_for_window(self)
        # BOTTOM (not BACKGROUND): sits *above* hyprpaper's wallpaper layer
        # but still below every normal application window. Using BACKGROUND
        # caused hyprpaper to clobber us when it re-attached its surface
        # (e.g. on wallpaper change).
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
        GtkLayerShell.set_namespace(self, "xp-desktop")
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self, edge, True)
        # We want to be drawn under everything but still receive input on bare
        # background -> the BACKGROUND layer normally takes input only when no
        # foreground client is over it, which is exactly what we want.
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_exclusive_zone(self, 0)

        # Transparent surface
        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)

        # Background event capture (right-click on empty area)
        self.bg = Gtk.EventBox()
        self.bg.set_visible_window(False)
        self.bg.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.bg.connect("button-press-event", self._on_bg_press)

        # Free-positioned icon container
        self.fixed = Gtk.Fixed()
        self.bg.add(self.fixed)
        self.add(self.bg)

        # state
        self.icons     = {}                  # path -> XPIcon
        self.icon_pos  = load_positions()    # path -> (x, y)
        self.selected  = None

        # Initial scan + live watch
        self._seed_defaults()
        self.scan()
        self._monitor = Gio.File.new_for_path(DESKTOP_DIR) \
                            .monitor_directory(Gio.FileMonitorFlags.NONE, None)
        self._monitor.connect("changed", self._on_dir_changed)

        self.connect("destroy", lambda *_: Gtk.main_quit())

    # ---- defaults (first-launch shortcuts) -------------------------------

    def _seed_defaults(self):
        """If ~/Desktop has nothing yet, drop a handful of useful XP-flavored
        shortcuts so the user has something to look at."""
        try:
            existing = [n for n in os.listdir(DESKTOP_DIR) if not n.startswith(".")]
        except Exception:
            existing = []
        if existing:
            return

        candidates = [
            ("My Computer.desktop",  "Computer",          "thunar /",                 "computer"),
            ("My Documents.desktop", "My Documents",      f"thunar {HOME}/Documents", "folder-documents"),
            ("Internet.desktop",     "Internet",          "brave",                    "web-browser"),
            ("WezTerm.desktop",      "WezTerm",           "wezterm",                  "utilities-terminal"),
            ("File Manager.desktop", "File Manager",      "thunar",                   "system-file-manager"),
            ("Pictures.desktop",     "Pictures",          f"thunar {HOME}/Pictures",  "folder-pictures"),
        ]
        for fname, name, exec_cmd, icon in candidates:
            # Skip exec'ables that aren't installed
            head = exec_cmd.split()[0]
            if not shutil.which(head):
                continue
            path = os.path.join(DESKTOP_DIR, fname)
            try:
                with open(path, "w") as f:
                    f.write(
                        "[Desktop Entry]\n"
                        "Type=Application\n"
                        f"Name={name}\n"
                        f"Exec={exec_cmd}\n"
                        f"Icon={icon}\n"
                        "Terminal=false\n"
                    )
                os.chmod(path, 0o755)
            except Exception as e:
                print(f"[xp-desktop] seed {fname}: {e}", file=sys.stderr)

    # ---- scan / sync ----------------------------------------------------

    def scan(self):
        try:
            files = sorted(os.listdir(DESKTOP_DIR))
        except Exception:
            files = []
        wanted = {os.path.join(DESKTOP_DIR, f)
                  for f in files if not f.startswith(".")}

        # remove icons for gone files
        for p in list(self.icons.keys()):
            if p not in wanted:
                self.fixed.remove(self.icons[p])
                del self.icons[p]
                self.icon_pos.pop(p, None)

        # add icons for new files
        for p in sorted(wanted):
            if p in self.icons:
                self.icons[p].refresh()
                continue
            ic = XPIcon(self, p)
            self.icons[p] = ic
            x, y = self._next_grid_slot()
            self.icon_pos.setdefault(p, (x, y))
            self.fixed.put(ic, *self.icon_pos[p])
            ic.show_all()

        self.save_positions()

    def _on_dir_changed(self, _mon, _f, _o, _evt):
        self.scan()

    # ---- layout helpers --------------------------------------------------

    def _next_grid_slot(self):
        """Find the next empty grid cell (top-down, then left-right)."""
        screen = Gdk.Screen.get_default()
        h = screen.get_height() - WAYBAR_RESERVE_BOTTOM - MARGIN_Y * 2
        w = screen.get_width()  - MARGIN_X * 2
        cols = max(1, w // GRID_DX)
        rows = max(1, h // GRID_DY)
        used = {(int((x - MARGIN_X) / GRID_DX), int((y - MARGIN_Y) / GRID_DY))
                for x, y in self.icon_pos.values()}
        for col in range(cols):
            for row in range(rows):
                if (col, row) not in used:
                    return (MARGIN_X + col * GRID_DX, MARGIN_Y + row * GRID_DY)
        return (MARGIN_X, MARGIN_Y)

    def move_icon(self, icon, x, y):
        self.fixed.move(icon, int(x), int(y))
        self.icon_pos[icon.path] = (int(x), int(y))

    def snap_icon(self, icon):
        x, y = self.icon_pos[icon.path]
        col = max(0, round((x - MARGIN_X) / GRID_DX))
        row = max(0, round((y - MARGIN_Y) / GRID_DY))
        x = MARGIN_X + col * GRID_DX
        y = MARGIN_Y + row * GRID_DY
        self.fixed.move(icon, x, y)
        self.icon_pos[icon.path] = (x, y)

    def save_positions(self):
        save_positions({p: list(v) for p, v in self.icon_pos.items()})

    # ---- selection -------------------------------------------------------

    def select_only(self, icon):
        if self.selected is icon:
            return
        if self.selected is not None:
            self.selected.set_selected(False)
        self.selected = icon
        if icon is not None:
            icon.set_selected(True)

    def deselect(self):
        self.select_only(None)

    # ---- desktop right-click ---------------------------------------------

    def _on_bg_press(self, _w, event):
        if event.button == 1:
            self.deselect()
            return False
        if event.button == 3:
            self.deselect()
            self._show_desktop_menu(event)
            return True
        return False

    def _show_desktop_menu(self, event):
        m = XPMenu()

        # View submenu
        view = XPMenu()
        view.add_item("Large Icons", lambda: None, enabled=False)
        view.add_item("Icons",       lambda: None, bold=True)
        view.add_item("List",        lambda: None, enabled=False)
        view_item = m.add_item("View", icon="zoom-fit-best")
        view_item.set_submenu(view)

        # Arrange Icons By submenu
        arrange = XPMenu()
        arrange.add_item("Name",          lambda: self.arrange_by("name"))
        arrange.add_item("Size",          lambda: self.arrange_by("size"))
        arrange.add_item("Type",          lambda: self.arrange_by("type"))
        arrange.add_item("Modified",      lambda: self.arrange_by("mtime"))
        arrange.add_separator()
        arrange.add_item("Auto Arrange",  lambda: self.arrange_by("name"))
        arrange.add_item("Align to Grid", lambda: self.align_all())
        arrange_item = m.add_item("Arrange Icons By", icon="view-sort-ascending")
        arrange_item.set_submenu(arrange)

        m.add_item("Refresh", self.scan, icon="view-refresh")
        m.add_separator()
        m.add_item("Paste",          lambda: self._paste_clipboard(),     icon="edit-paste")
        m.add_item("Paste Shortcut", lambda: self._paste_clipboard(link=True),
                   icon="emblem-symbolic-link")
        m.add_separator()

        # New submenu
        new = XPMenu()
        new.add_item("Folder",        lambda: self.create_new("folder"),    icon="folder")
        new.add_item("Shortcut",      lambda: self.create_new("shortcut"),  icon="emblem-symbolic-link")
        new.add_item("Text Document", lambda: self.create_new("text"),      icon="text-x-generic")
        new_item = m.add_item("New", icon="document-new")
        new_item.set_submenu(new)

        m.add_separator()
        m.add_item("Open Terminal Here",
                   lambda: run_detached(["wezterm", "start", "--cwd", DESKTOP_DIR]),
                   icon="utilities-terminal")
        m.add_item("Properties", self._desktop_props, icon="document-properties")
        m.popup_at(event)

    # ---- New ... actions -------------------------------------------------

    def _unique_path(self, base, ext=""):
        i = 1
        p = os.path.join(DESKTOP_DIR, f"{base}{ext}")
        while os.path.exists(p):
            p = os.path.join(DESKTOP_DIR, f"{base} ({i}){ext}")
            i += 1
        return p

    def create_new(self, kind):
        if kind == "folder":
            p = self._unique_path("New Folder")
            try:
                os.makedirs(p, exist_ok=False)
            except Exception as e:
                print(f"[xp-desktop] new folder: {e}", file=sys.stderr)
        elif kind == "text":
            p = self._unique_path("New Text Document", ".txt")
            try:
                open(p, "w").close()
            except Exception as e:
                print(f"[xp-desktop] new text: {e}", file=sys.stderr)
        elif kind == "shortcut":
            # Prompt for a target path
            d = Gtk.Dialog(title="Create Shortcut", modal=True)
            d.set_default_size(400, 70)
            e = Gtk.Entry()
            e.set_placeholder_text("Command or path (e.g. brave, /home/abd/Documents)")
            e.set_activates_default(True)
            d.get_content_area().pack_start(e, True, True, 8)
            d.add_button("Cancel", Gtk.ResponseType.CANCEL)
            d.add_button("OK",     Gtk.ResponseType.OK)
            d.set_default_response(Gtk.ResponseType.OK)
            d.show_all()
            resp = d.run()
            target = e.get_text().strip()
            d.destroy()
            if resp != Gtk.ResponseType.OK or not target:
                return
            p = self._unique_path("New Shortcut", ".desktop")
            with open(p, "w") as f:
                f.write("[Desktop Entry]\nType=Application\n"
                        f"Name=New Shortcut\nExec={target}\n"
                        "Icon=application-x-executable\nTerminal=false\n")
            os.chmod(p, 0o755)

    # ---- arrange ---------------------------------------------------------

    def arrange_by(self, key):
        items = list(self.icons.values())
        def keyfn(ic):
            try: st = os.stat(ic.path)
            except: st = None
            if key == "name":  return os.path.basename(ic.path).lower()
            if key == "size":  return -(st.st_size if st else 0)
            if key == "mtime": return -(st.st_mtime if st else 0)
            if key == "type":  return os.path.splitext(ic.path)[1].lower()
            return ic.path
        items.sort(key=keyfn)
        for n, ic in enumerate(items):
            x, y = self._slot_for_index(n)
            self.move_icon(ic, x, y)
        self.save_positions()

    def _slot_for_index(self, n):
        h = Gdk.Screen.get_default().get_height() \
            - WAYBAR_RESERVE_BOTTOM - MARGIN_Y * 2
        rows = max(1, h // GRID_DY)
        col, row = divmod(n, rows)
        return (MARGIN_X + col * GRID_DX, MARGIN_Y + row * GRID_DY)

    def align_all(self):
        for ic in self.icons.values():
            self.snap_icon(ic)
        self.save_positions()

    # ---- paste / props (best-effort) -------------------------------------

    def _paste_clipboard(self, link=False):
        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        text = cb.wait_for_text()
        if not text or not os.path.exists(text):
            return
        dst = os.path.join(DESKTOP_DIR, os.path.basename(text))
        if dst == text:
            dst = self._unique_path(os.path.splitext(os.path.basename(text))[0],
                                    os.path.splitext(text)[1])
        try:
            if link:
                os.symlink(text, dst)
            elif os.path.isdir(text):
                shutil.copytree(text, dst)
            else:
                shutil.copy2(text, dst)
        except Exception as e:
            print(f"[xp-desktop] paste: {e}", file=sys.stderr)

    def _desktop_props(self):
        d = Gtk.MessageDialog(
            modal=True, message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK, text="Display Properties")
        screen = Gdk.Screen.get_default()
        d.format_secondary_text(
            f"Resolution: {screen.get_width()} x {screen.get_height()} pixels\n"
            f"Items on Desktop: {len(self.icons)}\n"
            f"Theme: Windows XP Luna")
        d.run(); d.destroy()


# ==========================================================================
# main
# ==========================================================================

def main():
    css = Gtk.CssProvider()
    css.load_from_data(XP_CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    win = XPDesktop()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
