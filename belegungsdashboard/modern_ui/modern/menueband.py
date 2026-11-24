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
    nur: tuple = ()                                          # 1.23: nur auf diesen (Seite, Ansicht) – leer: immer


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
    ohne: tuple = ()                                         # 1.23: (Seite, Ansicht), auf denen er trotzdem fehlt
    symbol: str = ""                                         # 1.39: Piktogramm der Registerkarte („p:…“)


NACHRICHTEN = "nachrichten"                                  # 1.39: Cockpit mit der ersten Nachricht offen


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
    ("termine", "liste"): ("calendar_ltr", BLAU),          # 1.13: nicht wie „geplant“
    ("termine", "monat"): ("calendar_month", BLAU),
    ("assistenz", "auftraege"): ("clipboard_task", TEAL),
    ("assistenz", "mails"): ("mail", BLAU),
    ("assistenz", "fragen"): ("sparkle", AMBER),
    ("anreisen", "zuteilen"): ("conference_room", GRUEN),
    ("anreisen", "personen"): ("people_list", BLAU),
    ("anreisen", "abreisen"): ("door_arrow_right", AMBER),
    ("anreisen", "eintragen"): ("briefcase", BLAU),
    ("mieter", None): ("key", AMBER),
    ("mieter", "mieter"): ("key", AMBER),
    ("mieter", "gaeste"): ("bed", TEAL),
    ("zimmer", "uebersicht"): ("grid", BLAU),
    ("zimmer", "zeitstrahl"): ("gantt_chart", GRUEN),
    ("zimmer", "liste"): ("table", TEAL),
    ("zimmer", "karten"): ("content_view_gallery", BLAU),
    ("zimmer", "maengel"): ("wrench", AMBER),
    ("zimmer", "qr"): ("qr_code", BLAU),
    ("zimmer", "aenderungen"): ("history", BASIS),
    ("reinigung", "liste"): ("broom", BLAU),
    ("reinigung", "last"): ("calendar_arrow_right", BASIS),   # 1.13: Vorschau statt Woche
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
    "nachricht_neu": ("people_team", VIOLETT), "fm_mail": ("send", BLAU), "mn_suche": ("search", VIOLETT),       # 1.58      # 1.36
    "aw:aw_chart=trend": ("arrow_trending_lines", BLAU), "aw:aw_chart=reserve": ("battery_charge", GRUEN),
    "aw:aw_chart=jahr": ("arrow_swap", AMBER), "awt:aw_status": ("people_add", TEAL),
    "awt:aw_parallel": ("layout_column_three", TEAL), "aw:aw_brutto=false": ("person", BLAU),
    "aw:aw_brutto=true": ("people", BLAU),
    "dg_modus:karte": ("content_view", BLAU), "dg_modus:klassisch": ("chart_multiple", BLAU),
    "dg_modus:einfach": ("lightbulb", AMBER),
    "dg_typ:auto": ("sparkle", BLAU), "dg_typ:linie": ("data_line", BLAU), "dg_typ:flaeche": ("data_area", BLAU), "dg_typ:saeule": ("data_bar_vertical", BLAU),
}
TEXT_SYMBOLE: dict[str, tuple] = {   # Schaltflächen ohne eigenes Ziel (Ausklappmenüs) → nach Text
    "Standort": ("location", ROT), "Zeitraum": ("calendar_date", BLAU), "Anteile": ("data_pie", AMBER),
    "Diagrammtyp": ("data_line", BLAU),
    "Elemente": ("layer", VIOLETT), "Legende": ("tag", VIOLETT), "Steuerung": ("target_arrow", BASIS),
    "Inventar": ("box", BLAU),
    "Betten": ("bed", BLAU), "Vergleich": ("layout_column_three", TEAL), "Sicherheit": ("p:a_sicherheit", BASIS),
}


def symbol(p: "Punkt") -> tuple[str, str]:
    """(Symbol, Bedeutungsfarbe) einer Schaltfläche im Menüband. 1.39: „p:…“ = eigenes Piktogramm (eine Farbe)."""
    if p.icon.startswith("p:"):
        return (p.icon, BASIS)
    z = p.ziel
    if z and z[0] == "seite":
        _s, seite, ansicht, zustand = z
        if seite == "heute":
            ansicht = (zustand or {}).get("heute_ansicht", "postfach")
        if (seite, ansicht) in SYMBOLE:
            return SYMBOLE[(seite, ansicht)]
        if (seite, None) in SYMBOLE:
            return SYMBOLE[(seite, None)]
    if z and z[0] == "seite":                       # 1.39: Kontextkarten nennen ihr Fluent-Symbol selbst
        from . import symbole

        if symbole.vorhanden(p.icon):
            return (p.icon, BLAU)
    if z and z[0] == "aktion" and z[1] in AKTION_SYMBOLE:
        return AKTION_SYMBOLE[z[1]]
    t = p.text.replace("\u00ad", "")
    if t in TEXT_SYMBOLE:
        return TEXT_SYMBOLE[t]
    return ("more_horizontal", BASIS)


ICONS = {   # Symbole der Unteransichten – leicht erkennbar, wie in Office
    "anreisen": {"zuteilen": "meeting_room", "personen": "groups", "abreisen": "luggage", "eintragen": "domain"},
    "zimmer": {"uebersicht": "grid_view", "karten": "map", "zeitstrahl": "align_horizontal_left", "liste": "table_chart",
               "maengel": "build", "qr": "qr_code_2", "aenderungen": "history"},
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


def _haken(text: str, key: str, nur: tuple = ()) -> Punkt:
    """Menüpunkt mit Häkchen (an/aus) – Zustand zeigt die Oberfläche."""
    return Punkt(text, "haken", A(f"dg:{key}"), False, nur=nur)


# 0.69 – Regeln der Anordnung (nach zwei Reviews):
#  1. Jeder Arbeitsbereich ist eine Registerkarte; seine Ansichten stehen SICHTBAR im Band (kein Zielen auf ▾).
#  2. Jeder Befehl steht an genau einer Stelle. Standort, Glocke, Hilfe: Titelleiste. Zoom, Kompakt, Vollbild,
#     Hell/Dunkel: Statusleiste (wie Word/Excel). Farben, Layout, Programm-Einstellungen: Datei → Optionen.
#  3. Höchstens 8 Schaltflächen je Registerkarte; Split-Buttons nur für Seltenes (Steuerung, Inventar).
#  4. Kontext-Registerkarte nur für „Diagramm“; Filter bleiben in EINER Kopfzeile direkt über dem Inhalt.
#  5. Gruppenpfeil ↘ öffnet den Dialog zur Gruppe (statt eigener Schaltfläche).
KONTEXT_DIAGRAMM = ("auswertung", "steuerung")
# 1.39: Name der Werkzeug-Registerkarte einer Seite (sonst der Name der Ansicht)
KONTEXT_TITEL = {"termine": "Kalender", "zimmer": "Zimmer", "inventar": "Inventar", "steuerung": "Renovierung"}
# 1.23: Seiten ohne einstellbare Diagramme bekommen keinen „Diagrammentwurf“ – eine Option, die nichts bewirkt, fehlt
OHNE_DIAGRAMM = (("auswertung", "zimmer"), ("steuerung", "vorhaben"), ("steuerung", "grundlagen"))
MIT_DIAGRAMMTYP = (("auswertung", "lage"), ("auswertung", "belegung"), ("auswertung", "prognose"), ("auswertung", "massnahmen"),
                   ("steuerung", "zeitplan"), ("steuerung", "finanzen"))       # Cockpit hat eine eigene Gruppe „Diagramm“
# Maßnahmen: die Säulen tragen ihre Werte immer – dort bewirkt „Datenbeschriftungen“ nichts
# Überblick: Tageswerte (zu viele Punkte für lesbare Beschriftungen)
MIT_WERTEN = tuple(x for x in MIT_DIAGRAMMTYP if x not in (("auswertung", "massnahmen"), ("auswertung", "lage"))) \
    + (("steuerung", "cockpit"),)
# Seiten mit reinen Säulen: Punkte/Glätten wirken dort erst, wenn der Diagrammtyp Linie oder Fläche ist (Cockpit: nie)
NUR_LINIEN = {"dg_punkte": (("auswertung", "belegung"), ("auswertung", "massnahmen"), ("steuerung", "finanzen"),
                            ("steuerung", "cockpit")),
              "dg_glatt": (("auswertung", "belegung"),)}


def linien_option_sichtbar(key: str, seite: str, ansicht: str | None, dg_typ: str) -> bool:
    ort = (seite, ansicht)
    if ort not in NUR_LINIEN.get(key, ()):
        return True
    return ort != ("steuerung", "cockpit") and dg_typ in ("linie", "flaeche")


MIT_ANTEILEN = (("auswertung", "belegung"), ("auswertung", "massnahmen"))
MIT_DARSTELLUNG = (("auswertung", "belegung"), ("auswertung", "prognose"), ("auswertung", "massnahmen"))


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
            Punkt("Betten", "bed", None, False, "Welche Betten zählen (1.39: statt Netto/Brutto)",   # 1.39
                  [Punkt("Belegbare Betten", "radio_button_unchecked", A("aw:aw_brutto=false"), False,
                         "Nur Betten, die belegt werden können (ohne Puffer)"),
                   Punkt("Alle Betten", "radio_button_unchecked", A("aw:aw_brutto=true"), False,
                         "Alle Betten, auch Puffer und gesperrte")]),
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
    """1.39 – Navigation 2.0 (Konzept C „Hybrid“): sieben Arbeitsbereiche als Registerkarten, Datei wie in Office,
    Kontext-Registerkarten nur solange sie gebraucht werden. Jede Funktion hat genau einen Ort und einen Namen.
    ``ansichten``: Seite → {Unteransicht: Titel} (aus den Seiten-Modulen). ``leitung``: „Renovierung & Budget“ zeigen."""
    def p(text: str, sym: str, ziel: tuple, tipp: str) -> Punkt:
        return Punkt(trenn(text), f"p:{sym}", ziel, True, tipp)

    planung_haus = [p("Reinigungs­vorschau", "reinigungsvorschau", S("reinigung", "last"),
                      "Wie viel in den nächsten 6 Wochen zu reinigen ist")]
    if leitung:
        planung_haus.append(p("Renovierung & Budget", "renovierung", S("steuerung", "cockpit"),
                              "Renovierungsvorhaben, Zeitplan, Kapazität und Finanzen (Leitung)"))
    return [
        Reiter("uebersicht", "Übersicht", [
            Gruppe("Cockpit", [p("Cockpit", "uebersicht", S("heute", heute_ansicht="postfach"),
                                 "Startseite: Zahlen von heute, Aufgaben, Nachrichten – rechts lesen und erledigen")]),
            Gruppe("Kommunikation", [
                p("Nachrichten", "nachrichten", S("heute", heute_ansicht="postfach", pf_auswahl=NACHRICHTEN),
                  "Nachrichten am Standort lesen und beantworten"),
                p("Neue Nachricht", "nachricht_neu", A("nachricht_neu"), "Nachricht an alle am Standort schreiben"),
                p("Mail an FM", "fm_mail", A("fm_mail"), "Mail an das Facility-Management – über Ihr Outlook")]),
        ], symbol="p:uebersicht"),
        Reiter("anreisen", "Anreisen", [
            Gruppe("Anreisen", [p("Zuteilen", "zuteilen", S("anreisen", "zuteilen"), "Anreisenden Zimmer zuteilen"),
                                p("Teilnehmer­liste", "teilnehmer", S("anreisen", "personen"),
                                  "Alle Personen mit Zimmer, Hinweisen und Suche"),
                                p("Abreisen", "abreisen", S("anreisen", "abreisen"), "Abreisen und frei werdende Zimmer")]),
            Gruppe("Abgleich", [p("Daten­abgleich", "datenabgleich", S("anreisen", "eintragen"),
                                  "Was in RIOS einzutragen oder zu prüfen ist")]),
            Gruppe("Gäste & Mieter", [p("Gäste", "a_bett", S("mieter", "gaeste"),
                                        "Gäste anlegen – auch im Doppelzimmer, allein oder mit Begleitperson"),
                                      p("Mieter", "mieter", S("mieter", "mieter"), "Mieter und Mietverträge")]),
        ], symbol="p:anreisen"),
        Reiter("zimmer", "Zimmer & Haus", [
            Gruppe("Zimmer", [p("Zimmer­übersicht", "zimmeruebersicht", S("zimmer", "uebersicht"),
                                "Alle Zimmer je Etage – Darstellung Raster oder Karten in der Registerkarte „Zimmer“"),
                              p("Zimmer­liste", "zimmerliste", S("zimmer", "liste"), "Alle Zimmer als Tabelle")]),
            Gruppe("Pflege", [p("Reinigung", "reinigung", S("reinigung", "liste"), "Reinigungsliste"),
                              p("Facility-Checks", "facility", S("reinigung", "facility"), "Prüfgänge im Haus")]),
            Gruppe("Schäden", [p("Defekte Zimmer", "defekt", S("zimmer", "maengel"), "Gemeldete Mängel, Sperren, FM-Aufträge"),
                               p("QR-Meldungen", "qr", S("zimmer", "qr"), "Per QR-Code am Zimmer gemeldete Mängel")]),
            Gruppe("Ausstattung", [p("Inventar", "inventar", S("inventar", "gegenstaende"),
                                     "Gegenstände – je Zimmer und je Haus in der Registerkarte „Inventar“")]),
        ], symbol="p:zimmer"),
        Reiter("planung", "Planung", [
            Gruppe("Belegung", [p("Belegungs­plan", "belegungsplan", S("zimmer", "zeitstrahl"),
                                  "Zeitstrahl: wer wann in welchem Zimmer wohnt")]),
            Gruppe("Termine", [p("Kalender", "kalender", S("termine", "liste"),
                                 "Termine und Wiedervorlagen – Liste oder Monat in der Registerkarte „Kalender“")]),
            Gruppe("Haus", planung_haus),
        ], symbol="p:planung"),
        Reiter("auswertung", "Auswertung", [
            Gruppe("Berichte", [p("Belegung", "belegung", S("auswertung", "belegung"),   # 1.41: mit den Kennzahlen
                                  "Belegung im Zeitraum: Kennzahlen, Verlauf, Häuser, Personentage"),
                                p("Belegungs­prognose", "prognose", S("auswertung", "prognose"),
                                  "Vorhersage der Belegung mit Sicherheitsband"),
                                p("Maßnahmen", "massnahmen", S("auswertung", "massnahmen"), "Teilnehmende je Maßnahme"),
                                # 1.58: der schnellste Weg zu einer Maßnahme – Neuanmeldungen je Monat, 2 Jahre
                                p("Maßnahme ansehen", "suche", A("mn_suche"),
                                  "Eine Maßnahme suchen (z. B. KBM) – Neuanmeldungen je Monat, angemeldet + erwartet"),
                                p("Zimmer-Engpässe", "engpaesse", S("auswertung", "zimmer"), "Wo Betten knapp werden")]),
        ], symbol="p:auswertung"),
        Reiter("ki", "KI-Assistent", [
            Gruppe("Assistent", [p("Aufträge", "auftraege", S("assistenz", "auftraege"),
                                   "Dem Assistenten Aufgaben geben, z. B. „alle EMR vom 26.11. einplanen“"),
                                 p("Schnell­auskunft", "schnellauskunft", S("assistenz", "fragen"),
                                   "Frage zu Belegung und Zahlen stellen – Antwort sofort"),
                                 p("Outlook-Mails auswerten", "mails_ki", S("assistenz", "mails"),
                                   "Mails aus Outlook lesen und Anreisen, Abreisen oder Änderungen daraus übernehmen")]),
        ], symbol="p:ki"),
        Reiter("verwaltung", "Verwaltung", [
            Gruppe("Daten", [p("Daten einlesen", "daten_einlesen", S("daten"),
                               "Anreiselisten, Gebäudeplan und weitere Dateien einlesen"),
                             p("Zimmer-Stammdaten", "stammdaten", S("einstellungen", "stammdaten"),
                               "Zimmer anlegen und pflegen")]),
            Gruppe("Zugang", [p("Benutzer & Rechte", "benutzer", S("einstellungen", "benutzer"),
                                "Konten, Rollen und Standorte (nur Admin)")]),
            Gruppe("Programm", [p("Einstellungen", "einstellungen", S("einstellungen", "allgemein"),
                                  "Einstellungen für alle: Mail-Adressen, Standorte, Regeln"),
                                p("Automati­sierung", "automatisierung", A("automatisierung"),
                                  "QR-Eingang und Power Automate einrichten"),
                                p("Änderungs­verlauf", "verlauf", S("zimmer", "aenderungen"),
                                  "Wer hat wann was geändert – auch als Excel"),
                                p("Versand­protokoll", "a_mail", A("versandprotokoll"),         # 1.59
                                  "Welche Mails INNternat wann an wen verschickt oder vorbereitet hat")]),
        ], symbol="p:verwaltung"),
        # ---- Kontext-Registerkarten: erscheinen nur, solange sie gebraucht werden. Die Ansichtswahl einer Seite
        # (Raster | Karten, Liste | Monat, Inventar, Renovierung) steht in ihrer Werkzeug-Registerkarte (KONTEXT_TITEL).
        Reiter("prognose", "Prognose", [
            Gruppe("Daten", _daten_punkte(standorte)),
            Gruppe("Ansicht", [Punkt(t, i, A(f"aw:aw_chart={k}"), tipp=t) for k, (t, i) in PROGNOSE_DIAGRAMME.items()]
                   + [Punkt("Vergleich", "layout_column_three", None, True, "Weitere Linien bei „Trend & Prognose“",
                            [Punkt("Mit UWT und Mietern", "haken", A("awt:aw_status"), False),
                             Punkt("Standorte einzeln", "haken", A("awt:aw_parallel"), False)])]),
            Gruppe("Sicherheit", [Punkt("Sicherheit", "verified", None, True, "Wie sicher die Vorhersage ist",
                                        [Punkt("95-%-Band", "haken", A("awt:aw_95"), False),
                                         Punkt("Prognose-Genauigkeit (frühere Vorhersagen)", "haken",
                                               A("awt:aw_backtest"), False)])]),
        ], kontext=("auswertung",), ohne=tuple(("auswertung", k) for k in ("lage", "belegung", "massnahmen", "zimmer"))),
        Reiter("diagramm", "Diagramm", [                 # 0.96: wie die Kontext-Registerkarte in Excel; 1.39 verschlankt
            Gruppe("Form", [Punkt("Diagrammtyp", "show_chart", None, True,           # 1.12: wie „Diagrammtyp ändern“ in Excel
                                  "Gilt für alle Diagramme: Automatisch = jedes in seiner eigenen Form; Linie, Fläche oder "
                                  "Säulen stellen alle Verläufe um",
                                  [Punkt(t, "radio_button_unchecked", A(f"dg_typ:{k}"), False) for k, (t, _i) in _dg_typen()],
                                  nur=MIT_DIAGRAMMTYP),
                            Punkt("Anteile", "donut_large", None, True,
                                  "Anteils-Diagramme: links Ring oder Kreis (wie viel insgesamt), rechts 100 %-Säulen oder "
                                  "100 %-Fläche (wann) – beides lässt sich getrennt wählen",
                                  [Punkt(t, "radio_button_unchecked", A(f"dg_anteil:{k}"), False) for k, (t, _i) in _dg_anteile()],
                                  nur=MIT_ANTEILEN),
                            Punkt("Legende", "legend_toggle", None, True, "Position der Legende",
                                  [Punkt(t, "radio_button_unchecked", A(f"dg_legende:{k}"), False)
                                   for k, t in (("oben", "Oben"), ("unten", "Unten"), ("aus", "Keine"))])]),
            Gruppe("Details", [Punkt("Elemente", "checklist", None, True, "Diagrammelemente ein- und ausblenden",
                                     [_haken("Linien glätten", "dg_glatt"), _haken("Datenpunkte", "dg_punkte"),
                                      _haken("Datenbeschriftungen", "dg_werte", MIT_WERTEN), _haken("Gitternetzlinien", "dg_gitter"),
                                      _haken("Animation", "dg_anim")])],
                   starter=A("optionen:diagramme")),
        ], kontext=KONTEXT_DIAGRAMM, ohne=OHNE_DIAGRAMM),
    ]


DATEI = [   # „Datei“ wie die Backstage-Ansicht in Office – 1.39: nur Ausgabe und Persönliches
    Punkt("Drucken … (Strg+P)", "p:drucken", A("drucken"), False),
    Punkt("Exportieren …", "p:exportieren", A("exportieren"), False),
    Punkt("Informationen & Sicherung", "p:info", S("einstellungen", "sicherung"), False,
          "Version, Neuigkeiten, Sicherungen"),
    Punkt("Konto", "p:konto", A("konto"), False, "Angemeldet als …, Passwort ändern, Abmelden, Darstellung"),  # 1.33
]
# Titelleiste rechts (wie in Office): Glocke, Hilfe – der Standort steht als Auswahl neben dem Programmnamen
TITELLEISTE = [Punkt("Chat", "forum", A("chat"), False, "Chat mit allen, die gerade im Programm sind"),   # 1.43
               Punkt("Benachrichtigungen", "notifications", A("neuigkeiten"), False),
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


def sichtbar(r: Reiter, seite: str, ansicht: str | None = None) -> bool:
    return (not r.kontext or seite in r.kontext) and (seite, ansicht) not in r.ohne


def punkt_sichtbar(p: Punkt, seite: str, ansicht: str | None) -> bool:
    return not p.nur or (seite, ansicht) in p.nur


def aktiv(p: Punkt, seite: str, ansicht_von, heute_ansicht: str = "postfach") -> bool:
    """Ist die Schaltfläche die gerade offene Seite/Ansicht? ``ansicht_von(seite)`` liefert die aktuelle Unteransicht.
    Split-Button: aktiv, wenn seine Standardansicht oder eine Ansicht aus dem Pfeil offen ist."""
    if p.menue and any(aktiv(m, seite, ansicht_von, heute_ansicht) for m in p.menue):
        return True
    if not p.ziel or p.ziel[0] != "seite" or p.ziel[1] != seite:
        return False
    _s, s, ans, zustand = p.ziel
    if s == "heute":                                # 1.39: „Nachrichten“ ist ein Sprung ins Cockpit, kein eigener Ort
        return "pf_auswahl" not in zustand and zustand.get("heute_ansicht", "postfach") == heute_ansicht
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
    return "uebersicht"


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
