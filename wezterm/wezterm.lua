-- Frutiger Aero wezterm config
-- Ported from the kitty look. WezTerm scales cells to fill the window
-- so there's no bottom-strip artifact like kitty had.

local wezterm = require 'wezterm'
local config = wezterm.config_builder()

-- Font
config.font = wezterm.font_with_fallback {
    'JetBrainsMono Nerd Font Propo',
    'JetBrainsMono Nerd Font',
    'Noto Sans',
}
config.font_size = 13.0

-- Window
config.initial_cols = 110
config.initial_rows = 30
config.window_padding = { left = 0, right = 0, top = 0, bottom = 8 }
config.window_decorations = 'NONE'
config.adjust_window_size_when_changing_font_size = false

-- Aero background image with light tint, no internal blur (rely on hyprland)
config.background = {
    {
        source = { File = wezterm.config_dir .. '/aero-bg.png' },
        hsb = { brightness = 0.95, saturation = 1.0, hue = 1.0 },
        height = 'Cover',
        width = 'Cover',
        vertical_align = 'Middle',
        horizontal_align = 'Center',
        attachment = { Parallax = 0.0 },
    },
    {
        source = { Color = '#0a3878' },
        opacity = 0.45,
        height = '100%',
        width = '100%',
    },
}

config.window_background_opacity = 0.92
config.text_background_opacity = 0.0
config.macos_window_background_blur = 0
config.win32_system_backdrop = 'Auto'

-- Tab bar (XP-cyan)
config.use_fancy_tab_bar = false
config.tab_bar_at_bottom = false
config.hide_tab_bar_if_only_one_tab = true
config.tab_max_width = 32
config.show_new_tab_button_in_tab_bar = false

-- Cursor
config.default_cursor_style = 'BlinkingBlock'
config.cursor_blink_rate = 600
config.cursor_thickness = 2

-- Color scheme (XP/aero brights, white text)
config.colors = {
    foreground = '#ffffff',
    background = '#0a3878',
    cursor_bg = '#ffffff',
    cursor_fg = '#0a3878',
    cursor_border = '#ffffff',
    selection_fg = '#082555',
    selection_bg = '#c6f25e',

    ansi = {
        '#2156a0', -- 0  black (lifted so it's readable on blue)
        '#ff7878', -- 1  red
        '#9bef5a', -- 2  green
        '#ffe066', -- 3  yellow
        '#5fb8ff', -- 4  blue
        '#d77bff', -- 5  magenta
        '#6ff0ff', -- 6  cyan
        '#ffffff', -- 7  white
    },
    brights = {
        '#d2e8ff', -- 8  bright black / dim gray
        '#ffa1a1', -- 9  bright red
        '#c6f25e', -- 10 bright green
        '#fff2a8', -- 11 bright yellow
        '#a8dcff', -- 12 bright blue
        '#f0a8ff', -- 13 bright magenta
        '#c8faff', -- 14 bright cyan
        '#ffffff', -- 15 bright white
    },

    tab_bar = {
        background = '#0a4998',
        active_tab = {
            bg_color  = '#1ea7ff',
            fg_color  = '#ffffff',
            intensity = 'Bold',
        },
        inactive_tab = {
            bg_color = '#0d63b8',
            fg_color = '#e6f3ff',
        },
        inactive_tab_hover = {
            bg_color = '#1689e0',
            fg_color = '#ffffff',
        },
        new_tab = {
            bg_color = '#0a4998',
            fg_color = '#e6f3ff',
        },
        new_tab_hover = {
            bg_color = '#1ea7ff',
            fg_color = '#ffffff',
        },
    },
}

-- Misc
config.enable_scroll_bar = false
config.scrollback_lines = 10000
config.audible_bell = 'Disabled'
config.visual_bell = {
    fade_in_duration_ms  = 0,
    fade_out_duration_ms = 0,
    target = 'CursorColor',
}
config.check_for_updates = false
config.warn_about_missing_glyphs = false
config.front_end = 'OpenGL'

-- Keep behavior close to most terms
config.keys = {
    { key = 'c', mods = 'CTRL|SHIFT', action = wezterm.action.CopyTo 'Clipboard' },
    { key = 'v', mods = 'CTRL|SHIFT', action = wezterm.action.PasteFrom 'Clipboard' },
    { key = 't', mods = 'CTRL|SHIFT', action = wezterm.action.SpawnTab 'CurrentPaneDomain' },
    { key = 'w', mods = 'CTRL|SHIFT', action = wezterm.action.CloseCurrentTab { confirm = true } },
}

return config
