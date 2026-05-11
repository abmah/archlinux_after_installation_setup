#!/usr/bin/env python3
"""
Windows XP Luna styled list dialog.

Usage:
    xp-menu.py "Title" "Option 1" "Option 2" ...

Prints the chosen option to stdout. Exit 0 on choice, 1 on cancel.
"""

import gi, sys, os

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, Pango, GLib

# ---------- styling ---------------------------------------------------------

XP_CSS = b"""
window.xp-window {
    background-color: #ECE9D8;
    border: 1px solid #0A246A;
}

/* Title bar - XP Luna jelly-bean blue gradient */
.xp-titlebar {
    background-image:
        linear-gradient(180deg,
            #0A246A 0%,
            #0058E6 4%,
            #3A93FF 9%,
            #0F76E6 16%,
            #1E64DB 60%,
            #0050D2 100%);
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

/* Close (X) button on the title bar */
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

/* Body - inset bevel container */
.xp-body {
    background-color: #ECE9D8;
    padding: 6px;
}

/* List */
.xp-list {
    background-color: #FFFFFF;
    border: 1px solid #7F9DB9;
    box-shadow:
        inset  1px  1px 0 rgba(112,112,96,0.4),
        inset -1px -1px 0 rgba(255,255,255,0.7);
}

.xp-list row {
    padding: 5px 12px;
    color: #000000;
    font-family: "Tahoma", "Verdana", sans-serif;
    font-size: 11pt;
    background-color: transparent;
}

.xp-list row:hover {
    background-color: #316AC5;
    color: #FFFFFF;
}

.xp-list row:selected {
    background-color: #316AC5;
    color: #FFFFFF;
}

/* Button row at bottom */
.xp-buttons {
    background-color: #ECE9D8;
    padding: 4px;
    border-top: 1px solid #FFFFFF;
}

/* XP raised button */
.xp-btn {
    background-image:
        linear-gradient(180deg,
            #FFFFFF 0%,
            #ECE9D8 45%,
            #D8D2BD 100%);
    color: #000000;
    font-family: "Tahoma", "Verdana", sans-serif;
    font-size: 10pt;
    border: 1px solid #003C74;
    border-radius: 3px;
    padding: 3px 14px;
    margin: 0 4px;
    min-width: 70px;
    text-shadow: none;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.9),
        inset -1px -1px 0 rgba(112,112,96,0.55);
}
.xp-btn:hover {
    background-image:
        linear-gradient(180deg,
            #FFFFFF 0%,
            #F5F1E2 45%,
            #DAD5C2 100%);
    border-color: #0A246A;
}
.xp-btn:active {
    background-image:
        linear-gradient(180deg,
            #D4D0C8 0%,
            #ECE9D8 100%);
    box-shadow:
        inset 1px 1px 0 rgba(112,112,96,0.55),
        inset -1px -1px 0 rgba(255,255,255,0.6);
}
.xp-btn:focus {
    outline: 1px dotted #000000;
    outline-offset: -4px;
}
"""


# ---------- dialog ----------------------------------------------------------

def main(title, options):
    css = Gtk.CssProvider()
    css.load_from_data(XP_CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    win.set_decorated(False)
    win.set_skip_taskbar_hint(True)
    win.set_keep_above(True)
    win.set_position(Gtk.WindowPosition.CENTER)
    win.set_default_size(320, max(120, 60 + 32 * len(options)))
    win.set_resizable(False)
    win.set_title(title)
    win.set_wmclass("XPMenu", "XPMenu")
    win.get_style_context().add_class("xp-window")

    chosen = {"value": None}

    def submit(v=None):
        if chosen["value"] is None:
            chosen["value"] = v
        win.close()

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    win.add(vbox)

    # Title bar - GtkBox, background applied via CSS
    titlebar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    titlebar.get_style_context().add_class("xp-titlebar")
    title_lbl = Gtk.Label(label=title, xalign=0.0)
    title_lbl.set_hexpand(True)
    title_lbl.set_margin_start(8)
    titlebar.pack_start(title_lbl, True, True, 0)
    close_btn = Gtk.Button(label="✕")
    close_btn.get_style_context().add_class("xp-close")
    close_btn.set_focus_on_click(False)
    close_btn.connect("clicked", lambda *_: submit(None))
    titlebar.pack_end(close_btn, False, False, 0)
    vbox.pack_start(titlebar, False, False, 0)

    # Allow dragging the borderless window from the title bar - wrap in EventBox
    drag_eb = Gtk.EventBox()
    drag_eb.set_visible_window(False)  # transparent overlay
    titlebar.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
    def begin_move(widget, event):
        if event.button == 1:
            win.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
        return False
    titlebar.connect("button-press-event", begin_move)

    # Body container
    body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    body.get_style_context().add_class("xp-body")
    vbox.pack_start(body, True, True, 0)

    # List
    listbox = Gtk.ListBox()
    listbox.get_style_context().add_class("xp-list")
    listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    for opt in options:
        row = Gtk.ListBoxRow()
        lbl = Gtk.Label(label=opt, xalign=0.0)
        lbl.set_margin_top(2); lbl.set_margin_bottom(2)
        lbl.set_margin_start(8); lbl.set_margin_end(8)
        row.add(lbl)
        listbox.add(row)
    listbox.connect("row-activated",
                    lambda lb, row: submit(options[row.get_index()]))
    body.pack_start(listbox, True, True, 0)
    listbox.select_row(listbox.get_row_at_index(0))

    # Button row
    btnrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    btnrow.get_style_context().add_class("xp-buttons")
    spacer = Gtk.Label()
    spacer.set_hexpand(True)
    btnrow.pack_start(spacer, True, True, 0)

    ok_btn = Gtk.Button(label="OK")
    ok_btn.get_style_context().add_class("xp-btn")
    ok_btn.connect("clicked",
                   lambda *_: submit(options[listbox.get_selected_row().get_index()])
                   if listbox.get_selected_row() else submit(None))
    btnrow.pack_start(ok_btn, False, False, 0)

    cancel_btn = Gtk.Button(label="Cancel")
    cancel_btn.get_style_context().add_class("xp-btn")
    cancel_btn.connect("clicked", lambda *_: submit(None))
    btnrow.pack_start(cancel_btn, False, False, 0)
    vbox.pack_start(btnrow, False, False, 0)

    # Esc closes
    def on_key(widget, event):
        if event.keyval == Gdk.KEY_Escape:
            submit(None)
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            r = listbox.get_selected_row()
            if r is not None:
                submit(options[r.get_index()])
    win.connect("key-press-event", on_key)
    win.connect("destroy", Gtk.main_quit)

    win.show_all()
    Gtk.main()

    if chosen["value"] is not None:
        print(chosen["value"])
        return 0
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: xp-menu.py 'Title' 'Option 1' 'Option 2' ...", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2:]))
