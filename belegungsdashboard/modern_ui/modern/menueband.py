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
    nur: tuple = ()                                          # 0.96: nur auf diesen (Seite, Ansicht) – leer: immer


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


# 1.00: Symbole aus Microsoft Fluent 2 (modern/symbole, MIT) – zweifarbig: Kontur in Schiefergrau, darunter dieselbe
# Form zart in einer Bedeutungsfarbe. Jede Funktion hat ein eigenes Bild (keine Doppelungen innerhalb eines Reiters).
BASIS = ""
BLAU, TEAL, GRUEN, AMBER, VIOLETT, ROT = "#0284c7", "#0f766e", "#10b981", "#f59e0b", "#8b5cf6", "#e11d48"
SYMBOLE: dict[tuple, tuple] = {   # (Seite, Ansicht) → (Fluent-Symbol, Bedeutungsfarbe)
    ("heute", "zentrale"): ("weather_sunny", AMBER),
    ("heute", "postfach"): ("tasks_app", GRUEN),
    ("termine", "liste"): ("calendar_clock", BLAU),
    ("termine", "monat"): ("calendar_month", BLAU),
    ("assistenz", "auftraege"): ("clipboard_task", TEAL),
    ("assistenz", "mails"): ("mail", BLAU),
    ("assistenz", "fragen"): ("sparkle", AMBER),
    ("anreisen", "zuteilen"): ("conference_room", GRUEN),
    ("anreisen", "personen"): ("people", BLAU),
    ("anreisen", "abreisen"): ("door_arrow_right", AMBER),
    ("anreisen", "eintragen"): ("briefcase", BLAU),
    ("mieter", None): ("key", AMBER),
    ("zimmer", "uebersicht"): ("grid", BLAU),
    ("zimmer", "zeitstrahl"): ("gantt_chart", GRUEN),
    ("zimmer", "liste"): ("table", TEAL),
    ("zimmer", "karten"): ("content_view_gallery", BLAU),
    ("zimmer", "maengel"): ("wrench", AMBER),
    ("zimmer", "aenderungen"): ("history", BASIS),
    ("reinigung", "liste"): ("broom", BLAU),
    ("reinigung", "last"): ("calendar_week_numbers", BASIS),
    ("reinigung", "facility"): ("clipboard_checkmark", TEAL),
    ("auswertung", "lage"): ("apps", BLAU),
    ("auswertung", "belegung"): ("building_people", GRUEN),
    ("auswertung", "prognose"): ("arrow_trending_lines", BLAU),
    ("auswertung", "massnahmen"): ("hat_graduation", VIOLETT),
    ("auswertung", "zimmer"): ("bed", ROT),
    ("steuerung", "cockpit"): ("target_arrow", BASIS),
    ("inventar", "gegenstaende"): ("box", BLAU),
    ("einstellungen", "stammdaten"): ("document_edit", BASIS),
}
AKTION_SYMBOLE: dict[str, tuple] = {   # Aktionsname (Präfix) → (Fluent-Symbol, Farbe)
    "aw:aw_chart=trend": ("arrow_trending_lines", BLAU), "aw:aw_chart=reserve": ("battery_charge", GRUEN),
    "aw:aw_chart=jahr": ("arrow_swap", AMBER), "awt:aw_status": ("people_add", TEAL),
    "awt:aw_parallel": ("layout_column_three", TEAL), "aw:aw_brutto=false": ("person", BLAU),
    "aw:aw_brutto=true": ("people", BLAU),
    "dg_modus:karte": ("content_view", BLAU), "dg_modus:klassisch": ("chart_multiple", BLAU),
    "dg_modus:einfach": ("lightbulb", AMBER),
    "dg_typ:linie": ("data_line", BLAU), "dg_typ:flaeche": ("data_area", BLAU), "dg_typ:saeule": ("data_bar_vertical", BLAU),
}
TEXT_SYMBOLE: dict[str, tuple] = {   # Schaltflächen ohne eigenes Ziel (Ausklappmenüs) → nach Text
    "Standort": ("location", ROT), "Zeitraum": ("calendar_date", BLAU), "Anteile": ("data_pie", AMBER),
    "Elemente": ("layer", VIOLETT), "Legende": ("tag", VIOLETT), "Steuerung": ("target_arrow", BASIS),
    "Inventar": ("box", BLAU),
}


def symbol(p: "Punkt") -> tuple[str, str]:
    """(Fluent-Symbol, Bedeutungsfarbe) einer Schaltfläche im Menüband."""
    z = p.ziel
    if z and z[0] == "seite":
        _s, seite, ansicht, zustand = z
        if seite == "heute":
            ansicht = (zustand or {}).get("heute_ansicht", "zentrale")
        if (seite, ansicht) in SYMBOLE:
            return SYMBOLE[(seite, ansicht)]
        if (seite, None) in SYMBOLE:
            return SYMBOLE[(seite, None)]
    if z and z[0] == "aktion" and z[1] in AKTION_SYMBOLE:
        return AKTION_SYMBOLE[z[1]]
    t = p.text.replace("\u00ad", "")
    if t in TEXT_SYMBOLE:
        return TEXT_SYMBOLE[t]
    return ("more_horizontal", BASIS)


ICONS = {   # Symbole der Unteransichten – leicht erkennbar, wie in Office
    "anreisen": {"zuteilen": "meeting_room", "personen": "groups", "abreisen": "luggage", "eintragen": "domain"},
    "zimmer": {"uebersicht": "grid_view", "karten": "map", "zeitstrahl": "align_horizontal_left", "liste": "table_chart",
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
TRENNUNG = {"RIOS-Daten": "RIOS-Daten", "Gegenstände": "Gegen\u00adstände",
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


PROGNOSE = (("auswertung", "prognose"),)
PROGNOSE_DIAGRAMME = {"trend": ("Trend & Prognose", "trending_up"), "reserve": ("Reserve", "align_vertical_bottom"),
                      "jahr": ("Vorjahr", "compare_arrows")}
ZEITRAEUME = {12: "12 Monate", 24: "24 Monate"}


def _daten_punkte(standorte: dict | None) -> list[Punkt]:
    """Gruppe „Daten“ (wie „Daten auswählen“ in Excel): Standort, Personenkreis, Zeitraum."""
    st = standorte or {}
    return [Punkt("Standort", "location_city", None, True, "Welcher Standort im Diagramm",
                  [Punkt(t, "radio_button_unchecked", A(f"aw:aw_standort={k}"), False) for k, t in st.items()]),
            Punkt("Netto", "person", A("aw:aw_brutto=false"), False, "Nur belegte Plätze (ohne Puffer)"),
            Punkt("Brutto", "groups", A("aw:aw_brutto=true"), False, "Mit Puffer/Sperren"),
            Punkt("Zeitraum", "date_range", None, False, "Wie weit die Prognose reicht",
                  [Punkt(t, "radio_button_unchecked", A(f"aw:aw_horizont={k}"), False) for k, t in ZEITRAEUME.items()])]


def aw_wert(text: str):
    """„aw:aw_horizont=24“ → ("aw_horizont", 24). Werte: true/false, ganze Zahlen, sonst Text."""
    key, _, roh = text.partition("=")
    if roh in ("true", "false"):
        return key, roh == "true"
    if roh.lstrip("-").isdigit():
        return key, int(roh)
    return key, roh


def gruppe_sichtbar(g: Gruppe, seite: str, ansicht: str | None) -> bool:
    return not g.nur or (seite, ansicht) in g.nur


def reiter(ansichten: dict[str, dict[str, str]], leitung: bool = True, standorte: dict | None = None) -> list[Reiter]:
    """1.01: alle Schaltflächen groß (Symbol über dem Text) – es ist genug Platz, kleine Knöpfe waren zu klein."""
    alle = _reiter(ansichten, leitung, standorte)
    for r in alle:
        for g in r.gruppen:
            for p in g.punkte:
                p.gross = True
    return alle


def _reiter(ansichten: dict[str, dict[str, str]], leitung: bool = True, standorte: dict | None = None) -> list[Reiter]:
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
            Gruppe("Heute", [Punkt("Tages­übersicht", "wb_twilight", S("heute", heute_ansicht="zentrale"),
                                   tipp="Kennzahlen und offene Aufgaben des Tages"),
                             Punkt("Aufgaben", "task_alt", S("heute", heute_ansicht="postfach"),
                                   tipp="Alle Aufgaben mit ihren Fällen bearbeiten (Postfach)")]),
            Gruppe("Termine", [v("termine", "liste", "Termine", "calendar_today", tipp="Termine und Wiedervorlagen als Liste"),
                               v("termine", "monat", "Kalender", "calendar_month", tipp="Termine im Monatskalender")]),
            Gruppe("Assistenz", _einzeln("assistenz", ansichten, gross=False)),
        ]),
        Reiter("anreisen", "Anreisen", [
            Gruppe("Anreisen", _einzeln("anreisen", ansichten)),
            Gruppe("Mieter", [Punkt("Mieter", "description", S("mieter"), tipp="Mieter und Mietverträge")]),
        ]),
        Reiter("zimmer", "Zimmer & Haus", [
            Gruppe("Zimmer", [v("zimmer", "uebersicht"), v("zimmer", "zeitstrahl"), v("zimmer", "liste"),
                              v("zimmer", "karten")]),                    # 0.99: vier gleich große Ansichten
            Gruppe("Betrieb", [v("reinigung", "liste", "Reinigung", "cleaning_services", tipp="Reinigungsliste"),
                               v("zimmer", "maengel", icon="warning_amber"),
                               v("reinigung", "last", gross=False), v("reinigung", "facility", gross=False)]),
        ]),
        Reiter("auswertung", "Auswertung", auswertung),
        Reiter("verwalten", "Verwalten", [
            Gruppe("Bestand", [_split("inventar", ansichten, "Inventar", "inventory_2", standard="gegenstaende"),
                               v("einstellungen", "stammdaten", icon="edit_note", tipp="Zimmer anlegen und pflegen")]),
            Gruppe("Verlauf", [v("zimmer", "aenderungen", icon="history", tipp="Alle Änderungen, auch als Excel")]),
        ]),
        Reiter("diagramm", "Diagrammentwurf", [                 # 0.96: wie die Kontext-Registerkarte in Excel
            Gruppe("Daten", _daten_punkte(standorte), nur=PROGNOSE),
            Gruppe("Diagramm", [Punkt(t, i, A(f"aw:aw_chart={k}"), tipp=t) for k, (t, i) in PROGNOSE_DIAGRAMME.items()]
                   + [Punkt("inkl. UWTler und Mieter", "group_add", A("awt:aw_status"), False,
                            "Gesamtlinie mit UWTlern und Mietern (Trend & Prognose)"),
                      Punkt("Standorte einzeln", "stacked_line_chart", A("awt:aw_parallel"), False,
                            "Bei „Gesamt“: die drei Standorte nebeneinander")], nur=PROGNOSE),
            Gruppe("Darstellung", [Punkt(t, i, A(f"dg_modus:{k}"), tipp=b_) for k, t, i, b_ in _dg_modi()]),
            Gruppe("Typ", [Punkt(t, i, A(f"dg_typ:{k}"), tipp=f"Verläufe als {t} (Darstellung „Klassisch“)")
                           for k, (t, i) in _dg_typen()]
                   + [Punkt("Anteile", "donut_large", None, True,
                            "Anteils-Diagramme (Belegung, Maßnahmen): Ring, Kreis, 100 %-Säulen oder 100 %-Fläche",
                            [Punkt(t, "radio_button_unchecked", A(f"dg_anteil:{k}"), False) for k, (t, _i) in _dg_anteile()])]),
            Gruppe("Elemente", [Punkt("Elemente", "checklist", None, True, "Diagrammelemente ein- und ausblenden",
                                      [_haken("Linien glätten", "dg_glatt"), _haken("Datenpunkte", "dg_punkte"),
                                       _haken("Datenbeschriftungen", "dg_werte"), _haken("Gitternetzlinien", "dg_gitter"),
                                       _haken("Animation", "dg_anim"),
                                       Punkt("95 %-Band (Prognose, Klassisch)", "haken", A("awt:aw_95"), False),
                                       Punkt("Backtest – frühere Vorhersagen (Prognose)", "haken", A("awt:aw_backtest"),
                                             False)]),
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
    Punkt("Exportieren …", "ios_share", A("exportieren"), False),
    Punkt("Importieren", "upload_file", S("daten"), False),
    Punkt("Informationen & Sicherung", "backup", S("einstellungen", "sicherung"), False),
    Punkt("Seitenleiste statt Menüband", "view_sidebar", A("nav:leiste"), False),          # 0.91 – Option
    Punkt("Optionen", "settings", A("optionen"), False),
]
# Titelleiste rechts (wie in Office): Glocke, Hilfe – der Standort steht als Auswahl neben dem Programmnamen
TITELLEISTE = [Punkt("Neuigkeiten", "notifications", A("neuigkeiten"), False),
               Punkt("Hilfe (F1)", "help_outline", A("hilfe"), False),
               Punkt("Standort", "location_city", A("standort"), False)]
# Statusleiste rechts (wie in Word/Excel): Darstellung des Arbeitsbereichs
# 0.96: Bildschirmfoto ganz links – auf jeder Seite sichtbar (dazu Strg+Umschalt+F)
STATUSLEISTE = [Punkt("Bildschirmfoto", "photo_camera", A("foto"), False,
                      "Bildschirmfoto: Fenster in die Zwischenablage (Strg+V) und nach Bilder\\INNternat (Strg+Umschalt+F)"),
                Punkt("Ausschnitt", "screenshot_region", A("foto:ausschnitt"), False,
                      "Bildschirmfoto eines Ausschnitts – Bereich mit der Maus wählen (Windows-Ausschneidewerkzeug)"),
                Punkt("Kompakt", "density_small", A("dichte"), False, "Mehr Zeilen auf einen Blick"),
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


def _dg_modi():
    from .darstellung_kern import DG_MODI

    icons = {"karte": "dashboard", "klassisch": "show_chart", "einfach": "speed"}
    return [(k, t, icons.get(k, "insert_chart"), b_) for k, (t, b_) in DG_MODI.items()]


def _dg_anteile():
    from .darstellung_kern import DG_ANTEILE

    return list(DG_ANTEILE.items())


def _zoom():
    from .darstellung_kern import ZOOM_STUFEN

    return ZOOM_STUFEN


def sichtbar(r: Reiter, seite: str) -> bool:
    return not r.kontext or seite in r.kontext


def leiste(ansichten: dict, leitung: bool = True) -> list[tuple[str, list[Punkt]]]:
    """0.91: Seitenleiste – (Gruppe, Einträge). Jedes häufige Ziel steht direkt da (kein Suchen hinter Registerkarten);
    seltenere Unteransichten (Karten, Änderungen, Vorschau, Facility-Checks …) bleiben als Umschalter auf der Seite."""
    def v(seite, k, text=None, icon=None):
        t = text or (ansichten.get(seite) or {}).get(k, k)
        return Punkt(t.replace("\u00ad", ""), icon or ICONS.get(seite, {}).get(k, "chevron_right"), S(seite, k), False)

    erg = [("", [Punkt("Heute", "today", S("heute", heute_ansicht="zentrale"), False),
                 Punkt("Termine", "event", S("termine"), False),
                 Punkt("Assistenz", "auto_awesome", S("assistenz"), False)]),
           ("Anreisen", [v("anreisen", "zuteilen"), v("anreisen", "personen"), v("anreisen", "abreisen"),
                         v("anreisen", "eintragen", "RIOS-Daten"), Punkt("Mieter", "key", S("mieter"), False)]),
           ("Zimmer und Haus", [v("zimmer", "uebersicht"), v("zimmer", "zeitstrahl"), v("zimmer", "liste"),
                                Punkt("Reinigung", "cleaning_services", S("reinigung", "liste"), False),
                                v("zimmer", "maengel", "Mängel und Prüfungen")]),
           ("Auswertung", [v("auswertung", "prognose", "Belegung und Prognose"), v("auswertung", "massnahmen"),
                           v("auswertung", "zimmer", "Engpässe")]
            + ([Punkt("Steuerung", "query_stats", S("steuerung"), False)] if leitung else [])),
           ("Verwalten", [Punkt("Inventar", "inventory_2", S("inventar"), False),
                          Punkt("Daten und Import", "upload_file", S("daten"), False),
                          Punkt("Einstellungen", "settings", S("einstellungen"), False)])]
    return erg


def leiste_aktiv(eintraege: list[tuple[str, list[Punkt]]], seite: str, ansicht_von, heute_ansicht: str) -> Punkt | None:
    """Welcher Eintrag ist markiert? Genau einer: zuerst die genaue Ansicht, sonst der erste Eintrag der Seite."""
    alle = [p for _g, ps in eintraege for p in ps]
    genau = next((p for p in alle if aktiv(p, seite, ansicht_von, heute_ansicht) and p.ziel[2] is not None), None)
    if seite == "heute":
        return alle[0]
    return genau or next((p for p in alle if p.ziel and p.ziel[1] == seite), None)


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
