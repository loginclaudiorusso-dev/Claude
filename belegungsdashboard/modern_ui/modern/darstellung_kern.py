"""Darstellungs-Optionen (0.66) wie in Office: Farbschema/Akzentfarbe (Voreinstellungen oder eigene Farbe wie in
Windows), Titelleiste, Zoom, Schriftart, Menüband-Größe und Diagrammstil. Rein, ohne NiceGUI.

Grundsätze:
* Eigene Farben werden automatisch lesbar gemacht (Kontrast mind. 4,5 : 1 zu Weiß bzw. zum dunklen Hintergrund).
* Statusfarben (rot = kritisch, orange = Warnung, grün = frei) bleiben fest – sie tragen Bedeutung.
* Alles ist persönlich je PC (wie die übrige Darstellung).
"""

from __future__ import annotations

import re

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
DG_TYPEN = {"linie": ("Linie", "show_chart"), "flaeche": ("Fläche", "area_chart"), "saeule": ("Säulen", "bar_chart")}
DG_LEGENDE = {"oben": "oben", "unten": "unten", "aus": "aus"}

STANDARD = {"farbe": "petrol", "farbe_eigen": "#007F7F", "titelleiste": "farbig", "zoom": 100, "schrift": "standard",
            "band_gross": False, "dg_typ": "linie", "dg_glatt": False, "dg_punkte": False, "dg_werte": False,
            "dg_gitter": True, "dg_legende": "oben", "dg_anim": True}

_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")


def hex_ok(s) -> str | None:
    m = _HEX.match(str(s or "").strip())
    return f"#{m.group(1).upper()}" if m else None


def bereinigen(d: dict) -> dict:
    """Nur die Optionen dieses Moduls – Unbekanntes → Standard."""
    e = dict(STANDARD)
    if d.get("farbe") in FARBSCHEMATA or d.get("farbe") == "eigen":
        e["farbe"] = d["farbe"]
    e["farbe_eigen"] = hex_ok(d.get("farbe_eigen")) or STANDARD["farbe_eigen"]
    e["titelleiste"] = d.get("titelleiste") if d.get("titelleiste") in TITELLEISTE else "farbig"
    try:
        e["zoom"] = max(ZOOM_MIN, min(ZOOM_MAX, int(d.get("zoom", 100))))
    except (TypeError, ValueError):
        pass
    e["schrift"] = d.get("schrift") if d.get("schrift") in SCHRIFTEN else "standard"
    e["dg_typ"] = d.get("dg_typ") if d.get("dg_typ") in DG_TYPEN else "linie"
    e["dg_legende"] = d.get("dg_legende") if d.get("dg_legende") in DG_LEGENDE else "oben"
    for k in ("band_gross", "dg_glatt", "dg_punkte", "dg_werte", "dg_gitter", "dg_anim"):
        if k in d:
            e[k] = bool(d[k])
    return e


def zoom_schritt(zoom: int, richtung: int) -> int:
    """Nächste Zoomstufe wie in Office (− / +)."""
    if richtung > 0:
        return next((z for z in ZOOM_STUFEN if z > zoom), ZOOM_MAX)
    return next((z for z in reversed(ZOOM_STUFEN) if z < zoom), ZOOM_MIN)


# ---- Farbrechnung ------------------------------------------------------------------------------------

def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(r: float, g: float, b: float) -> str:
    return "#" + "".join(f"{max(0, min(255, round(x))):02X}" for x in (r, g, b))


def mischen(a: str, b: str, anteil_b: float) -> str:
    ra, ga, ba = _rgb(a)
    rb, gb, bb = _rgb(b)
    t = anteil_b
    return _hex(ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t)


def leuchtdichte(h: str) -> float:
    def kanal(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(h)
    return 0.2126 * kanal(r) + 0.7152 * kanal(g) + 0.0722 * kanal(b)


def kontrast(a: str, b: str) -> float:
    la, lb = sorted((leuchtdichte(a), leuchtdichte(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def lesbar(farbe: str, hinter: str, ziel: float = 4.5) -> str:
    """Farbe so weit abdunkeln (heller Hintergrund) bzw. aufhellen (dunkler), bis der Kontrast reicht."""
    zu = "#000000" if leuchtdichte(hinter) > 0.4 else "#FFFFFF"
    f = farbe
    for i in range(1, 21):
        if kontrast(f, hinter) >= ziel:
            return f
        f = mischen(farbe, zu, i * 0.05)
    return f


def akzent(d: dict) -> tuple[str, str]:
    """(Akzent, Titelleiste) aus Voreinstellung oder eigener Farbe."""
    if d.get("farbe") == "eigen":
        c = hex_ok(d.get("farbe_eigen")) or STANDARD["farbe_eigen"]
        return c, mischen(c, "#000000", 0.35)
    _n, c, t = FARBSCHEMATA.get(d.get("farbe"), FARBSCHEMATA["petrol"])
    return c, t


def standard_farbe(d: dict) -> bool:
    return d.get("farbe", "petrol") == "petrol"


def css_variablen(d: dict, dunkel: bool) -> dict[str, str]:
    """CSS-Variablen für <body> (inline – gehen den Theme-Klassen vor). Leer, wenn alles Standard ist."""
    v: dict[str, str] = {}
    if not standard_farbe(d) or d.get("titelleiste", "farbig") != "farbig":
        c, titel = akzent(d)
        if dunkel:
            fl = "#141B1B"
            hell_ = lesbar(mischen(c, "#FFFFFF", 0.35), fl)
            v.update({"--akzent": hell_, "--akzent-hell": hell_, "--akzent-hover": mischen(hell_, "#FFFFFF", .15),
                      "--fokus": hell_, "--akzent-text": "#0B1414", "--ob-akzent": hell_,
                      "--ob-an": mischen(c, fl, .65), "--ob-hover": mischen(c, fl, .8)})
            titel_bg = mischen(titel, "#000000", .3)
        else:
            a = lesbar(c, "#FFFFFF")
            v.update({"--akzent": a, "--akzent-hell": a, "--akzent-hover": mischen(a, "#000000", .15), "--fokus": a,
                      "--akzent-text": "#FFFFFF" if kontrast("#FFFFFF", a) >= 4.5 else "#111111", "--ob-akzent": a,
                      "--ob-an": mischen(c, "#FFFFFF", .8), "--ob-hover": mischen(c, "#FFFFFF", .88)})
            titel_bg = titel
        tl = d.get("titelleiste", "farbig")
        if tl == "hell":
            v.update({"--ob-titel": "#FFFFFF" if not dunkel else "#1E2626",
                      "--ob-titel-text": "#1F2A2A" if not dunkel else "#E6EEEE"})
        elif tl == "dunkel":
            v.update({"--ob-titel": "#1F2626", "--ob-titel-text": "#FFFFFF"})
        else:
            v.update({"--ob-titel": titel_bg, "--ob-titel-text": "#FFFFFF" if kontrast("#FFFFFF", titel_bg) >= 4.5
                      else "#111111"})
    schrift = SCHRIFTEN.get(d.get("schrift", "standard"), SCHRIFTEN["standard"])[1]
    if schrift:
        v.update({"--schrift": schrift, "--titel-schrift": schrift, "--ob-schrift": schrift})
    z = d.get("zoom", 100)
    if z != 100:
        v["--m-zoom"] = f"{z / 100:.2f}"
    return v


def style_text(v: dict[str, str]) -> str:
    return " ".join(f"{k}: {w};" for k, w in v.items())


def diagramm_akzent(d: dict, dunkel: bool, standard: str) -> str:
    """Akzentfarbe der Diagramme (Prognose-Linie usw.) – folgt der gewählten Farbe."""
    if standard_farbe(d):
        return standard
    c, _t = akzent(d)
    return lesbar(mischen(c, "#FFFFFF", .35), "#141B1B") if dunkel else lesbar(c, "#FFFFFF", 3.0)
