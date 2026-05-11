#!/usr/bin/env python3
"""
Windows XP Luna styled Bluetooth Devices dialog.

Models the real XP "Bluetooth Devices" dialog.
Backend: bluetoothctl.
"""

import gi, os, re, subprocess, shlex, threading, time
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango, GObject


# ===========================================================================
# CSS  (kept aligned with xp-audio.py for a consistent system look)
# ===========================================================================

XP_CSS = b"""
window.xp-window {
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
    min-width: 22px; min-height: 18px;
    padding: 0 2px; margin: 3px;
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

.xp-body { background-color: #ECE9D8; padding: 8px; }

.xp-tabbar { padding: 8px 8px 0 8px; }
.xp-tab {
    background-image: linear-gradient(180deg, #FFFFFF 0%, #ECE9D8 60%, #D8D2BD 100%);
    color: #000000;
    font-family: "Tahoma"; font-size: 9pt;
    border: 1px solid #919B9C; border-bottom: none;
    border-radius: 3px 3px 0 0;
    padding: 4px 14px 5px 14px;
    margin: 0 -1px 0 0;
}
.xp-tab.active {
    background-image: linear-gradient(180deg, #FFFFFF 0%, #FAF8EE 100%);
    border-bottom: 1px solid #FAF8EE;
    padding-top: 5px; padding-bottom: 6px;
    font-weight: bold;
}
.xp-tab:hover {
    background-image: linear-gradient(180deg, #FFFFFF 0%, #F5F1E2 50%, #DAD5C2 100%);
}

.xp-tabpage {
    background-color: #FAF8EE;
    border: 1px solid #919B9C;
    padding: 12px;
}

label.xp-lbl { font-family: "Tahoma"; font-size: 9pt; color: #000000; }
label.xp-hint { font-family: "Tahoma"; font-size: 8pt; color: #555555; }

/* Force black text inside the tab page (override system theme) */
.xp-tabpage,
.xp-tabpage label,
.xp-tabpage checkbutton label,
.xp-tabpage checkbutton {
    color: #000000;
}
.xp-tabpage checkbutton check {
    background-color: #FFFFFF;
    border: 1px solid #7F9DB9;
    min-width: 13px; min-height: 13px;
    box-shadow:
        inset 1px 1px 0 rgba(0,0,0,0.15),
        inset -1px -1px 0 rgba(255,255,255,0.85);
}
.xp-tabpage checkbutton check:hover { border-color: #0A246A; }

/* Device list  */
.xp-list-frame {
    background-color: #FFFFFF;
    border: 1px solid #7F9DB9;
    padding: 0;
    box-shadow:
        inset  1px  1px 0 rgba(0,0,0,0.10),
        inset -1px -1px 0 rgba(255,255,255,0.85);
}
.xp-list { background-color: #FFFFFF; }
.xp-list row {
    padding: 6px 10px;
    color: #000000;
    font-family: "Tahoma"; font-size: 9pt;
    background-color: transparent;
    border-bottom: 1px dotted #DAD5C2;
}
.xp-list row:hover {
    background-color: #DDEAFB;
    color: #000000;
}
.xp-list row:selected {
    background-color: #316AC5;
    color: #FFFFFF;
}
.xp-list row label.dev-status-ok    { color: #1A5E1A; font-weight: bold; }
.xp-list row label.dev-status-paired{ color: #555555; }
.xp-list row label.dev-status-busy  { color: #C76A00; font-weight: bold; }
.xp-list row:selected label.dev-status-ok,
.xp-list row:selected label.dev-status-paired,
.xp-list row:selected label.dev-status-busy { color: #FFFFFF; }

/* XP raised button */
.xp-btn {
    background-image: linear-gradient(180deg, #FFFFFF 0%, #ECE9D8 45%, #D8D2BD 100%);
    color: #000000;
    font-family: "Tahoma"; font-size: 9pt;
    border: 1px solid #003C74; border-radius: 3px;
    padding: 3px 14px; margin: 0 4px;
    min-width: 90px;
    text-shadow: none;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.9),
        inset -1px -1px 0 rgba(112,112,96,0.55);
}
.xp-btn label {
    color: #000000;
    text-shadow: none;
}
.xp-btn:hover {
    background-image: linear-gradient(180deg, #FFFFFF 0%, #F5F1E2 45%, #DAD5C2 100%);
    border-color: #0A246A;
    color: #000000;
}
.xp-btn:hover label { color: #000000; }
.xp-btn:active {
    background-image: linear-gradient(180deg, #D4D0C8 0%, #ECE9D8 100%);
    box-shadow:
        inset 1px 1px 0 rgba(112,112,96,0.55),
        inset -1px -1px 0 rgba(255,255,255,0.6);
    color: #000000;
}
.xp-btn:active label { color: #000000; }
/* All buttons render identically -- no "default action" heavy border, no
   muted variant. Click validity is decided inside the handlers (the
   _xp_enabled flag), so every button has the same XP-Luna look. */
.xp-btn.xp-mute,
.xp-btn-default {
    background-image: linear-gradient(180deg, #FFFFFF 0%, #ECE9D8 45%, #D8D2BD 100%);
    border: 1px solid #003C74;
    padding: 3px 14px;
}
/* Suppress GTK's auto-focused/default-action decoration */
.xp-btn:focus,
.xp-btn:focus-visible,
.xp-btn.default,
.xp-btn.suggested-action {
    border: 1px solid #003C74;
    outline: none;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.9),
        inset -1px -1px 0 rgba(112,112,96,0.55);
}

.xp-buttons { background-color: #ECE9D8; padding: 8px 6px 6px 6px; }

.xp-toggle-row {
    background-color: #FAF8EE;
    padding: 0 0 8px 0;
}

/* Toolbar above list */
.xp-toolbar {
    background-image: linear-gradient(180deg, #FAF8EE 0%, #ECE9D8 100%);
    border: 1px solid #ACA899;
    border-bottom: none;
    padding: 4px 6px;
}
.xp-toolbar button {
    background-image: linear-gradient(180deg, #FFFFFF 0%, #ECE9D8 50%, #D8D2BD 100%);
    border: 1px solid #ACA899;
    border-radius: 3px;
    padding: 1px 8px;
    margin: 0 3px 0 0;
    min-width: 0;
    font-family: "Tahoma"; font-size: 8pt;
    color: #000000;
    text-shadow: none;
}
.xp-toolbar button label { color: #000000; text-shadow: none; }
.xp-toolbar button:hover {
    background-image: linear-gradient(180deg, #FFFFFF 0%, #F5F1E2 50%, #DAD5C2 100%);
    border-color: #0A246A;
    color: #000000;
}
.xp-toolbar button:hover label { color: #000000; }
.xp-toolbar button:active label { color: #000000; }

.xp-status {
    font-family: "Tahoma"; font-size: 8pt; color: #555555;
    padding: 4px 6px;
}
"""


# ===========================================================================
# bluetoothctl helpers
# ===========================================================================

def bt(*args, timeout=4):
    try:
        return subprocess.check_output(
            ["bluetoothctl"] + list(args),
            text=True, stderr=subprocess.DEVNULL, timeout=timeout)
    except Exception:
        return ""

def adapter_powered():
    out = bt("show")
    m = re.search(r"Powered:\s*(yes|no)", out)
    return (m.group(1) == "yes") if m else False

def set_powered(on):
    bt("power", "on" if on else "off")

def list_devices():
    """Return [{mac, name, connected, paired, trusted, icon}]."""
    out = bt("devices")
    macs = []
    for line in out.splitlines():
        m = re.match(r"Device\s+([0-9A-F:]{17})\s+(.+)", line)
        if m:
            macs.append((m.group(1), m.group(2).strip()))

    devs = []
    for mac, name in macs:
        info = bt("info", mac)
        connected = "Connected: yes" in info
        paired    = "Paired: yes"    in info
        trusted   = "Trusted: yes"   in info
        icon = ""
        mi = re.search(r"Icon:\s*(\S+)", info)
        if mi:
            icon = mi.group(1)
        # Prefer the name from `info` (resolved) over the cached one.
        n2 = re.search(r"Name:\s*(.+)", info)
        if n2:
            name = n2.group(1).strip()
        devs.append({
            "mac": mac, "name": name,
            "connected": connected, "paired": paired,
            "trusted": trusted, "icon": icon,
        })
    return devs

def icon_for(dev):
    table = {
        "audio-headphones": "🎧",
        "audio-headset":    "🎧",
        "audio-card":       "🔊",
        "computer":         "💻",
        "phone":            "📱",
        "input-mouse":      "🖱",
        "input-keyboard":   "⌨",
        "input-gaming":     "🎮",
    }
    return table.get(dev.get("icon", ""), "📡")


# ===========================================================================
# Dialog
# ===========================================================================

def _btn_markup(text):
    # Always render label in solid black via Pango markup. GTK dims the entire
    # widget if you call set_sensitive(False), so we never go insensitive --
    # instead we toggle an .xp-mute class for visual cue and gate handlers.
    return (f'<span foreground="#000000" font_desc="Tahoma 9">'
            f'{GLib.markup_escape_text(text)}</span>')


def make_btn(text, classes=("xp-btn",)):
    btn = Gtk.Button()
    lbl = Gtk.Label()
    lbl.show()
    btn.add(lbl)
    ctx = btn.get_style_context()
    for c in classes:
        ctx.add_class(c)
    btn._xp_label = lbl
    btn._xp_text  = text
    btn._xp_enabled = True
    lbl.set_markup(_btn_markup(text))
    return btn


def set_btn_text(btn, text):
    btn._xp_text = text
    btn._xp_label.set_markup(_btn_markup(text))


def set_btn_enabled(btn, enabled):
    """Visual-only enable/disable. Real gating happens in the click handler."""
    btn._xp_enabled = enabled
    ctx = btn.get_style_context()
    if enabled:
        ctx.remove_class("xp-mute")
    else:
        ctx.add_class("xp-mute")


class BluetoothDialog(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(False)
        self.set_keep_above(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_size(480, 460)
        self.set_resizable(False)
        self.set_title("Bluetooth Devices")
        self.set_wmclass("xp-bluetooth.py", "xp-bluetooth.py")
        self.get_style_context().add_class("xp-window")

        self._scanning = False
        self._scan_proc = None

        self._build()
        self._refresh()
        self._poll_id = GLib.timeout_add(2500, self._refresh_quiet)
        self.connect("destroy", self._on_destroy)
        self.connect("key-press-event", self._on_key)

    # ---- UI ---------------------------------------------------------------

    def _build(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(outer)

        # title
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        tb.get_style_context().add_class("xp-titlebar")
        title_lbl = Gtk.Label(label="Bluetooth Devices", xalign=0.0)
        title_lbl.set_margin_start(6)
        title_lbl.set_hexpand(True)
        tb.pack_start(title_lbl, True, True, 0)
        close = Gtk.Button(label="✕")
        close.get_style_context().add_class("xp-close")
        close.set_focus_on_click(False)
        close.connect("clicked", lambda *_: self.close())
        tb.pack_end(close, False, False, 0)
        tb.connect("button-press-event", self._begin_drag)
        outer.pack_start(tb, False, False, 0)

        # body
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        body.get_style_context().add_class("xp-body")
        outer.pack_start(body, True, True, 0)

        tabstrip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tabstrip.get_style_context().add_class("xp-tabbar")
        tab_lbl = Gtk.Label(label="Devices")
        tab_lbl.get_style_context().add_class("xp-tab")
        tab_lbl.get_style_context().add_class("active")
        tabstrip.pack_start(tab_lbl, False, False, 0)
        body.pack_start(tabstrip, False, False, 0)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.get_style_context().add_class("xp-tabpage")
        body.pack_start(page, True, True, 0)

        # Adapter power toggle row
        pwr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.power_chk = Gtk.CheckButton.new_with_label("Bluetooth adapter is on")
        self.power_chk.set_active(adapter_powered())
        self.power_chk.connect("toggled", self._on_power_toggled)
        pwr.pack_start(self.power_chk, False, False, 0)
        spacer = Gtk.Label(); spacer.set_hexpand(True)
        pwr.pack_start(spacer, True, True, 0)
        self.status_lbl = Gtk.Label(label="", xalign=1.0)
        self.status_lbl.get_style_context().add_class("xp-status")
        pwr.pack_end(self.status_lbl, False, False, 0)
        page.pack_start(pwr, False, False, 0)

        # Toolbar (Scan / Refresh)
        tools = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tools.get_style_context().add_class("xp-toolbar")
        self.scan_btn = make_btn("🔎  Scan for devices", classes=())
        self.scan_btn.connect("clicked", self._on_scan_clicked)
        tools.pack_start(self.scan_btn, False, False, 0)
        rfb = make_btn("↻  Refresh", classes=())
        rfb.connect("clicked", lambda *_: self._refresh())
        tools.pack_start(rfb, False, False, 0)
        page.pack_start(tools, False, False, 0)

        # Device list (scrolled)
        listframe = Gtk.Frame()
        listframe.get_style_context().add_class("xp-list-frame")
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_height(200)
        self.listbox = Gtk.ListBox()
        self.listbox.get_style_context().add_class("xp-list")
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", lambda *_: self._update_action_states())
        scroller.add(self.listbox)
        listframe.add(scroller)
        page.pack_start(listframe, True, True, 0)

        # Action buttons
        act = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.btn_connect = make_btn("Connect", classes=("xp-btn", "xp-btn-default"))
        self.btn_connect.connect("clicked", self._on_connect)
        act.pack_start(self.btn_connect, False, False, 0)

        self.btn_disconnect = make_btn("Disconnect")
        self.btn_disconnect.connect("clicked", self._on_disconnect)
        act.pack_start(self.btn_disconnect, False, False, 0)

        self.btn_pair = make_btn("Pair")
        self.btn_pair.connect("clicked", self._on_pair)
        act.pack_start(self.btn_pair, False, False, 0)

        self.btn_remove = make_btn("Remove")
        self.btn_remove.connect("clicked", self._on_remove)
        act.pack_start(self.btn_remove, False, False, 0)
        page.pack_start(act, False, False, 0)

        # Bottom OK / Cancel
        btnrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        btnrow.get_style_context().add_class("xp-buttons")
        sp = Gtk.Label(); sp.set_hexpand(True)
        btnrow.pack_start(sp, True, True, 0)
        ok = make_btn("OK")
        ok.connect("clicked", lambda *_: self.close())
        btnrow.pack_start(ok, False, False, 0)
        ca = make_btn("Cancel")
        ca.connect("clicked", lambda *_: self.close())
        btnrow.pack_start(ca, False, False, 0)
        outer.pack_start(btnrow, False, False, 0)

    # ---- Row rendering ----------------------------------------------------

    def _make_row(self, dev):
        row = Gtk.ListBoxRow()
        row.dev = dev
        h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        ico = Gtk.Label(label=icon_for(dev))
        ico.set_xalign(0.5)
        ico.set_size_request(28, -1)
        h.pack_start(ico, False, False, 0)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        name = Gtk.Label(label=dev["name"] or dev["mac"], xalign=0.0)
        name.get_style_context().add_class("xp-lbl")
        v.pack_start(name, False, False, 0)
        sub = Gtk.Label(label=dev["mac"], xalign=0.0)
        sub.get_style_context().add_class("xp-hint")
        v.pack_start(sub, False, False, 0)
        h.pack_start(v, True, True, 0)

        if dev["connected"]:
            status = Gtk.Label(label="Connected")
            status.get_style_context().add_class("dev-status-ok")
        elif dev["paired"]:
            status = Gtk.Label(label="Paired")
            status.get_style_context().add_class("dev-status-paired")
        else:
            status = Gtk.Label(label="Discovered")
            status.get_style_context().add_class("dev-status-busy")
        status.set_xalign(1.0)
        h.pack_end(status, False, False, 6)

        row.add(h)
        return row

    # ---- Refresh ---------------------------------------------------------

    def _refresh(self):
        prev_mac = None
        sel = self.listbox.get_selected_row()
        if sel and getattr(sel, "dev", None):
            prev_mac = sel.dev["mac"]

        for c in list(self.listbox.get_children()):
            self.listbox.remove(c)
        devs = list_devices()
        # connected first, then paired, then discovered
        devs.sort(key=lambda d: (not d["connected"], not d["paired"], d["name"].lower()))
        for d in devs:
            self.listbox.add(self._make_row(d))
        self.listbox.show_all()

        # Restore previous selection if possible; otherwise auto-select first row
        # so action buttons aren't all stuck in disabled (gray) state on launch.
        target = None
        if prev_mac:
            for row in self.listbox.get_children():
                if getattr(row, "dev", {}).get("mac") == prev_mac:
                    target = row
                    break
        if target is None and self.listbox.get_row_at_index(0) is not None:
            target = self.listbox.get_row_at_index(0)
        if target is not None:
            self.listbox.select_row(target)

        self.power_chk.handler_block_by_func(self._on_power_toggled)
        self.power_chk.set_active(adapter_powered())
        self.power_chk.handler_unblock_by_func(self._on_power_toggled)

        if self._scanning:
            self.status_lbl.set_text("Scanning…")
        else:
            self.status_lbl.set_text(f"{len(devs)} device(s)")

        self._update_action_states()

    def _refresh_quiet(self):
        self._refresh()
        return True

    def _update_action_states(self):
        row = self.listbox.get_selected_row()
        has = row is not None
        dev = getattr(row, "dev", None) if has else None
        set_btn_enabled(self.btn_connect,    bool(has and dev and not dev["connected"]))
        set_btn_enabled(self.btn_disconnect, bool(has and dev and     dev["connected"]))
        set_btn_enabled(self.btn_pair,       bool(has and dev and not dev["paired"]))
        set_btn_enabled(self.btn_remove,     bool(has and dev and     dev["paired"]))

    # ---- Actions ----------------------------------------------------------

    def _selected(self):
        row = self.listbox.get_selected_row()
        return getattr(row, "dev", None) if row else None

    def _run_async(self, name, fn):
        """Run a blocking bluetoothctl op without freezing the UI."""
        self.status_lbl.set_text(f"{name}…")
        def worker():
            fn()
            GLib.idle_add(self._refresh)
        threading.Thread(target=worker, daemon=True).start()

    def _on_connect(self, *_):
        if not self.btn_connect._xp_enabled: return
        d = self._selected()
        if d:
            if not d["paired"]:
                self._run_async("Pairing & connecting",
                                lambda: (bt("trust", d["mac"]),
                                         bt("pair", d["mac"], timeout=20),
                                         bt("connect", d["mac"], timeout=15)))
            else:
                self._run_async("Connecting",
                                lambda: bt("connect", d["mac"], timeout=15))

    def _on_disconnect(self, *_):
        if not self.btn_disconnect._xp_enabled: return
        d = self._selected()
        if d:
            self._run_async("Disconnecting",
                            lambda: bt("disconnect", d["mac"], timeout=10))

    def _on_pair(self, *_):
        if not self.btn_pair._xp_enabled: return
        d = self._selected()
        if d:
            self._run_async("Pairing",
                            lambda: (bt("trust", d["mac"]),
                                     bt("pair", d["mac"], timeout=20)))

    def _on_remove(self, *_):
        if not self.btn_remove._xp_enabled: return
        d = self._selected()
        if d:
            self._run_async("Removing",
                            lambda: bt("remove", d["mac"], timeout=10))

    def _on_power_toggled(self, chk):
        set_powered(chk.get_active())
        GLib.idle_add(self._refresh)

    def _on_scan_clicked(self, *_):
        if self._scanning:
            self._stop_scan()
        else:
            self._start_scan()

    def _start_scan(self):
        # Run `bluetoothctl scan on` in background until we stop it.
        if not adapter_powered():
            set_powered(True)
        try:
            self._scan_proc = subprocess.Popen(
                ["bluetoothctl", "scan", "on"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True)
            self._scanning = True
            set_btn_text(self.scan_btn, "■  Stop scan")
            self._refresh()
        except Exception:
            pass

    def _stop_scan(self):
        if self._scan_proc:
            try:
                self._scan_proc.terminate()
                self._scan_proc.wait(timeout=2)
            except Exception:
                try: self._scan_proc.kill()
                except Exception: pass
        # Also tell controller to stop scanning explicitly
        bt("scan", "off")
        self._scan_proc = None
        self._scanning = False
        set_btn_text(self.scan_btn, "🔎  Scan for devices")
        self._refresh()

    # ---- Misc -------------------------------------------------------------

    def _begin_drag(self, widget, event):
        if event.button == 1:
            self.begin_move_drag(event.button,
                                 int(event.x_root), int(event.y_root),
                                 event.time)
        return False

    def _on_key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.close()

    def _on_destroy(self, *_):
        if self._scanning:
            try: self._stop_scan()
            except Exception: pass
        Gtk.main_quit()


# ===========================================================================

def main():
    css = Gtk.CssProvider()
    css.load_from_data(XP_CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    BluetoothDialog().show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
