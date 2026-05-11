#!/usr/bin/env python3
"""
xp-titlebar - Draws a Windows XP-style title bar over every floating
Hyprland window. Min / Max / Close buttons dispatch hyprctl commands.

Wayland-native via gtk-layer-shell. Tracks window state by subscribing
to Hyprland's IPC event socket (.socket2.sock).
"""

import gi, os, json, socket, subprocess, sys, threading
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib, Pango

# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------

BAR_H        = 26
EVENT_DEBOUNCE_MS = 16

XDG_RT = os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")
HIS    = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
if not HIS:
    hypr_dirs = sorted(os.listdir(f"{XDG_RT}/hypr"))
    if hypr_dirs:
        HIS = hypr_dirs[-1]
SOCKET2 = f"{XDG_RT}/hypr/{HIS}/.socket2.sock"


# --------------------------------------------------------------------------
# CSS - XP Luna title bar
# --------------------------------------------------------------------------

XP_CSS = b"""
window.xp-titlebar { background-color: rgba(0,0,0,0); }

.xp-bar {
    background-image: linear-gradient(180deg,
        #0A246A 0%,
        #0058E6 4%,
        #3A93FF 9%,
        #0F76E6 16%,
        #1E64DB 60%,
        #0050D2 100%);
    border-top: 1px solid #0A246A;
    border-left: 1px solid #0A246A;
    border-right: 1px solid #0A246A;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

.xp-title {
    color: #FFFFFF;
    font-family: "Trebuchet MS", "Tahoma", "Verdana", sans-serif;
    font-weight: bold;
    font-size: 10pt;
    text-shadow: 1px 1px 1px rgba(0,0,0,0.55);
    padding: 0 6px 0 8px;
}

/* Buttons - white "raised glass" tiles like real XP */
.xp-btn {
    min-width: 22px;
    min-height: 18px;
    padding: 0;
    margin: 2px 2px 2px 0;
    border-radius: 3px;
    border: 1px solid #003366;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.65),
        inset -1px -1px 0 rgba(0,0,0,0.30);
    color: #FFFFFF;
    font-family: "Tahoma";
    font-weight: bold;
    font-size: 9pt;
    text-shadow: 0 1px 1px rgba(0,0,0,0.6);
}

/* Minimize / Maximize - blue glass */
.xp-min, .xp-max {
    background-image: linear-gradient(180deg,
        #6FA0FF 0%, #3978E7 50%, #1955C9 51%, #2A6BD7 100%);
}
.xp-min:hover, .xp-max:hover {
    background-image: linear-gradient(180deg,
        #84B2FF 0%, #4D8AF0 50%, #2C68D8 51%, #3A7BE0 100%);
}

/* Close - red glass */
.xp-close {
    background-image: linear-gradient(180deg,
        #FF8E70 0%, #E73E1A 50%, #B92500 51%, #DD3B16 100%);
    border: 1px solid #6E0F00;
}
.xp-close:hover {
    background-image: linear-gradient(180deg,
        #FFA98E 0%, #F25531 50%, #C92F0F 51%, #EE5128 100%);
}

.xp-btn:active {
    box-shadow:
        inset 1px 1px 0 rgba(0,0,0,0.35),
        inset -1px -1px 0 rgba(255,255,255,0.25);
}
"""


# --------------------------------------------------------------------------
# Hyprland helpers
# --------------------------------------------------------------------------

def hyprctl(*args, json_out=False):
    cmd = ["hyprctl"] + list(args)
    if json_out:
        cmd += ["-j"]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        return json.loads(out) if json_out else out
    except Exception:
        return [] if json_out else ""


def dispatch(*args):
    """Run hyprctl dispatch <args>."""
    try:
        subprocess.Popen(["hyprctl", "dispatch"] + list(args),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


# --------------------------------------------------------------------------
# One title bar per floating window
# --------------------------------------------------------------------------

class XPTitleBar(Gtk.Window):
    def __init__(self, addr):
        super().__init__()
        self.addr = addr
        self.get_style_context().add_class("xp-titlebar")

        # Layer-shell on TOP so we sit above every normal window.
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_namespace(self, f"xp-titlebar-{addr}")
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_exclusive_zone(self, 0)

        # Transparent surface
        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)

        # ----- bar layout -----
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        bar.get_style_context().add_class("xp-bar")
        bar.set_size_request(-1, BAR_H)
        self.add(bar)

        self.title_lbl = Gtk.Label(xalign=0.0)
        self.title_lbl.get_style_context().add_class("xp-title")
        self.title_lbl.set_hexpand(True)
        self.title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        bar.pack_start(self.title_lbl, True, True, 0)

        # Drag from the title bar = move the window via hyprctl
        self.title_lbl.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        bar.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        for w in (bar, self.title_lbl):
            w.connect("button-press-event", self._on_bar_press)

        self.min_btn = Gtk.Button(label="–")
        self.max_btn = Gtk.Button(label="□")
        self.cls_btn = Gtk.Button(label="✕")
        for b, css in ((self.min_btn, "xp-min"),
                       (self.max_btn, "xp-max"),
                       (self.cls_btn, "xp-close")):
            ctx = b.get_style_context()
            ctx.add_class("xp-btn"); ctx.add_class(css)
            b.set_focus_on_click(False)
            bar.pack_start(b, False, False, 0)

        self.min_btn.connect("clicked", lambda *_: self._minimize())
        self.max_btn.connect("clicked", lambda *_: self._toggle_max())
        self.cls_btn.connect("clicked", lambda *_: self._close())

        self.show_all()

    # ---- updates --------------------------------------------------------

    def update(self, x, y, width, title):
        """Reposition + resize + retitle."""
        # Top edge of title bar sits BAR_H pixels above the window's top
        ty = max(0, int(y) - BAR_H)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, max(0, int(x)))
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP,  ty)
        self.set_size_request(max(120, int(width)), BAR_H)
        self.title_lbl.set_markup(
            f'<span foreground="#FFFFFF" font_desc="Trebuchet MS Bold 10">'
            f'{GLib.markup_escape_text(title or "")}</span>')

    # ---- ops ------------------------------------------------------------

    def _close(self):
        dispatch("closewindow", f"address:{self.addr}")

    def _minimize(self):
        # Hyprland has no real "minimize"; closest equivalent is move
        # the window to a hidden special workspace, restorable later.
        dispatch("movetoworkspacesilent",
                 f"special:minimized,address:{self.addr}")

    def _toggle_max(self):
        # Toggle floating maximize for the window: fullscreen state 1
        dispatch("fullscreen", "1")  # active window; works when focused

    def _on_bar_press(self, _w, event):
        if event.button == 1:
            # Focus the target window so the dispatch lands on it, then
            # tell Hyprland to start a move-drag of the active window.
            dispatch("focuswindow", f"address:{self.addr}")
            dispatch("movewindow")  # mouse-driven move via Hyprland
            return True
        return False


# --------------------------------------------------------------------------
# Overlay manager
# --------------------------------------------------------------------------

class TitleBarManager:
    def __init__(self):
        self.bars = {}  # addr -> XPTitleBar
        # initial sync
        GLib.idle_add(self.refresh)
        # event subscription thread
        threading.Thread(target=self._event_loop, daemon=True).start()

    def refresh(self):
        clients = hyprctl("clients", json_out=True)
        # Figure out which addresses *currently* need a bar
        wanted = {}
        for c in clients:
            if not c.get("floating"):
                continue
            if c.get("fullscreen") in (1, 2):
                continue
            if not c.get("mapped", True):
                continue
            addr = c["address"]
            x, y = c["at"]
            w, h = c["size"]
            title = c.get("title", "")
            wanted[addr] = (x, y, w, h, title)

        # remove bars for gone windows
        for addr in list(self.bars.keys()):
            if addr not in wanted:
                self.bars[addr].destroy()
                del self.bars[addr]

        # create / update bars
        for addr, (x, y, w, h, title) in wanted.items():
            if addr not in self.bars:
                self.bars[addr] = XPTitleBar(addr)
            self.bars[addr].update(x, y, w, title)
        return False

    def _event_loop(self):
        if not HIS or not os.path.exists(SOCKET2):
            print(f"[xp-titlebar] no Hyprland socket at {SOCKET2}", file=sys.stderr)
            return
        relevant = {"openwindow", "closewindow", "movewindow", "windowtitle",
                    "windowtitlev2", "activewindow", "activewindowv2",
                    "changefloatingmode", "fullscreen", "workspace",
                    "windowtitlechanged"}
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(SOCKET2)
                buf = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        evt = line.decode(errors="replace").split(">>", 1)[0]
                        if evt in relevant:
                            # batch updates via idle_add to avoid GTK threading
                            GLib.idle_add(self.refresh)
        except Exception as e:
            print(f"[xp-titlebar] event loop ended: {e}", file=sys.stderr)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    css = Gtk.CssProvider()
    css.load_from_data(XP_CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    TitleBarManager()
    Gtk.main()


if __name__ == "__main__":
    main()
