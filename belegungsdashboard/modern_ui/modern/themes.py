"""Designs (Themes) der neuen Oberfläche.

* ``original`` ist das bisherige Design – dafür gibt es hier **keine einzige Regel**. Alles Neue greift nur unter
  ``body.pro`` bzw. ``body.th-<name>``; ohne diese Klassen bleibt das Aussehen 1:1 wie in 0.7.
* Die vier neuen Designs teilen sich eine gemeinsame, ruhige Grundschicht (``body.pro``: keine Glows, keine
  Verläufe, klare Kanten) und unterscheiden sich in Farben, Dichte, Typografie und Layout (``body.th-…``).
* Navigation (nur in den neuen Designs): Seitenleiste, schmale Seitenleiste (nur Symbole) oder Leiste oben.
"""

from __future__ import annotations

from .stil import T as _ORIGINAL

THEMES = {
    "original": ("Original", "Das bisherige Design – unverändert"),
    "corporate": ("inn-tegrativ Corporate", "Seriös und strukturiert: Navigation in inn-tegrativ Deep Blue, heller Arbeitsbereich"),
    "linear": ("Linear Monochrome", "Ultra-minimal und dicht: Graustufen, harte Kanten, maximal viele Zeilen"),
    "bento": ("Bento Modern", "Kärtchen im Raster, dezentes Glas, großzügige Typografie"),
    "editorial": ("High Contrast Editorial", "Barrierearm: warmes Papier, größte Schrift, stärkste Kontraste"),
}
HELL = {"corporate", "editorial"}
NAV = {"seite": "Seitenleiste", "schmal": "Schmale Seitenleiste (nur Symbole)", "oben": "Navigation oben"}

# ---------------------------------------------------------------------------------------
# Farben je Design
# ---------------------------------------------------------------------------------------

_STATUS_DUNKEL = {   # gedeckte Töne (950/50 Hintergrund · 400 Schrift · 800/50 Rand)
    "ok": ("rgba(2,44,34,.5)", "#34d399", "rgba(6,95,70,.5)"),
    "krit": ("rgba(76,5,25,.5)", "#fb7185", "rgba(159,18,57,.5)"),
    "warn": ("rgba(69,26,3,.5)", "#fbbf24", "rgba(146,64,14,.5)"),
    "blau": ("rgba(23,37,84,.5)", "#60a5fa", "rgba(30,64,175,.5)"),
    "akzent": ("rgba(30,27,75,.5)", "#a5b4fc", "rgba(55,48,163,.5)"),
    "neutral": ("rgba(39,39,42,.5)", "#a1a1aa", "rgba(63,63,70,.5)"),
}

V = {
    "corporate": dict(
        bg="#f3f5f9", fl="#ffffff", fls="#ffffff", fl2="#eef2f7", rand="#dde3ec", rand2="#c5cfdd",
        text="#14213d", text2="#3b4a63", text3="#5b6880",
        akzent="#183861", akzent_text="#ffffff", akzent_hell="#183861", akzent_hover="#0f2341",
        rot="#b42318", orange="#b54708", gruen="#067647", blau="#1d4ed8",
        chrome="#183861", chrome_hover="#1f477a", chrome_aktiv="#0f2341", chrome_text="#ffffff",
        chrome_aktiv_text="#ffffff", chrome_aktiv_icon="#7fa7dc",
        chrome_text2="#c9d6ea", chrome_text3="#93a9c9", chrome_rand="#0f2341", chrome_strich="#7fa7dc",
        kopf="#ffffff", r="4px", r2="6px", fs="13.5px", zeile="44px",
        schrift='"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif',
        titel_schrift='"Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif',
        schatten="0 1px 2px rgba(16,24,40,.06)", panel_schatten="-12px 0 32px rgba(16,24,40,.14)",
        fokus="#183861",
        status={"ok": ("#ecfdf3", "#067647", "#abefc6"), "krit": ("#fef3f2", "#b42318", "#fecdca"),
                "warn": ("#fffaeb", "#b54708", "#fedf89"), "blau": ("#eff4ff", "#1d4ed8", "#c7d7fe"),
                "akzent": ("#f4f3ff", "#5925dc", "#d9d6fe"), "neutral": ("#f2f4f7", "#475467", "#d0d5dd")},
    ),
    "linear": dict(
        bg="#0a0a0b", fl="#111113", fls="#111113", fl2="#18181b", rand="#232327", rand2="#303036",
        text="#ededef", text2="#a1a1aa", text3="#8b8b94",
        akzent="#ededef", akzent_text="#0a0a0b", akzent_hell="#ededef", akzent_hover="#ffffff",
        rot="#f87171", orange="#fbbf24", gruen="#4ade80", blau="#60a5fa",
        chrome="#0a0a0b", chrome_hover="#141416", chrome_aktiv="#1c1c1f", chrome_text="#ededef",
        chrome_aktiv_text="#ededef", chrome_aktiv_icon="#ededef",
        chrome_text2="#a1a1aa", chrome_text3="#6b6b73", chrome_rand="#1c1c1f", chrome_strich="#ededef",
        kopf="#0a0a0b", r="4px", r2="4px", fs="12.5px", zeile="34px",
        schrift='"Inter", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif',
        titel_schrift='"Inter", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif',
        schatten="none", panel_schatten="-1px 0 0 #232327", fokus="#ededef",
        status=_STATUS_DUNKEL,
    ),
    "bento": dict(
        bg="#0d0f13", fl="rgba(255,255,255,.045)", fls="#16191f", fl2="rgba(255,255,255,.08)",
        rand="rgba(255,255,255,.09)", rand2="rgba(255,255,255,.15)",
        text="#f1f3f6", text2="#b4bac6", text3="#8f97a6",
        akzent="#7cc4fa", akzent_text="#06121e", akzent_hell="#9bd2fb", akzent_hover="#9bd2fb",
        rot="#f58f8f", orange="#f5b971", gruen="#6ee7a8", blau="#8fb4ff",
        chrome="rgba(255,255,255,.025)", chrome_hover="rgba(255,255,255,.06)", chrome_aktiv="rgba(124,196,250,.12)",
        chrome_text="#f1f3f6", chrome_aktiv_text="#f1f3f6", chrome_aktiv_icon="#9bd2fb", chrome_text2="#b4bac6", chrome_text3="#7d8594", chrome_rand="rgba(255,255,255,.07)",
        chrome_strich="#7cc4fa", kopf="transparent", r="10px", r2="20px", fs="13.5px", zeile="48px",
        schrift='"Segoe UI Variable Text", "Inter", "Segoe UI", system-ui, sans-serif',
        titel_schrift='"Segoe UI Variable Display", "Inter", "Segoe UI", system-ui, sans-serif',
        schatten="0 1px 0 rgba(255,255,255,.04) inset", panel_schatten="-24px 0 48px rgba(0,0,0,.45)",
        fokus="#9bd2fb",
        status=_STATUS_DUNKEL,
    ),
    "editorial": dict(
        bg="#f6f2ea", fl="#fffdf8", fls="#fffdf8", fl2="#efe8da", rand="#cfc6b6", rand2="#9c9282",
        text="#1a1714", text2="#3a342d", text3="#4f4840",
        akzent="#1f2a37", akzent_text="#fffdf8", akzent_hell="#1f2a37", akzent_hover="#0f1720",
        rot="#9b1c1c", orange="#8a4b00", gruen="#14632f", blau="#1e40af",
        chrome="#efe8da", chrome_hover="#e3d9c6", chrome_aktiv="#1f2a37", chrome_text="#1a1714",
        chrome_aktiv_text="#fffdf8", chrome_aktiv_icon="#fffdf8",
        chrome_text2="#2b2620", chrome_text3="#4f4840", chrome_rand="#cfc6b6", chrome_strich="#b45309",
        kopf="#fffdf8", r="4px", r2="8px", fs="14.5px", zeile="50px",
        schrift='"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif',
        titel_schrift='"Iowan Old Style", "Charter", "Georgia", "Cambria", serif',
        schatten="none", panel_schatten="-10px 0 30px rgba(26,23,20,.18)", fokus="#b45309",
        status={"ok": ("#e3f1e6", "#0f4d24", "#2f7a45"), "krit": ("#fbe4e2", "#7f1d1d", "#b91c1c"),
                "warn": ("#fbeccf", "#5c3200", "#a16207"), "blau": ("#e1e9f7", "#1e3a8a", "#3b5bb5"),
                "akzent": ("#ece6f6", "#4c1d95", "#6d4bb3"), "neutral": ("#e9e4da", "#2e2a25", "#8a8174")},
    ),
}


def _vars(name: str) -> str:
    v = V[name]
    zeilen = [f"--{k.replace('_', '-')}: {w};" for k, w in v.items() if k != "status"]
    for st, (bg, fg, bd) in v["status"].items():
        zeilen += [f"--s-{st}-bg: {bg};", f"--s-{st}-fg: {fg};", f"--s-{st}-bd: {bd};"]
    # Namen, die das bisherige CSS benutzt – auf das Design umbiegen
    zeilen += ["--glas: var(--fls);", "--glas2: var(--fl);", "--glasrand: var(--rand);", "--mono: inherit;",
               "--violett: var(--akzent);", "--indigo: var(--akzent);"]
    return f"body.th-{name} {{ " + " ".join(zeilen) + " }"


def farben(name: str) -> dict:
    """Farben für Diagramme (ECharts bekommt Farben aus Python, nicht aus dem CSS)."""
    if name not in V:
        return dict(_ORIGINAL)
    v = V[name]
    solid = {"bento": ("#1c2028", "#2a2f39")}.get(name, (v["fl2"], v["rand2"]))
    return {"text": v["text"], "text2": v["text2"], "text3": v["text3"], "rand": v["rand"] if name != "bento" else "#262a33",
            "rand2": solid[1], "fl2": solid[0], "akzent": v["akzent"] if name not in ("linear", "editorial") else
            {"linear": "#d4d4d8", "editorial": "#1f2a37"}[name],
            "blau": v["blau"], "gruen": v["gruen"], "orange": v["orange"], "rot": v["rot"]}


AKTIV = "original"          # zuletzt gewähltes Design (eine Oberfläche je Programm – reicht als Modulwert)


def klassen(theme: str, nav: str) -> list[str]:
    """Klassen am <body>. Für „original“ keine – damit bleibt das bisherige Design unberührt."""
    if theme not in V:
        return []
    k = ["pro", f"th-{theme}"] + (["hell"] if theme in HELL else [])
    if nav == "schmal":
        k.append("nav-schmal")
    elif nav == "oben":
        k.append("nav-oben")
    return k


ALLE_KLASSEN = ["pro", "hell", "nav-schmal", "nav-oben"] + [f"th-{t}" for t in V]

# ---------------------------------------------------------------------------------------
# CSS – nur unter body.pro / body.th-…
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
body.pro .m-kachel.frei, body.pro .m-legende i.frei { background: var(--s-ok-bg); border: 1px solid var(--s-ok-bd); }
body.pro .m-kachel.teilweise, body.pro .m-legende i.teilweise { background: var(--fls); border: 1px dashed var(--s-ok-fg); }
body.pro .m-kachel.belegt, body.pro .m-legende i.belegt, body.pro .m-zs-b.belegt, body.pro .m-zs-punkt { background: var(--s-blau-bg); color: var(--s-blau-fg); box-shadow: inset 0 0 0 1px var(--s-blau-bd); }
body.pro .m-kachel.geplant, body.pro .m-legende i.geplant, body.pro .m-zs-b.geplant, body.pro .m-zs-punkt.geplant { background: var(--s-akzent-bg); color: var(--s-akzent-fg); box-shadow: inset 0 0 0 1px var(--s-akzent-bd); }
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
body.pro .m-menue, body.pro .m-popup, body.pro .q-menu { background: var(--fls) !important; border: 1px solid var(--rand2); border-radius: var(--r) !important;
  color: var(--text); backdrop-filter: none; box-shadow: 0 8px 24px rgba(0,0,0,.18); }
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
body.pro .q-dialog__backdrop { background: rgba(0,0,0,.35) !important; }

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
body.pro.nav-schmal .m-navgruppe { font-size: 0; height: 1px; padding: 0; margin: 10px 6px; background: var(--chrome-rand); }
body.pro.nav-schmal .m-navpunkt { justify-content: center; padding: 6px 0; position: relative; }
body.pro.nav-schmal .m-nav .m-navpunkt > :not(.q-icon):not(.m-zahl) { display: none; }
body.pro.nav-schmal .m-navpunkt .m-zahl { position: absolute; top: 2px; right: 4px; margin: 0 !important; min-width: 16px; height: 16px; font-size: 10px; padding: 0 4px; }
body.pro.nav-schmal .m-navpunkt.aktiv::before { left: -8px; }
body.pro.nav-schmal .m-navfuss { display: none; }
body.pro.nav-schmal .m-navklapp .q-icon { transform: rotate(180deg); }

/* Navigation: oben (alle Punkte, Verwalten als Dropdown) */
.m-topnav, .m-navklapp { display: none; }
body.pro.nav-oben .m-nav { display: none; }
body.pro.nav-oben .m-topnav { display: flex; align-items: center; gap: 2px; padding: 0 14px; height: 46px; flex: none; background: var(--chrome);
  border-bottom: 1px solid var(--chrome-rand); overflow-x: auto; scrollbar-width: none; }
body.pro .m-topnav .m-marke { padding: 0 14px 0 2px; }
body.pro .m-topnav .m-navpunkt { width: auto; height: 32px; padding: 0 10px; gap: 7px; flex: none; display: inline-flex; align-items: center; }
body.pro .m-topnav .m-navpunkt .q-icon { font-size: 17px; }
body.pro .m-topnav .m-navpunkt.aktiv::before { left: 10px; right: 10px; top: auto; bottom: -7px; width: auto; height: 2px; border-radius: 2px 2px 0 0; }
body.pro .m-topnav .m-trenner { width: 1px; height: 20px; background: var(--chrome-rand); margin: 0 6px; flex: none; }
body.pro .m-topnav .m-suche { margin: 0 0 0 auto; border: 1px solid var(--chrome-rand) !important; }
body.pro .m-topnav .m-zahl { margin-left: 2px !important; }

/* Navigation einklappen */
body.pro .m-navklapp { margin-top: 6px; align-items: center; gap: 10px; color: var(--chrome-text3); }
body.pro.nav-schmal .m-navklapp { justify-content: center; }
"""

_EIGEN = {
    # ---- inn-tegrativ Corporate: Navy-Rahmen, heller, ruhiger Arbeitsbereich -------------------------
    "corporate": """
body.th-corporate .m-kopf { box-shadow: 0 1px 0 var(--rand); }
body.th-corporate .m-titel { font-size: 16px; color: var(--akzent); }
body.th-corporate .m-btitel { color: var(--akzent); font-weight: 600; }
body.th-corporate .m-tkopf > div { text-transform: uppercase; font-size: 10.5px; letter-spacing: .06em; }
body.th-corporate .m-stat { border-top: 3px solid var(--akzent); }
body.th-corporate .m-stat.an { border-color: var(--akzent); }
body.th-corporate .m-block { border-top: 3px solid var(--akzent); }
body.th-corporate .m-segm button.an { background: var(--akzent); color: var(--akzent-text); box-shadow: none; }
body.th-corporate .m-nav .m-logo, body.th-corporate .m-topnav .m-logo { background: #ffffff; color: var(--akzent); }
body.th-corporate .m-navgruppe { text-transform: uppercase; }
""",
    # ---- Linear Monochrome: dicht, harte Kanten, Graustufen ------------------------------------------
    "linear": """
body.th-linear .m-kopf { min-height: 44px; padding: 6px 16px; }
body.th-linear .m-leiste { padding: 8px 16px; gap: 8px; }
body.th-linear .m-titel { font-size: 13.5px; }
body.th-linear .m-knopf { height: 28px; padding: 0 10px; font-size: 12.5px; }
body.th-linear .m-segm button { height: 24px; font-size: 12px; padding: 0 9px; }
body.th-linear .m-stat { padding: 6px 10px; min-width: 104px; }
body.th-linear .m-stat .z { font-size: 18px !important; }
body.th-linear .m-stat .s { font-size: 14px; color: var(--text3); }
body.th-linear .m-stat .l { font-size: 11px; }
body.th-linear .m-zeile > div { padding: 3px 8px; }
body.th-linear .m-tkopf > div { padding: 6px 8px; font-size: 11px; }
body.th-linear .m-navpunkt { height: 30px; font-size: 12.5px; }
body.th-linear .m-nav { width: 196px; padding: 10px 8px; }
body.th-linear.nav-schmal .m-nav { width: 52px; }
body.th-linear .m-block { padding: 12px 14px; }
body.th-linear .m-heute, body.th-linear .m-zwei { gap: 12px; padding: 12px 16px; }
body.th-linear .m-karte { padding: 10px 12px; gap: 6px; }
body.th-linear .m-karte .k2, body.th-linear .m-karte .k3 { padding-left: 40px; }
body.th-linear .m-ksymbol { width: 28px; height: 28px; --c: var(--text2) !important; }
body.th-linear .m-ksymbol .q-icon { font-size: 16px; }
body.th-linear .m-kachel { width: 40px; height: 26px; font-size: 11px; }
body.th-linear .m-badge { height: 20px; font-size: 11px; }
body.th-linear .m-knopf.primaer:hover { background: #ffffff; }
body.th-linear .m-stat .s { color: var(--text3) !important; }
""",
    # ---- Bento Modern: Kärtchen im Raster, Soft-Glas, großzügige Typografie --------------------------
    "bento": """
html:has(body.th-bento), body.th-bento, body.th-bento .q-layout, body.th-bento .q-page-container {
  background: radial-gradient(1200px 700px at 85% -10%, rgba(124,196,250,.07), transparent 60%),
              radial-gradient(900px 600px at -10% 110%, rgba(110,231,168,.05), transparent 60%), var(--bg) !important;
  background-attachment: fixed !important; }
body.th-bento .m-nav { backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); }
body.th-bento .m-kopf, body.th-bento .m-leiste { border-bottom: 0; }
body.th-bento .m-kopf { padding: 16px 24px 8px; min-height: 60px; }
body.th-bento .m-titel { font-size: 22px; font-weight: 600; letter-spacing: -0.02em; }
body.th-bento .m-leiste { padding: 8px 24px 16px; }
body.th-bento .m-stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; flex: 1 1 100%; }
body.th-bento .m-stat { padding: 14px 16px; border-radius: 16px; backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); gap: 8px; }
body.th-bento .m-stat .l { order: -1; text-transform: uppercase; font-size: 10.5px; letter-spacing: .08em; font-weight: 600; }
body.th-bento .m-stat .z { font-size: 30px !important; font-weight: 500 !important; letter-spacing: -0.035em !important; }
body.th-bento .m-stat .s { width: 30px; height: 30px; border-radius: 10px; display: grid; place-items: center;
  background: color-mix(in srgb, var(--c) 14%, transparent); }
body.th-bento .m-block, body.th-bento .m-khaus, body.th-bento .m-kpikarte, body.th-bento .m-willkommen {
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); padding: 20px 22px; }
body.th-bento .m-btitel { font-size: 15.5px; font-weight: 600; letter-spacing: -0.01em; }
body.th-bento .m-heute { gap: 16px; padding: 8px 24px 24px; grid-template-columns: minmax(380px, 1.1fr) minmax(360px, 1fr); }
body.th-bento .m-heute-rechts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; align-items: start; }
body.th-bento .m-heute-rechts > .m-block:first-child, body.th-bento .m-heute-rechts > .m-block:nth-child(2) { grid-column: 1 / -1; }
@media (max-width: 1250px) { body.th-bento .m-heute-rechts { grid-template-columns: 1fr; } }
body.th-bento .m-heute-links { gap: 12px; }
body.th-bento .m-karte { border-radius: 16px; padding: 16px 18px; }
body.th-bento .m-zwei { gap: 16px; padding: 8px 24px 24px; }
body.th-bento .m-kpis { padding: 8px 24px 0; gap: 16px; }
body.th-bento .m-kpikarte { border-radius: 16px; }
body.th-bento .m-inhalt > .m-tkopf, body.th-bento .m-inhalt > .m-zeile { margin: 0 24px; }
body.th-bento .m-inhalt > .m-tkopf { border-radius: 14px 14px 0 0; background: var(--fls); border: 1px solid var(--rand); }
body.th-bento .m-inhalt > .m-zeile { background: var(--fl); border-left: 1px solid var(--rand); border-right: 1px solid var(--rand); }
body.th-bento .m-inhalt > .m-zeile:last-child { border-radius: 0 0 14px 14px; margin-bottom: 24px; }
body.th-bento .m-khaus { margin: 8px 24px 16px; }
body.th-bento .m-segm { border-radius: 12px; }
body.th-bento .m-segm button { border-radius: 9px; }
body.th-bento .m-knopf.primaer { border-radius: 999px; padding: 0 16px; }
body.th-bento .m-zkarte { border-radius: 12px; }
body.th-bento .m-center, body.th-bento .m-center.offen { background: rgba(22,25,31,.92); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
  border-radius: 20px 0 0 20px; }
body.th-bento .m-schleier { backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px); }
""",
    # ---- High Contrast Editorial: Papier, Serifen-Überschriften, größte Kontraste ---------------------
    "editorial": """
body.th-editorial { line-height: 1.55; }
body.th-editorial .m-titel { font-size: 21px; font-weight: 700; }
body.th-editorial .m-btitel, body.th-editorial .m-ckopf .m-titel, body.th-editorial .m-abschnitt { font-family: var(--titel-schrift); font-weight: 700; font-size: 17px; }
body.th-editorial .m-kopf { border-bottom: 2px solid var(--text); }
body.th-editorial .m-nav { border-right: 2px solid var(--text); }
body.th-editorial .m-navpunkt { font-weight: 500; }
body.th-editorial .m-navpunkt.aktiv::before { background: var(--chrome-strich); width: 4px; }
body.th-editorial .m-knopf { border-width: 1.5px; border-color: var(--text); font-weight: 600; }
body.th-editorial .m-knopf.leise { text-decoration: underline; text-underline-offset: 3px; }
body.th-editorial .m-badge, body.th-editorial .m-pille { border-width: 1.5px !important; font-weight: 700; }
body.th-editorial .m-stat { border: 1.5px solid var(--text); }
body.th-editorial .m-stat .l { color: var(--text2); font-size: 12.5px; }
body.th-editorial .m-stat .z { font-size: 26px !important; font-weight: 700 !important; }
body.th-editorial .m-segm { border: 1.5px solid var(--text); background: var(--fls); }
body.th-editorial .m-segm button.an { background: var(--akzent); color: var(--akzent-text); box-shadow: none; }
body.th-editorial .m-zeile { border-bottom: 1px solid var(--rand2); }
body.th-editorial .m-tkopf > div { color: var(--text); font-weight: 700; }
body.th-editorial .m-tkopf { border-bottom: 2px solid var(--text); }
body.th-editorial .m-zweite, body.th-editorial .m-mono { color: var(--text2); }
body.th-editorial .m-link { text-decoration: underline; text-underline-offset: 3px; }
body.th-editorial .m-karte { border-left-width: 6px; border-color: var(--rand2); }
body.th-editorial .m-karte.dringend { background: var(--s-krit-bg); }
body.th-editorial :focus-visible { outline: 3px solid var(--fokus) !important; outline-offset: 2px; }
body.th-editorial .m-kachel { font-weight: 700; }
body.th-editorial .m-block { border: 1.5px solid var(--rand2); }
""",
}

CSS = "\n".join([_vars(n) for n in V] + [_PRO] + list(_EIGEN.values()))
