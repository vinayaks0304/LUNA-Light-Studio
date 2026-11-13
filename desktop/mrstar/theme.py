"""Colour-derived, accessible dark UI theme for LUNA.

This module is deliberately independent of Qt and Bluetooth so theme generation
can be tested without hardware or a graphical session. A selected LED colour is
not necessarily a readable UI accent (pure black, for example), so the accent
keeps its hue while its brightness/contrast is adapted for controls.
"""
from __future__ import annotations

import colorsys
from dataclasses import dataclass

from .palette import normalise_hex

DEFAULT_COLOUR = '#9568FF'


def _rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def _hex(rgb: tuple[int, int, int]) -> str:
    return '#%02X%02X%02X' % tuple(max(0, min(255, round(c))) for c in rgb)


def _mix(a: str, b: str, fraction: float) -> str:
    x, y = _rgb(a), _rgb(b)
    return _hex(tuple(xi * (1 - fraction) + yi * fraction for xi, yi in zip(x, y)))


def _luminance(value: str) -> float:
    channels = [v / 255 for v in _rgb(value)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
    return sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))


def contrast_ratio(a: str, b: str) -> float:
    """WCAG relative-luminance contrast ratio."""
    light, dark = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (light + .05) / (dark + .05)


def _foreground(background: str) -> str:
    options = ('#0C1220', '#FFFFFF')
    return max(options, key=lambda colour: contrast_ratio(colour, background))


@dataclass(frozen=True)
class Theme:
    selected: str
    accent: str
    accent_hover: str
    accent_soft: str
    on_accent: str
    on_accent_hover: str
    background: str
    sidebar: str
    surface: str
    inset: str
    border: str
    hover: str
    nav_active: str
    text: str
    muted: str


def theme_for_colour(selected: str) -> Theme:
    """Derive a dark UI theme from the currently selected strip colour.

    Preserves the hue of colourful shades while adapting extreme dark/light
    values so buttons and sliders remain visible. Near-greys produce a neutral
    accent instead of reverting to LUNA's old purple theme.
    """
    selected = normalise_hex(selected) or DEFAULT_COLOUR
    r, g, b = (c / 255 for c in _rgb(selected))
    hue, saturation, value = colorsys.rgb_to_hsv(r, g, b)

    if saturation < .10:
        # A neutral LED colour should produce a neutral interface, not purple.
        hue = .60
        ui_saturation = .025 + saturation * .35
        ui_value = max(.72, min(.94, .72 + value * .22))
    else:
        ui_saturation = max(.48, min(.89, saturation * .88))
        ui_value = max(.72, min(.96, value * .83 + .23))

    accent = _hex(tuple(c * 255 for c in colorsys.hsv_to_rgb(hue, ui_saturation, ui_value)))
    # Highly saturated blues can be surprisingly dark in perceived luminance.
    # Brighten them towards white just enough for accessible controls.
    while contrast_ratio(accent, '#0B0E17') < 5.2:
        accent = _mix(accent, '#FFFFFF', .045)
    accent_hover = _mix(accent, '#FFFFFF', .14)
    accent_soft = _mix(accent, '#FFFFFF', .27)

    # Tint dark surfaces only slightly. The selected colour remains dominant
    # in controls, while backgrounds stay calm and readable.
    background = _mix('#0B0E17', accent, .040)
    sidebar = _mix('#10131E', accent, .055)
    surface = _mix('#171B29', accent, .065)
    inset = _mix('#101522', accent, .045)
    border = _mix('#32384B', accent, .105)
    hover = _mix('#30374A', accent, .115)
    nav_active = _mix('#232A3A', accent, .23)

    return Theme(
        selected=selected, accent=accent, accent_hover=accent_hover,
        accent_soft=accent_soft, on_accent=_foreground(accent),
        on_accent_hover=_foreground(accent_hover), background=background,
        sidebar=sidebar, surface=surface, inset=inset, border=border,
        hover=hover, nav_active=nav_active, text='#F5F5FA', muted='#A5ADBE',
    )


def stylesheet(theme: Theme) -> str:
    """Build one consistent application-wide QSS stylesheet."""
    t = theme
    return f'''
        QWidget {{ background:{t.background}; color:{t.text}; font-family:'Noto Sans','Inter','Segoe UI',sans-serif; font-size:13px; }}
        QFrame#sidebar {{ background:{t.sidebar}; border-right:1px solid {t.border}; }}
        QFrame#card {{ background:{t.surface}; border:1px solid {t.border}; border-radius:20px; }}
        QFrame#savedColour {{ background:{t.inset}; border:1px solid {t.border}; border-radius:13px; }}
        QFrame#themeChip {{ background:{t.selected}; border:1px solid {t.accent_soft}; border-radius:7px; }}
        QLabel {{ background:transparent; }}
        QLabel#brand {{ font-size:27px; font-weight:900; letter-spacing:5px; color:{t.text}; }}
        QLabel#eyebrow {{ font-size:10px; font-weight:800; letter-spacing:2px; color:{t.accent_soft}; }}
        QLabel#heading {{ font-size:29px; font-weight:800; }}
        QLabel#section {{ font-size:18px; font-weight:750; }}
        QLabel#muted {{ color:{t.muted}; font-size:12px; }}
        QLabel#body {{ color:#DCE0E9; }}
        QLabel#value {{ font-size:20px; font-weight:800; }}
        QPushButton {{ background:{t.hover}; border:1px solid {t.border}; border-radius:12px; padding:11px 16px; font-weight:650; }}
        QPushButton:hover {{ background:{t.nav_active}; border-color:{t.accent}; }}
        QPushButton:pressed {{ background:{t.nav_active}; }}
        QPushButton:disabled {{ color:#72798B; background:{t.inset}; border-color:{t.border}; }}
        QPushButton#primary {{ background:{t.accent}; border:1px solid {t.accent_hover}; color:{t.on_accent}; }}
        QPushButton#primary:hover {{ background:{t.accent_hover}; color:{t.on_accent_hover}; }}
        QPushButton#primary:disabled {{ background:{t.inset}; color:#72798B; border-color:{t.border}; }}
        QPushButton#nav {{ text-align:left; background:transparent; border:0; color:#ADB5C5; padding:14px 18px; border-radius:12px; }}
        QPushButton#nav:hover {{ background:{t.hover}; color:white; }}
        QPushButton#nav[active='true'] {{ background:{t.nav_active}; color:{t.accent_soft}; border-left:3px solid {t.accent}; }}
        QPushButton#swatch {{ border:2px solid #ffffff30; border-radius:14px; min-width:42px; min-height:42px; padding:0; }}
        QPushButton#savedColourApply {{ text-align:left; background:transparent; border:0; padding:5px 2px; font-weight:650; }}
        QPushButton#savedColourApply:hover {{ background:{t.hover}; }}
        QPushButton#savedColourAction {{ background:transparent; border:0; padding:4px; min-width:20px; color:#B7BDCC; }}
        QPushButton#savedColourAction:hover {{ background:{t.hover}; color:white; }}
        QLineEdit, QSpinBox, QComboBox {{ background:{t.inset}; border:1px solid {t.border}; border-radius:11px; padding:11px; selection-background-color:{t.accent}; selection-color:{t.on_accent}; }}
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border:1px solid {t.accent}; }}
        QSlider::groove:horizontal {{ height:7px; background:{t.border}; border-radius:3px; }}
        QSlider::sub-page:horizontal {{ background:{t.accent}; border-radius:3px; }}
        QSlider::handle:horizontal {{ background:{t.accent_soft}; border:3px solid {t.accent}; width:17px; margin:-8px 0; border-radius:11px; }}
        QCheckBox {{ spacing:8px; background:transparent; color:#E6EAF2; }}
        QCheckBox::indicator {{ width:17px; height:17px; }}
        QTimeEdit {{ background:{t.inset}; border:1px solid {t.border}; border-radius:11px; padding:11px; selection-background-color:{t.accent}; selection-color:{t.on_accent}; }}
        QTimeEdit:focus {{ border-color:{t.accent}; }}
        QListWidget {{ background:{t.inset}; border:1px solid {t.border}; border-radius:11px; padding:6px; }}
        QListWidget::item {{ padding:9px; border-radius:7px; }}
        QListWidget::item:selected {{ background:{t.nav_active}; color:{t.accent_soft}; }}
        QProgressBar {{ background:{t.border}; border:0; border-radius:6px; text-align:center; min-height:12px; }}
        QProgressBar::chunk {{ background:{t.accent}; border-radius:6px; }}
        QScrollArea {{ border:0; background:transparent; }}
        QScrollBar:vertical {{ background:{t.sidebar}; width:9px; }}
        QScrollBar::handle:vertical {{ background:{t.hover}; border-radius:4px; }}
    '''
