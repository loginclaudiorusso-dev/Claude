"""Design-Tokens und das eine globale Stylesheet.

Alle Farben kommen aus ``T`` (aktuelles Theme). Widgets setzen nur Rollen über
``setProperty`` (z. B. ``variant="primary"``) – das Stylesheet übernimmt den Rest. Ein
Theme-Wechsel ist deshalb ein einziges ``app.setStyleSheet`` plus Neuzeichnen der Charts,
ohne das Fenster neu aufzubauen.

Standortfarben wurden mit dem Farbvalidator (Helligkeitsband, Sättigung, Unterscheidbarkeit
bei Rot-/Grün-/Blauschwäche, Kontrast) für hellen und dunklen Hintergrund geprüft.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication


@dataclass
class Theme:
    name: str
    dunkel: bool
    bg: str             # Fensterhintergrund
    surface: str        # Karten
    surface_2: str      # abgesetzte Flächen (Eingaben, Tabellenkopf, Sidebar)
    hover: str
    border: str
    border_strong: str
    text: str
    text_2: str
    text_3: str
    accent: str
    accent_hover: str
    accent_text: str
    accent_soft: str
    fokus: str
    ok: str
    knapp: str
    kritisch: str
    ueber: str
    standort: dict[str, str] = field(default_factory=dict)
    kategorie: dict[str, str] = field(default_factory=dict)
    raster: str = ""
    tooltip_bg: str = ""
    tooltip_text: str = ""


_KAT_HELL = {
    "Reha": "#2a78d6", "Anreise": "#8db7ec", "Mieter": "#eb6834", "Gäste": "#1baf7a", "DRK": "#eda100",
    "Landkreis": "#e87ba4", "UWT": "#008300", "FRAI": "#4a3aa7", "Jugendhilfe": "#e34948",
    "Pflegeschule": "#8a877f", "andere Bereiche": "#c9c7c0",
}
_KAT_DUNKEL = {
    "Reha": "#3987e5", "Anreise": "#2b5b93", "Mieter": "#d95926", "Gäste": "#199e70", "DRK": "#c98500",
    "Landkreis": "#d55181", "UWT": "#008300", "FRAI": "#9085e9", "Jugendhilfe": "#e66767",
    "Pflegeschule": "#8f8c84", "andere Bereiche": "#4a4944",
}

HELL = Theme(
    name="hell", dunkel=False,
    bg="#F5F6F8", surface="#FFFFFF", surface_2="#F0F2F5", hover="#EBEEF2", border="#E3E6EB", border_strong="#CBD1D9",
    text="#101828", text_2="#475467", text_3="#8A94A6",
    accent="#00797A", accent_hover="#00696A", accent_text="#FFFFFF", accent_soft="#E3F3F2", fokus="#00908F",
    ok="#16A34A", knapp="#CA8A04", kritisch="#EA580C", ueber="#DC2626",
    standort={"BFW BP": "#00908F", "BFW GS": "#D4700A", "BFW WE": "#5646C0", "Gesamt": "#344054"},
    kategorie=_KAT_HELL, raster="#EEF0F3", tooltip_bg="#101828", tooltip_text="#FFFFFF",
)

DUNKEL = Theme(
    name="dunkel", dunkel=True,
    bg="#0D1117", surface="#161B22", surface_2="#1C232C", hover="#222A35", border="#262E39", border_strong="#353F4C",
    text="#E6EDF3", text_2="#A6B0BD", text_3="#6E7A89",
    accent="#1FA7A6", accent_hover="#35B8B7", accent_text="#04171A", accent_soft="#12302F", fokus="#35B8B7",
    ok="#3FB950", knapp="#D29922", kritisch="#F0883E", ueber="#F85149",
    standort={"BFW BP": "#1A9C9F", "BFW GS": "#CC7A22", "BFW WE": "#9085E9", "Gesamt": "#C9D1D9"},
    kategorie=_KAT_DUNKEL, raster="#1F262F", tooltip_bg="#E6EDF3", tooltip_text="#0D1117",
)

HOCHKONTRAST = replace(
    DUNKEL, name="hochkontrast", bg="#000000", surface="#000000", surface_2="#0A0A0A", hover="#1A1A1A",
    border="#FFFFFF", border_strong="#FFFFFF", text="#FFFFFF", text_2="#FFFFFF", text_3="#D0D0D0",
    accent="#00E5E5", accent_hover="#66F0F0", accent_text="#000000", accent_soft="#003333", fokus="#FFFF00",
    raster="#333333", tooltip_bg="#FFFFFF", tooltip_text="#000000",
)

THEMES = {"hell": HELL, "dunkel": DUNKEL, "hochkontrast": HOCHKONTRAST}
T: Theme = HELL

RADIUS = 10
RADIUS_KLEIN = 7


def system_ist_dunkel() -> bool:
    app = QApplication.instance()
    try:
        from PySide6.QtCore import Qt
        return app is not None and app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False


def aufloesen(modus: str) -> Theme:
    if modus == "system":
        return DUNKEL if system_ist_dunkel() else HELL
    return THEMES.get(modus, HELL)


def setzen(modus: str) -> Theme:
    global T
    T = aufloesen(modus)
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(stylesheet(T))
        pal = app.palette()
        for rolle, farbe in ((QPalette.Window, T.bg), (QPalette.Base, T.surface), (QPalette.Text, T.text),
                             (QPalette.WindowText, T.text), (QPalette.Highlight, T.accent),
                             (QPalette.HighlightedText, T.accent_text), (QPalette.ToolTipBase, T.tooltip_bg),
                             (QPalette.ToolTipText, T.tooltip_text), (QPalette.Button, T.surface),
                             (QPalette.ButtonText, T.text), (QPalette.PlaceholderText, T.text_3)):
            pal.setColor(rolle, QColor(farbe))
        app.setPalette(pal)
    return T


def schrift() -> QFont:
    familien = set(QFontDatabase.families())
    for name in ("Segoe UI Variable Text", "Segoe UI", "Inter", "SF Pro Text", "Helvetica Neue", "Noto Sans", "DejaVu Sans"):
        if name in familien:
            f = QFont(name)
            break
    else:
        f = QFont()
    f.setPointSizeF(9.75 if sys.platform == "win32" else 10)
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


def mpl_schrift() -> list[str]:
    return ["Segoe UI", "Inter", "Helvetica Neue", "DejaVu Sans"]


def alpha(farbe: str, a: float) -> str:
    c = QColor(farbe)
    return f"rgba({c.red()},{c.green()},{c.blue()},{a:.3f})"


def _icon_datei(name: str, farbe: str) -> str:
    """Schreibt ein eingefärbtes Icon als PNG in einen Cache-Ordner (QSS braucht Dateipfade)."""
    import tempfile
    from pathlib import Path

    from . import icons

    ordner = Path(tempfile.gettempdir()) / "belegungsdashboard_icons"
    ordner.mkdir(exist_ok=True)
    pfad = ordner / f"{name}_{farbe.strip('#')}.png"
    if not pfad.exists():
        icons.pixmap(name, farbe, 14, 2.0).save(str(pfad))
    return pfad.as_posix()


def stylesheet(t: Theme) -> str:
    try:
        haken = _icon_datei("haken", t.accent_text)
        pfeil = _icon_datei("runter", t.text_2)
    except Exception:
        haken = pfeil = ""
    return f"""
* {{ outline: none; }}
QWidget {{ color: {t.text}; font-size: 13px; }}
QMainWindow, QDialog, #wurzel {{ background: {t.bg}; }}
QToolTip {{ background: {t.tooltip_bg}; color: {t.tooltip_text}; border: none; padding: 6px 8px; border-radius: 6px; }}
QLabel {{ background: transparent; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QStackedWidget {{ background: transparent; }}

/* ---------- Sidebar ---------- */
#sidebar {{ background: {t.surface}; border-right: 1px solid {t.border}; }}
#sidebar QLabel#marke {{ font-size: 15px; font-weight: 700; color: {t.text}; }}
#sidebar QLabel#marke_sub {{ font-size: 11px; color: {t.text_3}; }}
QPushButton[nav="true"] {{
    text-align: left; padding: 9px 12px; border: none; border-radius: {RADIUS_KLEIN}px;
    color: {t.text_2}; font-weight: 500; background: transparent;
}}
QPushButton[nav="true"]:hover {{ background: {t.hover}; color: {t.text}; }}
QPushButton[nav="true"]:checked {{ background: {t.accent_soft}; color: {t.accent}; font-weight: 600; }}
QLabel[rolle="nav_gruppe"] {{ color: {t.text_3}; font-size: 11px; font-weight: 600; padding: 12px 12px 4px 12px; letter-spacing: 0.4px; }}

/* ---------- Kopfzeile ---------- */
#kopf {{ background: {t.bg}; }}
QLabel[rolle="seitentitel"] {{ font-size: 22px; font-weight: 700; color: {t.text}; }}
QLabel[rolle="seitenuntertitel"] {{ font-size: 13px; color: {t.text_2}; }}

/* ---------- Karten ---------- */
QFrame[karte="true"] {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: {RADIUS}px; }}
QFrame[karte="true"][klickbar="true"]:hover {{ border-color: {t.border_strong}; }}
QFrame[karte="true"][aktiv="true"] {{ border: 1.5px solid {t.accent}; }}
QLabel[rolle="kartentitel"] {{ font-size: 14px; font-weight: 600; color: {t.text}; }}
QLabel[rolle="kartenuntertitel"] {{ font-size: 12px; color: {t.text_2}; }}
QLabel[rolle="kpi_label"] {{ font-size: 12px; color: {t.text_2}; font-weight: 500; }}
QLabel[rolle="kpi_wert"] {{ font-size: 26px; font-weight: 700; color: {t.text}; }}
QLabel[rolle="kpi_wert_klein"] {{ font-size: 20px; font-weight: 700; color: {t.text}; }}
QLabel[rolle="kpi_detail"] {{ font-size: 12px; color: {t.text_3}; }}
QLabel[rolle="muted"] {{ color: {t.text_2}; }}
QLabel[rolle="klein"] {{ color: {t.text_3}; font-size: 12px; }}
QLabel[rolle="fett"] {{ font-weight: 600; }}
QLabel[rolle="abschnitt"] {{ font-size: 15px; font-weight: 600; }}

/* ---------- Pillen / Badges ---------- */
QLabel[pille] {{ border-radius: 10px; padding: 2px 9px; font-size: 11.5px; font-weight: 600; }}
QLabel[pille="ok"] {{ background: {alpha(t.ok, .14)}; color: {t.ok}; }}
QLabel[pille="knapp"] {{ background: {alpha(t.knapp, .16)}; color: {t.knapp}; }}
QLabel[pille="kritisch"] {{ background: {alpha(t.kritisch, .16)}; color: {t.kritisch}; }}
QLabel[pille="ueber"] {{ background: {alpha(t.ueber, .16)}; color: {t.ueber}; }}
QLabel[pille="unbekannt"], QLabel[pille="neutral"] {{ background: {t.surface_2}; color: {t.text_2}; }}
QLabel[pille="akzent"] {{ background: {t.accent_soft}; color: {t.accent}; }}

/* ---------- Hinweise ---------- */
QFrame[hinweis] {{ border-radius: {RADIUS_KLEIN}px; }}
QFrame[hinweis="info"] {{ background: {t.accent_soft}; }}
QFrame[hinweis="warnung"] {{ background: {alpha(t.knapp, .13)}; }}
QFrame[hinweis="fehler"] {{ background: {alpha(t.ueber, .12)}; }}

/* ---------- Knöpfe ---------- */
QPushButton {{
    background: {t.surface}; color: {t.text}; border: 1px solid {t.border_strong};
    border-radius: {RADIUS_KLEIN}px; padding: 7px 14px; font-weight: 500;
}}
QPushButton:hover {{ background: {t.hover}; }}
QPushButton:pressed {{ background: {t.surface_2}; }}
QPushButton:disabled {{ color: {t.text_3}; border-color: {t.border}; background: {t.surface_2}; }}
QPushButton:focus {{ border-color: {t.fokus}; }}
QPushButton[variant="primary"] {{ background: {t.accent}; color: {t.accent_text}; border: 1px solid {t.accent}; font-weight: 600; }}
QPushButton[variant="primary"]:hover {{ background: {t.accent_hover}; border-color: {t.accent_hover}; }}
QPushButton[variant="primary"]:disabled {{ background: {t.border_strong}; border-color: {t.border_strong}; color: {t.surface}; }}
QPushButton[variant="ghost"] {{ background: transparent; border: 1px solid transparent; color: {t.text_2}; }}
QPushButton[variant="ghost"]:hover {{ background: {t.hover}; color: {t.text}; }}
QPushButton[variant="gefahr"] {{ color: {t.ueber}; border-color: {alpha(t.ueber, .45)}; background: transparent; }}
QPushButton[variant="gefahr"]:hover {{ background: {alpha(t.ueber, .10)}; }}
QPushButton[variant="chip"] {{
    background: {t.surface}; border: 1px solid {t.border_strong}; border-radius: 15px;
    padding: 5px 12px; color: {t.text_2}; font-size: 12.5px;
}}
QPushButton[variant="chip"]:hover {{ border-color: {t.accent}; color: {t.accent}; background: {t.accent_soft}; }}
QPushButton[variant="icon"] {{ background: transparent; border: none; padding: 5px; border-radius: 6px; }}
QPushButton[variant="icon"]:hover {{ background: {t.hover}; }}
QToolButton {{ background: transparent; border: none; border-radius: 6px; padding: 4px; }}
QToolButton:hover {{ background: {t.hover}; }}

/* ---------- Segmentierte Auswahl ---------- */
QFrame[segment="true"] {{ background: {t.surface_2}; border: 1px solid {t.border}; border-radius: 9px; }}
QFrame[segment="true"] QPushButton {{
    border: none; background: transparent; color: {t.text_2}; padding: 5px 12px; border-radius: 6px; font-weight: 500;
}}
QFrame[segment="true"] QPushButton:hover {{ color: {t.text}; }}
QFrame[segment="true"] QPushButton:checked {{ background: {t.surface}; color: {t.text}; font-weight: 600; border: 1px solid {t.border}; }}

/* ---------- Eingaben ---------- */
QLineEdit, QSpinBox, QDateEdit, QComboBox, QPlainTextEdit, QTextEdit {{
    background: {t.surface}; color: {t.text}; border: 1px solid {t.border_strong};
    border-radius: {RADIUS_KLEIN}px; padding: 6px 9px; selection-background-color: {t.accent}; selection-color: {t.accent_text};
}}
QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{ border: 1px solid {t.fokus}; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {t.text_3}; background: {t.surface_2}; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}
QComboBox::drop-down, QDateEdit::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: url({pfeil}); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {t.surface}; color: {t.text}; border: 1px solid {t.border}; border-radius: 6px;
    selection-background-color: {t.accent_soft}; selection-color: {t.text}; padding: 4px;
}}
QLineEdit#chat_eingabe {{ border-radius: 12px; padding: 11px 14px; font-size: 14px; }}

/* ---------- Kalender ---------- */
QCalendarWidget QWidget {{ alternate-background-color: {t.surface_2}; }}
QCalendarWidget QToolButton {{ color: {t.text}; font-weight: 600; padding: 4px 8px; }}
QCalendarWidget QAbstractItemView {{ background: {t.surface}; color: {t.text}; selection-background-color: {t.accent}; selection-color: {t.accent_text}; }}
QCalendarWidget #qt_calendar_navigationbar {{ background: {t.surface_2}; }}

/* ---------- Tabellen ---------- */
QTableView, QTableWidget {{
    background: {t.surface}; alternate-background-color: {t.surface_2}; border: none;
    gridline-color: transparent; selection-background-color: {t.accent_soft}; selection-color: {t.text};
}}
QTableView::item {{ padding: 6px 8px; border-bottom: 1px solid {t.border}; }}
QHeaderView::section {{
    background: {t.surface}; color: {t.text_3}; border: none; border-bottom: 1px solid {t.border_strong};
    padding: 8px; font-size: 11.5px; font-weight: 600;
}}
QTableCornerButton::section {{ background: {t.surface}; border: none; }}

/* ---------- Scrollbars ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {t.border_strong}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {t.text_3}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {t.border_strong}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ width: 0; height: 0; background: none; }}

/* ---------- Sonstiges ---------- */
QProgressBar {{ background: {t.surface_2}; border: none; border-radius: 3px; height: 6px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {t.accent}; border-radius: 3px; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {t.border_strong}; background: {t.surface}; }}
QCheckBox::indicator:checked {{ background: {t.accent}; border-color: {t.accent}; image: url({haken}); }}
QMenu {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 8px; padding: 5px; }}
QMenu::item {{ padding: 7px 14px; border-radius: 5px; }}
QMenu::item:selected {{ background: {t.hover}; }}
QFrame[trenner="true"] {{ background: {t.border}; max-height: 1px; min-height: 1px; border: none; }}
#toast {{ background: {t.tooltip_bg}; border-radius: 10px; }}
#toast QLabel {{ color: {t.tooltip_text}; }}
QFrame[blase="nutzer"] {{ background: {t.accent}; border-radius: 14px; }}
QFrame[blase="nutzer"] QLabel {{ color: {t.accent_text}; }}
QFrame[blase="assistent"] {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 14px; }}
QFrame[blase="hinweis"] {{ background: {t.surface_2}; border-radius: 14px; }}
"""
