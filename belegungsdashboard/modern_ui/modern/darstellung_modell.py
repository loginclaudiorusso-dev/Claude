"""1.29: EIN Einstellungsmodell für die Darstellung – Kataloge, Standardwerte und Prüfung an einer Stelle.

Bis 1.28 hatten ``themes.py`` (Layout, Theme, Hell/Dunkel, Dichte, Leiste, Dock) und ``darstellung_kern.py``
(Farbschema, Helligkeit, Titelleiste, Zoom, Schrift, Menüband, Knopf-/Symbolstil, Diagramme) je eigene Standards und
eine eigene Prüfung. Jetzt gilt:

* ``STANDARD`` – alle Felder mit ihrem Standardwert (eine Tabelle).
* ``bereinigen(d)`` – prüft ALLE Felder, übernimmt ältere Namen und hält Theme-Modus und Helligkeit stimmig.
* ``themes.py`` enthält nur noch Paletten und CSS, ``darstellung_kern.py`` nur noch die Farbrechnung; beide holen
  Kataloge, Standard und Prüfung von hier (die bisherigen Namen gelten weiter).

Rein, ohne NiceGUI. Verhalten unverändert gegenüber 1.28 (geprüft mit 4000 zufälligen Einstellungen); einzige
Ausnahme: ein ungültiger Wert ``dg_typ_v`` in einer beschädigten Datei führt nicht mehr zum Absturz.
"""

from __future__ import annotations

import re

# =======================================================================================================
# Aufbau: Layout (Informationsarchitektur) und Theme (Palette, je Theme hell und/oder dunkel)
# =======================================================================================================

LAYOUTS = {
    "original": ("Original-Zustand", "Bisheriges Design und Layout – exakt wie vorher", "restart_alt"),
    "office": ("Menüband (wie Office)", "Registerkarten oben mit großen Symbolen und Ausklappmenüs – vertraut wie Word "
                                        "und Excel", "view_agenda"),
    "grid": ("Classic Enterprise Grid", "Einklappbare Seitenleiste, hohe Datendichte, volle Funktion", "view_sidebar"),
    "canvas": ("AI-Canvas & Prompt", "Zentrale Eingabe (Strg+K, /) filtert live – Antworten als Karten", "auto_awesome"),
    "showcase": ("Showcase", "Schwebendes Dock oben, großzügige Karten, viel Weißraum, Glas", "dashboard"),
}
THEMES = {
    "innternat": ("INNternat", "Türkis-Grau wie das Logo – ruhig, klar, hell und dunkel", "dunkel"),
    "original": ("Original", "Die Farben des bisherigen Designs", "dunkel"),
    "inn": ("inn-tegrativ", "Corporate Deep Blue #183861 – ruhig und seriös", "hell"),
    "linear": ("Linear Monochrome", "Graustufen, messerscharfe Kanten, hohe Dichte", "dunkel"),
    "obsidian": ("Executive Obsidian", "Dunkler Obsidian mit Bronze- und Champagner-Akzenten", "dunkel"),
    "nordic": ("Soft Nordic", "Augenschonend: warme Slate- und Sandtöne", "hell"),
}
ALT = {"corporate": "inn", "bento": "obsidian", "editorial": "nordic"}      # Namen aus 0.8
# Welche Helligkeits-Modi es je Theme gibt (Reihenfolge = erste Wahl zuerst) – muss zu den Paletten in themes.P passen
MODI = {"innternat": ("dunkel", "hell"), "original": ("dunkel",), "inn": ("hell", "dunkel"), "linear": ("dunkel", "hell"),
        "obsidian": ("dunkel", "hell"), "nordic": ("hell", "dunkel")}
DICHTEN = ("normal", "kompakt", "komfort")
# 1.34: nur noch EINE Oberfläche – das Menüband (Office) im Theme INNternat. Die übrigen Layouts und Themes bleiben
# als Namen bekannt (ältere Einstellungen werden übernommen), sind aber nicht mehr wählbar.
LAYOUT = "office"
THEME = "innternat"
_AUFBAU_STANDARD = {"layout": LAYOUT, "theme": THEME, "modus": "hell", "dichte": "normal", "schmal": False,
            "vollbild": False, "notiz": "", "dock": None, "dock_fest": True}

# =======================================================================================================
# Farben, Schrift, Zoom, Menüband, Knöpfe/Symbole, Diagramme (Office-Optionen, 0.66 ff.)
# =======================================================================================================

# Schlüssel → (Name, Akzent, Titelleiste) – Petrol/Türkis aus dem Corporate Design, der Rest wie die Office-Farben
FARBSCHEMATA = {
    "petrol": ("Petrol (Standard)", "#007F7F", "#134F4F"),
    "tuerkis": ("Türkis", "#00807F", "#00696A"),
    "blau": ("Blau", "#1F5FAD", "#174A87"),
    "marine": ("Marineblau", "#2B4C7E", "#1E3657"),
    "gruen": ("Grün", "#2E7D32", "#215A24"),
    "oliv": ("Oliv", "#6A7A1F", "#4E5A17"),
    "violett": ("Violett", "#6B3FA0", "#4F2E77"),
    "beere": ("Beere", "#A1306B", "#7A2451"),
    "rot": ("Rot", "#B3261E", "#8A1D17"),
    "orange": ("Orange", "#B85600", "#8F4300"),
    "braun": ("Braun", "#7A5230", "#5C3D24"),
    "graphit": ("Graphit", "#4A5560", "#353D45"),
}
# Farbfelder zum Anklicken – wie die Akzentfarben in den Windows-Einstellungen (zusätzlich zu „Eigene Farbe …“)
FELDER = ["#FFB900", "#FF8C00", "#F7630C", "#CA5010", "#DA3B01", "#EF6950", "#D13438", "#FF4343",
          "#E74856", "#E81123", "#EA005E", "#C30052", "#E3008C", "#BF0077", "#C239B3", "#9A0089",
          "#0078D4", "#0063B1", "#8E8CD8", "#6B69D6", "#8764B8", "#744DA9", "#B146C2", "#881798",
          "#0099BC", "#2D7D9A", "#00B7C3", "#038387", "#00B294", "#018574", "#00CC6A", "#10893E",
          "#7A7574", "#5D5A58", "#68768A", "#515C6B", "#567C73", "#486860", "#498205", "#107C10",
          "#767676", "#4C4A48", "#69797E", "#4A5459", "#647C64", "#525E54", "#847545", "#7E735F"]
TITELLEISTE = {"farbig": "Farbig", "hell": "Hell (weiß)", "dunkel": "Dunkel"}
SCHRIFTEN = {   # nur Schriften, die unter Windows vorhanden sind (Webfonts sind im Netz gesperrt)
    "standard": ("Standard der Darstellung", ""),
    "segoe": ("Segoe UI", '"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif'),
    "aptos": ("Aptos (Office neu)", '"Aptos", "Segoe UI", system-ui, sans-serif'),
    "calibri": ("Calibri", '"Calibri", "Segoe UI", system-ui, sans-serif'),
    "arial": ("Arial", 'Arial, "Helvetica Neue", Helvetica, sans-serif'),
    "verdana": ("Verdana (sehr gut lesbar)", 'Verdana, Geneva, "Segoe UI", sans-serif'),
    "tahoma": ("Tahoma", 'Tahoma, Verdana, "Segoe UI", sans-serif'),
    "ptsans": ("PT Sans (Corporate Design)", '"PT Sans", "PT_Sans-Web", "Segoe UI", system-ui, sans-serif'),
    "bahnschrift": ("Bahnschrift", '"Bahnschrift", "Segoe UI", system-ui, sans-serif'),
    "georgia": ("Georgia (mit Serifen)", 'Georgia, "Times New Roman", serif'),
}
ZOOM_STUFEN = [50, 75, 90, 100, 110, 125, 150, 175, 200]
ZOOM_MIN, ZOOM_MAX = 50, 200
# 1.12: „Automatisch“ = jedes Diagramm in seiner eigenen Form; Linie/Fläche/Säulen stellen ALLE Diagramme um
DG_TYPEN = {"auto": ("Automatisch", "auto_awesome"), "linie": ("Linie", "show_chart"), "flaeche": ("Fläche", "area_chart"), "saeule": ("Säulen", "bar_chart")}
DG_LEGENDE = {"oben": "oben", "unten": "unten", "aus": "aus"}
# 0.96: Anteils-Diagramme wie in Excel („Kreis oder Ring“, „100 % gestapelt“) – für „wer macht wie viel aus, und wann“
DG_ANTEILE = {"ring": ("Ring", "donut_large"), "kreis": ("Kreis", "pie_chart"),
              "saeule100": ("100 %-Säulen", "stacked_bar_chart"), "flaeche100": ("100 %-Fläche", "area_chart")}

FARB_STANDARD = {"farbe": "petrol", "farbe_eigen": "#007F7F", "titelleiste": "farbig", "zoom": 100, "schrift": "standard",
            "band_gross": False, "dg_typ": "auto", "dg_typ_v": 2, "dg_glatt": False, "dg_punkte": False, "dg_werte": False,
            "dg_gitter": True, "dg_legende": "oben", "dg_anim": True, "leitung": True, "band_zu": False,
            "knopfstil": "klar", "symbolstil": "linie", "kontrast": False,
            "helligkeit": "hell", "faerbung": "akzent", "dg_modus": "karte", "nav": "band",
            "dg_anteil": "ring", "dg_anteil_zeit": "saeule100", "werkzeuge_oben": True, "symbole": "fluent"}
# 1.34: zwei Symbol-Varianten im Menüband – die bisherigen (Fluent, zweifarbig) oder farbige, realistischere
SYMBOLE = {"fluent": ("Klar (zweifarbig)", "Die bisherigen Symbole: feine Kontur mit zarter Bedeutungsfarbe"),
           "farbig": ("Farbig (realistischer)", "Vollfarbige Symbole mit Verlauf und Tiefe, wie in Microsoft 365")}
# 0.92: Navigation im Windows-Look – Menüband wie in Office (Standard, bleibt) oder als Option die Seitenleiste.
# Neuer Schlüssel „nav“: Die Einstellung „navigation“ aus 0.91 (dort war die Seitenleiste Standard) gilt nicht mehr.
NAVIGATION = {"band": ("Menüband (wie Office)", "Registerkarten oben mit großen Symbolen – wie Word und Excel"),
              "leiste": ("Seitenleiste", "Alle Bereiche links immer sichtbar, Zähler direkt am Eintrag")}
# 0.89: Darstellung der Auswertungs-Diagramme – je nach Publikum wählbar (gilt je PC)
DG_MODI = {"karte": ("Karte", "Diagramm-Karte mit Knöpfen, „Auf einen Blick“ und einheitlichem Stil"),
           "klassisch": ("Klassisch", "Wie bis Version 0.86: Diagramm mit Legende unten und Leiste darunter"),
           "einfach": ("Einfach", "Für die Geschäftsführung: die Aussage als Überschrift, Füllstand, höchstens drei Zahlen")}
HELLIGKEIT = {"hell": "Hell", "gedaempft": "Gedämpft", "dunkel": "Dunkel"}          # 0.72
FAERBUNG = {"akzent": "Nur Akzent", "ganz": "Ganzes Design"}
# 0.75: Knopf- und Symbolstil – gelten immer für ALLE Knöpfe bzw. Symbole gleichzeitig (nie gemischt)
KNOPFSTILE = {"klar": "Klar (wie Office)", "weich": "Weich", "kontur": "Kontur", "kraeftig": "Kräftig"}
SYMBOLSTILE = {"linie": "Linie", "gefuellt": "Gefüllt", "rund": "Rund"}
SYMBOL_SCHRIFT = {"linie": "Material Icons Outlined", "gefuellt": "Material Icons", "rund": "Material Icons Round"}
# 0.75: fertige Vorlagen – ein Klick setzt Farbe, Helligkeit, Färbung, Titelleiste und Kontrast. Die Statusfarben
# (frei grün, belegt blau, geplant violett …) bleiben in jeder Vorlage gleich.
VORLAGEN = {
    "petrol": ("Petrol (Standard)", "ruhig, wie gewohnt",
               {"farbe": "petrol", "helligkeit": "hell", "faerbung": "akzent", "titelleiste": "farbig", "kontrast": False}),
    "nordic": ("Nordic Slate", "kühl, klar, maximale Schärfe",
               {"farbe": "eigen", "farbe_eigen": "#2563EB", "helligkeit": "hell", "faerbung": "akzent",
                "titelleiste": "dunkel", "kontrast": False}),
    "sand": ("Sand (warm)", "papierähnlich, augenschonend",
             {"farbe": "eigen", "farbe_eigen": "#B45309", "helligkeit": "hell", "faerbung": "ganz", "titelleiste": "farbig",
              "kontrast": False}),
    "praesentation": ("Dunkel · Präsentation", "für Beamer und Cockpit",
                      {"farbe": "eigen", "farbe_eigen": "#0891B2", "helligkeit": "dunkel", "faerbung": "akzent",
                       "titelleiste": "farbig", "kontrast": False}),
    "kontrast": ("Hoher Kontrast", "schwarz auf weiß, kräftige Ränder",
                 {"farbe": "eigen", "farbe_eigen": "#005A9E", "helligkeit": "hell", "faerbung": "akzent",
                  "titelleiste": "dunkel", "kontrast": True}),
}


def vorlage_von(d: dict) -> str | None:
    """Welche Vorlage passt zu den aktuellen Einstellungen? (für die Markierung in den Optionen)"""
    for k, (_n, _t, werte) in VORLAGEN.items():
        if all(d.get(f) == w for f, w in werte.items() if not (f == "farbe_eigen" and d.get("farbe") != "eigen")):
            return k
    return None

_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")


def hex_ok(s) -> str | None:
    m = _HEX.match(str(s or "").strip())
    return f"#{m.group(1).upper()}" if m else None



# =======================================================================================================
# Das eine Modell
# =======================================================================================================

STANDARD = {**_AUFBAU_STANDARD, **FARB_STANDARD}
FARB_FELDER = tuple(FARB_STANDARD)
AUFBAU_FELDER = tuple(_AUFBAU_STANDARD)


def _zahl(x, ersatz: int) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return ersatz


def modi(theme: str) -> list[str]:
    return list(MODI.get(theme, ()))


def farben_bereinigen(d: dict) -> dict:
    """Nur Farben, Schrift, Zoom, Menüband, Diagramme – Unbekanntes → Standard."""
    e = dict(FARB_STANDARD)
    if d.get("farbe") in FARBSCHEMATA or d.get("farbe") == "eigen":
        e["farbe"] = d["farbe"]
    e["farbe_eigen"] = hex_ok(d.get("farbe_eigen")) or FARB_STANDARD["farbe_eigen"]
    e["titelleiste"] = d.get("titelleiste") if d.get("titelleiste") in TITELLEISTE else "farbig"
    try:
        e["zoom"] = max(ZOOM_MIN, min(ZOOM_MAX, int(d.get("zoom", 100))))
    except (TypeError, ValueError):
        pass
    e["schrift"] = d.get("schrift") if d.get("schrift") in SCHRIFTEN else "standard"
    e["helligkeit"] = d.get("helligkeit") if d.get("helligkeit") in HELLIGKEIT else "hell"
    e["faerbung"] = d.get("faerbung") if d.get("faerbung") in FAERBUNG else "akzent"
    e["dg_typ"] = d.get("dg_typ") if d.get("dg_typ") in DG_TYPEN else "auto"
    if e["dg_typ"] == "linie" and _zahl(d.get("dg_typ_v"), 1) < 2:      # 1.12: bis 1.11 war „Linie“ der Standard = Automatisch
        e["dg_typ"] = "auto"
    e["dg_legende"] = d.get("dg_legende") if d.get("dg_legende") in DG_LEGENDE else "oben"
    e["dg_modus"] = d.get("dg_modus") if d.get("dg_modus") in DG_MODI else "karte"
    e["nav"] = "band"                                           # 1.34: Seitenleiste entfällt
    e["symbole"] = d.get("symbole") if d.get("symbole") in SYMBOLE else "fluent"
    alt = d.get("dg_anteil")                                    # bis 1.22 eine Einstellung für beide Diagramme
    e["dg_anteil"] = alt if alt in ("ring", "kreis") else "ring"
    zeit = d.get("dg_anteil_zeit") or (alt if alt in ("saeule100", "flaeche100") else None)
    e["dg_anteil_zeit"] = zeit if zeit in ("saeule100", "flaeche100") else "saeule100"
    e["knopfstil"] = d.get("knopfstil") if d.get("knopfstil") in KNOPFSTILE else "klar"
    e["symbolstil"] = "linie"                                   # 1.34: nicht mehr wählbar
    for k in ("band_gross", "band_zu", "kontrast", "dg_glatt", "dg_punkte", "dg_werte", "dg_gitter", "dg_anim", "leitung",
              "werkzeuge_oben"):
        if k in d:
            e[k] = bool(d[k])
    return e



def bereinigen(d: dict | None) -> dict:
    """Gespeicherten Zustand prüfen. 1.34: Layout und Theme sind fest (Menüband, INNternat); Hell/Gedämpft/Dunkel
    bleibt wählbar. Wer bisher dunkel arbeitete (Modus dunkel ohne Helligkeit), bleibt dunkel."""
    d = dict(d or {})
    erg = dict(STANDARD)
    erg["dichte"] = d.get("dichte") if d.get("dichte") in ("kompakt", "komfort") else "normal"   # 0.74: + Komfort
    erg["vollbild"] = bool(d.get("vollbild"))
    erg["notiz"] = str(d.get("notiz") or "")[:5000]
    erg.update(farben_bereinigen(d))
    if "helligkeit" not in d:
        erg["helligkeit"] = "dunkel" if d.get("modus") == "dunkel" and d.get("layout") not in (None, "original") else "hell"
    erg["modus"] = "hell" if erg["helligkeit"] == "hell" else "dunkel"
    erg["layout"], erg["theme"], erg["schmal"], erg["dock"], erg["dock_fest"] = LAYOUT, THEME, False, None, True
    return erg


# Was beim allerersten Start gilt: Menüband, INNternat, hell (1.34 – vorher Original-Layout, dunkel).
START = bereinigen({})
