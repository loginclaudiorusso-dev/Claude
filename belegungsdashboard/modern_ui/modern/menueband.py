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
    menue: list["Punkt"] = field(default_factory=list)      # Ausklappmenü; mit ``ziel`` zusammen: Split-Button
    farbe: str = ""                                          # Farbmuster statt Symbolfarbe (Menü „Farben“)


@dataclass
class Gruppe:
    titel: str
    punkte: list[Punkt]
    starter: tuple | None = None                             # ↘ in der Gruppenzeile öffnet den passenden Dialog (Office)


@dataclass
class Reiter:
    key: str
    titel: str
    gruppen: list[Gruppe]
    kontext: tuple = ()                                      # nicht leer → nur auf diesen Seiten (Kontext-Registerkarte)


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


def _menue(seite: str, ansichten: dict, keys: list[str] | None = None) -> list[Punkt]:
    views = ansichten.get(seite) or {}
    return [Punkt(views[k], ICONS.get(seite, {}).get(k, "chevron_right"), S(seite, k), False)
            for k in (keys or list(views)) if k in views]


def _split(seite: str, ansichten: dict, text: str, icon: str, keys: list[str] | None = None, tipp: str = "",
           standard: str | None = None) -> Punkt:
    """Split-Button wie in Office: oben öffnet die Standardansicht, der Pfeil die übrigen Ansichten."""
    return Punkt(text, icon, S(seite, standard), True, tipp or text, _menue(seite, ansichten, keys))


# Trennstellen für lange Wörter auf großen Schaltflächen (weiches Trennzeichen, nur wenn nötig sichtbar)
TRENNUNG = {"Firmenprogramm": "Firmen\u00adprogramm", "Gegenstände": "Gegen\u00adstände",
            "Reinigungsliste": "Reinigungs\u00adliste", "Neuanmeldungen": "Neu\u00adanmeldungen"}


def trenn(text: str) -> str:
    return " ".join(TRENNUNG.get(w, w) for w in text.split(" "))


def _einzeln(seite: str, ansichten: dict, keys: list[str] | None = None, gross: bool = True) -> list[Punkt]:
    views = ansichten.get(seite) or {}
    return [Punkt(trenn(views[k]) if gross else views[k], ICONS.get(seite, {}).get(k, "chevron_right"), S(seite, k), gross,
                  views[k]) for k in (keys or list(views)) if k in views]


def _haken(text: str, key: str) -> Punkt:
    """Menüpunkt mit Häkchen (an/aus) – Zustand zeigt die Oberfläche."""
    return Punkt(text, "haken", A(f"dg:{key}"), False)


# 0.69 – Regeln der Anordnung (nach zwei Reviews):
#  1. Jeder Arbeitsbereich ist eine Registerkarte; seine Ansichten stehen SICHTBAR im Band (kein Zielen auf ▾).
#  2. Jeder Befehl steht an genau einer Stelle. Standort, Glocke, Hilfe: Titelleiste. Zoom, Kompakt, Vollbild,
#     Hell/Dunkel: Statusleiste (wie Word/Excel). Farben, Layout, Programm-Einstellungen: Datei → Optionen.
#  3. Höchstens 8 Schaltflächen je Registerkarte; Split-Buttons nur für Seltenes (Steuerung, Inventar).
#  4. Kontext-Registerkarte nur für „Diagramm“; Filter bleiben in EINER Kopfzeile direkt über dem Inhalt.
#  5. Gruppenpfeil ↘ öffnet den Dialog zur Gruppe (statt eigener Schaltfläche).
KONTEXT_DIAGRAMM = ("auswertung", "steuerung")


def _v(ansichten: dict, seite: str, k: str, text: str | None = None, icon: str | None = None, gross: bool = True,
       tipp: str = "") -> Punkt:
    """Eine Unteransicht als Schaltfläche (Titel aus der Seite, wenn nicht anders angegeben)."""
    t = text or (ansichten.get(seite) or {}).get(k, k)
    return Punkt(t, icon or ICONS.get(seite, {}).get(k, "chevron_right"), S(seite, k), gross, tipp or t)


def reiter(ansichten: dict[str, dict[str, str]], leitung: bool = True) -> list[Reiter]:
    """Registerkarten des Menübands. ``ansichten``: Seite → {Unteransicht: Titel} (aus den Seiten-Modulen).
    ``leitung``: Gruppe „Leitung“ (Steuerung) zeigen – in den Optionen je PC abschaltbar."""
    v = lambda *x, **y: _v(ansichten, *x, **y)          # noqa: E731
    auswertung = [Gruppe("Berichte", _einzeln("auswertung", ansichten))]
    if leitung:
        auswertung.append(Gruppe("Leitung", [_split("steuerung", ansichten, "Steuerung", "query_stats",
                                                    tipp="Cockpit – Pfeil: Vorhaben, Zeitplan, Finanzen, Grundlagen",
                                                    standard="cockpit")]))
    return [
        Reiter("start", "Start", [
            Gruppe("Heute", [Punkt("Tages­übersicht", "today", S("heute", heute_ansicht="zentrale"),
                                   tipp="Kennzahlen und offene Aufgaben des Tages"),
                             Punkt("Aufgaben", "task_alt", S("heute", heute_ansicht="postfach"),
                                   tipp="Alle Aufgaben mit ihren Fällen bearbeiten (Postfach)")]),
            Gruppe("Termine", [v("termine", "liste", "Termine", "event", tipp="Termine und Wiedervorlagen als Liste"),
                               v("termine", "monat", "Kalender", "calendar_month", tipp="Termine im Monatskalender")]),
            Gruppe("Assistenz", _einzeln("assistenz", ansichten, gross=False)),
        ]),
        Reiter("anreisen", "Anreisen", [
            Gruppe("Anreisen", _einzeln("anreisen", ansichten)),
            Gruppe("Mieter", [Punkt("Mieter", "key", S("mieter"), tipp="Mieter und Mietverträge")]),
        ]),
        Reiter("zimmer", "Zimmer & Haus", [
            Gruppe("Zimmer", [v("zimmer", "uebersicht"), v("zimmer", "zeitstrahl"), v("zimmer", "liste"),
                              v("zimmer", "karten", gross=False)]),
            Gruppe("Betrieb", [v("reinigung", "liste", "Reinigung", "cleaning_services", tipp="Reinigungsliste"),
                               v("zimmer", "maengel", icon="build"),
                               v("reinigung", "last", gross=False), v("reinigung", "facility", gross=False)]),
        ]),
        Reiter("auswertung", "Auswertung", auswertung),
        Reiter("verwalten", "Verwalten", [
            Gruppe("Bestand", [_split("inventar", ansichten, "Inventar", "inventory_2", standard="gegenstaende"),
                               v("einstellungen", "stammdaten", icon="edit_note", tipp="Zimmer anlegen und pflegen")]),
            Gruppe("Verlauf", [v("zimmer", "aenderungen", icon="history", tipp="Alle Änderungen, auch als Excel")]),
        ]),
        Reiter("diagramm", "Diagramm", [
            Gruppe("Diagrammtyp", [Punkt(t, i, A(f"dg_typ:{k}"), tipp=f"Verläufe als {t}") for k, (t, i) in _dg_typen()]),
            Gruppe("Elemente", [Punkt("Elemente", "checklist", None, True, "Diagrammelemente ein- und ausblenden",
                                      [_haken("Linien glätten", "dg_glatt"), _haken("Datenpunkte", "dg_punkte"),
                                       _haken("Datenbeschriftungen", "dg_werte"), _haken("Gitternetzlinien", "dg_gitter"),
                                       _haken("Animation", "dg_anim")]),
                                Punkt("Legende", "legend_toggle", None, True, "Position der Legende",
                                      [Punkt(t, "radio_button_unchecked", A(f"dg_legende:{k}"), False)
                                       for k, t in (("oben", "Oben"), ("unten", "Unten"), ("aus", "Keine"))])],
                   starter=A("optionen:diagramme")),
        ], kontext=KONTEXT_DIAGRAMM),
    ]


LAYOUT_NAMEN = {"office": "Menüband (wie Office)", "original": "Original-Zustand", "grid": "Classic Enterprise Grid",
                "showcase": "Showcase", "canvas": "AI-Canvas & Prompt"}

DATEI = [   # „Datei“ wie die Backstage-Ansicht in Office – Ausgabe, Daten, Programm
    Punkt("Drucken … (Strg+P)", "print", A("drucken"), False),
    Punkt("Importieren", "upload_file", S("daten"), False),
    Punkt("Informationen & Sicherung", "backup", S("einstellungen", "sicherung"), False),
    Punkt("Optionen", "settings", A("optionen"), False),
]
# Titelleiste rechts (wie in Office): Glocke, Hilfe – der Standort steht als Auswahl neben dem Programmnamen
TITELLEISTE = [Punkt("Neuigkeiten", "notifications", A("neuigkeiten"), False),
               Punkt("Hilfe (F1)", "help_outline", A("hilfe"), False),
               Punkt("Standort", "location_city", A("standort"), False)]
# Statusleiste rechts (wie in Word/Excel): Darstellung des Arbeitsbereichs
STATUSLEISTE = [Punkt("Kompakt", "density_small", A("dichte"), False, "Mehr Zeilen auf einen Blick"),
                Punkt("Vollbild", "fullscreen", A("vollbild"), False, "Vollbild ein/aus"),
                Punkt("Helligkeit", "contrast", A("modus"), False, "Helligkeit: Hell → Gedämpft → Dunkel"),
                Punkt("Verkleinern", "remove", A("zoom:-"), False), Punkt("100 %", "", A("zoom:100"), False),
                Punkt("Vergrößern", "add", A("zoom:+"), False)]


def _farben():
    from .darstellung_kern import FARBSCHEMATA

    return list(FARBSCHEMATA.items())


def _dg_typen():
    from .darstellung_kern import DG_TYPEN

    return list(DG_TYPEN.items())


def _zoom():
    from .darstellung_kern import ZOOM_STUFEN

    return ZOOM_STUFEN


def sichtbar(r: Reiter, seite: str) -> bool:
    return not r.kontext or seite in r.kontext


def aktiv(p: Punkt, seite: str, ansicht_von, heute_ansicht: str = "zentrale") -> bool:
    """Ist die Schaltfläche die gerade offene Seite/Ansicht? ``ansicht_von(seite)`` liefert die aktuelle Unteransicht.
    Split-Button: aktiv, wenn seine Standardansicht oder eine Ansicht aus dem Pfeil offen ist."""
    if p.menue and any(aktiv(m, seite, ansicht_von, heute_ansicht) for m in p.menue):
        return True
    if not p.ziel or p.ziel[0] != "seite" or p.ziel[1] != seite:
        return False
    _s, s, ans, zustand = p.ziel
    if s == "heute":
        return zustand.get("heute_ansicht", "zentrale") == heute_ansicht
    return ans is None or ans == ansicht_von(s)


def _ziele(r: Reiter):
    for g in r.gruppen:
        for p in g.punkte:
            for q in [p] + p.menue:
                if q.ziel and q.ziel[0] == "seite":
                    yield q.ziel


def reiter_von(seite: str, ansichten: dict, ansicht: str | None = None) -> str:
    """Registerkarte, die zu Seite (und Ansicht) gehört – beim Sprung über Suche oder Aufgaben folgt das Band."""
    alle = [r for r in reiter(ansichten) if not r.kontext]
    for r in alle:                                  # genaue Ansicht zuerst (z. B. Zimmer → Änderungen = Verwalten)
        if any(z[1] == seite and z[2] == ansicht and ansicht for z in _ziele(r)):
            return r.key
    for r in alle:
        if any(z[1] == seite for z in _ziele(r)):
            return r.key
    return "start"


def alle_ziele(ansichten: dict) -> list[tuple]:
    """Alle Sprungziele aus Band und Datei-Menü (für die Prüfung „jede Ansicht erreichbar“)."""
    out = [z for r in reiter(ansichten) for z in _ziele(r)]
    out += [p.ziel for p in TITELLEISTE + STATUSLEISTE if p.ziel and p.ziel[0] == "seite"]
    return out + [p.ziel for p in DATEI if p.ziel and p.ziel[0] == "seite"]


def statuszeile(standort: str, karten, stand: str) -> str:
    dringend = sum(1 for k in karten if k.stufe == "dringend")
    teile = [standort, f"{len(karten)} offene Aufgabe{'n' if len(karten) != 1 else ''}"
             + (f" · {dringend} dringend" if dringend else "")]
    if stand:
        teile.append(stand)
    return "   |   ".join(teile)
