"""Symbole (1.00): Microsoft Fluent 2 – „Fluent UI System Icons“ (MIT, siehe ``symbole/LIZENZ.txt``), offline als SVG.

Ein Symbol ist zweifarbig wie in Microsoft 365 (Duotone):
* unten dieselbe Form **gefüllt** in einer Bedeutungsfarbe, zart (Deckung per CSS ``--sym-deckung``),
* darüber die feine **Kontur** in Schiefergrau (``--sym-basis``; im Dunkeln hell).
Kompakte Knöpfe (18 px) zeigen nur die Kontur – in der Bedeutungsfarbe, wie die 16-px-Symbole in Office.

Rein bis auf das Lesen der Dateien: liefert HTML-Text, die Oberfläche setzt ihn mit ``ui.html`` ein.
"""

from __future__ import annotations

import html as _html
from functools import lru_cache
from pathlib import Path

ORDNER = Path(__file__).resolve().parent / "symbole"

BASIS = ""                      # keine Bedeutungsfarbe → nur Schiefergrau
BLAU, TEAL, GRUEN, AMBER, VIOLETT, ROT = "#0284c7", "#0f766e", "#10b981", "#f59e0b", "#8b5cf6", "#e11d48"
FARBEN = {"blau": BLAU, "teal": TEAL, "gruen": GRUEN, "amber": AMBER, "violett": VIOLETT, "rot": ROT}


@lru_cache(maxsize=None)
def svg(name: str, stufe: str = "g", art: str = "r") -> str:
    """SVG-Text: ``stufe`` g (groß, 24–32er Zeichnung) | k (kompakt, 20er), ``art`` r (Kontur) | f (gefüllt)."""
    p = ORDNER / f"{name}.{stufe}.{art}.svg"
    if not p.exists() and stufe == "k":
        p = ORDNER / f"{name}.g.{art}.svg"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def vorhanden(name: str) -> bool:
    return bool(svg(name, "g", "r"))


def alle() -> list[str]:
    return sorted({p.name.split(".")[0] for p in ORDNER.glob("*.svg")})


# 1.01: Material-Symbolnamen der bisherigen Knöpfe → (Fluent-Symbol, Bedeutungsfarbe). So zeigen auch Seiten, die noch
# Material-Namen übergeben, im Menüband einheitlich Fluent.
MATERIAL = {
    # 1.13: eigene Symbole statt Dopplungen (Budget, Annahmen, Grenzen, Kennzahlen eingeben, Excel-Export)
    "account_balance_wallet": ("money", AMBER), "request_quote": ("calculator", TEAL), "straighten": ("ruler", BASIS),
    "dialpad": ("number_symbol_square", TEAL), "grid_on": ("table_arrow_up", GRUEN),
    "check": ("checkmark", GRUEN), "print": ("print", BASIS), "more_horiz": ("more_horizontal", BASIS),
    "delete": ("delete", ROT), "delete_outline": ("delete", ROT), "close": ("dismiss", BASIS), "add": ("add", BLAU),
    "undo": ("arrow_undo", BASIS), "table_view": ("table", TEAL), "content_copy": ("copy", BLAU), "search": ("search", BASIS),
    "restart_alt": ("arrow_reset", BASIS), "person_add": ("person_add", BLAU), "drive_file_move": ("folder_arrow_right", BLAU),
    "bookmark_add": ("bookmark_add", AMBER), "auto_awesome": ("sparkle", AMBER), "visibility": ("eye", BLAU),
    "view_timeline": ("gantt_chart", GRUEN), "update": ("arrow_sync", BLAU), "sync": ("arrow_sync", BLAU),
    "tune": ("options", VIOLETT), "swap_horiz": ("arrow_swap", AMBER), "send": ("send", BLAU), "school": ("hat_graduation", VIOLETT),
    "save": ("save", BLAU), "restore": ("history", BASIS), "remove": ("subtract", BASIS),
    "playlist_add_check": ("clipboard_checkmark", TEAL), "play_arrow": ("play", BLAU), "picture_as_pdf": ("document_pdf", ROT),
    "open_in_new": ("open", BASIS), "notifications": ("alert", AMBER), "mail": ("mail", BLAU), "logout": ("sign_out", BASIS),
    "list": ("list", BASIS), "ios_share": ("share", BLAU), "insights": ("data_trending", BLAU), "fullscreen": ("open", BASIS),
    "filter_list": ("filter", BASIS), "filter_alt": ("filter", BASIS), "fact_check": ("clipboard_checkmark", TEAL),
    "event": ("calendar", BLAU), "edit": ("edit", AMBER), "done_all": ("checkmark_circle_square", GRUEN),
    "description": ("document", BASIS), "construction": ("wrench", AMBER), "bolt": ("flash", AMBER),
    "backup": ("cloud_archive", BLAU), "assignment": ("clipboard_task", TEAL), "upload_file": ("arrow_upload", BLAU),
    "download": ("arrow_download", BLAU), "file_download": ("arrow_download", BLAU), "upload": ("arrow_upload", BLAU),
    "chevron_left": ("chevron_left", BASIS), "chevron_right": ("chevron_right", BASIS), "settings": ("settings", BASIS),
    "info": ("info", BLAU), "help_outline": ("question_circle", BLAU), "event_available": ("calendar_add", BLAU),
    "refresh": ("arrow_clockwise", BASIS), "emergency": ("person_alert", ROT), "view_sidebar": ("layout_column_three", BASIS),
    "filter_alt_off": ("arrow_reset", BASIS), "cleaning_services": ("broom", BLAU), "key": ("key", AMBER),
    "groups": ("people", BLAU), "person": ("person", BLAU), "apartment": ("building_multiple", BLAU),
    "calendar_month": ("calendar_month", BLAU), "date_range": ("calendar_date", BLAU), "warning": ("warning", AMBER),
    "build": ("wrench", AMBER), "history": ("history", BASIS), "bed": ("bed", BASIS), "check_circle": ("checkmark_circle", GRUEN),
    "block": ("prohibited", ROT), "handyman": ("wrench_settings", AMBER), "qr_code_2": ("qr_code", BLAU), "schedule": ("calendar_clock", BLAU), "today": ("calendar_today", BLAU),
    "event_seat": ("seat", VIOLETT), "checklist": ("checkbox_checked", TEAL), "edit_calendar": ("calendar_edit", BLAU),
    "table_rows": ("table", TEAL), "grid_view": ("grid", BLAU), "inventory_2": ("box", BLAU), "edit_note": ("document_edit", BASIS),
}
# Zustands- und Filterschlüssel der Kennzahl-Chips → Fluent
ZUSTAND = {
    "frei": ("checkmark_circle", GRUEN), "teilweise": ("checkmark_circle", GRUEN), "belegt": ("person", BLAU),
    "geplant": ("calendar_clock", BLAU), "gesperrt": ("lock_closed", BASIS), "nicht_nutzbar": ("prohibited", ROT),
    "maengel": ("wrench", AMBER), "unbewohnbar": ("prohibited", ROT), "pruefen": ("warning", AMBER), "ohne": ("person_question_mark", AMBER), "mit": ("home_checkmark", GRUEN),
    "handeln": ("alert_urgent", ROT), "alle": ("people", BLAU), "np": ("arrow_right", BASIS), "offen": ("clock", AMBER),
    "eilig": ("flash", ROT), "erledigt": ("checkmark_circle", GRUEN), "laufend": ("key", AMBER), "mail": ("mail", BLAU),
    "weitere": ("building_multiple", BASIS), "neu": ("new", VIOLETT), "bereit": ("checkmark_starburst", GRUEN),
    "unfertig": ("broom", AMBER), 3: ("prohibited", ROT), 2: ("warning", AMBER), 1: ("info", BLAU),
}
TON = {"ok": ("checkmark_circle", GRUEN), "warn": ("warning", AMBER), "krit": ("alert_urgent", ROT), "blau": ("person", BLAU),
       "akzent": ("calendar_clock", BLAU), "neutral": ("filter", BASIS)}


# 1.01: Knöpfe ohne Symbol im Menüband – nach Stichwort im Text (erstes passendes gilt), sonst „⋯“
TEXT = (("letzte", ("calendar_arrow_counterclockwise", BLAU)),        # 1.13: Zeiträume unterscheidbar
        ("nächste 3", ("calendar_arrow_right", BLAU)), ("heute", ("calendar_today", BLAU)), ("monat", ("calendar_month", BLAU)), ("jahr", ("calendar_date", BLAU)),
        ("woche", ("calendar_week_numbers", BLAU)), ("anzeigen", ("eye", BLAU)), ("ansehen", ("eye", BLAU)),
        ("hinzufügen", ("add", BLAU)), ("neue", ("add", BLAU)), ("entfernen", ("delete", ROT)), ("mail", ("mail", BLAU)),
        ("speichern", ("save", BLAU)), ("zurück", ("arrow_undo", BASIS)), ("reinigung", ("broom", BLAU)),
        ("umzug", ("arrow_swap", AMBER)), ("notiz", ("document_edit", BASIS)), ("zeitstrahl", ("gantt_chart", GRUEN)),
        ("diagramm", ("data_trending", BLAU)), ("prognose", ("data_trending", BLAU)), ("szenari", ("options", VIOLETT)),
        ("bearbeiten", ("edit", AMBER)), ("ändern", ("edit", AMBER)), ("planen", ("calendar_clock", BLAU)),
        ("zuteilen", ("person_add", BLAU)), ("zuweisen", ("person_add", BLAU)), ("person", ("person", BLAU)),
        ("übernehmen", ("checkmark", GRUEN)), ("zur ", ("arrow_right", BASIS)), ("zu den", ("arrow_right", BASIS)),
        ("tage", ("calendar_day", BLAU)))                                     # 1.13: „Tage“ statt „Mehr …“


def aus_text(text: str, ersatz: tuple = ("more_horizontal", BASIS)) -> tuple[str, str]:
    t = str(text or "").lower()
    for wort, ziel in TEXT:
        if wort in t and vorhanden(ziel[0]):
            return ziel
    return ersatz


def aus_material(icon: str, ersatz: tuple = ("more_horizontal", BASIS)) -> tuple[str, str]:
    """(Fluent-Symbol, Farbe) zu einem Material-Namen – unbekannt → ``ersatz``."""
    if icon in MATERIAL:
        return MATERIAL[icon]
    return (icon, BASIS) if vorhanden(icon) else ersatz


# 1.34: zweite Variante „farbig“ – vollfarbige Fluent-Symbole (Microsoft, MIT, Ordner ``symbole/farbig``). Gleicher
# Name wie die zweifarbige Fassung, sonst das nächstliegende Motiv; ohne passendes farbiges Motiv bleibt es zweifarbig.
FARBIG_ORDNER = ORDNER / "farbig"
FARBIG_ERSATZ = {
    "add": "add_circle", "archive": "document_folder", "arrow_clockwise": "arrow_sync",
    "arrow_download": "arrow_square_down", "arrow_reset": "arrow_clockwise_dashes", "arrow_swap": "arrow_sync",
    "arrow_trending": "arrow_trending_lines", "arrow_undo": "history", "battery_charge": "gauge",
    "bed": "building_home", "bookmark_add": "bookmark", "calculator": "receipt", "calendar_add": "calendar_edit",
    "calendar_arrow_counterclockwise": "calendar_sync", "calendar_arrow_right": "calendar_clock",
    "calendar_date": "calendar", "calendar_day": "calendar", "calendar_ltr": "calendar",
    "calendar_month": "calendar", "calendar_today": "calendar_checkmark",
    "calendar_week_numbers": "calendar_data_bar", "checkbox_checked": "checkbox", "checkmark": "checkmark_circle",
    "checkmark_circle_square": "checkmark_circle", "checkmark_starburst": "ribbon_star",
    "clipboard_checkmark": "clipboard_task", "clipboard_task_list_ltr": "clipboard_task", "cloud_archive": "cloud",
    "conference_room": "people_team", "content_view_gallery": "content_view", "copy": "document_add",
    "data_bar_vertical": "data_bar_vertical_ascending", "dismiss": "dismiss_circle",
    "document_checkmark": "clipboard_task", "document_pdf": "document_text", "door": "building_home",
    "door_arrow_right": "people_home", "eye": "search_visual", "folder_arrow_right": "document_folder",
    "gantt_chart": "chart_multiple", "grid": "apps", "hat_graduation": "certificate", "home_checkmark": "home",
    "info": "question_circle", "key": "person_key", "layer": "board", "layout_column_three": "board",
    "list": "list_bar", "location": "location_ripple", "money": "coin_multiple", "new": "add_starburst",
    "open": "arrow_square", "person_alert": "person_warning", "person_arrow_right": "person_available",
    "person_question_mark": "person_tentative", "play": "fast_forward_circle", "prohibited": "dismiss_circle",
    "qr_code": "scan_type", "search": "search_visual", "share": "share_ios", "slide_play": "video",
    "sparkle": "bot_sparkle", "table_arrow_up": "table", "tag": "ribbon",
    "task_list_square_ltr": "text_bullet_list_square", "tasks_app": "clipboard_task",
    "weather_sunny": "weather_sunny_low", "wrench_settings": "wrench_screwdriver",
}
VARIANTE = {"art": "fluent"}          # gilt im ganzen Programm (ein Prozess = eine Person); setzt die Oberfläche
VORSCHAU = (("calendar", BLAU), ("people", BLAU), ("building_multiple", BLAU), ("warning", AMBER), ("wrench", AMBER))


@lru_cache(maxsize=None)
def farbig(name: str, stufe: str = "g") -> str:
    """SVG-Text der farbigen Fassung ("" = gibt es nicht)."""
    p = FARBIG_ORDNER / f"{FARBIG_ERSATZ.get(name, name)}.{stufe}.svg"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def html(name: str, farbe: str = BASIS, gross: bool = True, klasse: str = "", overlay: str = "",
         ofarbe: str = "", variante: str | None = None) -> str:
    """Duotone-Symbol als HTML. ``farbe``: Bedeutungsfarbe (Hex) oder leer. 1.07: ``overlay`` = kleines zweites Symbol
    unten rechts (z. B. Trend-Pfeil, Filter, Wechsel-Pfeil) in ``ofarbe``. 1.34: ``variante`` „farbig“ → vollfarbige
    Fassung, wenn es sie gibt (ohne Angabe gilt ``VARIANTE``)."""
    farbe = FARBEN.get(farbe, farbe)
    if (variante or VARIANTE["art"]) == "farbig" and (bunt := farbig(name, "g" if gross else "k")):
        inhalt = f'<span class="m-sym-c">{bunt}</span>'
        if overlay and gross:
            of = FARBEN.get(ofarbe, ofarbe) or BLAU
            inhalt += f'<span class="m-sym-ov" style="color:{_html.escape(of)}">{svg(overlay, "k", "f")}</span>'
        return f'<span class="m-sym {"gross" if gross else "klein"} farbig {klasse}" aria-hidden="true">{inhalt}</span>'
    if gross:
        flaeche = (f'<span class="m-sym-f" style="color:{_html.escape(farbe)}">{svg(name, "g", "f")}</span>'
                   if farbe else "")
        inhalt = f'{flaeche}<span class="m-sym-k">{svg(name, "g", "r")}</span>'
        if overlay:
            of = FARBEN.get(ofarbe, ofarbe) or BLAU
            inhalt += f'<span class="m-sym-ov" style="color:{_html.escape(of)}">{svg(overlay, "k", "f")}</span>'
        return f'<span class="m-sym gross {klasse}" aria-hidden="true">{inhalt}</span>'
    stil = f' style="color:{_html.escape(farbe)}"' if farbe else ""
    return f'<span class="m-sym klein {klasse}" aria-hidden="true"><span class="m-sym-k"{stil}>{svg(name, "k", "r")}</span></span>'


CSS = """
:root { --sym-basis: #334155; --sym-deckung: .45; }
body:not(.hell) { --sym-basis: #CBD5E1; --sym-deckung: .55; }
.m-sym { position: relative; display: inline-block; flex: none; line-height: 0; }
.m-sym.gross { width: 32px; height: 32px; }
.m-sym.klein { width: 20px; height: 20px; }
.m-sym > span { position: absolute; inset: 0; display: block; }
.m-sym svg { width: 100%; height: 100%; display: block; }
.m-sym .m-sym-k { color: var(--sym-basis); }
.m-sym .m-sym-f { opacity: var(--sym-deckung); }
.m-sym .m-sym-ov { inset: auto; right: -5px; bottom: -4px; width: 17px; height: 17px; padding: 1px; box-sizing: border-box;
  border-radius: 50%; background: var(--ob-band, #F7F9F9); }
"""
