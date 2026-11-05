"""Menüband (0.65): Aufbau der Office-ähnlichen Darstellung – Registerkarten, Gruppen, große und kleine Schaltflächen,
Ausklappmenüs. Rein, ohne NiceGUI: Die Unteransichten der Seiten kommen als Wörterbuch herein (``ansichten``), damit
das Menüband nie von den Seiten abweicht und sich ohne Oberfläche prüfen lässt.

Ein Ziel ist entweder ``("seite", seite, ansicht | None, {zustand})`` oder ``("aktion", name)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Punkt:
    text: str
    icon: str
    ziel: tuple | None = None
    gross: bool = True
    tipp: str = ""
    menue: list["Punkt"] = field(default_factory=list)      # nicht leer → Ausklappmenü statt direktem Sprung
    farbe: str = ""                                          # Farbmuster statt Symbolfarbe (Menü „Farben“)


@dataclass
class Gruppe:
    titel: str
    punkte: list[Punkt]


@dataclass
class Reiter:
    key: str
    titel: str
    gruppen: list[Gruppe]


def S(seite: str, ansicht: str | None = None, **zustand) -> tuple:
    return ("seite", seite, ansicht, zustand)


def A(name: str) -> tuple:
    return ("aktion", name)


ICONS = {   # Symbole der Unteransichten – leicht erkennbar, wie in Office
    "anreisen": {"zuteilen": "how_to_reg", "personen": "groups", "abreisen": "flight_takeoff", "eintragen": "keyboard"},
    "zimmer": {"uebersicht": "grid_view", "karten": "view_module", "zeitstrahl": "view_timeline", "liste": "table_rows",
               "maengel": "build", "aenderungen": "history"},
    "reinigung": {"liste": "checklist", "last": "date_range", "facility": "fact_check"},
    "termine": {"liste": "view_list", "monat": "calendar_month"},
    "assistenz": {"auftraege": "assignment", "mails": "mail", "fragen": "help_center"},
    "auswertung": {"lage": "dashboard", "belegung": "stacked_line_chart", "prognose": "trending_up",
                   "massnahmen": "school", "zimmer": "bed"},
    "steuerung": {"cockpit": "speed", "vorhaben": "construction", "zeitplan": "event_note", "finanzen": "euro",
                  "grundlagen": "tune"},
    "inventar": {"gegenstaende": "inventory_2", "zimmer": "meeting_room", "haeuser": "apartment"},
    "einstellungen": {"allgemein": "settings", "stammdaten": "edit_note", "sicherung": "backup"},
}


def _auswahl(seite: str, ansichten: dict, text: str, icon: str, tipp: str = "") -> Punkt:
    """Große Schaltfläche mit Ausklappmenü: alle Unteransichten der Seite."""
    views = ansichten.get(seite) or {}
    menue = [Punkt(t, ICONS.get(seite, {}).get(k, "chevron_right"), S(seite, k), False) for k, t in views.items()]
    return Punkt(text, icon, S(seite), True, tipp or f"{text} – Ansicht wählen", menue)


def _einzeln(seite: str, ansichten: dict, keys: list[str] | None = None, gross: bool = True) -> list[Punkt]:
    """Jede Unteransicht als eigene Schaltfläche (für die Seite, die der Reiter vor allem zeigt)."""
    views = ansichten.get(seite) or {}
    return [Punkt(views[k], ICONS.get(seite, {}).get(k, "chevron_right"), S(seite, k), gross)
            for k in (keys or list(views)) if k in views]


def reiter(ansichten: dict[str, dict[str, str]]) -> list[Reiter]:
    """Registerkarten des Menübands. ``ansichten``: Seite → {Unteransicht: Titel} (aus den Seiten-Modulen)."""
    an = ansichten.get("anreisen") or {}
    return [
        Reiter("start", "Start", [
            Gruppe("Bearbeiten", [Punkt("Rückgängig", "undo", A("rueckgaengig"), tipp="Letzte Änderung zurücknehmen (Strg+Z)"),
                                  Punkt("Suchen", "search", A("suchen"), False, "Personen, Zimmer und Seiten suchen (Strg+K)"),
                                  Punkt("Aktualisieren", "refresh", A("aktualisieren"), False, "Daten neu einlesen")]),
            Gruppe("Heute", [Punkt("Tages­übersicht", "today", S("heute", heute_ansicht="zentrale"),
                                   tipp="Kennzahlen und offene Aufgaben des Tages"),
                             Punkt("Postfach", "inbox", S("heute", heute_ansicht="postfach"),
                                   tipp="Alle Aufgaben mit ihren Fällen bearbeiten")]),
            Gruppe("Aufgaben", [Punkt("Aufgaben", "task_alt", A("aufgaben"), tipp="Aufgaben-Center öffnen (Taste A)"),
                                Punkt("Neuigkeiten", "notifications", A("neuigkeiten"), tipp="Letzte Neuigkeiten")]),
            Gruppe("Belegung", [Punkt(an.get("zuteilen", "Zuteilen"), "how_to_reg", S("anreisen", "zuteilen"),
                                      tipp="Anreisen ein Zimmer zuteilen"),
                                _auswahl("zimmer", ansichten, "Zimmer", "meeting_room"),
                                Punkt("Reinigung", "cleaning_services", S("reinigung"), tipp="Reinigungsliste")]),
        ]),
        Reiter("belegung", "Belegung", [
            Gruppe("Anreisen", _einzeln("anreisen", ansichten)),
            Gruppe("Zimmer", _einzeln("zimmer", ansichten, ["uebersicht", "zeitstrahl", "liste"])
                   + _einzeln("zimmer", ansichten, ["karten", "maengel", "aenderungen"], gross=False)),
            Gruppe("Reinigung", _einzeln("reinigung", ansichten)),
            Gruppe("Mieter", [Punkt("Mieter", "key", S("mieter"), tipp="Mieter und Mietverträge")]),
        ]),
        Reiter("planung", "Planung", [
            Gruppe("Termine", _einzeln("termine", ansichten)),
            Gruppe("Assistenz", _einzeln("assistenz", ansichten)),
        ]),
        Reiter("auswertung", "Auswertung", [
            Gruppe("Auswertung", _einzeln("auswertung", ansichten)),
            Gruppe("Leitung", [_auswahl("steuerung", ansichten, "Steuerung", "query_stats",
                                        "Renovierung, Zeitplan, Finanzen – Ansicht wählen")]),
        ]),
        Reiter("verwalten", "Verwalten", [
            Gruppe("Daten", [Punkt("Daten & Import", "upload_file", S("daten"), tipp="Listen einlesen, Stand prüfen")]),
            Gruppe("Inventar", [_auswahl("inventar", ansichten, "Inventar", "inventory_2")]),
            Gruppe("Einstellungen", _einzeln("einstellungen", ansichten)),
            Gruppe("Standort", [Punkt("Standort", "location_city", A("standort"), tipp="Standort wechseln")]),
        ]),
        Reiter("ansicht", "Ansicht", [
            Gruppe("Design", [Punkt("Farben", "palette", None, True, "Farbschema wählen",
                                    [Punkt(n, "circle", A(f"farbe:{k}"), False, farbe=c) for k, (n, c, _t) in _farben()]
                                    + [Punkt("Weitere Farben …", "colorize", A("optionen:farben"), False)]),
                              Punkt("Hell / Dunkel", "contrast", A("modus"), tipp="Zwischen hell und dunkel wechseln"),
                              Punkt("Schriftart", "font_download", A("optionen:anzeige"), tipp="Schriftart wählen")]),
            Gruppe("Zoom", [Punkt("Zoom", "zoom_in", A("optionen:anzeige"), tipp="Zoom und Schrift einstellen"),
                            Punkt("100 %", "crop_free", A("zoom:100"), tipp="Zoom auf 100 % zurücksetzen"),
                            Punkt("Vergrößern", "add", A("zoom:+"), False, "Inhalt größer"),
                            Punkt("Verkleinern", "remove", A("zoom:-"), False, "Inhalt kleiner")]),
            Gruppe("Darstellung", [Punkt("Kompakt", "density_small", A("dichte"), False, "Mehr Zeilen auf einen Blick"),
                                   Punkt("Vollbild", "fullscreen", A("vollbild"), False, "Vollbild ein/aus"),
                                   Punkt("Großes Menüband", "touch_app", A("band_gross"), False, "Für Touch und große Monitore")]),
            Gruppe("Diagramme", [Punkt("Diagramm\u00adtyp", "insert_chart", None, True, "Linie, Fläche oder Säulen",
                                       [Punkt(t, i, A(f"dg_typ:{k}"), False) for k, (t, i) in _dg_typen()]
                                       + [Punkt("Diagramm-Optionen …", "tune", A("optionen:diagramme"), False)])]),
            Gruppe("Oberfläche", [Punkt("Layout", "space_dashboard", None, True, "Andere Darstellung wählen",
                                        [Punkt(n, "radio_button_unchecked", A(f"layout:{k}"), False)
                                         for k, n in LAYOUT_NAMEN.items()]),
                                  Punkt("Leitstand", "view_quilt", A("leitstand"),
                                        tipp="Zur Leitstand-Workbench wechseln (Strg+Umschalt+L)")]),
            Gruppe("Optionen", [Punkt("Optionen", "settings_suggest", A("optionen:farben"),
                                      tipp="Alle Einstellungen zur Darstellung (Farben, Zoom, Schrift, Diagramme)")]),
        ]),
    ]


LAYOUT_NAMEN = {"office": "Menüband (wie Office)", "original": "Original-Zustand", "grid": "Classic Enterprise Grid",
                "showcase": "Showcase", "canvas": "AI-Canvas & Prompt"}

DATEI = [   # Menü „Datei“ (links, farbig) – das Wichtigste rund um Daten und Programm
    Punkt("Daten einlesen", "upload_file", S("daten"), False),
    Punkt("Sicherung & Verlauf", "backup", S("einstellungen", "sicherung"), False),
    Punkt("Einstellungen", "settings", S("einstellungen", "allgemein"), False),
    Punkt("Standort wechseln", "location_city", A("standort"), False),
    Punkt("Leitstand-Workbench", "view_quilt", A("leitstand"), False),
    Punkt("Info", "info", A("info"), False),
    Punkt("Optionen", "settings_suggest", A("optionen:farben"), False),
]


def _farben():
    from .darstellung_kern import FARBSCHEMATA

    return list(FARBSCHEMATA.items())


def _dg_typen():
    from .darstellung_kern import DG_TYPEN

    return list(DG_TYPEN.items())


def aktiv(p: Punkt, seite: str, ansicht_von, heute_ansicht: str = "zentrale") -> bool:
    """Ist die Schaltfläche die gerade offene Seite/Ansicht? ``ansicht_von(seite)`` liefert die aktuelle Unteransicht."""
    if p.menue:
        return any(aktiv(m, seite, ansicht_von, heute_ansicht) for m in p.menue)
    if not p.ziel or p.ziel[0] != "seite" or p.ziel[1] != seite:
        return False
    _s, s, ans, zustand = p.ziel
    if s == "heute":
        return zustand.get("heute_ansicht", "zentrale") == heute_ansicht
    return ans is None or ans == ansicht_von(s)


def reiter_von(seite: str, ansichten: dict) -> str:
    """Registerkarte, die zu einer Seite gehört (beim Sprung über Suche oder Aufgaben folgt das Band der Seite)."""
    for r in reiter(ansichten)[1:]:            # „Start“ nur, wenn keine andere passt
        for g in r.gruppen:
            for p in g.punkte:
                for q in (p.menue or [p]):
                    if q.ziel and q.ziel[0] == "seite" and q.ziel[1] == seite:
                        return r.key
    return "start"


def statuszeile(standort: str, karten, stand: str) -> str:
    dringend = sum(1 for k in karten if k.stufe == "dringend")
    teile = [standort, f"{len(karten)} offene Aufgabe{'n' if len(karten) != 1 else ''}"
             + (f" · {dringend} dringend" if dringend else "")]
    if stand:
        teile.append(stand)
    return "   |   ".join(teile)
