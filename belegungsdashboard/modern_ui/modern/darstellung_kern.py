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
            "dg_gitter": True, "dg_legende": "oben", "dg_anim": True, "leitung": True, "band_zu": False,
            "knopfstil": "klar", "symbolstil": "linie", "kontrast": False,
            "helligkeit": "hell", "faerbung": "akzent"}
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
    e["helligkeit"] = d.get("helligkeit") if d.get("helligkeit") in HELLIGKEIT else "hell"
    e["faerbung"] = d.get("faerbung") if d.get("faerbung") in FAERBUNG else "akzent"
    e["dg_typ"] = d.get("dg_typ") if d.get("dg_typ") in DG_TYPEN else "linie"
    e["dg_legende"] = d.get("dg_legende") if d.get("dg_legende") in DG_LEGENDE else "oben"
    e["knopfstil"] = d.get("knopfstil") if d.get("knopfstil") in KNOPFSTILE else "klar"
    e["symbolstil"] = d.get("symbolstil") if d.get("symbolstil") in SYMBOLSTILE else "linie"
    for k in ("band_gross", "band_zu", "kontrast", "dg_glatt", "dg_punkte", "dg_werte", "dg_gitter", "dg_anim", "leitung"):
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


def naechste_helligkeit(h: str) -> str:
    """Schalter in der Statusleiste: Hell → Gedämpft → Dunkel → Hell."""
    reihe = list(HELLIGKEIT)
    return reihe[(reihe.index(h) + 1) % len(reihe)] if h in reihe else "hell"


# ---- 0.72: Ton-Paletten – aus EINER Farbe das ganze Design (Flächen, Ränder, Text), je Helligkeit ----------------
# Ebenen-Grundtöne je Stufe; jede Ebene bekommt einen Anteil der Farbe (× Stärke: 1 = ganzes Design, 0,25 = dezent)
_EBENEN = {
    "hell": dict(basis="#FFFFFF", bg=.145, fl=.045, fls=.075, fl2=.19, band=.10, reiter=.18, rand=.30, rand2=.42,
                 hover=.22, an=.30),
    "gedaempft": dict(bg=("#33373B", .20), fl=("#40454A", .18), fls=("#3A3F44", .18), fl2=("#4B5156", .18),
                      band=("#2E3236", .20), reiter=("#272B2F", .20), rand=("#5A6167", .20), rand2=("#6C747A", .20),
                      hover=("#4A5055", .30), an=("#4A5055", .45)),
    "dunkel": dict(bg=("#121416", .12), fl=("#1A1D20", .12), fls=("#16191C", .12), fl2=("#22262A", .12),
                   band=("#0F1113", .12), reiter=("#0B0D0E", .12), rand=("#2C3136", .16), rand2=("#3A4046", .16),
                   hover=("#262A2E", .28), an=("#262A2E", .42)),
}
_STATUS_HELL = dict(ok="#2F7A3E", krit="#B42318", warn="#9A5B00", blau="#1D5BB8")
_STATUS_DUNKEL = dict(ok="#8BD69B", krit="#FF9A8B", warn="#F2C46B", blau="#9CC2F5")


def ton_palette(c: str, stufe: str, staerke: float = 1.0) -> dict:
    """Alle Töne einer Stufe aus der Farbe ``c``. Text wird so lange nachgedunkelt/aufgehellt, bis er lesbar ist
    (Haupttext hell ≥ 12 : 1, gedämpft/dunkel ≥ 7 : 1 = WCAG AAA; Nebentext ≥ 6,5 : 1; leiser Text ≥ 4,5 : 1;
    Akzent auf Karten ≥ 4,6 : 1)."""
    stufe = stufe if stufe in _EBENEN else "hell"
    e = _EBENEN[stufe]
    p: dict = {}
    for k in ("bg", "fl", "fls", "fl2", "band", "reiter", "rand", "rand2", "hover", "an"):
        if stufe == "hell":
            p[k] = mischen(e["basis"], c, e[k] * staerke)
        else:
            basis, anteil = e[k]
            p[k] = mischen(basis, c, anteil * staerke)
    if stufe == "hell":
        p["text"] = lesbar(mischen("#000000", c, .18 * staerke), p["bg"], 12)
        p["text2"] = lesbar(mischen("#000000", c, .38 * staerke), p["bg"], 6.5)
        p["text3"] = lesbar(mischen("#6E6E6E", c, .45 * staerke), p["bg"], 4.5)
        p["akzent"] = lesbar(c, p["fl"], 4.6)
        p["titel"] = mischen(c, "#000000", .30)
        p.update(_STATUS_HELL)
    else:
        p["text"] = lesbar(mischen("#FFFFFF", c, .10 * staerke), p["bg"], 7)
        p["text2"] = lesbar(mischen("#E4E7EA", c, .25 * staerke), p["bg"], 6.5)
        p["text3"] = lesbar(mischen("#A4AAB0", c, .30 * staerke), p["bg"], 4.5)
        p["akzent"] = lesbar(mischen(c, "#FFFFFF", .35), p["fl"], 4.6)
        p["titel"] = mischen("#1E2124" if stufe == "gedaempft" else "#0E1012", c, .45 if stufe == "gedaempft" else .35)
        p.update(_STATUS_DUNKEL)
    p["akzent_text"] = "#FFFFFF" if kontrast("#FFFFFF", p["akzent"]) >= 4.5 else "#111111"
    p["dunkel"] = stufe != "hell"
    return p


def ton_variablen(p: dict) -> dict[str, str]:
    a = .18 if p["dunkel"] else .10
    v = {"--bg": p["bg"], "--fl": p["fl"], "--fl2": p["fl2"], "--fls": p["fls"], "--rand": p["rand"], "--rand2": p["rand2"],
         "--text": p["text"], "--text2": p["text2"], "--text3": p["text3"], "--akzent": p["akzent"],
         "--akzent-text": p["akzent_text"], "--akzent-hell": p["akzent"], "--akzent-hover": p["akzent"],
         "--fokus": p["akzent"], "--kopf": p["band"], "--rot": p["krit"], "--orange": p["warn"], "--gruen": p["ok"],
         "--blau": p["blau"], "--ob-akzent": p["akzent"], "--ob-band": p["band"], "--ob-reiter": p["reiter"],
         "--ob-rand": p["rand"], "--ob-text": p["text"], "--ob-text2": p["text2"], "--ob-hover": p["hover"],
         "--ob-an": p["an"], "--ob-fl": p["bg"], "--glas": p["fls"], "--glas2": p["fl"], "--glasrand": p["rand"]}
    for st, c in (("ok", p["ok"]), ("krit", p["krit"]), ("warn", p["warn"]), ("blau", p["blau"]),
                  ("akzent", p["akzent"]), ("neutral", p["text3"])):
        v.update({f"--s-{st}-bg": f"color-mix(in srgb, {c} {int(a * 100)}%, transparent)", f"--s-{st}-fg": c,
                  f"--s-{st}-bd": f"color-mix(in srgb, {c} 45%, transparent)"})
    return v


def _titelleiste(v: dict, tl: str, titel_bg: str, dunkel: bool) -> None:
    if tl == "hell":
        v.update({"--ob-titel": "#FFFFFF" if not dunkel else "#1E2626",
                  "--ob-titel-text": "#1F2A2A" if not dunkel else "#E6EEEE"})
    elif tl == "dunkel":
        v.update({"--ob-titel": "#1F2626", "--ob-titel-text": "#FFFFFF"})
    else:
        v.update({"--ob-titel": titel_bg, "--ob-titel-text": "#FFFFFF" if kontrast("#FFFFFF", titel_bg) >= 4.5
                  else "#111111"})


def css_variablen(d: dict, dunkel: bool) -> dict[str, str]:
    """CSS-Variablen für <body> (inline – gehen den Theme-Klassen vor). Leer, wenn alles Standard ist.
    0.72: „Ganzes Design“ oder „Gedämpft“ → Ton-Palette aus der Farbe (alle Flächen, Ränder, Texte)."""
    v: dict[str, str] = {}
    hl = d.get("helligkeit", "dunkel" if dunkel else "hell")
    if d.get("faerbung") == "ganz" or hl == "gedaempft":
        c, _t = akzent(d)
        p = ton_palette(c, hl, 1.0 if d.get("faerbung") == "ganz" else .25)
        v.update(ton_variablen(p))
        _titelleiste(v, d.get("titelleiste", "farbig"), p["titel"], p["dunkel"])
    elif not standard_farbe(d) or d.get("titelleiste", "farbig") != "farbig":
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
        _titelleiste(v, d.get("titelleiste", "farbig"), titel_bg, dunkel)
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
