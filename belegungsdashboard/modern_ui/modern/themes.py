"""Darstellung der neuen Oberfläche – zwei Ebenen, sauber getrennt.

* **Layout** (Informationsarchitektur): Original-Zustand · Classic Grid · AI-Canvas · Showcase.
* **Theme** (nur Farben, Typografie, Radien): Original · inn-tegrativ · Linear Monochrome · Executive Obsidian ·
  Soft Nordic – jeweils hell oder dunkel (Original nur dunkel). Dazu Dichte (normal/kompakt) und schmale Leiste.

Der **Original-Zustand** setzt am ``<body>`` keine einzige Klasse – dann gilt ausschließlich das bisherige CSS, 1:1
wie vor dem Umbau. Alles Neue greift nur unter ``body.pro`` (plus ``lay-…``, ``th-…``, ``mod-…``, ``dichte-…``).
"""

from __future__ import annotations

from .stil import T as _ORIGINAL

from . import darstellung_kern as _dk  # noqa: E402 – 0.66: Farbrechnung
from .darstellung_modell import LAYOUTS, STANDARD, THEMES, bereinigen  # noqa: E402,F401 – 1.29: ein Modell

# ---------------------------------------------------------------------------------------
# Paletten (je Theme hell/dunkel) – nur Farben
# ---------------------------------------------------------------------------------------

_DUNKEL = {   # gedeckte Status-Töne (950/50 Hintergrund · 400 Schrift · 800/50 Rand)
    "ok": ("rgba(2,44,34,.5)", "#34d399", "rgba(6,95,70,.5)"),
    "krit": ("rgba(76,5,25,.5)", "#fb7185", "rgba(159,18,57,.5)"),
    "warn": ("rgba(69,26,3,.5)", "#fbbf24", "rgba(146,64,14,.5)"),
    "blau": ("rgba(23,37,84,.5)", "#60a5fa", "rgba(30,64,175,.5)"),
    "akzent": ("rgba(30,27,75,.5)", "#a5b4fc", "rgba(55,48,163,.5)"),
    "neutral": ("rgba(39,39,42,.5)", "#a1a1aa", "rgba(63,63,70,.5)"),
}
# INNternat: Status bewusst NICHT türkis (das ist der Akzent) – frei grün, belegt blau, Mangel orange, kritisch rot
_INN_DUNKEL = {
    "ok": ("rgba(120,200,90,.15)", "#9AD96E", "rgba(120,200,90,.45)"),
    "krit": ("rgba(255,138,128,.14)", "#FF8A80", "rgba(255,138,128,.45)"),
    "warn": ("rgba(246,194,107,.14)", "#F6C26B", "rgba(246,194,107,.45)"),
    "blau": ("rgba(141,184,240,.14)", "#8DB8F0", "rgba(141,184,240,.45)"),
    "akzent": ("rgba(94,214,198,.14)", "#5ED6C6", "rgba(94,214,198,.45)"),
    "neutral": ("rgba(147,170,170,.14)", "#B4C7C6", "rgba(147,170,170,.40)"),
}
_INN_HELL = {
    "ok": ("#EEF7E8", "#2F6F14", "#BFE0A8"), "krit": ("#FDF0EE", "#B42318", "#F5C5BF"),
    "warn": ("#FFF6E5", "#8A5100", "#F2D49A"), "blau": ("#EDF3FC", "#1D5BB8", "#BFD3F2"),
    "akzent": ("#E6F4F2", "#0B6E66", "#A9DAD3"), "neutral": ("#EEF2F2", "#3D5558", "#CBD8D8"),
}

_HELL = {
    "ok": ("#ecfdf3", "#067647", "#abefc6"), "krit": ("#fef3f2", "#b42318", "#fecdca"),
    "warn": ("#fffaeb", "#b54708", "#fedf89"), "blau": ("#eff4ff", "#1d4ed8", "#c7d7fe"),
    "akzent": ("#f4f3ff", "#5925dc", "#d9d6fe"), "neutral": ("#f2f4f7", "#475467", "#d0d5dd"),
}


def _p(bg, fl, fl2, rand, rand2, text, text2, text3, akzent, akzent_text, akzent_hell, akzent_hover, rot, orange, gruen,
       blau, chrome, chrome_hover, chrome_aktiv, chrome_text, chrome_aktiv_text, chrome_aktiv_icon, chrome_text2,
       chrome_text3, chrome_rand, chrome_strich, kopf=None, fls=None, status=None, schatten="none",
       panel_schatten="-16px 0 40px rgba(0,0,0,.35)"):
    d = dict(locals())
    d["fls"] = fls or fl
    d["kopf"] = kopf or bg
    d["fokus"] = akzent_hell
    return d


P = {   # 1.34: nur noch das Theme INNternat (hell und dunkel)
    ("innternat", "dunkel"): _p("#132328", "#182b31", "#1f363d", "#25414a", "#33545e", "#E7F0EF", "#B4C7C6", "#93AAAA",
                                "#5ED6C6", "#0A1F22", "#5ED6C6", "#7FE3D6", "#FF8A80", "#F6C26B", "#9AD96E", "#8DB8F0",
                                "#0f1d21", "#173036", "#1d3d42", "#E7F0EF", "#5ED6C6", "#5ED6C6", "#B4C7C6", "#93AAAA",
                                "#1f363d", "#5ED6C6", status=_INN_DUNKEL, panel_schatten="-16px 0 40px rgba(0,0,0,.4)"),
    ("innternat", "hell"): _p("#F1F5F5", "#FFFFFF", "#E6EEEE", "#D3DFDF", "#B9CBCB", "#10272B", "#3D5558", "#53696C",
                              "#0B6E66", "#FFFFFF", "#0B6E66", "#085A53", "#B42318", "#9A5B00", "#17703F", "#1D5BB8",
                              "#E8F0F0", "#DCE8E8", "#CDE3E1", "#10272B", "#074B45", "#074B45", "#3D5558", "#53696C",
                              "#D3DFDF", "#0B6E66", kopf="#F1F5F5", status=_INN_HELL,
                              schatten="0 1px 2px rgba(16,39,43,.06)", panel_schatten="-12px 0 32px rgba(16,39,43,.14)"),
}

# Typografie und Kanten je Theme (unabhängig von hell/dunkel)
TYPO = {
    "innternat": dict(r="6px", r2="10px", fs="14px", zeile="44px", kante="none",
                      schrift='"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif',      # 0.55: statt Candara (ruhiger in Tabellen)
                      titel_schrift='"Bahnschrift", "Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif'),
}


def _vars(theme: str, modus: str) -> str:
    v = P[(theme, modus)]
    zeilen = [f"--{k.replace('_', '-')}: {w};" for k, w in v.items() if k != "status"]
    for st, (bg, fg, bd) in v["status"].items():
        zeilen += [f"--s-{st}-bg: {bg};", f"--s-{st}-fg: {fg};", f"--s-{st}-bd: {bd};"]
    zeilen += ["--glas: var(--fls);", "--glas2: var(--fl);", "--glasrand: var(--rand);", "--mono: inherit;",
               "--violett: var(--akzent);", "--indigo: var(--akzent);"]
    return f"body.pro.th-{theme}.mod-{modus} {{ " + " ".join(zeilen) + " }"


def _typo(theme: str) -> str:
    return f"body.pro.th-{theme} {{ " + " ".join(f"--{k.replace('_', '-')}: {w};" for k, w in TYPO[theme].items()) + " }"


def modi(theme: str) -> list[str]:
    return [m for (t, m) in P if t == theme]




def farben(d: dict | str) -> dict:
    """Farben für Diagramme (ECharts bekommt Farben aus Python, nicht aus dem CSS)."""
    if isinstance(d, str):
        d = {"layout": "grid" if d != "original" else "original", "theme": d}
    d = bereinigen(d)
    if d["layout"] == "original":
        return {**_ORIGINAL, "fls": _ORIGINAL["fl"], "hell": False}
    v = P[(d["theme"], d["modus"])]
    return {"text": v["text"], "text2": v["text2"], "text3": v["text3"], "rand": v["rand"], "rand2": v["rand2"],
            "fl2": v["fl2"], "akzent": _dk.diagramm_akzent(d, d["modus"] != "hell", v["akzent_hell"]), "blau": v["blau"], "gruen": v["gruen"], "orange": v["orange"],
            "rot": v["rot"], "bg": v["bg"], "fls": v["fls"], "hell": d["modus"] == "hell"}


AKTIV: dict = dict(STANDARD)      # aktueller Zustand (eine Oberfläche je Programm – reicht als Modulwert)


def klassen(d: dict) -> list[str]:
    """Klassen am <body>. 1.35: immer Menüband (lay-office) im Theme INNternat."""
    d = bereinigen(d)
    k = ["pro", "lay-office", "th-innternat", f"mod-{d['modus']}"]
    if d["modus"] == "hell":
        k.append("hell")
    if d["dichte"] in ("kompakt", "komfort"):
        k.append(f"dichte-{d['dichte']}")
    if d["band_gross"]:
        k.append("band-gross")
    if d.get("werkzeuge_oben", True):
        k.append("ob-oben")                     # 0.99: Werkzeuge der Seite in der Kontext-Registerkarte (wie Office)
    if d.get("band_zu"):
        k.append("band-zu")                     # 0.74: Menüband eingeklappt (Strg+F1)
    if d.get("knopfstil", "klar") != "klar":    # 0.75: Knopfstil, hoher Kontrast
        k.append(f"knopf-{d['knopfstil']}")
    if d.get("kontrast"):
        k.append("kontrast")
    return k


def stil(d: dict) -> str:
    """0.66: Inline-Stil für <body> – Akzentfarbe, Titelleiste, Schrift und Zoom."""
    d = bereinigen(d)
    return _dk.style_text(_dk.css_variablen(d, d["modus"] != "hell"))


ALLE_KLASSEN = ["pro", "hell", "dichte-kompakt", "dichte-komfort", "band-zu", "knopf-weich", "knopf-kontur", "knopf-kraeftig",
                "kontrast", "mod-hell", "mod-dunkel", "band-gross", "ob-oben", "ob-seite-an", "ob-hat-werkzeuge", "lay-office",
                "th-innternat"]

# ---------------------------------------------------------------------------------------
# CSS – nur unter body.pro
# ---------------------------------------------------------------------------------------

_PRO = """
/* ===== Neue Designs: gemeinsame ruhige Grundschicht ===== */
html:has(body.pro), body.pro, body.pro .q-layout, body.pro .q-page-container { background: var(--bg) !important; }
body.pro { color: var(--text); font-family: var(--schrift); font-size: var(--fs); letter-spacing: 0; }
body.pro * { scrollbar-color: var(--rand2) transparent; }
body.pro :focus-visible { outline: 2px solid var(--fokus) !important; outline-offset: 2px; }

/* Navigation (Seitenleiste) */

body.pro .m-suche { border-color: var(--chrome-rand) !important; }

/* Kopf und Leisten */
body.pro .m-kopf, body.pro .m-leiste { background: var(--kopf); border-bottom: 1px solid var(--rand); backdrop-filter: none; -webkit-backdrop-filter: none; }
body.pro .m-titel { font-family: var(--titel-schrift); font-weight: 600; letter-spacing: -0.01em; }
body.pro .m-kpi { color: var(--text2); }

/* Knöpfe – flach, klare Kante, keine Skalierung, kein Glow */
body.pro .m-knopf { background: var(--fls); border: 1px solid var(--rand2); color: var(--text); border-radius: var(--r);
  box-shadow: var(--schatten); transform: none; filter: none; transition: background .12s, border-color .12s, color .12s; }
body.pro .m-knopf:hover { background: var(--fl2); border-color: var(--rand2); transform: none; box-shadow: var(--schatten); }
body.pro .m-knopf:active { transform: none; background: var(--fl2); }
body.pro .m-knopf.primaer { background: var(--akzent); border-color: var(--akzent); color: var(--akzent-text); box-shadow: none; }
body.pro .m-knopf.primaer:hover { background: var(--akzent-hover); border-color: var(--akzent-hover); filter: none; box-shadow: none; }
body.pro .m-knopf.leise { background: transparent; border-color: transparent; box-shadow: none; color: var(--text2); }
body.pro .m-knopf.leise:hover { background: var(--fl2); color: var(--text); border-color: transparent; }
body.pro .m-knopf.gruen { background: var(--s-ok-bg); border-color: var(--s-ok-bd); color: var(--s-ok-fg); box-shadow: none; }
body.pro .m-knopf.gruen:hover { background: var(--s-ok-bg); border-color: var(--s-ok-fg); }
body.pro .m-knopf.akzent { background: var(--s-blau-bg); border-color: var(--s-blau-bd); color: var(--s-blau-fg); }
body.pro .m-zahl { background: var(--fl2); color: var(--text2); }
body.pro .m-zahl.rot { background: var(--s-krit-fg); color: #fff; }
body.pro .m-taste { color: var(--text3); border-color: var(--rand2); }

/* Umschalter */
body.pro .m-segm { background: var(--fl2); border: 1px solid var(--rand); border-radius: var(--r); box-shadow: none; padding: 2px; }
body.pro .m-segm button { color: var(--text2); border-radius: calc(var(--r) - 1px); }
body.pro .m-segm button:hover { color: var(--text); background: transparent; }
body.pro .m-segm button.an { background: var(--fls); color: var(--text); font-weight: 600; box-shadow: 0 0 0 1px var(--rand2); }

/* Kennzahlen: eckige Kärtchen, ruhige Ziffern, gedämpfte Labels */
body.pro .m-stat { background: var(--fl); border: 1px solid var(--rand); border-radius: var(--r2); box-shadow: none; backdrop-filter: none;
  -webkit-backdrop-filter: none; transform: none; padding: 10px 14px; min-width: 128px; }
body.pro .m-stat:hover { transform: none; border-color: var(--rand2); background: var(--fl2); box-shadow: none; }
body.pro .m-stat.an { background: var(--fl2); border-color: var(--akzent-hell); box-shadow: inset 0 0 0 1px var(--akzent-hell); }
body.pro .m-stat .z, body.pro .m-stat.ok .z, body.pro .m-stat.warn .z, body.pro .m-stat.krit .z, body.pro .m-stat.blau .z,
body.pro .m-stat.akzent .z, body.pro .m-stat.neutral .z { font-family: var(--schrift); font-size: 24px; font-weight: 600; letter-spacing: -0.025em;
  color: var(--text); font-variant-numeric: tabular-nums; }
body.pro .m-stat .l { color: var(--text3); font-size: 12px; font-weight: 500; }
body.pro .m-stat .s { background: transparent; width: auto; height: auto; font-size: 16px; color: var(--c); }
body.pro .m-stat.ok { --c: var(--s-ok-fg); } body.pro .m-stat.warn { --c: var(--s-warn-fg); } body.pro .m-stat.krit { --c: var(--s-krit-fg); }
body.pro .m-stat.blau { --c: var(--s-blau-fg); } body.pro .m-stat.akzent { --c: var(--s-akzent-fg); } body.pro .m-stat.neutral { --c: var(--text3); }
body.pro .m-kpikarte { background: var(--fl); border-color: var(--rand); border-radius: var(--r2); }
body.pro .m-kpiwert { color: var(--text); }

/* Zustände: gedeckte Badges (frei, belegt, geplant, gesperrt, Mängel, unbewohnbar) */
body.pro .m-badge { border-radius: var(--r); box-shadow: none; font-weight: 600; }
body.pro .m-badge.ok, body.pro .m-pille.ok, body.pro .m-chip.ok { background: var(--s-ok-bg); color: var(--s-ok-fg); border: 1px solid var(--s-ok-bd); }
body.pro .m-badge.krit, body.pro .m-pille.krit { background: var(--s-krit-bg); color: var(--s-krit-fg); border: 1px solid var(--s-krit-bd); }
body.pro .m-badge.warn, body.pro .m-pille.warn, body.pro .m-chip.warn { background: var(--s-warn-bg); color: var(--s-warn-fg); border: 1px solid var(--s-warn-bd); }
body.pro .m-badge.blau { background: var(--s-blau-bg); color: var(--s-blau-fg); border: 1px solid var(--s-blau-bd); }
body.pro .m-badge.akzent, body.pro .m-chip.akzent { background: var(--s-akzent-bg); color: var(--s-akzent-fg); border: 1px solid var(--s-akzent-bd); }
body.pro .m-badge.neutral, body.pro .m-pille, body.pro .m-chip { background: var(--s-neutral-bg); color: var(--s-neutral-fg); border: 1px solid var(--s-neutral-bd); }
body.pro .m-pille, body.pro .m-chip { border-radius: var(--r); }
body.pro .m-neu-badge { background: var(--s-blau-bg); color: var(--s-blau-fg); border: 1px solid var(--s-blau-bd); box-shadow: none; border-radius: var(--r); }
body.pro .m-ampel.ok { background: var(--s-ok-fg); } body.pro .m-ampel.warn { background: var(--s-warn-fg); }
body.pro .m-ampel.krit { background: var(--s-krit-fg); } body.pro .m-ampel.akzent { background: var(--s-akzent-fg); }
body.pro .m-krit { color: var(--rot) !important; } body.pro .m-warn { color: var(--orange) !important; }
body.pro .m-bar.ok { background: var(--s-ok-fg); } body.pro .m-bar.warn { background: var(--s-warn-fg); }
body.pro .m-bar.krit { background: var(--s-krit-fg); } body.pro .m-bar.akzent { background: var(--akzent-hell); }
body.pro .m-spur { background: var(--fl2); }

/* Zimmer-Kacheln, Zeitstrahl, Legende */
body.pro .m-kachel { border-radius: var(--r); transition: none; color: var(--text); }
body.pro .m-kachel:hover { transform: none; box-shadow: 0 0 0 1px var(--text3); filter: none; }
body.pro .m-kachel.frei, body.pro .m-legende i.frei { background: color-mix(in srgb, var(--s-ok-fg) 30%, var(--fls)); border: 1px solid var(--s-ok-fg); }
body.pro .m-kachel.teilweise, body.pro .m-legende i.teilweise { /* 0.80: halb belegt, halb frei – nicht mehr gestrichelt (wie „geplant“) */
  /* 0.86: zwei Bett-Segmente (links belegt, rechts frei) mit Trennstrich statt halber Diagonale */
  background: linear-gradient(90deg, var(--s-blau-bg) 0 calc(50% - 1px), var(--s-ok-fg) calc(50% - 1px) calc(50% + 1px),
                              color-mix(in srgb, var(--s-ok-fg) 30%, var(--fls)) calc(50% + 1px) 100%);
  color: var(--s-blau-fg); border: 1px solid var(--s-ok-fg); }
body.pro .m-kachel.belegt, body.pro .m-legende i.belegt, body.pro .m-zs-b.belegt, body.pro .m-zs-punkt { background: var(--s-blau-bg); color: var(--s-blau-fg); box-shadow: inset 0 0 0 1px var(--s-blau-bd); }
body.pro .m-kachel.geplant, body.pro .m-legende i.geplant, body.pro .m-zs-b.geplant, body.pro .m-zs-punkt.geplant { background: var(--fls); color: var(--s-akzent-fg); box-shadow: none; border: 1.5px dashed var(--s-akzent-fg); box-sizing: border-box; }
body.pro .m-kachel.gesperrt, body.pro .m-legende i.gesperrt, body.pro .m-zs-b.gesperrt, body.pro .m-zs-punkt.gesperrt { background: repeating-linear-gradient(135deg, var(--s-neutral-bg) 0 5px, var(--fl2) 5px 10px); color: var(--s-neutral-fg); box-shadow: inset 0 0 0 1px var(--s-neutral-bd); }
body.pro .m-zs-b.konflikt, body.pro .m-legende i.konflikt { background: var(--s-krit-bg); color: var(--s-krit-fg); box-shadow: inset 0 0 0 1px var(--s-krit-fg); }
body.pro .m-kachel.unbew { border: 2px solid var(--s-krit-fg); }
body.pro .m-kachel.nn { background: repeating-linear-gradient(135deg, var(--s-neutral-bg) 0 5px, var(--fl2) 5px 10px);
  color: var(--s-neutral-fg); }                     /* 0.70: „nicht nutzbar“ einheitlich gestreift (Grund: roter Rahmen = Mangel) */
body.pro .m-kachel-m { background: var(--s-warn-fg); color: var(--fls); }
body.pro .m-zs-tag.heute { color: var(--akzent-hell); } body.pro .m-zs-jetzt { background: var(--akzent-hell); }
body.pro .m-zs-kopf, body.pro .m-tkopf { background: var(--bg); }

/* Tabellen */
body.pro .m-zeile { min-height: var(--zeile); border-bottom-color: var(--rand); }
body.pro .m-zeile:hover { background: var(--fl2); }
body.pro .m-tkopf { border-bottom-color: var(--rand2); }
body.pro .m-tkopf > div { color: var(--text3); font-weight: 600; }
body.pro .m-mono { font-family: var(--schrift); color: var(--text2); }
body.pro .m-zweite { color: var(--text3); }
body.pro .m-ptext { color: var(--text2); }
body.pro .m-haken.an { background: var(--s-ok-fg); border-color: var(--s-ok-fg); color: var(--fls); }

/* Flächen: Blöcke, Karten, Panels – ohne Glas, ohne Schatten-Spielerei */
body.pro .m-block, body.pro .m-khaus, body.pro .m-ketage, body.pro .m-zkarte, body.pro .m-kandidat, body.pro .m-wo, body.pro .m-plan-u,
body.pro .m-w-schritt { background: var(--fl); border: 1px solid var(--rand); border-radius: var(--r2); box-shadow: var(--schatten);
  backdrop-filter: none; -webkit-backdrop-filter: none; }
body.pro .m-ketage { background: var(--bg); }
body.pro .m-zkarte { border-radius: var(--r); background: var(--fls); }
body.pro .m-zkarte:hover { transform: none; border-color: var(--akzent-hell); background: var(--fls); box-shadow: none; }
body.pro .m-zkarte.unbew { border-color: var(--s-krit-fg); box-shadow: none; }
body.pro .m-zk-bel .q-icon { color: var(--s-blau-fg); } body.pro .m-zk-bel.geplant .q-icon { color: var(--s-akzent-fg); }
body.pro .m-zk-bel.gesperrt .q-icon { color: var(--s-neutral-fg); }
body.pro .m-zk-mangel .q-icon { color: var(--s-warn-fg); } body.pro .m-zk-mangel.warn { color: var(--s-warn-fg); }
body.pro .m-zk-mangel.krit, body.pro .m-zk-mangel.krit .q-icon { color: var(--s-krit-fg); }
body.pro .m-khaus-kopf .q-icon { color: var(--text3); }
body.pro .m-hinweisbox { background: var(--s-warn-bg); border: 1px solid var(--s-warn-bd); color: var(--text); border-radius: var(--r); }
body.pro .m-willkommen { background: var(--fl); border: 1px solid var(--rand); border-radius: var(--r2); box-shadow: none; animation: none;
  backdrop-filter: none; -webkit-backdrop-filter: none; }
body.pro .m-w-gruss { color: var(--text3); }
body.pro .m-w-nr { background: var(--fl2); border: 1px solid var(--rand); color: var(--text2); border-radius: var(--r); }

/* Aufgaben: linker Rand zeigt die Dringlichkeit – ohne Glow und Puls */
body.pro .m-karte { background: var(--fls); border: 1px solid var(--rand); border-left-width: 3px; border-radius: var(--r2); box-shadow: none; transform: none; }
body.pro .m-karte:hover { transform: none; box-shadow: none; background: var(--fls); border-color: var(--rand2); }
body.pro .m-karte.dringend { border-left-color: var(--s-krit-fg); background: var(--fls); box-shadow: none; }
body.pro .m-karte.bald { border-left-color: var(--s-warn-fg); }
body.pro .m-karte.info { border-left-color: var(--rand2); }
body.pro .m-karte.dringend:hover, body.pro .m-karte.bald:hover { border-color: var(--rand2); }
body.pro .m-karte.dringend:hover { border-left-color: var(--s-krit-fg); } body.pro .m-karte.bald:hover { border-left-color: var(--s-warn-fg); }
body.pro .m-ksymbol { background: var(--fl2); border: 1px solid var(--rand); border-radius: var(--r); box-shadow: none !important; animation: none !important; }
body.pro .m-ksymbol.krit { --c: var(--s-krit-fg); } body.pro .m-ksymbol.warn { --c: var(--s-warn-fg); } body.pro .m-ksymbol.ok { --c: var(--text2); }
body.pro .m-kstufe.krit { color: var(--s-krit-fg); } body.pro .m-kstufe.warn { color: var(--s-warn-fg); } body.pro .m-kstufe.ok { color: var(--text3); }
body.pro .m-cgruppe { color: var(--text3); }

/* Slide-over und Schleier */
body.pro .m-center, body.pro .m-center.offen { background: var(--fls); border-left: 1px solid var(--rand); border-radius: 0;
  backdrop-filter: none; -webkit-backdrop-filter: none; box-shadow: var(--panel-schatten); }
body.pro .m-ckopf { border-bottom-color: var(--rand); }
body.pro .m-schleier { background: rgba(0,0,0,.32); backdrop-filter: none; -webkit-backdrop-filter: none; }
body.hell .m-schleier { background: rgba(15,23,42,.22); }

/* Menüs, Auswahllisten, Suche, Toast */
body.pro .m-menue, body.pro .m-popup, body.pro .q-menu { background: color-mix(in srgb, var(--fls) 95%, transparent) !important;
  border: 1px solid color-mix(in srgb, var(--rand2) 70%, transparent); border-radius: 12px !important; color: var(--text);
  backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); box-shadow: 0 18px 40px rgba(0,0,0,.28); padding: 6px; min-width: 180px; }
body.pro .q-menu .q-item, body.pro .m-popup .q-item { border-radius: 8px; min-height: 34px; padding: 0 12px; font-size: 13px; transition: background .15s; }
body.pro .m-menue .q-item, body.pro .m-popup .q-item, body.pro .q-menu .q-item { color: var(--text); }
body.pro .m-popup .q-item:hover, body.pro .m-popup .q-item.q-manual-focusable--focused, body.pro .q-menu .q-item:hover { background: var(--fl2); }
body.pro .m-mhaken { color: var(--text3); } body.pro .m-mhaken.an { color: var(--akzent-hell); }
body.pro .m-palette { background: var(--fls); border-color: var(--rand2); border-radius: var(--r2); }
body.pro .m-palette-z:hover, body.pro .m-palette-z.an { background: var(--fl2); }
body.pro .m-toast { background: var(--text); color: var(--bg); border-radius: var(--r); }
body.pro .m-toast.fehler { background: var(--s-krit-fg); color: #fff; }
body.pro .m-blase.nutzer { background: var(--s-blau-bg); } body.pro .m-blase.assistent { background: var(--fl); border-color: var(--rand); }
body.pro .m-monat { background: var(--rand); border-color: var(--rand); border-radius: var(--r2); }
body.pro .m-monat-kopf { background: var(--fl2); } body.pro .m-monat-tag { background: var(--fls); }
body.pro .m-monat-tag.we { background: var(--bg); }
body.pro .m-monat-tag.heute .m-monat-nr { background: var(--akzent); color: var(--akzent-text); }
body.pro .m-feld .q-field__control, body.pro .m-zimmer .q-field__control { background: var(--fls) !important; border-radius: var(--r) !important; }
body.pro .m-feld .q-field__control:before, body.pro .m-zimmer .q-field__control:before { border-color: var(--rand2) !important; }
/* Dialoge: Milchglas-Hintergrund, weiche Kante, leichtes Hineinzoomen */
body.pro .q-dialog__backdrop { background: rgba(0,0,0,.6) !important; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  transition: opacity .3s; }
body.pro .q-dialog .m-palette { border-radius: 16px; border: 1px solid var(--rand2); box-shadow: 0 30px 70px rgba(0,0,0,.45);
  animation: m-zoom .2s ease-out both; }
@keyframes m-zoom { from { opacity: 0; transform: scale(.95); } }
/* Formulare: sauberer Fokus-Ring */
body.pro .q-field--focused .q-field__control { box-shadow: 0 0 0 3px color-mix(in srgb, var(--akzent-hell) 35%, transparent); border-radius: var(--r); }
body.pro .m-zeile:hover { background: color-mix(in srgb, var(--text) 5%, transparent); }

/* Helle Designs: Quasar-Felder, Menüs und Häkchen auf hell umstellen */
body.hell .q-field__native, body.hell .q-field__input, body.hell .q-field__marginal, body.hell .q-select__dropdown-icon,
body.hell .q-field__prefix, body.hell .q-field__suffix { color: var(--text) !important; }
body.hell .q-field__label { color: var(--text3) !important; }
body.hell .q-field--outlined .q-field__control:before { border-color: var(--rand2) !important; }
body.hell .q-field--outlined.q-field--focused .q-field__control:after { border-color: var(--akzent) !important; }
body.hell .q-checkbox__label, body.hell .q-toggle__label, body.hell .q-item__label { color: var(--text) !important; }
body.hell .q-checkbox__bg { border-color: var(--text3) !important; }
body.hell .q-toggle__track { background: var(--rand2); opacity: 1; }
body.hell input, body.hell textarea { color-scheme: light; }
body.hell .q-separator { background: var(--rand) !important; }
body.hell .m-palette-ein input { color: var(--text) !important; }
body.hell .m-toast { box-shadow: 0 10px 30px rgba(16,24,40,.25); }

/* Navigation: schmal (nur Symbole, Tooltips) */


/* Navigation einklappen */

"""

_THEME_EIGEN = """
/* Theme-Feinheiten (nur Optik, keine Struktur) */
body.pro .m-stat, body.pro .m-block { border-top: var(--kante); }
"""

_DICHTE = """
/* Dichte: kompakt */
body.pro.dichte-kompakt { --zeile: 30px; font-size: 12.5px; }
body.pro.dichte-kompakt .m-zeile > div { padding: 2px 8px; }
body.pro.dichte-kompakt .m-tkopf > div { padding: 5px 8px; }
body.pro.dichte-kompakt .m-kopf { min-height: 42px; padding-top: 4px; padding-bottom: 4px; }
body.pro.dichte-kompakt .m-leiste { padding: 6px 16px; gap: 8px; }
body.pro.dichte-kompakt .m-stat { padding: 5px 10px; min-width: 96px; }
body.pro.dichte-kompakt .m-stat .z { font-size: 17px !important; }
body.pro.dichte-kompakt .m-stat .l { font-size: 11px; }
body.pro.dichte-kompakt .m-knopf { height: 26px; padding: 0 9px; }
body.pro.dichte-kompakt .m-segm button { height: 22px; padding: 0 8px; }
body.pro.dichte-kompakt .m-block { padding: 10px 12px; gap: 6px; }
body.pro.dichte-kompakt .m-heute, body.pro.dichte-kompakt .m-zwei { gap: 10px; padding: 10px 14px; }
body.pro.dichte-kompakt .m-karte { padding: 9px 11px; gap: 5px; }
body.pro.dichte-kompakt .m-kachel { width: 40px; height: 26px; }
"""

_LAYOUTS = """
/* ===== Layout: Classic Enterprise Grid – Seitenleiste wie gewohnt, einklappbar (Grundschicht) ===== */

/* ===== Layout: AI-Canvas & Prompt ===== */
.m-topnav { display: none; }
body.pro .m-cv { padding: 18px 24px 40px; display: flex; flex-direction: column; gap: 18px; max-width: 1400px; margin: 0 auto; width: 100%;
  animation: m-cv-rein .25s ease-out both; }
@keyframes m-cv-rein { from { opacity: 0; transform: translateY(6px); } }

/* ===== Layout: Showcase – schwebendes Dock, großzügige Karten, Glas ===== */

@media (prefers-reduced-motion: reduce) { body.pro .m-cv { animation: none; } }
"""

# ---- 0.15: Heute als Newsfeed, Morgen-Briefing, Aufgaben-Drawer aus Glas (nur neue Layouts) ----------------------------
_FEED = """
body.pro .m-feed { max-width: 860px; margin: 0 auto; padding: 22px 24px 64px; display: flex; flex-direction: column; gap: 10px;
  position: relative; }
body.pro .m-feed::before { content: ""; position: absolute; left: 41px; top: 74px; bottom: 70px; width: 1px;
  background: linear-gradient(var(--rand2), transparent); }
body.pro .m-feed-abschnitt { display: flex; align-items: center; gap: 10px; margin: 14px 0 2px; font-size: 11.5px; font-weight: 700;
  letter-spacing: .08em; text-transform: uppercase; color: var(--text3); position: relative; z-index: 1; }
body.pro .m-feed-abschnitt .q-icon { width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; font-size: 18px;
  background: var(--fls); border: 1px solid var(--rand2); color: var(--text2); }
body.pro .m-feed-abschnitt.krit .q-icon { color: var(--s-krit-fg); border-color: color-mix(in srgb, var(--s-krit-fg) 45%, transparent); }
body.pro .m-feed-eintrag { margin-left: 50px; position: relative; }
body.pro .m-feed-zeile { font: inherit; text-align: left; color: var(--text); display: flex; align-items: center; gap: 12px;
  padding: 12px 14px; border-radius: var(--r2); background: var(--fls); border: 1px solid var(--rand); border-left: 3px solid var(--rand2);
  transition: border-color .15s, transform .15s; width: calc(100% - 50px); }
body.pro button.m-feed-zeile { cursor: pointer; }
body.pro button.m-feed-zeile:hover { border-color: var(--rand2); transform: translateX(2px); }
body.pro .m-feed-zeile.krit { border-left-color: var(--s-krit-fg); }
body.pro .m-feed-zeile.warn { border-left-color: var(--s-warn-fg); }
body.pro .m-feed-zeile.ok { border-left-color: var(--s-ok-fg, var(--gruen)); }
body.pro .m-feed-symbol { width: 32px; height: 32px; flex: none; border-radius: 9px; display: grid; place-items: center;
  background: color-mix(in srgb, var(--text) 6%, transparent); color: var(--text2); }
body.pro .m-feed-symbol.krit { color: var(--s-krit-fg); background: color-mix(in srgb, var(--s-krit-fg) 12%, transparent); }
body.pro .m-feed-symbol.warn { color: var(--s-warn-fg); background: color-mix(in srgb, var(--s-warn-fg) 12%, transparent); }
body.pro .m-feed-symbol.ok { color: var(--gruen); background: color-mix(in srgb, var(--gruen) 12%, transparent); }
body.pro .m-feed-txt { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
body.pro .m-feed-txt .m-zweite { white-space: normal; }
body.pro .m-feed-pfeil { color: var(--text3); }
body.pro .m-feed-eintrag > .m-karte { width: calc(100% - 50px); }
body.pro .m-feed-mehr { margin: 16px 0 0 50px; }
body.pro .m-feed-kopf { margin-left: 50px; }
body.pro .m-briefing-text { display: none; margin: 0 0 6px; padding: 12px 16px 12px 34px; border-radius: var(--r2); background: var(--fls);
  border: 1px solid var(--rand); color: var(--text2); line-height: 1.6; width: calc(100% - 50px); }
body.pro .m-briefing-text.offen { display: block; animation: m-xg-ein .25s ease-out both; }
body.pro .m-briefing-text li.jetzt { color: var(--text); font-weight: 600; }
body.pro .m-briefing { font: inherit; font-size: 13px; font-weight: 600; display: inline-flex; align-items: center; gap: 9px; height: 34px;
  padding: 0 14px 0 12px; border-radius: 17px; cursor: pointer; color: var(--text); background: var(--fls);
  border: 1px solid color-mix(in srgb, var(--akzent) 45%, var(--rand2)); box-shadow: 0 1px 0 rgba(255,255,255,.04) inset; }
body.pro .m-briefing:hover { border-color: var(--akzent); }
body.pro .m-welle { display: inline-flex; align-items: center; gap: 2px; height: 16px; }
body.pro .m-welle i { width: 3px; border-radius: 2px; background: var(--akzent); height: 6px; }
body.pro .m-welle i:nth-child(2) { height: 12px; } body.pro .m-welle i:nth-child(3) { height: 16px; } body.pro .m-welle i:nth-child(4) { height: 9px; }
body.pro .m-briefing.spricht .m-welle i { animation: m-welle .45s ease-in-out infinite alternate; }
body.pro .m-briefing.spricht .m-welle i:nth-child(2) { animation-delay: .15s; } body.pro .m-briefing.spricht .m-welle i:nth-child(3) { animation-delay: .3s; }
body.pro .m-briefing.spricht .m-welle i:nth-child(4) { animation-delay: .45s; }
body.pro .m-briefing.spricht { border-color: var(--akzent); background: color-mix(in srgb, var(--akzent) 14%, var(--fls)); }
@media (prefers-reduced-motion: reduce) { body.pro .m-briefing.spricht .m-welle i { animation: none; } }
body.pro .m-kspaeter { margin-left: auto; height: 28px; width: 28px; padding: 0; justify-content: center; border-color: transparent;
  background: transparent; color: var(--text3); flex: none; }
body.pro .m-kspaeter:hover { color: var(--text); background: color-mix(in srgb, var(--text) 8%, transparent); }
body.pro .m-center, body.pro .m-center.offen { background: rgba(9, 9, 11, .90); backdrop-filter: blur(24px) saturate(1.25);
  -webkit-backdrop-filter: blur(24px) saturate(1.25); border-left: 1px solid rgba(255, 255, 255, .08); }
body.pro.hell .m-center, body.pro.hell .m-center.offen { background: rgba(255, 255, 255, .86); border-left-color: rgba(15, 23, 42, .10); }
body.pro .m-center .m-ckopf { border-bottom-color: rgba(255, 255, 255, .07); }
body.pro.hell .m-center .m-ckopf { border-bottom-color: rgba(15, 23, 42, .08); }
body.pro .m-center .m-cinhalt { scroll-behavior: smooth; overscroll-behavior: contain; scrollbar-width: thin; gap: 10px; }
body.pro .m-center .m-cgruppe { position: sticky; top: -16px; z-index: 2; padding: 10px 2px 6px; margin: 0 -2px;
  background: inherit; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
body.pro .m-center .m-karte { background: color-mix(in srgb, var(--text) 3.5%, transparent); border: 1px solid color-mix(in srgb, var(--text) 8%, transparent);
  border-left: 1px solid color-mix(in srgb, var(--text) 8%, transparent); position: relative; overflow: hidden; flex: none; }
body.pro .m-center .m-karte.dringend::before { content: ""; position: absolute; left: 0; top: 10px; bottom: 10px; width: 2px;
  border-radius: 2px; background: var(--s-krit-fg); box-shadow: 0 0 10px color-mix(in srgb, var(--s-krit-fg) 55%, transparent); }
body.pro .m-center .m-karte:hover { border-color: color-mix(in srgb, var(--text) 16%, transparent); }
body.pro .m-schleier.offen { backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px); }
@keyframes m-welle { from { transform: scaleY(.45); } to { transform: scaleY(1); } }
"""

# Haptik (0.22): Eingaben bekommen Gewicht – Knöpfe geben beim Drücken spürbar nach (wie eine Taste), während des
# Speicherns läuft oben ein schmaler Balken, und die Bestätigung rastet sichtbar ein. Nur in den Layouts (body.pro);
# bei „Bewegung reduzieren“ (System) bleibt nur der Farbwechsel.
_HAPTIK = """
body.pro .m-knopf, body.pro .m-stat, body.pro .m-segm button, body.pro .m-kachel,
body.pro .m-chip, body.pro .m-neu, body.pro .m-feed-zeile, body.pro .m-xs-pill, body.pro .m-monat-tag, body.pro .q-btn {
  transition: transform .14s cubic-bezier(.2,.9,.3,1.25), box-shadow .14s ease, background .12s, border-color .12s, color .12s; }
body.pro .m-knopf { box-shadow: 0 1px 0 var(--rand2), var(--schatten); }
body.pro .m-knopf:hover { transform: translateY(-1px); box-shadow: 0 2px 0 var(--rand2), 0 6px 14px -8px rgba(0,0,0,.45); }
body.pro .m-knopf.primaer { box-shadow: inset 0 1px 0 rgba(255,255,255,.18), 0 2px 0 color-mix(in srgb, var(--akzent) 55%, #000),
  0 6px 16px -8px color-mix(in srgb, var(--akzent) 70%, transparent); }
body.pro .m-knopf.primaer:hover { transform: translateY(-1px); box-shadow: inset 0 1px 0 rgba(255,255,255,.2),
  0 3px 0 color-mix(in srgb, var(--akzent) 55%, #000), 0 10px 20px -10px color-mix(in srgb, var(--akzent) 80%, transparent); }
body.pro .m-knopf.leise, body.pro .m-knopf.leise:hover { box-shadow: none; }
body.pro .m-toast .m-knopf, body.pro .m-toast .m-knopf:hover { box-shadow: none; transform: none; }
body.pro .m-glocke .m-zahl { position: absolute; top: -5px; right: -5px; min-width: 17px; height: 17px; padding: 0 4px;
  font-size: 10.5px; line-height: 17px; border-radius: 9px; background: var(--akzent); color: var(--akzent-text); }
body.pro .m-knopf:active, body.pro .m-knopf.primaer:active { transform: translateY(2px) scale(.97); transition-duration: .05s;
  box-shadow: inset 0 2px 4px rgba(0,0,0,.28); }
body.pro .m-knopf.leise:active { transform: scale(.94); background: var(--fl2); }
body.pro .m-segm button:active, body.pro .m-chip:active, body.pro .m-neu:active,
body.pro .m-feed-zeile:active, body.pro .m-xs-pill:active, body.pro .q-btn:active { transform: scale(.96); transition-duration: .05s; }
body.pro .m-stat:active, body.pro .m-kachel:active { transform: translateY(1px) scale(.97); transition-duration: .05s;
  box-shadow: inset 0 2px 5px rgba(0,0,0,.25); }
body.pro .m-monat-tag:active { transform: scale(.985); transition-duration: .05s; }
body.pro .m-stat.an, body.pro .m-segm button.an { box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--akzent) 55%, transparent),
  0 0 0 3px color-mix(in srgb, var(--akzent) 16%, transparent); }
/* Eingabefelder: Fokus mit Ring, Schalter mit nachfederndem Knopf */
body.pro .q-field--outlined .q-field__control { transition: box-shadow .16s ease; }
body.pro .q-field--outlined.q-field--focused .q-field__control { box-shadow: 0 0 0 3px color-mix(in srgb, var(--akzent) 28%, transparent); }
body.pro .q-toggle__thumb { transition: left .22s cubic-bezier(.3,1.6,.5,1) !important; }
body.pro .q-toggle__inner--truthy .q-toggle__thumb:after { box-shadow: 0 0 0 4px color-mix(in srgb, var(--akzent) 22%, transparent); }
body.pro .q-checkbox__bg { transition: transform .14s cubic-bezier(.3,1.6,.5,1), background .12s; }
body.pro .q-checkbox:active .q-checkbox__bg { transform: scale(.85); }
/* Während gespeichert/geladen wird: schmaler Balken oben, Zeiger „arbeitet“ */
body.pro.m-arbeitet { cursor: progress; }
body.pro.m-arbeitet::after { content: ""; position: fixed; left: 0; top: 0; height: 3px; width: 100%; z-index: 9999; pointer-events: none;
  background: linear-gradient(90deg, transparent, var(--akzent), transparent); background-size: 40% 100%; background-repeat: no-repeat;
  animation: m-arbeitet 0.9s ease-in-out infinite; }
@keyframes m-arbeitet { from { background-position: -40% 0; } to { background-position: 140% 0; } }
/* Bestätigung rastet ein */
body.pro .m-toast { animation: m-einrasten .38s cubic-bezier(.2,1.4,.4,1); }
body.pro .m-toast .m-toast-ok { color: var(--gruen); font-size: 20px; animation: m-haken .45s cubic-bezier(.2,1.6,.4,1) .08s both; }
@keyframes m-einrasten { from { opacity: 0; transform: translate(-50%, 14px) scale(.94); } to { opacity: 1; transform: translate(-50%, 0) scale(1); } }
@keyframes m-haken { from { transform: scale(.2) rotate(-25deg); opacity: 0; } to { transform: scale(1) rotate(0); opacity: 1; } }
@media (prefers-reduced-motion: reduce) {
  body.pro .m-knopf, body.pro .m-knopf:hover, body.pro .m-knopf:active, body.pro .m-stat:active, body.pro .m-kachel:active, body.pro .m-segm button:active { transform: none; }
  body.pro .m-toast, body.pro .m-toast .m-toast-ok, body.pro.m-arbeitet::after { animation: none; }
}
"""

# 0.36: Showcase aufgeräumt – Standort im Dock, nur fünf Hauptbereiche (Rest unter „Mehr“), flachere Kennzahlen
# 0.38: Theme „INNternat“ – Bahnschrift für Überschriften und Kennzahlen, Candara für Text, Türkis nur als Akzent
_INNTERNAT = """
body.pro.th-innternat .m-btitel, body.pro.th-innternat .m-pf-dtitel, body.pro.th-innternat .m-pf-titel,
body.pro.th-innternat .m-stat .z, body.pro.th-innternat .m-zahl, body.pro.th-innternat .m-tz-zahl,
body.pro.th-innternat .m-tz-titel, body.pro.th-innternat .m-tz-ab {
  font-family: var(--titel-schrift); }
body.pro.th-innternat .m-btitel { font-weight: 600; letter-spacing: .01em; }
body.pro.th-innternat .m-knopf.primaer { font-family: var(--titel-schrift); letter-spacing: .02em; }
"""


# 0.38.1: Laptop – unter 1200 px Fensterbreite wird die Seitenleiste automatisch schmal (Symbole mit Tooltip), damit
# Tabellen und Tageszentrale Platz haben; „Leiste einklappen“ braucht es dort nicht.
_LAPTOP = """

"""


CSS = "\n".join([_vars(t, m) for (t, m) in P] + [_typo(t) for t in TYPO] + [_PRO]
                + [_THEME_EIGEN, _DICHTE, _LAYOUTS, _FEED, _HAPTIK, _INNTERNAT, _LAPTOP])
