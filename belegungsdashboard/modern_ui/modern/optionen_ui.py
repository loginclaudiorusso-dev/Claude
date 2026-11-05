"""Optionen-Dialog (0.66) wie „Datei → Optionen“ in Office: links die Kategorien, rechts die Einstellungen. Jede
Änderung wirkt sofort (Vorschau im Programm dahinter) und wird je PC gemerkt. Logik: ``darstellung_kern``,
``diagramm_stil``."""

from __future__ import annotations

from nicegui import ui

from . import darstellung_kern as dk, diagramm_stil, themes
from .ui_bausteine import attr, knopf

KATEGORIEN = {"farben": ("Farben & Design", "palette"), "anzeige": ("Anzeige & Schrift", "format_size"),
              "diagramme": ("Diagramme", "insert_chart"), "oberflaeche": ("Oberfläche", "space_dashboard"),
              "programm": ("Programm", "settings"), "zuruecksetzen": ("Zurücksetzen", "restart_alt")}


def _vorschau_option(d: dict) -> dict:
    """Kleines Beispieldiagramm mit erfundenen Werten: Ist, Prognose mit Spanne, Kapazität."""
    t = themes.farben(d)
    monate = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug"]
    ist = [62, 66, 71, 69, 74, None, None, None]
    prog = [None, None, None, None, 74, 77, 79, 76]
    unten = [None, None, None, None, 74, 72, 71, 67]
    breite = [None, None, None, None, 0, 10, 15, 18]
    achse = {"axisLine": {"lineStyle": {"color": t["rand2"]}}, "axisLabel": {"color": t["text3"]},
             "splitLine": {"lineStyle": {"color": t["rand"]}}}
    o = {"backgroundColor": "transparent", "textStyle": {"color": t["text2"]}, "tooltip": {"trigger": "axis"},
         "grid": {"left": 36, "right": 12, "top": 30, "bottom": 24},
         "legend": {"top": 0, "right": 6, "textStyle": {"color": t["text2"]}, "data": ["Ist", "Prognose", "Kapazität"]},
         "xAxis": {"type": "category", "data": monate, "boundaryGap": False, **achse},
         "yAxis": {"type": "value", "min": 50, **achse},
         "series": [
             {"name": "u", "type": "line", "data": unten, "stack": "band", "lineStyle": {"opacity": 0}, "symbol": "none"},
             {"name": "80 %-Spanne", "type": "line", "data": breite, "stack": "band", "lineStyle": {"opacity": 0},
              "symbol": "none", "areaStyle": {"color": t["akzent"], "opacity": .15}},
             {"name": "Ist", "type": "line", "data": ist, "symbol": "none", "color": t["text"],
              "lineStyle": {"color": t["text"], "width": 2}},
             {"name": "Prognose", "type": "line", "data": prog, "symbol": "none", "color": t["akzent"],
              "lineStyle": {"color": t["akzent"], "width": 2, "type": "dashed"}},
             {"name": "Kapazität", "type": "line", "data": [85] * 8, "symbol": "none", "color": t["rot"],
              "lineStyle": {"color": t["rot"], "width": 1, "type": "dotted"}}]}
    return diagramm_stil.anwenden(o, d)


def oeffnen(a, kategorie: str = "farben") -> None:
    ablage = getattr(a, "dialog_ablage", None)
    ctx = ablage if ablage is not None else ui.element("div")
    with ctx, ui.dialog() as dlg, ui.element("div").classes("m-opt"):
        with ui.element("div").classes("m-opt-kopf"):
            ui.label("Optionen").classes("m-opt-titel")
            ui.label("Darstellung dieses PCs – wirkt sofort und wird gemerkt").classes("m-opt-unter")
            ui.element("div").style("flex:1")
            knopf("", dlg.close, "leise", "close", "Schließen (Esc)")
        with ui.element("div").classes("m-opt-koerper"):
            links = ui.element("nav").classes("m-opt-nav")
            rechts = ui.element("section").classes("m-opt-inhalt")
        with ui.element("div").classes("m-opt-fuss"):
            ui.label("Statusfarben (rot, orange, grün) bleiben fest – sie tragen Bedeutung.").classes("m-opt-unter")
            ui.element("div").style("flex:1")
            knopf("OK", dlg.close, "primaer")
    zustand = {"k": kategorie if kategorie in KATEGORIEN else "farben"}

    async def setzen(**w):
        await a.design_setzen(**w)
        fuellen()

    def nav():
        links.clear()
        with links:
            for k, (t, icon) in KATEGORIEN.items():
                b = ui.element("button").classes("m-opt-navpunkt" + (" an" if k == zustand["k"] else ""))
                with b:
                    ui.icon(icon)
                    ui.label(t)
                b.on("click", lambda k=k: (zustand.update(k=k), fuellen()))

    def fuellen():
        nav()
        rechts.clear()
        d = a.design
        with rechts:
            {"farben": _farben, "anzeige": _anzeige, "diagramme": _diagramme, "oberflaeche": _oberflaeche,
             "programm": lambda a, d, s: _programm(a, dlg), "zuruecksetzen": _zurueck}[zustand["k"]](a, d, setzen)

    fuellen()
    dlg.on("hide", lambda: dlg.delete() if not dlg.is_deleted else None)
    dlg.open()


def _titel(text: str, unter: str = "") -> None:
    ui.label(text).classes("m-opt-abschnitt")
    if unter:
        ui.label(unter).classes("m-opt-unter").style("margin:-4px 0 8px")


def _wahl(optionen: dict, aktiv, bei, icons: dict | None = None) -> None:
    with ui.element("div").classes("m-opt-wahl"):
        for k, text in optionen.items():
            b = ui.element("button").classes("m-opt-chip" + (" an" if k == aktiv else ""))
            attr(b, aria_pressed=str(k == aktiv).lower())
            with b:
                if icons and k in icons:
                    ui.icon(icons[k])
                ui.label(text)
            b.on("click", lambda k=k: bei(k))


def _haken(text: str, an: bool, bei) -> None:
    b = ui.element("button").classes("m-opt-haken" + (" an" if an else ""))
    with b:
        ui.icon("check_box" if an else "check_box_outline_blank")
        ui.label(text)
    b.on("click", lambda: bei(not an))


def _farben(a, d: dict, setzen) -> None:
    office = d["layout"] == "office"
    if d["layout"] == "original":
        with ui.element("div").classes("m-opt-hinweis"):
            ui.label("Farben und Schrift gibt es in den weiteren Darstellungen. Am vertrautesten ist das Menüband.")
            knopf("Menüband einschalten", lambda: setzen(layout="office"), "primaer", "view_agenda")
    _titel("Design", "Hell oder dunkel – wie das Office-Design „Weiß“ bzw. „Schwarz“.")
    if len(themes.modi(d["theme"])) > 1:
        _wahl({"hell": "Hell", "dunkel": "Dunkel"}, d["modus"], lambda m: setzen(modus=m),
              {"hell": "light_mode", "dunkel": "dark_mode"})
    else:
        ui.label("Dieses Farbthema gibt es nur in einer Variante.").classes("m-opt-unter")
    _titel("Farbschema", "Akzentfarbe für Titelleiste, Symbole, Knöpfe und Diagramme.")
    with ui.element("div").classes("m-opt-schemata"):
        for k, (name, farbe, titel) in dk.FARBSCHEMATA.items():
            b = ui.element("button").classes("m-opt-schema" + (" an" if d["farbe"] == k else ""))
            attr(b, title=name)
            with b:
                with ui.element("span").classes("m-opt-muster"):
                    ui.element("i").style(f"background:{titel}")
                    ui.element("i").style(f"background:{farbe}")
                ui.label(name)
            b.on("click", lambda k=k: setzen(farbe=k))
    _titel("Akzentfarbe selbst wählen", "Wie in den Windows-Einstellungen: ein Feld anklicken oder eine eigene Farbe "
           "mischen. Zu helle Farben werden automatisch so weit abgedunkelt, dass Schrift lesbar bleibt.")
    with ui.element("div").classes("m-opt-felder"):
        for f in dk.FELDER:
            b = ui.element("button").classes("m-opt-feld" + (" an" if d["farbe"] == "eigen" and d["farbe_eigen"] == f else ""))
            b.style(f"background:{f}")
            attr(b, title=f, aria_label=f"Farbe {f}")
            b.on("click", lambda f=f: setzen(farbe="eigen", farbe_eigen=f))
    with ui.element("div").classes("m-opt-zeile"):
        eingabe = ui.color_input("Eigene Farbe (Hex)", value=d["farbe_eigen"]).props("dense outlined").style("width:220px")

        async def eigene(e):
            f = dk.hex_ok(e.value)
            if f and (f != d["farbe_eigen"] or d["farbe"] != "eigen"):
                await setzen(farbe="eigen", farbe_eigen=f)
        eingabe.on_value_change(eigene)
        c, _t = dk.akzent(d)
        echt = dk.lesbar(c, "#FFFFFF")
        if echt != c:
            ui.label(f"Für gute Lesbarkeit wird {c} als {echt} dargestellt.").classes("m-opt-unter")
    if office:
        _titel("Titelleiste", "Wie in Office: farbig, hell oder dunkel.")
        _wahl(dk.TITELLEISTE, d["titelleiste"], lambda t: setzen(titelleiste=t))


def _anzeige(a, d: dict, setzen) -> None:
    _titel("Zoom", "Vergrößert oder verkleinert den Inhalt (nicht das Menüband) – wie der Zoom-Regler in Office. "
           "Auch unten rechts in der Statusleiste.")
    with ui.element("div").classes("m-opt-zeile"):
        knopf("", lambda: setzen(zoom=dk.zoom_schritt(d["zoom"], -1)), "leise", "remove", "Verkleinern")
        regler = ui.slider(min=dk.ZOOM_MIN, max=dk.ZOOM_MAX, step=5, value=d["zoom"]).props("label-always").style("width:260px")
        regler.on("change", lambda e: setzen(zoom=int(regler.value)))
        knopf("", lambda: setzen(zoom=dk.zoom_schritt(d["zoom"], 1)), "leise", "add", "Vergrößern")
    _wahl({z: f"{z} %" for z in (75, 90, 100, 110, 125, 150)}, d["zoom"], lambda z: setzen(zoom=z))
    _titel("Schriftart", "Nur Schriften, die unter Windows vorhanden sind.")
    with ui.element("div").classes("m-opt-schriften"):
        for k, (name, fam) in dk.SCHRIFTEN.items():
            b = ui.element("button").classes("m-opt-schrift" + (" an" if d["schrift"] == k else ""))
            with b:
                ui.label(name).style(f"font-family:{fam}" if fam else "")
                ui.label("Anreise 07.11. · Zimmer 2-517 · 123 frei").classes("m-opt-unter").style(
                    f"font-family:{fam}" if fam else "")
            b.on("click", lambda k=k: setzen(schrift=k))
    _titel("Dichte")
    _wahl({"normal": "Normal", "kompakt": "Kompakt (mehr Zeilen)"}, d["dichte"], lambda x: setzen(dichte=x))
    if d["layout"] == "office":
        _titel("Menüband", "„Groß“ ist angenehm auf Touch-Bildschirmen und für große Monitore.")
        _wahl({False: "Normal", True: "Groß"}, d["band_gross"], lambda x: setzen(band_gross=x))


def _diagramme(a, d: dict, setzen) -> None:
    _titel("Diagrammtyp", "Gilt für Verläufe (Belegung, Prognose, Maßnahmen, Steuerung). Unsicherheitsbänder und die "
           "Kapazitätslinie bleiben, wie sie sind.")
    _wahl({k: t for k, (t, _i) in dk.DG_TYPEN.items()}, d["dg_typ"], lambda x: setzen(dg_typ=x),
          {k: i for k, (_t, i) in dk.DG_TYPEN.items()})
    _titel("Elemente")
    with ui.element("div").classes("m-opt-spalten"):
        _haken("Linien glätten", d["dg_glatt"], lambda x: setzen(dg_glatt=x))
        _haken("Datenpunkte zeigen", d["dg_punkte"], lambda x: setzen(dg_punkte=x))
        _haken(f"Datenbeschriftungen (bei bis zu {diagramm_stil.WERTE_MAX} Werten)", d["dg_werte"],
               lambda x: setzen(dg_werte=x))
        _haken("Gitternetzlinien", d["dg_gitter"], lambda x: setzen(dg_gitter=x))
        _haken("Animation", d["dg_anim"], lambda x: setzen(dg_anim=x))
    _titel("Legende")
    _wahl({"oben": "Oben", "unten": "Unten", "aus": "Keine"}, d["dg_legende"], lambda x: setzen(dg_legende=x))
    _titel("Vorschau", "Beispiel mit erfundenen Zahlen.")
    ui.echart(_vorschau_option(d)).classes("m-opt-chart")


def _oberflaeche(a, d: dict, setzen) -> None:
    from .menueband import LAYOUT_NAMEN

    _titel("Aufbau der Oberfläche", "Das Menüband ist für den Alltag gedacht. Die anderen Aufbauten sind Alternativen.")
    _wahl(LAYOUT_NAMEN, d["layout"], lambda k: setzen(layout=k))
    with ui.element("div").classes("m-opt-zeile"):
        from . import leitstand_ui

        knopf("Zur Leitstand-Workbench wechseln", lambda: leitstand_ui.umschalten(a), "", "view_quilt")
        ui.label("Strg+Umschalt+L wechselt hin und zurück.").classes("m-opt-unter")
    _titel("Bereiche", "Was nicht gebraucht wird, verschwindet aus dem Menüband – nur auf diesem PC.")
    _haken("Leitung anzeigen (Steuerung: Renovierung, Zeitplan, Finanzen)", d["leitung"], lambda x: setzen(leitung=x))


def _programm(a, dlg) -> None:
    """0.69: Einstellungen und Optionen an einer Stelle – die Programm-Einstellungen gelten für alle PCs."""
    _titel("Programm-Einstellungen", "Regeln, Erinnerungen, Engpass-Grenzen, Outlook, KI – gelten für alle PCs am Standort.")

    async def oeffnen(ansicht: str):
        dlg.close()
        await a.oeffnen("einstellungen", ansicht)
    with ui.element("div").classes("m-opt-wahl"):
        for k, t, icon in (("allgemein", "Allgemeine Einstellungen", "tune"),
                           ("stammdaten", "Zimmer-Stammdaten", "edit_note"),
                           ("sicherung", "Sicherung & Verlauf", "backup")):
            b = ui.element("button").classes("m-opt-chip")
            with b:
                ui.icon(icon)
                ui.label(t)
            b.on("click", lambda k=k: oeffnen(k))


def _zurueck(a, d: dict, setzen) -> None:
    _titel("Auf Standard zurücksetzen")
    ui.label("Setzt Farben, Zoom, Schrift und Diagramme zurück. Das Layout (z. B. Menüband) bleibt.").classes("m-opt-unter")
    with ui.element("div").classes("m-opt-zeile"):
        knopf("Farben & Design", lambda: setzen(**{k: dk.STANDARD[k] for k in ("farbe", "farbe_eigen", "titelleiste")}),
              "", "palette")
        knopf("Anzeige & Schrift", lambda: setzen(zoom=100, schrift="standard", band_gross=False, dichte="normal"), "",
              "format_size")
        knopf("Diagramme", lambda: setzen(**{k: v for k, v in dk.STANDARD.items() if k.startswith("dg_")}), "", "insert_chart")
        knopf("Alles", lambda: setzen(**dict(dk.STANDARD), dichte="normal"), "primaer", "restart_alt")


CSS = r"""
.m-opt { width: min(920px, 96vw); max-width: 96vw !important; height: min(640px, 92vh); display: flex; flex-direction: column; border-radius: 8px;
  overflow: hidden; background: var(--ob-fl, var(--fl, #fff)); color: var(--ob-text, var(--text, #1F2A2A));
  box-shadow: 0 18px 50px rgba(0,0,0,.28); font-family: var(--ob-schrift, "Segoe UI", system-ui, sans-serif); }
.m-opt-kopf { display: flex; align-items: center; gap: 14px; padding: 12px 16px; border-bottom: 1px solid var(--ob-rand, var(--rand, #ddd)); }
.m-opt-titel { font-size: 18px; font-weight: 600; }
.m-opt-unter { font-size: 12px; color: var(--ob-text2, var(--text2, #5E6E6E)); white-space: normal; }
.m-opt-koerper { flex: 1; display: flex; min-height: 0; }
.m-opt-nav { width: 210px; flex: none; padding: 10px 8px; background: var(--ob-reiter, var(--fl2, #EEF1F1));
  border-right: 1px solid var(--ob-rand, var(--rand, #ddd)); display: flex; flex-direction: column; gap: 2px; }
.m-opt-navpunkt { display: flex; align-items: center; gap: 10px; height: 36px; padding: 0 10px; border-radius: 4px;
  background: none; border: 0; color: inherit; font: inherit; text-align: left; cursor: pointer; }
.m-opt-navpunkt .q-icon { font-size: 19px; color: var(--ob-akzent, var(--akzent, #007F7F)); }
.m-opt-navpunkt:hover { background: var(--ob-hover, rgba(0,0,0,.05)); }
.m-opt-navpunkt.an { background: var(--ob-an, rgba(0,127,127,.14)); font-weight: 600; }
.m-opt-inhalt { flex: 1; overflow: auto; padding: 8px 22px 22px; }
.m-opt-abschnitt { font-size: 14px; font-weight: 600; margin: 16px 0 8px; padding-bottom: 4px;
  border-bottom: 1px solid var(--ob-rand, var(--rand, #ddd)); }
.m-opt-fuss { display: flex; align-items: center; gap: 10px; padding: 10px 16px; border-top: 1px solid var(--ob-rand, var(--rand, #ddd)); }
.m-opt-wahl, .m-opt-zeile { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.m-opt-zeile { gap: 10px; margin: 6px 0; }
.m-opt-chip { display: inline-flex; align-items: center; gap: 6px; height: 32px; padding: 0 12px; border-radius: 4px; cursor: pointer;
  border: 1px solid var(--ob-rand, var(--rand, #ccc)); background: transparent; color: inherit; font: inherit; }
.m-opt-chip .q-icon { font-size: 18px; color: var(--ob-akzent, var(--akzent, #007F7F)); }
.m-opt-chip:hover { background: var(--ob-hover, rgba(0,0,0,.05)); }
.m-opt-chip.an { border-color: var(--ob-akzent, var(--akzent, #007F7F)); background: var(--ob-an, rgba(0,127,127,.14)); font-weight: 600; }
.m-opt-schemata { display: grid; grid-template-columns: repeat(auto-fill, minmax(132px, 1fr)); gap: 8px; }
.m-opt-schema { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 6px; cursor: pointer; font: inherit;
  color: inherit; background: transparent; border: 1px solid var(--ob-rand, var(--rand, #ccc)); text-align: left; }
.m-opt-schema:hover { background: var(--ob-hover, rgba(0,0,0,.05)); }
.m-opt-schema.an { outline: 2px solid var(--ob-akzent, var(--akzent, #007F7F)); outline-offset: 1px; font-weight: 600; }
.m-opt-muster { display: inline-flex; border-radius: 4px; overflow: hidden; flex: none; }
.m-opt-muster i { width: 14px; height: 24px; display: block; }
.m-opt-felder { display: grid; grid-template-columns: repeat(8, 34px); gap: 6px; margin-bottom: 8px; }
.m-opt-feld { width: 34px; height: 34px; border-radius: 4px; border: 0; cursor: pointer; }
.m-opt-feld:hover { outline: 2px solid var(--ob-text, #333); outline-offset: 1px; }
.m-opt-feld.an { outline: 3px solid var(--ob-text, #111); outline-offset: 2px; }
.m-opt-schriften { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
.m-opt-schrift { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 8px 10px; border-radius: 6px;
  cursor: pointer; color: inherit; background: transparent; border: 1px solid var(--ob-rand, var(--rand, #ccc)); text-align: left; font-size: 14px; }
.m-opt-schrift:hover { background: var(--ob-hover, rgba(0,0,0,.05)); }
.m-opt-schrift.an { outline: 2px solid var(--ob-akzent, var(--akzent, #007F7F)); outline-offset: 1px; }
.m-opt-spalten { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 2px 12px; }
.m-opt-haken { display: flex; align-items: center; gap: 8px; height: 32px; padding: 0 6px; border-radius: 4px; border: 0;
  background: none; color: inherit; font: inherit; cursor: pointer; text-align: left; }
.m-opt-haken .q-icon { font-size: 20px; color: var(--ob-text2, #5E6E6E); }
.m-opt-haken.an .q-icon { color: var(--ob-akzent, var(--akzent, #007F7F)); }
.m-opt-haken:hover { background: var(--ob-hover, rgba(0,0,0,.05)); }
.m-opt-chart { height: 220px; width: 100%; border: 1px solid var(--ob-rand, var(--rand, #ddd)); border-radius: 6px; }
.m-opt-hinweis { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; padding: 10px 12px; margin-top: 10px;
  border-radius: 6px; background: var(--ob-an, rgba(0,127,127,.12)); }
@media (max-width: 640px) { .m-opt-nav { width: 56px; } .m-opt-navpunkt > div { display: none; } }
"""
