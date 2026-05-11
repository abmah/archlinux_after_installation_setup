#!/usr/bin/env python3
"""
Windows XP Luna styled Sounds and Audio Devices dialog.

Models the real XP "Sounds and Audio Devices Properties" dialog.
Backend: pactl (PipeWire-pulse compatible).
"""

import gi, os, re, subprocess
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango


# ===========================================================================
# XP Luna CSS
# ===========================================================================

XP_CSS = b"""
window.xp-window {
    background-color: #ECE9D8;
    border: 1px solid #0A246A;
}

/* ---- Title bar ----------------------------------------------------- */
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
.xp-titlebar image {
    margin-right: 4px;
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

.xp-min {
    background-image:
        linear-gradient(180deg, #6FA0FF 0%, #3978E7 50%, #1955C9 51%, #2A6BD7 100%);
    color: #FFFFFF;
    border: 1px solid #0A246A;
    border-radius: 3px;
    min-width: 22px;
    min-height: 18px;
    padding: 0;
    margin: 3px 0;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.55),
        inset -1px -1px 0 rgba(0,0,0,0.25);
}

/* ---- Body ---------------------------------------------------------- */
.xp-body {
    background-color: #ECE9D8;
    padding: 8px;
}

/* ---- Tab bar ------------------------------------------------------- */
.xp-tabbar {
    background-color: #ECE9D8;
    padding: 8px 8px 0 8px;
}
.xp-tab {
    background-image:
        linear-gradient(180deg, #FFFFFF 0%, #ECE9D8 60%, #D8D2BD 100%);
    color: #000000;
    font-family: "Tahoma";
    font-size: 9pt;
    border: 1px solid #919B9C;
    border-bottom: none;
    border-radius: 3px 3px 0 0;
    padding: 4px 14px 5px 14px;
    margin: 0 -1px 0 0;
    text-shadow: none;
}
.xp-tab.active {
    background-image:
        linear-gradient(180deg, #FFFFFF 0%, #FAF8EE 100%);
    border: 1px solid #919B9C;
    border-bottom: 1px solid #FAF8EE;
    padding-top: 5px;
    padding-bottom: 6px;
    font-weight: bold;
}
.xp-tab:hover {
    background-image:
        linear-gradient(180deg, #FFFFFF 0%, #F5F1E2 50%, #DAD5C2 100%);
}

.xp-tabpage {
    background-color: #FAF8EE;
    border: 1px solid #919B9C;
    padding: 12px;
}

/* ---- Group box (frame with floating label) ------------------------ */
.xp-group {
    background-color: transparent;
    padding: 0;
    margin: 8px 0;
}
.xp-group > frame > border {
    border: 1px solid #ACA899;
    border-radius: 0;
}
frame.xp-group > label {
    color: #0A246A;
    font-family: "Tahoma";
    font-size: 9pt;
    font-weight: bold;
    padding: 0 4px;
    background-color: #FAF8EE;
    margin-left: 8px;
}
.xp-group-body {
    padding: 10px 10px 12px 10px;
    background-color: transparent;
}

/* ---- Generic label ------------------------------------------------- */
label.xp-lbl {
    font-family: "Tahoma";
    font-size: 9pt;
    color: #000000;
}
label.xp-mono {
    font-family: "Tahoma";
    font-size: 8pt;
    color: #555555;
}

/* ---- ComboBox ------------------------------------------------------ */
.xp-combo {
    background-color: #FFFFFF;
    color: #000000;
    font-family: "Tahoma";
    font-size: 9pt;
    border: 1px solid #7F9DB9;
    padding: 1px 2px;
    min-height: 22px;
    box-shadow:
        inset  1px  1px 0 rgba(0,0,0,0.10),
        inset -1px -1px 0 rgba(255,255,255,0.85);
}
.xp-combo button {
    background-image:
        linear-gradient(180deg, #FDFCF6 0%, #ECE9D8 50%, #D8D2BD 100%);
    border: 1px solid #ACA899;
    color: #000000;
    border-radius: 2px;
    padding: 0 4px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(0,0,0,0.20);
}
.xp-combo button:hover {
    background-image:
        linear-gradient(180deg, #FFFFFF 0%, #F5F1E2 50%, #DAD5C2 100%);
    border-color: #0A246A;
}
.xp-combo menu {
    background-color: #FFFFFF;
    border: 1px solid #7F9DB9;
}
.xp-combo menu menuitem {
    padding: 3px 8px;
    color: #000000;
}
.xp-combo menu menuitem:hover,
.xp-combo menu menuitem:selected {
    background-color: #316AC5;
    color: #FFFFFF;
}

/* ---- Volume slider ------------------------------------------------- */
.xp-scale trough {
    background-color: #FFFFFF;
    border: 1px solid #7F9DB9;
    min-height: 4px;
    box-shadow:
        inset  1px  1px 0 rgba(0,0,0,0.15),
        inset -1px -1px 0 rgba(255,255,255,0.85);
}
.xp-scale highlight {
    background-image:
        linear-gradient(90deg, #79B3FF 0%, #3A86F0 100%);
    border: 1px solid #0A246A;
    min-height: 4px;
}
.xp-scale slider {
    background-image:
        linear-gradient(180deg, #FFFFFF 0%, #ECE9D8 60%, #D8D2BD 100%);
    border: 1px solid #003C74;
    min-width: 12px;
    min-height: 22px;
    border-radius: 3px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(0,0,0,0.25);
}
.xp-scale slider:hover {
    background-image:
        linear-gradient(180deg, #FFFFFF 0%, #F5F1E2 60%, #DAD5C2 100%);
}

/* ---- Checkbox ------------------------------------------------------ */
.xp-check {
    font-family: "Tahoma";
    font-size: 9pt;
    color: #000000;
}
.xp-check check {
    background-color: #FFFFFF;
    border: 1px solid #7F9DB9;
    min-width: 13px;
    min-height: 13px;
    box-shadow:
        inset 1px 1px 0 rgba(0,0,0,0.15),
        inset -1px -1px 0 rgba(255,255,255,0.85);
}
.xp-check check:hover {
    border-color: #0A246A;
}
.xp-check check:checked {
    background-color: #FFFFFF;
    color: #000000;
}

/* ---- Buttons ------------------------------------------------------- */
.xp-btn {
    background-image:
        linear-gradient(180deg, #FFFFFF 0%, #ECE9D8 45%, #D8D2BD 100%);
    color: #000000;
    font-family: "Tahoma";
    font-size: 9pt;
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
        linear-gradient(180deg, #FFFFFF 0%, #F5F1E2 45%, #DAD5C2 100%);
    border-color: #0A246A;
}
.xp-btn:active {
    background-image:
        linear-gradient(180deg, #D4D0C8 0%, #ECE9D8 100%);
    box-shadow:
        inset 1px 1px 0 rgba(112,112,96,0.55),
        inset -1px -1px 0 rgba(255,255,255,0.6);
}
.xp-btn:focus {
    outline: 1px dotted #000000;
    outline-offset: -4px;
}
.xp-btn-default {
    border: 2px solid #0A246A;
    padding: 2px 13px;
}
.xp-btn:disabled {
    color: #ACA899;
    background-image:
        linear-gradient(180deg, #ECE9D8 0%, #ECE9D8 100%);
}

/* ---- Bottom button row -------------------------------------------- */
.xp-buttons {
    background-color: #ECE9D8;
    padding: 8px 6px 6px 6px;
}

/* ---- Inline volume readout / level meter -------------------------- */
.xp-level {
    background-color: #FFFFFF;
    border: 1px solid #7F9DB9;
    min-height: 10px;
}
.xp-level-bar {
    background-image:
        linear-gradient(90deg, #79B3FF 0%, #3A86F0 100%);
}

/* ---- Status pill (connected / disconnected etc.) ----------------- */
.xp-status-ok {
    color: #1A5E1A;
    font-weight: bold;
}
.xp-status-bad {
    color: #6E0F00;
    font-weight: bold;
}
"""


# ===========================================================================
# Backend helpers (pactl)
# ===========================================================================

def sh(cmd):
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return ""

def list_sinks():
    """Returns [(name, description, mute, volume_percent)]."""
    out = sh(["pactl", "list", "sinks"])
    blocks = re.split(r"\nSink #", "\n" + out)
    devs = []
    for b in blocks:
        if not b.strip():
            continue
        name = re.search(r"Name:\s*(\S+)", b)
        desc = re.search(r"Description:\s*(.+)", b)
        mute = re.search(r"Mute:\s*(yes|no)", b)
        vol  = re.search(r"Volume:.*?(\d+)%", b)
        if name and desc:
            devs.append((name.group(1),
                         desc.group(1).strip(),
                         (mute.group(1) == "yes") if mute else False,
                         int(vol.group(1)) if vol else 0))
    return devs

def list_sources():
    out = sh(["pactl", "list", "sources"])
    blocks = re.split(r"\nSource #", "\n" + out)
    devs = []
    for b in blocks:
        if not b.strip():
            continue
        name = re.search(r"Name:\s*(\S+)", b)
        desc = re.search(r"Description:\s*(.+)", b)
        mute = re.search(r"Mute:\s*(yes|no)", b)
        vol  = re.search(r"Volume:.*?(\d+)%", b)
        if not name or not desc:
            continue
        # hide monitor sources from selectable inputs
        if name.group(1).endswith(".monitor"):
            continue
        devs.append((name.group(1),
                     desc.group(1).strip(),
                     (mute.group(1) == "yes") if mute else False,
                     int(vol.group(1)) if vol else 0))
    return devs

def default_sink():
    return sh(["pactl", "get-default-sink"]).strip()

def default_source():
    return sh(["pactl", "get-default-source"]).strip()

def set_default_sink(name):
    sh(["pactl", "set-default-sink", name])

def set_default_source(name):
    sh(["pactl", "set-default-source", name])

def set_sink_volume(name, pct):
    sh(["pactl", "set-sink-volume", name, f"{int(pct)}%"])

def set_source_volume(name, pct):
    sh(["pactl", "set-source-volume", name, f"{int(pct)}%"])

def set_sink_mute(name, mute):
    sh(["pactl", "set-sink-mute", name, "1" if mute else "0"])

def set_source_mute(name, mute):
    sh(["pactl", "set-source-mute", name, "1" if mute else "0"])


# ===========================================================================
# Dialog
# ===========================================================================

class AudioDialog(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(False)
        self.set_keep_above(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_size(460, 480)
        self.set_resizable(False)
        self.set_title("Sounds and Audio Devices Properties")
        self.set_wmclass("xp-audio.py", "xp-audio.py")
        self.get_style_context().add_class("xp-window")

        self._build()
        self._poll_id = GLib.timeout_add(1500, self._refresh_quiet)
        self.connect("destroy", lambda *_: Gtk.main_quit())
        self.connect("key-press-event", self._on_key)

    # ---- UI scaffold ------------------------------------------------------

    def _build(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(outer)

        # ---- Title bar ----
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        tb.get_style_context().add_class("xp-titlebar")
        title_lbl = Gtk.Label(label="Sounds and Audio Devices Properties", xalign=0.0)
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

        # ---- Tab strip + page ----
        tabwrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        tabwrap.get_style_context().add_class("xp-body")
        outer.pack_start(tabwrap, True, True, 0)

        tabstrip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tabstrip.get_style_context().add_class("xp-tabbar")
        for name in ("Audio",):
            btn = Gtk.Label(label=name)
            btn.set_margin_top(0)
            ctx = btn.get_style_context()
            ctx.add_class("xp-tab")
            ctx.add_class("active")
            eb = Gtk.EventBox()
            eb.add(btn)
            tabstrip.pack_start(eb, False, False, 0)
        tabwrap.pack_start(tabstrip, False, False, 0)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.get_style_context().add_class("xp-tabpage")
        tabwrap.pack_start(page, True, True, 0)

        # ---- Sound playback group ----
        self.playback_combo, self.playback_scale, self.playback_mute = \
            self._build_group(page, "Sound playback", is_input=False)

        # ---- Sound recording group ----
        self.record_combo, self.record_scale, self.record_mute = \
            self._build_group(page, "Sound recording", is_input=True)

        # ---- Bottom buttons ----
        btnrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        btnrow.get_style_context().add_class("xp-buttons")
        spacer = Gtk.Label(); spacer.set_hexpand(True)
        btnrow.pack_start(spacer, True, True, 0)

        for label, default, fn in (
            ("OK",      True,  lambda *_: self.close()),
            ("Cancel",  False, lambda *_: self.close()),
            ("Apply",   False, lambda *_: self._apply()),
        ):
            b = Gtk.Button(label=label)
            ctx = b.get_style_context()
            ctx.add_class("xp-btn")
            if default:
                ctx.add_class("xp-btn-default")
            b.connect("clicked", fn)
            btnrow.pack_start(b, False, False, 0)
        outer.pack_start(btnrow, False, False, 0)

        # Populate after widgets exist
        self._refresh()

    def _build_group(self, parent, title, is_input):
        frame = Gtk.Frame(label=title)
        frame.get_style_context().add_class("xp-group")
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        body.get_style_context().add_class("xp-group-body")
        frame.add(body)
        parent.pack_start(frame, False, False, 0)

        # Default device row
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label="Default device:", xalign=0.0)
        lbl.get_style_context().add_class("xp-lbl")
        lbl.set_size_request(110, -1)
        row.pack_start(lbl, False, False, 0)

        store = Gtk.ListStore(str, str)  # display, name
        combo = Gtk.ComboBox.new_with_model(store)
        renderer = Gtk.CellRendererText()
        combo.pack_start(renderer, True)
        combo.add_attribute(renderer, "text", 0)
        combo.get_style_context().add_class("xp-combo")
        row.pack_start(combo, True, True, 0)
        body.pack_start(row, False, False, 0)

        # Volume row
        vol_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        vlbl = Gtk.Label(label="Volume:", xalign=0.0)
        vlbl.get_style_context().add_class("xp-lbl")
        vlbl.set_size_request(110, -1)
        vol_row.pack_start(vlbl, False, False, 0)

        scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_draw_value(True)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.set_digits(0)
        scale.set_hexpand(True)
        scale.get_style_context().add_class("xp-scale")
        vol_row.pack_start(scale, True, True, 0)
        body.pack_start(vol_row, False, False, 0)

        # Mute row
        mute_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        spacer = Gtk.Label()
        spacer.set_size_request(110, -1)
        mute_row.pack_start(spacer, False, False, 0)
        chk = Gtk.CheckButton.new_with_label("Mute")
        chk.get_style_context().add_class("xp-check")
        mute_row.pack_start(chk, False, False, 0)
        body.pack_start(mute_row, False, False, 0)

        # Wire signals
        combo.connect("changed", self._on_combo_changed, is_input)
        scale.connect("value-changed", self._on_scale_changed, is_input)
        chk.connect("toggled", self._on_mute_toggled, is_input)

        return combo, scale, chk

    # ---- Signal handlers --------------------------------------------------

    def _begin_drag(self, widget, event):
        if event.button == 1:
            self.begin_move_drag(event.button,
                                 int(event.x_root), int(event.y_root),
                                 event.time)
        return False

    def _on_key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.close()

    _suppress = False

    def _on_combo_changed(self, combo, is_input):
        if self._suppress:
            return
        it = combo.get_active_iter()
        if it is None:
            return
        store = combo.get_model()
        name = store[it][1]
        if is_input:
            set_default_source(name)
        else:
            set_default_sink(name)
        # refresh per-device volume display for the now-default
        GLib.idle_add(self._refresh)

    def _on_scale_changed(self, scale, is_input):
        if self._suppress:
            return
        v = scale.get_value()
        name = default_source() if is_input else default_sink()
        if not name:
            return
        if is_input:
            set_source_volume(name, v)
        else:
            set_sink_volume(name, v)

    def _on_mute_toggled(self, chk, is_input):
        if self._suppress:
            return
        name = default_source() if is_input else default_sink()
        if not name:
            return
        if is_input:
            set_source_mute(name, chk.get_active())
        else:
            set_sink_mute(name, chk.get_active())

    def _apply(self):
        # Currently every change is applied live; this is mainly for the look.
        pass

    # ---- Refresh ----------------------------------------------------------

    def _refresh(self):
        self._suppress = True
        try:
            sinks = list_sinks()
            dsink = default_sink()
            store = self.playback_combo.get_model()
            store.clear()
            sel_iter = None
            for n, d, m, v in sinks:
                it = store.append([d, n])
                if n == dsink:
                    sel_iter = it
            if sel_iter:
                self.playback_combo.set_active_iter(sel_iter)
            elif len(store) > 0:
                self.playback_combo.set_active(0)

            # use currently-default sink's volume / mute
            for n, d, m, v in sinks:
                if n == dsink:
                    self.playback_scale.set_value(v)
                    self.playback_mute.set_active(m)
                    break

            sources = list_sources()
            dsrc = default_source()
            store = self.record_combo.get_model()
            store.clear()
            sel_iter = None
            for n, d, m, v in sources:
                it = store.append([d, n])
                if n == dsrc:
                    sel_iter = it
            if sel_iter:
                self.record_combo.set_active_iter(sel_iter)
            elif len(store) > 0:
                self.record_combo.set_active(0)

            for n, d, m, v in sources:
                if n == dsrc:
                    self.record_scale.set_value(v)
                    self.record_mute.set_active(m)
                    break
        finally:
            self._suppress = False

    def _refresh_quiet(self):
        # Don't fight the user mid-drag of a slider.
        if not (self.playback_scale.has_focus() or self.record_scale.has_focus()):
            self._refresh()
        return True


# ===========================================================================
# Entry point
# ===========================================================================

def main():
    css = Gtk.CssProvider()
    css.load_from_data(XP_CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    AudioDialog().show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
