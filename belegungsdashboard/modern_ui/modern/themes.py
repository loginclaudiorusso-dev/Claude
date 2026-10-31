"""Darstellung der neuen Oberfläche – zwei Ebenen, sauber getrennt.

* **Layout** (Informationsarchitektur): Original-Zustand · Classic Grid · AI-Canvas · Showcase.
* **Theme** (nur Farben, Typografie, Radien): Original · inn-tegrativ · Linear Monochrome · Executive Obsidian ·
  Soft Nordic – jeweils hell oder dunkel (Original nur dunkel). Dazu Dichte (normal/kompakt) und schmale Leiste.

Der **Original-Zustand** setzt am ``<body>`` keine einzige Klasse – dann gilt ausschließlich das bisherige CSS, 1:1
wie vor dem Umbau. Alles Neue greift nur unter ``body.pro`` (plus ``lay-…``, ``th-…``, ``mod-…``, ``dichte-…``).
"""

from __future__ import annotations

from .stil import T as _ORIGINAL

LAYOUTS = {
    "original": ("Original-Zustand", "Bisheriges Design und Layout – exakt wie vorher", "restart_alt"),
    "grid": ("Classic Enterprise Grid", "Einklappbare Seitenleiste, hohe Datendichte, volle Funktion", "view_sidebar"),
    "canvas": ("AI-Canvas & Prompt", "Zentrale Eingabe (Strg+K, /) filtert live – Antworten als Karten", "auto_awesome"),
    "showcase": ("Showcase", "Schwebendes Dock oben, großzügige Karten, viel Weißraum, Glas", "dashboard"),
}
THEMES = {
    "original": ("Original", "Die Farben des bisherigen Designs", "dunkel"),
    "inn": ("inn-tegrativ", "Corporate Deep Blue #183861 – ruhig und seriös", "hell"),
    "linear": ("Linear Monochrome", "Graustufen, messerscharfe Kanten, hohe Dichte", "dunkel"),
    "obsidian": ("Executive Obsidian", "Dunkler Obsidian mit Bronze- und Champagner-Akzenten", "dunkel"),
    "nordic": ("Soft Nordic", "Augenschonend: warme Slate- und Sandtöne", "hell"),
}
ALT = {"corporate": "inn", "bento": "obsidian", "editorial": "nordic"}      # Namen aus 0.8
STANDARD = {"layout": "original", "theme": "original", "modus": "dunkel", "dichte": "normal", "schmal": False,
            "vollbild": False, "notiz": ""}

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


P = {
    ("original", "dunkel"): _p("#0E0F12", "#15171C", "#1B1E24", "#262A32", "#323743", "#E6E8EC", "#A2A8B4", "#8A919D",
                               "#7C8CFF", "#0E0F12", "#94A2FF", "#94A2FF", "#F2706B", "#E9A15A", "#4CC38A", "#6E8BD8",
                               "#15171C", "#1B1E24", "#22252D", "#E6E8EC", "#E6E8EC", "#94A2FF", "#A2A8B4", "#848B98",
                               "#262A32", "#7C8CFF", status=_DUNKEL),
    ("inn", "hell"): _p("#f3f5f9", "#ffffff", "#eef2f7", "#dde3ec", "#c5cfdd", "#14213d", "#3b4a63", "#5b6880",
                        "#183861", "#ffffff", "#183861", "#0f2341", "#b42318", "#b54708", "#067647", "#1d4ed8",
                        "#183861", "#1f477a", "#0f2341", "#ffffff", "#ffffff", "#7fa7dc", "#c9d6ea", "#93a9c9",
                        "#0f2341", "#7fa7dc", kopf="#ffffff", status=_HELL, schatten="0 1px 2px rgba(16,24,40,.06)",
                        panel_schatten="-12px 0 32px rgba(16,24,40,.14)"),
    ("inn", "dunkel"): _p("#0b1320", "#101b2d", "#16243a", "#1f2f47", "#2b3f5e", "#e6edf7", "#b0bfd5", "#8798b2",
                          "#234d84", "#ffffff", "#7fa7dc", "#2c5c9c", "#f38b8b", "#f2b56b", "#5fd3a0", "#7fa7dc",
                          "#081326", "#0f2341", "#183861", "#ffffff", "#ffffff", "#9fc0ea", "#b9c8de", "#7d91b0",
                          "#0f2341", "#7fa7dc", status=_DUNKEL),
    ("linear", "dunkel"): _p("#0a0a0b", "#111113", "#18181b", "#232327", "#303036", "#ededef", "#a1a1aa", "#8b8b94",
                             "#ededef", "#0a0a0b", "#ededef", "#ffffff", "#f87171", "#fbbf24", "#4ade80", "#60a5fa",
                             "#0a0a0b", "#141416", "#1c1c1f", "#ededef", "#ededef", "#ededef", "#a1a1aa", "#6b6b73",
                             "#1c1c1f", "#ededef", status=_DUNKEL, panel_schatten="-1px 0 0 #232327"),
    ("linear", "hell"): _p("#ffffff", "#ffffff", "#f4f4f5", "#e4e4e7", "#d4d4d8", "#09090b", "#52525b", "#6b6b74",
                           "#18181b", "#ffffff", "#18181b", "#000000", "#b91c1c", "#a16207", "#15803d", "#1d4ed8",
                           "#fafafa", "#f4f4f5", "#e4e4e7", "#09090b", "#09090b", "#09090b", "#52525b", "#8a8a93",
                           "#e4e4e7", "#09090b", status=_HELL, panel_schatten="-1px 0 0 #e4e4e7"),
    ("obsidian", "dunkel"): _p("#0c0b0a", "#141311", "#1d1b18", "#2a2723", "#3a352f", "#f3eee6", "#c4b9a8", "#9a8f80",
                               "#c9a46a", "#17130d", "#e2c99a", "#d8b67f", "#e8857a", "#e0a85c", "#8fc79a", "#93b0d6",
                               "#0a0908", "#171512", "#201d19", "#f3eee6", "#f3eee6", "#e2c99a", "#b3a796", "#7c7266",
                               "#201d19", "#c9a46a", fls="#161513", status=_DUNKEL,
                               panel_schatten="-24px 0 60px rgba(0,0,0,.55)"),
    ("obsidian", "hell"): _p("#f7f3ec", "#fffdf9", "#efe8dc", "#e2d8c8", "#cdbfa8", "#1c1813", "#4a4136", "#6b5f50",
                             "#7a5a2b", "#ffffff", "#7a5a2b", "#64491f", "#a3271b", "#8f4f05", "#1f6b3a", "#2a4f8f",
                             "#1c1813", "#2a241c", "#3a3227", "#f3eee6", "#f3eee6", "#e2c99a", "#c4b9a8", "#8f8474",
                             "#2a241c", "#c9a46a", kopf="#fffdf9", status=_HELL,
                             schatten="0 1px 2px rgba(28,24,19,.06)", panel_schatten="-12px 0 32px rgba(28,24,19,.16)"),
    ("nordic", "hell"): _p("#f3efe7", "#fbf9f5", "#ece6da", "#ddd5c6", "#c7bca8", "#2b3540", "#4d5966", "#636e7a",
                           "#4a6878", "#ffffff", "#3f5b6a", "#3f5b6a", "#a33a3a", "#94600f", "#3b7356", "#3f6290",
                           "#e9e2d5", "#e0d7c7", "#d6cbb6", "#2b3540", "#2b3540", "#3f5b6a", "#4d5966", "#6d7884",
                           "#d6ccba", "#4a6878", kopf="#fbf9f5", status=_HELL,
                           schatten="0 1px 2px rgba(43,53,64,.05)", panel_schatten="-12px 0 32px rgba(43,53,64,.14)"),
    ("nordic", "dunkel"): _p("#1d2227", "#232a30", "#2c343c", "#343d46", "#44505b", "#e7e2d8", "#bdb6a8", "#9a9487",
                             "#8fb3c2", "#12181c", "#a9c6d2", "#a9c6d2", "#e39a8f", "#e0b073", "#9cc9a8", "#9fb8dc",
                             "#191d21", "#232a30", "#2c343c", "#e7e2d8", "#e7e2d8", "#a9c6d2", "#bdb6a8", "#8a8478",
                             "#2c343c", "#8fb3c2", fls="#252c33", status=_DUNKEL),
}

# Typografie und Kanten je Theme (unabhängig von hell/dunkel)
TYPO = {
    "original": dict(r="8px", r2="12px", fs="13.5px", zeile="44px", kante="none",
                     schrift='"Inter", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif',
                     titel_schrift='"Inter", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif'),
    "inn": dict(r="4px", r2="6px", fs="13.5px", zeile="44px", kante="3px solid var(--akzent-hell)",
                schrift='"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif',
                titel_schrift='"Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif'),
    "linear": dict(r="3px", r2="4px", fs="12.5px", zeile="34px", kante="none",
                   schrift='"Inter", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif',
                   titel_schrift='"Inter", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif'),
    "obsidian": dict(r="6px", r2="14px", fs="13.5px", zeile="46px", kante="1px solid color-mix(in srgb, var(--akzent) 45%, transparent)",
                     schrift='"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif',
                     titel_schrift='"Segoe UI Variable Display", "Georgia", serif'),
    "nordic": dict(r="8px", r2="12px", fs="14px", zeile="48px", kante="none",
                   schrift='"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif',
                   titel_schrift='"Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif'),
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


def bereinigen(d: dict | None) -> dict:
    """Gespeicherten Zustand prüfen und ältere Namen (0.8) übernehmen. Unbekanntes → Original-Zustand."""
    d = dict(d or {})
    erg = dict(STANDARD)
    if "layout" not in d and d.get("theme") not in (None, "original"):       # Stand 0.8: theme + nav
        d["layout"] = {"oben": "showcase"}.get(d.get("nav"), "grid")
        d["schmal"] = d.get("nav") == "schmal"
    theme = ALT.get(d.get("theme"), d.get("theme"))
    erg["layout"] = d.get("layout") if d.get("layout") in LAYOUTS else "original"
    erg["theme"] = theme if theme in THEMES else "original"
    if erg["layout"] == "original":
        erg["theme"] = "original"
    erg["modus"] = d.get("modus") if d.get("modus") in modi(erg["theme"]) else THEMES[erg["theme"]][2]
    erg["dichte"] = "kompakt" if d.get("dichte") == "kompakt" else "normal"
    erg["schmal"] = bool(d.get("schmal"))
    erg["vollbild"] = bool(d.get("vollbild"))
    erg["notiz"] = str(d.get("notiz") or "")[:5000]
    return erg


def farben(d: dict | str) -> dict:
    """Farben für Diagramme (ECharts bekommt Farben aus Python, nicht aus dem CSS)."""
    if isinstance(d, str):
        d = {"layout": "grid" if d != "original" else "original", "theme": d}
    d = bereinigen(d)
    if d["layout"] == "original":
        return {**_ORIGINAL, "fls": _ORIGINAL["fl"], "hell": False}
    v = P[(d["theme"], d["modus"])]
    return {"text": v["text"], "text2": v["text2"], "text3": v["text3"], "rand": v["rand"], "rand2": v["rand2"],
            "fl2": v["fl2"], "akzent": v["akzent_hell"], "blau": v["blau"], "gruen": v["gruen"], "orange": v["orange"],
            "rot": v["rot"], "bg": v["bg"], "fls": v["fls"], "hell": d["modus"] == "hell"}


AKTIV: dict = dict(STANDARD)      # aktueller Zustand (eine Oberfläche je Programm – reicht als Modulwert)


def klassen(d: dict) -> list[str]:
    """Klassen am <body>. Im Original-Zustand keine – damit gilt ausschließlich das bisherige CSS."""
    d = bereinigen(d)
    if d["layout"] == "original":
        return []
    k = ["pro", f"lay-{d['layout']}", f"th-{d['theme']}", f"mod-{d['modus']}"]
    if d["modus"] == "hell":
        k.append("hell")
    if d["dichte"] == "kompakt":
        k.append("dichte-kompakt")
    if d["schmal"] or d["layout"] == "canvas":
        k.append("nav-schmal")
    return k


ALLE_KLASSEN = (["pro", "hell", "nav-schmal", "dichte-kompakt", "mod-hell", "mod-dunkel"] + [f"lay-{x}" for x in LAYOUTS]
                + [f"th-{t}" for t in THEMES])

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
body.pro .m-nav { background: var(--chrome); border-right: 1px solid var(--chrome-rand); backdrop-filter: none; -webkit-backdrop-filter: none;
  transition: width .2s ease, padding .2s ease; }
body.pro .m-marke { color: var(--chrome-text); }
body.pro .m-logo { background: var(--akzent); color: var(--akzent-text); border-radius: var(--r); box-shadow: none; }
body.pro .m-navgruppe { color: var(--chrome-text3); font-size: 11px; font-weight: 600; letter-spacing: .04em; }
body.pro .m-navpunkt { color: var(--chrome-text2); border-radius: var(--r); }
body.pro button.m-navpunkt:hover { background: var(--chrome-hover); color: var(--chrome-text); }
body.pro .m-navpunkt.aktiv, body.pro button.m-navpunkt.aktiv:hover { background: var(--chrome-aktiv); color: var(--chrome-aktiv-text); }
body.pro .m-navpunkt.aktiv::before { background: var(--chrome-strich); width: 2px; }
body.pro .m-navpunkt.aktiv .material-icons, body.pro .m-navpunkt.aktiv .q-icon { color: var(--chrome-aktiv-icon); }
body.pro .m-navfuss { color: var(--chrome-text3); }
body.pro .m-suche { border-color: var(--chrome-rand) !important; }
body.pro .m-nav .m-taste { color: var(--chrome-text3); border-color: var(--chrome-rand); }
body.pro .m-nav .m-zahl { background: var(--chrome-aktiv); color: var(--chrome-text); }
body.pro .m-nav .m-zahl.rot { background: var(--s-krit-fg); color: #fff; }
body.pro .m-navklapp { display: flex; }

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
body.pro .m-kachel.teilweise, body.pro .m-legende i.teilweise { background: var(--fls); border: 1px dashed var(--s-ok-fg); }
body.pro .m-kachel.belegt, body.pro .m-legende i.belegt, body.pro .m-zs-b.belegt, body.pro .m-zs-punkt { background: var(--s-blau-bg); color: var(--s-blau-fg); box-shadow: inset 0 0 0 1px var(--s-blau-bd); }
body.pro .m-kachel.geplant, body.pro .m-legende i.geplant, body.pro .m-zs-b.geplant, body.pro .m-zs-punkt.geplant { background: var(--fls); color: var(--s-akzent-fg); box-shadow: none; border: 1.5px dashed var(--s-akzent-fg); box-sizing: border-box; }
body.pro .m-kachel.gesperrt, body.pro .m-legende i.gesperrt, body.pro .m-zs-b.gesperrt, body.pro .m-zs-punkt.gesperrt { background: repeating-linear-gradient(135deg, var(--s-neutral-bg) 0 5px, var(--fl2) 5px 10px); color: var(--s-neutral-fg); box-shadow: inset 0 0 0 1px var(--s-neutral-bd); }
body.pro .m-zs-b.konflikt, body.pro .m-legende i.konflikt { background: var(--s-krit-bg); color: var(--s-krit-fg); box-shadow: inset 0 0 0 1px var(--s-krit-fg); }
body.pro .m-kachel.unbew { border: 2px solid var(--s-krit-fg); }
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
body.pro.nav-schmal .m-nav { width: 60px; padding: 14px 8px; }
body.pro.nav-schmal .m-marke { padding: 4px 2px 14px; justify-content: center; }
body.pro.nav-schmal .m-marke > :not(.m-logo) { display: none; }
body.pro.nav-schmal .m-nav .m-navgruppe { font-size: 0 !important; height: 1px; padding: 0; margin: 10px 6px; background: var(--chrome-rand); }
body.pro.nav-schmal .m-navpunkt { justify-content: center; padding: 6px 0; position: relative; }
body.pro.nav-schmal .m-nav .m-navpunkt > :not(.q-icon):not(.m-zahl) { display: none; }
body.pro.nav-schmal .m-navpunkt .m-zahl { position: absolute; top: 2px; right: 4px; margin: 0 !important; min-width: 16px; height: 16px; font-size: 10px; padding: 0 4px; }
body.pro.nav-schmal .m-navpunkt.aktiv::before { left: -8px; }
body.pro.nav-schmal .m-navfuss { display: none; }
body.pro.nav-schmal .m-navklapp .q-icon { transform: rotate(180deg); }

/* Navigation einklappen */
body.pro .m-navklapp { margin-top: 6px; align-items: center; gap: 10px; color: var(--chrome-text3); }
body.pro.nav-schmal .m-navklapp { justify-content: center; }
"""

_THEME_EIGEN = """
/* Theme-Feinheiten (nur Optik, keine Struktur) */
body.pro .m-stat, body.pro .m-block { border-top: var(--kante); }
body.pro.th-inn .m-titel, body.pro.th-inn .m-btitel { color: var(--akzent-hell); }
body.pro.th-inn .m-tkopf > div { text-transform: uppercase; font-size: 10.5px; letter-spacing: .06em; }
body.pro.th-inn.mod-hell .m-segm button.an { background: var(--akzent); color: var(--akzent-text); box-shadow: none; }
body.pro.th-inn .m-nav .m-logo, body.pro.th-inn .m-topnav .m-logo { background: #ffffff; color: #183861; }
body.pro.th-linear .m-stat .s { color: var(--text3) !important; }
body.pro.th-linear .m-ksymbol { --c: var(--text2) !important; }
body.pro.th-linear .m-knopf { height: 28px; font-size: 12.5px; }
body.pro.th-obsidian .m-titel { font-weight: 500; letter-spacing: .01em; }
body.pro.th-obsidian .m-btitel { font-family: var(--titel-schrift); font-weight: 500; letter-spacing: .01em; font-size: 15px; }
body.pro.th-obsidian .m-stat .l, body.pro.th-obsidian .m-navgruppe, body.pro.th-obsidian .m-tkopf > div { text-transform: uppercase;
  letter-spacing: .12em; font-size: 10.5px; }
body.pro.th-obsidian .m-stat .z { font-weight: 500 !important; }
body.pro.th-obsidian .m-logo { background: linear-gradient(135deg, #e2c99a, #9c7a45); color: #17130d; }
body.pro.th-nordic { line-height: 1.55; }
body.pro.th-nordic .m-stat .z { font-weight: 600; }
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
body.pro.dichte-kompakt .m-navpunkt { height: 28px; }
body.pro.dichte-kompakt .m-kachel { width: 40px; height: 26px; }
"""

_LAYOUTS = """
/* ===== Layout: Classic Enterprise Grid – Seitenleiste wie gewohnt, einklappbar (Grundschicht) ===== */

/* ===== Layout: AI-Canvas & Prompt ===== */
.m-prompt-zeile, .m-topnav, .m-navklapp, .m-cv-start { display: none; }
body.lay-canvas .m-prompt-zeile { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 18px 24px 10px; flex: none;
  background: var(--bg); border-bottom: 1px solid var(--rand); }
body.lay-canvas .m-prompt { width: min(760px, 100%); display: flex; align-items: center; gap: 10px; padding: 4px 8px 4px 16px;
  background: var(--fls); border: 1px solid var(--rand2); border-radius: 16px; box-shadow: 0 8px 28px rgba(0,0,0,.18);
  transition: border-color .15s, box-shadow .15s; }
body.lay-canvas .m-prompt:focus-within { border-color: var(--akzent-hell); box-shadow: 0 0 0 4px color-mix(in srgb, var(--akzent-hell) 22%, transparent), 0 8px 28px rgba(0,0,0,.18); }
body.lay-canvas .m-prompt > .q-icon { color: var(--akzent-hell); font-size: 22px; }
body.lay-canvas .m-prompt .q-field { flex: 1; }
body.lay-canvas .m-prompt .q-field__native { font-size: 16px !important; color: var(--text) !important; }
body.lay-canvas .m-prompt .q-field__control:before, body.lay-canvas .m-prompt .q-field__control:after { border: 0 !important; }
body.lay-canvas .m-prompt .q-field--focused .q-field__control { box-shadow: none; }
body.lay-canvas .m-prompt .m-taste { flex: none; }
body.lay-canvas .m-vorschlaege { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
body.lay-canvas .m-vorschlag { font: inherit; font-size: 12px; cursor: pointer; color: var(--text2); background: transparent;
  border: 1px solid var(--rand2); border-radius: 999px; padding: 3px 10px; transition: background .15s, color .15s; }
body.lay-canvas .m-vorschlag:hover { background: var(--fl2); color: var(--text); }
body.lay-canvas .m-kopf { min-height: 44px; }
body.pro .m-cv { padding: 18px 24px 40px; display: flex; flex-direction: column; gap: 18px; max-width: 1400px; margin: 0 auto; width: 100%;
  animation: m-cv-rein .25s ease-out both; }
@keyframes m-cv-rein { from { opacity: 0; transform: translateY(6px); } }
body.pro .m-cv-verstanden { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; color: var(--text3); font-size: 12.5px; }
body.pro .m-cv-tag { padding: 2px 8px; border-radius: 999px; background: var(--fl2); color: var(--text); border: 1px solid var(--rand); font-size: 12px; }
body.pro .m-cv-gruppe { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
body.pro .m-cv-gruppe .m-btitel { font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: var(--text3); }
body.pro .m-cv-raster { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; }
body.pro .m-cv-raster.zahlen { grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); }
body.pro .m-cv-karte { font: inherit; color: var(--text); text-align: left; cursor: pointer; display: flex; flex-direction: column; gap: 6px;
  padding: 14px 16px; border-radius: var(--r2); background: var(--fl); border: 1px solid var(--rand); transition: border-color .15s, background .15s; }
body.pro .m-cv-karte:hover { border-color: var(--akzent-hell); background: var(--fl2); }
body.pro .m-cv-karte .z { font-size: 28px; font-weight: 600; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
body.pro .m-cv-karte .k { display: flex; align-items: center; gap: 8px; min-width: 0; }
body.pro .m-cv-karte .k .m-name { flex: 1; }
body.pro .m-cv-leer { color: var(--text3); padding: 30px 0; text-align: center; }

/* ===== Layout: Showcase – schwebendes Dock, großzügige Karten, Glas ===== */
html:has(body.lay-showcase), body.lay-showcase, body.lay-showcase .q-layout, body.lay-showcase .q-page-container {
  background: radial-gradient(1100px 700px at 85% -10%, color-mix(in srgb, var(--akzent-hell) 10%, transparent), transparent 60%),
              radial-gradient(900px 600px at -10% 110%, color-mix(in srgb, var(--blau) 7%, transparent), transparent 60%), var(--bg) !important;
  background-attachment: fixed !important; }
body.lay-showcase .m-nav { display: none; }
body.lay-showcase .m-topnav { display: flex; align-items: center; gap: 2px; align-self: center; margin: 14px auto 4px; padding: 6px 8px;
  max-width: calc(100% - 32px); overflow-x: auto; scrollbar-width: none; border-radius: 18px; flex: none;
  background: color-mix(in srgb, var(--fls) 78%, transparent); border: 1px solid var(--rand);
  backdrop-filter: blur(24px) saturate(1.3); -webkit-backdrop-filter: blur(24px) saturate(1.3); box-shadow: 0 12px 34px rgba(0,0,0,.22); }
body.lay-showcase .m-topnav .m-marke { padding: 0 10px 0 4px; }
body.lay-showcase .m-topnav .m-navpunkt { width: auto; height: 34px; padding: 0 12px; gap: 7px; flex: none; display: inline-flex; align-items: center;
  border-radius: 12px; color: var(--text2); }
body.lay-showcase .m-topnav .m-navpunkt:hover { background: var(--fl2); color: var(--text); }
body.lay-showcase .m-topnav .m-navpunkt.aktiv { background: var(--akzent); color: var(--akzent-text); }
body.lay-showcase .m-topnav .m-navpunkt.aktiv .q-icon { color: var(--akzent-text); }
body.lay-showcase .m-topnav .m-navpunkt.aktiv::before { display: none; }
body.lay-showcase .m-topnav .m-navpunkt .q-icon { font-size: 18px; }
body.lay-showcase .m-topnav .m-trenner { width: 1px; height: 20px; background: var(--rand); margin: 0 4px; flex: none; }
body.lay-showcase .m-topnav .m-suche { margin: 0 0 0 6px; border: 1px solid var(--rand) !important; }
body.lay-showcase .m-topnav .m-zahl { margin-left: 2px !important; }
body.lay-showcase .m-kopf, body.lay-showcase .m-leiste { background: transparent; border-bottom: 0;
  padding-left: max(28px, calc((100% - 1360px) / 2)); padding-right: max(28px, calc((100% - 1360px) / 2)); }
body.lay-showcase .m-kopf { padding-top: 18px; min-height: 64px; }
body.lay-showcase .m-titel { font-size: 28px; font-weight: 600; letter-spacing: -0.025em; }
body.lay-showcase .m-leiste { padding-bottom: 18px; }
body.lay-showcase .m-stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 14px; flex: 1 1 100%; }
body.lay-showcase .m-stat { padding: 16px 18px; border-radius: 18px; gap: 10px; background: color-mix(in srgb, var(--fl) 80%, transparent);
  backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); }
body.lay-showcase .m-stat .l { order: -1; text-transform: uppercase; font-size: 10.5px; letter-spacing: .08em; font-weight: 600; }
body.lay-showcase .m-stat .z { font-size: 32px !important; font-weight: 500 !important; letter-spacing: -0.035em !important; }
body.lay-showcase .m-inhalt > * { animation: m-cv-rein .35s ease-out both; }
body.lay-showcase .m-inhalt { padding: 0 max(28px, calc((100% - 1360px) / 2)) 32px; }
body.lay-showcase .m-block, body.lay-showcase .m-khaus, body.lay-showcase .m-kpikarte, body.lay-showcase .m-willkommen, body.lay-showcase .m-karte {
  border-radius: 22px; background: color-mix(in srgb, var(--fl) 80%, transparent); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
  box-shadow: 0 10px 30px rgba(0,0,0,.12); }
body.lay-showcase .m-block, body.lay-showcase .m-willkommen { padding: 24px 26px; }
body.lay-showcase .m-btitel { font-size: 17px; font-weight: 600; letter-spacing: -0.01em; }
body.lay-showcase .m-heute, body.lay-showcase .m-zwei { gap: 20px; padding: 6px 0 24px; }
body.lay-showcase .m-kpis { padding: 6px 0 0; gap: 16px; }
body.lay-showcase .m-heute-rechts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; align-items: start; }
body.lay-showcase .m-heute-rechts > .m-block:first-child, body.lay-showcase .m-heute-rechts > .m-block:nth-child(2) { grid-column: 1 / -1; }
@media (max-width: 1250px) { body.lay-showcase .m-heute-rechts { grid-template-columns: 1fr; } }
body.lay-showcase .m-inhalt > .m-tkopf { border-radius: 18px 18px 0 0; background: var(--fls); border: 1px solid var(--rand); margin-top: 6px; }
body.lay-showcase .m-inhalt > .m-zeile { background: color-mix(in srgb, var(--fl) 85%, transparent); border-left: 1px solid var(--rand); border-right: 1px solid var(--rand); }
body.lay-showcase .m-inhalt > .m-zeile:last-child { border-radius: 0 0 18px 18px; }
body.lay-showcase .m-khaus { margin: 8px 0 18px; }
body.lay-showcase .m-haeuser { padding: 6px 0 18px; }
body.lay-showcase .m-segm { border-radius: 12px; } body.lay-showcase .m-segm button { border-radius: 9px; }
body.lay-showcase .m-knopf.primaer { border-radius: 999px; padding: 0 18px; }
body.lay-showcase .m-center, body.lay-showcase .m-center.offen { border-radius: 22px 0 0 22px; background: color-mix(in srgb, var(--fls) 92%, transparent);
  backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); }
@media (prefers-reduced-motion: reduce) { body.lay-showcase .m-inhalt > *, body.pro .m-cv { animation: none; } }
"""

_TOOLBAR = """
/* ===== Schwebende Werkzeugleiste (in jedem Zustand, eigene neutrale Optik) ===== */
.m-tb { position: fixed; right: 24px; bottom: 24px; z-index: 60; display: flex; align-items: center; gap: 8px; padding: 8px;
  border-radius: 16px; background: rgba(9,9,11,.86); border: 1px solid rgba(63,63,70,.55); box-shadow: 0 20px 50px rgba(0,0,0,.45);
  backdrop-filter: blur(28px); -webkit-backdrop-filter: blur(28px); transition: opacity .25s, padding .2s, gap .2s; color: #d4d4d8; }
.m-tb-k { font: inherit; width: 34px; height: 34px; border-radius: 10px; border: 0; background: transparent; color: #d4d4d8; cursor: pointer;
  display: grid; place-items: center; flex: none; transition: background .15s, color .15s; }
.m-tb-k:hover { background: rgba(255,255,255,.1); color: #fff; }
.m-tb-k.an { background: rgba(255,255,255,.14); color: #fff; }
.m-tb-k.aus { opacity: .35; cursor: default; }
.m-tb-k .q-icon { font-size: 19px; }
.m-tb-k.reset { color: #fda4af; } .m-tb-k.reset:hover { background: rgba(244,63,94,.18); color: #fecdd3; }
.m-tb-t { width: 1px; height: 22px; background: rgba(82,82,91,.6); flex: none; }
.m-tb:not(.wach):not(.fest):not(:hover):not(:focus-within) { opacity: .55; padding: 6px; gap: 0; }
.m-tb:not(.wach):not(.fest):not(:hover):not(:focus-within) > :not(.m-tb-griff) { display: none; }
.m-tb.fest .m-tb-griff { background: rgba(255,255,255,.14); color: #fff; }
.m-tb-menue, body .q-menu.m-tb-menue { background: rgba(24,24,27,.96) !important; color: #e4e4e7 !important;
  border: 1px solid rgba(63,63,70,.6) !important; border-radius: 12px !important; padding: 6px; min-width: 220px; backdrop-filter: blur(24px); }
.m-tb-menue .q-item, body .q-menu.m-tb-menue .q-item, body .q-menu.m-tb-menue .q-item__label { color: #e4e4e7 !important;
  border-radius: 8px; min-height: 34px; }
.m-tb-menue .q-item:hover, body .q-menu.m-tb-menue .q-item:hover { background: rgba(255,255,255,.08) !important; }
body .q-menu.m-tb-menue textarea { color: #e4e4e7 !important; }
body .q-menu.m-tb-menue .q-field__control:before { border-color: rgba(82,82,91,.8) !important; }
.m-tb-menue .q-item.disabled, .m-tb-menue .q-item--disabled { opacity: .4 !important; }
.m-tb-menue .m-mgruppe, body .q-menu.m-tb-menue .m-mgruppe { color: #a1a1aa !important; }
.m-tb-menue .m-zweite, body .q-menu.m-tb-menue .m-zweite { color: #a1a1aa !important; }
.m-tb-menue .m-mhaken { color: #71717a !important; } .m-tb-menue .m-mhaken.an { color: #e4e4e7 !important; }
.m-tb-notiz { width: 300px; padding: 10px; display: flex; flex-direction: column; gap: 6px; }
.m-tb-notiz textarea { color: #e4e4e7 !important; min-height: 160px; font-size: 13px; line-height: 1.5; }
@media print { .m-tb { display: none; } }
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
body:has(.m-center.offen) .m-tb { opacity: 0 !important; pointer-events: none !important; transform: translateY(8px); }
@keyframes m-welle { from { transform: scaleY(.45); } to { transform: scaleY(1); } }
"""

# Haptik (0.22): Eingaben bekommen Gewicht – Knöpfe geben beim Drücken spürbar nach (wie eine Taste), während des
# Speicherns läuft oben ein schmaler Balken, und die Bestätigung rastet sichtbar ein. Nur in den Layouts (body.pro);
# bei „Bewegung reduzieren“ (System) bleibt nur der Farbwechsel.
_HAPTIK = """
body.pro .m-knopf, body.pro .m-navpunkt, body.pro .m-stat, body.pro .m-segm button, body.pro .m-kachel,
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
body.pro .m-navpunkt:active, body.pro .m-segm button:active, body.pro .m-chip:active, body.pro .m-neu:active,
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
  body.pro .m-knopf, body.pro .m-knopf:hover, body.pro .m-knopf:active, body.pro .m-stat:active, body.pro .m-kachel:active,
  body.pro .m-navpunkt:active, body.pro .m-segm button:active { transform: none; }
  body.pro .m-toast, body.pro .m-toast .m-toast-ok, body.pro.m-arbeitet::after { animation: none; }
}
"""

# 0.36: Showcase aufgeräumt – Standort im Dock, nur fünf Hauptbereiche (Rest unter „Mehr“), flachere Kennzahlen
_SHOWCASE_RUHIG = """
body.lay-showcase .m-topnav .m-dock-standort { font: inherit; font-weight: 600; color: var(--text); background: transparent;
  border: 0; border-radius: 10px; height: 34px; padding: 0 8px 0 4px; gap: 8px; display: inline-flex; align-items: center;
  cursor: pointer; width: auto; margin: 0; }
body.lay-showcase .m-topnav .m-dock-standort:hover { background: var(--fl2); }
body.lay-showcase .m-topnav .m-dock-standort .m-standort-name { font-size: 13px; color: var(--text); }
body.lay-showcase .m-topnav .m-nur-symbol { padding: 0 10px; }
body.lay-showcase .m-topnav .m-punkt-neu { width: 7px; height: 7px; border-radius: 50%; background: var(--akzent); flex: none; }
body.lay-showcase .m-stats { grid-template-columns: repeat(auto-fill, minmax(132px, 1fr)); gap: 10px; }
body.lay-showcase .m-stat { padding: 10px 14px; border-radius: 14px; gap: 4px; }
body.lay-showcase .m-stat .l { font-size: 10px; letter-spacing: .06em; }
body.lay-showcase .m-stat .z { font-size: 22px !important; }
body.lay-showcase .m-leiste { padding-bottom: 12px; }
"""


CSS = "\n".join([_vars(t, m) for (t, m) in P] + [_typo(t) for t in TYPO] + [_PRO]
                + [_THEME_EIGEN, _DICHTE, _LAYOUTS, _TOOLBAR, _FEED, _HAPTIK, _SHOWCASE_RUHIG])
