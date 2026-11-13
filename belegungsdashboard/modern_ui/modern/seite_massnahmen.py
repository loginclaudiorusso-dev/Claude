"""Auswertung → Maßnahmen (0.56): Neuanmeldungen je Halbjahr und Maßnahmenart – alle Teilnehmenden (Pendler und
Internat) – als Grundlage für den Wirtschaftsplan. Kein Bestand (eine zweijährige Maßnahme trägt zwei Jahrgänge), keine
Betten – die Internatsbelegung steht in der allgemeinen Prognose. Kleinst- und eingestellte Maßnahmen sind ausgeblendet.
Darstellung: ein gemeinsames Diagramm oder je Maßnahme ein kleines Diagramm.
Rechnet in ``massnahmen_kern``."""

from __future__ import annotations

import json

from nicegui import ui

from . import diagramm_stil as _ds
from . import massnahmen_kern as mk
from .ui_bausteine import attr, knopf, leer, segmente, tabelle

MON = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
# 1.04: Menü der Maßnahmen-Auswahl im Menüband
CSS = r"""
.m-mn-menue { width: 380px; max-width: 92vw; padding: 0 !important; }
.m-mn-kopf { padding: 14px 16px 8px; display: grid; gap: 2px; }
.m-mn-titel { font-weight: 600; font-size: 14px; }
.m-mn-suche { margin: 0 16px 8px; }
.m-mn-schnell { display: flex; gap: 8px; padding: 0 16px 8px; border-bottom: 1px solid var(--rand); }
.m-mn-liste { max-height: 380px; overflow-y: auto; padding: 6px 8px; }
.m-mn-zeile { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 4px 8px;
  padding: 2px 8px; border-radius: 6px; cursor: pointer; min-height: 36px; }
.m-mn-zeile:hover { background: var(--fl2); }
.m-mn-name { font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-mn-art { font-size: 12px; color: var(--text2); border: 1px solid var(--rand); border-radius: 10px; padding: 1px 8px; }
.m-mn-art.lang { color: var(--akzent); border-color: color-mix(in srgb, var(--akzent) 45%, transparent); }
.m-mn-wahl { font: inherit; color: inherit; background: none; border: 0; width: 100%; text-align: left;
  grid-template-columns: auto minmax(0, 1fr); }
.m-mn-wahl.an .m-bg-punkt { border-width: 4px; border-color: var(--ob-akzent, #007F7F); }
.m-mn-wahl .m-bg-punkt { width: 12px; height: 12px; border-radius: 50%; border: 1.5px solid var(--sym-basis, #334155);
  box-sizing: border-box; }
/* 1.06: „Andere Sicht“ (z. B. Belegung des Internats) ganz rechts im Band, deutlich abgesetzt */
body.ob-seite-an .m-kz:has(.m-bg-rechts) .m-kz-luft { display: none !important; }   /* Platz geht nach rechts */
.m-bg-rechts { margin-left: auto; padding-left: 40px; display: flex; }
.m-bg-rechts > .m-bg { border-left: 1px solid var(--ob-rand, #D9DEDE); border-right: 0; }
.m-mn-fuss { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px 12px;
  border-top: 1px solid var(--rand); }
"""
KURZ = {"lang": "Haupt", "vorbereitung": "Vorb.", "ibtz": "IBTZ", "uebrige": "übrige", "ohne": "ohne Zimmer"}
FARBEN_EXTRA = ["#9b6bd6", "#c2a14a", "#4fb3bf", "#d67fa6", "#7a8f3a", "#b5654a", "#5c7fb8", "#8c8c8c"]
EIN_DIAGRAMM_BIS = 5


def _z(x: float | None, nk: int = 0) -> str:
    return "–" if x is None else f"{x:,.{nk}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def daten(a) -> None:
    if getattr(a, "mn_ansicht", "neu") == "prognose":      # 0.79: Bestandsprognose – Planung und Leitung
        from . import bestand_prognose_ui

        a.daten = {"bprog": bestand_prognose_ui.daten(a)}
        return
    if getattr(a, "mn_ansicht", "neu") == "bestand":       # 0.76: Bestandsmodell – Schritt 1 Prüfbericht
        from . import bestand_ui

        a.daten = {"bestand": bestand_ui.daten(a)}
        return
    vor = int(getattr(a, "mn_vor", 4) or 4)
    if vor not in (2, 4, 6):
        vor = 4
    roh = mk._roh()
    liste = mk.familien_liste(roh, a.heute)
    alle_fam = [f for f, g, _t in liste if g != "ohne"]
    vl = mk.vorlauf_messen()
    tests = mk.verfahren_testen(roh, [f for f, g, _t in liste if g == "lang"] or alle_fam) if liste else []
    verfahren = getattr(a, "mn_verfahren", None) or mk.bestes_verfahren(tests)
    reihen = mk.neuanmeldungen(roh, a.heute, alle_fam, 8, vor, verfahren, vl, tests) if liste else {}
    eigen = mk.sichtbarkeit(roh)
    alle_zeigen = bool(getattr(a, "mn_alle", False))

    def zeigen(f: str) -> bool:
        r = reihen.get(f)
        return eigen.get(f, r.aktiv if r else False)
    versteckt = [f for f in reihen if not zeigen(f)]
    wahl_liste = [(f, g, t) for f, g, t in liste if f in reihen and (alle_zeigen or zeigen(f))]
    auswahl = [f for f in (getattr(a, "mn_auswahl", None) or []) if f in reihen]
    arten = auswahl or [f for f, _g, _t in wahl_liste]
    darstellung = getattr(a, "mn_darstellung", None) or ("ein" if len(arten) <= EIN_DIAGRAMM_BIS else "je")
    a.daten = {"stand": mk.stand(), "vor": vor, "liste": wahl_liste, "auswahl": auswahl, "arten": arten,
               "darstellung": darstellung, "skala": getattr(a, "mn_skala", "gleich"),
               "reihen": {f: reihen[f] for f in arten if f in reihen}, "tests": tests, "verfahren": verfahren,
               "auto": not getattr(a, "mn_verfahren", None), "versteckt": versteckt, "alle": alle_zeigen, "eigen": eigen,
               "quelle": mk.pickup_kurve(vl).quelle, "plan_jahr": a.heute.year + 1,
               "stufe": 95 if getattr(a, "mn_stufe", 80) == 95 else 80,
               "takt": "monat" if getattr(a, "mn_takt", "welle") == "monat" else "welle", "gruende": {f: r.grund for f, r in reihen.items()}}


def _umschalter(a) -> None:
    with a.werkzeuge:
        segmente({"neu": "Neuanmeldungen", "prognose": "Teilnehmer-Prognose", "bestand": "Prüfbericht"},   # 0.86: Name nach der Frage
                 getattr(a, "mn_ansicht", "neu"),
                 lambda v: a.setzen(mn_ansicht=v, nur_seite=True))


def auswahl_text(auswahl: list, alle: int) -> str:
    """Kurztext für den Auswahl-Knopf – rein."""
    if not auswahl or len(auswahl) >= alle:
        return f"alle {alle}"
    return f"{len(auswahl)} von {alle}"


def _auswahl_band(a, d: dict, haupt: list) -> None:
    """1.04: Maßnahmen-Auswahl im Menüband – ein großer Knopf, dahinter ein Menü mit Suche, Schnellauswahl und
    Häkchen. Übernommen wird beim Schließen (nicht bei jedem Häkchen – sonst schlösse sich das Menü)."""
    from . import band_ui, symbole

    liste = d["liste"]
    gewaehlt = set(d["auswahl"])
    zustand = {"wahl": set(gewaehlt)}
    with band_ui.gruppe("Maßnahmen"):
        k = band_ui.gross("Auswahl", "checkbox_checked", symbole.TEAL, pfeil=True,
                          zahl=len(gewaehlt) if gewaehlt else None,
                          tipp=f"Welche Maßnahmen gezeigt werden – {auswahl_text(d['auswahl'], len(liste))}")
        with k, ui.menu().props('anchor="bottom left" self="top left"').classes("m-mn-menue") as menue:
            with ui.element("div").classes("m-mn-kopf").on("click.stop", lambda: None):
                ui.label("Maßnahmen zeigen").classes("m-mn-titel")
                ui.label(auswahl_text(d["auswahl"], len(liste))).classes("m-zweite")
            suche = ui.input(placeholder="Suchen …").props("dense outlined clearable autofocus").classes("m-mn-suche")
            suche.on("click.stop", lambda: None)
            with ui.element("div").classes("m-mn-schnell"):
                def alle_():
                    zustand["wahl"] = set()
                    menue.close()

                def haupt_():
                    zustand["wahl"] = set(haupt)
                    menue.close()
                knopf("Alle", alle_, "leise", "done_all")
                if haupt:
                    knopf("Nur Hauptmaßnahmen", haupt_, "leise", "checklist")
            zeilen = ui.element("div").classes("m-mn-liste")
            boxen: dict = {}
            with zeilen:
                for f, g, _t in liste:
                    with ui.element("label").classes("m-mn-zeile") as z:
                        cb = ui.checkbox(value=f in gewaehlt,
                                         on_change=lambda e, f=f: (zustand["wahl"].add(f) if e.value
                                                                   else zustand["wahl"].discard(f)))
                        ui.label(f).classes("m-mn-name")
                        ui.label(KURZ.get(g, g)).classes("m-mn-art " + g)
                    boxen[f] = (z, cb)

            def filtern(e) -> None:
                q = str(e.value or "").lower().strip()
                for f, (z, _cb) in boxen.items():
                    z.set_visibility(not q or q in f.lower())
            suche.on_value_change(filtern)
            with ui.element("div").classes("m-mn-fuss"):
                ui.label("Ohne Häkchen = alle").classes("m-zweite")
                knopf("Übernehmen", menue.close, "primaer")

        def zu() -> None:
            if zustand["wahl"] != gewaehlt:
                a.setzen(mn_auswahl=[f for f, _g, _t in liste if f in zustand["wahl"]], mn_darstellung=None, nur_seite=True)
        menue.on("hide", zu)


def aufraeumen_panel(a) -> None:
    """1.06: Veraltete Maßnahmen aus allen Prognosen nehmen. Sie bleiben im Pivot (und lassen sich jederzeit
    wiederherstellen), zählen aber in Neuanmeldungen, Teilnehmer-Prognose und Prüfbericht nicht mehr."""
    infos = mk.familien_uebersicht()
    wahl = {x.familie for x in infos if x.entfernt}
    grenze = a.heute.replace(year=a.heute.year - 2)

    def bauen():
        ui.label("Häkchen = entfernen. Die Maßnahme bleibt im Pivot gespeichert und lässt sich jederzeit wiederherstellen "
                 "(Häkchen weg). Ganz oben stehen die, die am längsten nicht mehr begonnen haben.").classes(
            "m-ptext").style("white-space:normal")
        alt = [x.familie for x in infos if x.letzter < grenze]
        with ui.element("div").classes("m-paktionen"):
            def alle_alten():
                wahl.update(alt)
                for f_, cb in boxen.items():
                    cb.value = f_ in wahl
            if alt:
                knopf(f"Alle seit über 2 Jahren ohne Start markieren ({len(alt)})", alle_alten, "leise", "history")
        sp = "minmax(190px,1.8fr) minmax(100px,1fr) minmax(60px,.6fr) minmax(120px,.9fr)"
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for k_ in ("Maßnahme entfernen", "letzter Start", "Kurse", "Neuanmeldungen"):
                ui.label(k_)
        boxen: dict = {}
        for x in infos:
            with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                cb = ui.checkbox(x.familie, value=x.familie in wahl,
                                 on_change=lambda e, f_=x.familie: wahl.add(f_) if e.value else wahl.discard(f_))
                boxen[x.familie] = cb
                ui.label(f"{x.letzter:%m.%Y}").classes("m-zweite" + (" m-warn" if x.letzter < grenze else ""))
                ui.label(str(x.kurse)).classes("m-zweite")
                ui.label(str(x.teilnehmende)).classes("m-zweite")

        async def speichern():
            if await a.aendern(mk.entfernt_schritt, sorted(wahl)):
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Maßnahmen aufräumen", bauen, breit=True)


def zeichnen(a) -> None:
    d = a.daten
    _umschalter(a)
    if "bprog" in d:
        from . import bestand_prognose_ui

        bestand_prognose_ui.zeichnen(a, d["bprog"])
        return
    if "bestand" in d:
        from . import bestand_ui

        bestand_ui.zeichnen(a, d["bestand"])
        return
    from .ui_bausteine import im_band

    with a.leiste:
        optionen = {f: f"{f} · {KURZ.get(g, g)}" for f, g, _t in d["liste"]}
        haupt = [f for f, g, _t in d["liste"] if g == "lang"]
        band = im_band()
        if band:                                          # 1.04: im Menüband ein Knopf mit Menü statt vieler Chips
            _auswahl_band(a, d, haupt)
        else:
            ui.select(optionen, value=d["auswahl"], multiple=True, with_input=True, label="Maßnahmen (leer = alle)",
                      on_change=lambda e: a.setzen(mn_auswahl=list(e.value or []), mn_darstellung=None,
                                                   nur_seite=True)).classes(
                "m-feld").props('dense outlined dark use-chips clearable options-dense popup-content-class="m-popup"').style(
                "min-width:280px;max-width:420px")
        if not band and haupt and d["auswahl"] != haupt:
            knopf("Nur Hauptmaßnahmen", lambda: a.setzen(mn_auswahl=haupt, mn_darstellung=None, nur_seite=True), "leise",
                  "checklist")
        segmente({"welle": "je Startwelle", "monat": "je Monat"}, d["takt"],      # 1.05
                 lambda v: a.setzen(mn_takt=v, nur_seite=True), sofort=True)
        segmente({"ein": "Ein Diagramm", "je": "Je Maßnahme"}, d["darstellung"],
                 lambda v: a.setzen(mn_darstellung=v, nur_seite=True), sofort=True)
        if d["darstellung"] == "je":
            segmente({"gleich": "gleiche Skala", "eigen": "eigene Skala"}, d["skala"],
                     lambda v: a.setzen(mn_skala=v, nur_seite=True), sofort=True)
        segmente({2: "1 Jahr", 4: "2 Jahre", 6: "3 Jahre"}, d["vor"], lambda v: a.setzen(mn_vor=v, nur_seite=True),
                 sofort=True)
        b_ = knopf("Geplante Plätze …", lambda: _plaetze_panel(a), "", "event_seat")
        if not band:
            b_.style("margin-left:auto")
        knopf("Maßnahmen aufräumen …", lambda: aufraeumen_panel(a), "leise", "delete",
              "Veraltete Maßnahmen aus allen Prognosen nehmen (wiederherstellbar)")
        if d["darstellung"] == "je":
            from . import diagramm_karte

            diagramm_karte.modus_wahl(a)
    with a.inhalt:
        if not d["stand"]["pivot"]:
            leer("Noch kein Maßnahmen-Pivot eingelesen. Unter Daten & Import → „Maßnahmen-Prognose“ hochladen.")
            knopf("Zu Daten & Import", lambda: a.oeffnen("daten"), "primaer", "upload_file")
            return
        if not d["reihen"]:
            leer("Für diese Auswahl gibt es keine Daten.")
            return
        with ui.element("div").classes("m-rv"):
            pv = d["stand"]["pivot"]
            monat = d["takt"] == "monat"
            reihen = mk.monatlich(None, a.heute, d["reihen"]) if monat else d["reihen"]
            ui.label(("Neuanmeldungen je Monat (letzte 24 Monate und Prognose; künftige Monate: schon gebucht + Rest der "
                      "Wellen-Erwartung nach dem Startmuster früherer Jahre)" if monat else
                      "Neuanmeldungen je Startwelle – Winterstart (Nov–Apr) und Sommerstart (Mai–Okt)") + " – alle "
                     f"Teilnehmenden (Pendler und Internat) · Maßnahmen-Pivot "
                     f"{pv['von'][:10]} – {pv['bis'][:10]}").classes("m-zweite").style("white-space:normal")
            _kpis(d)
            with ui.element("section").classes("m-block m-breit"):
                ui.label(f"{len(d['reihen'])} Maßnahme(n) – Neuanmeldungen " +
                         ("je Monat" if monat else "je Startwelle (W = Winter, S = Sommer)")).classes("m-btitel")
                if d["darstellung"] == "ein":
                    _ein_diagramm(reihen)
                else:
                    from . import diagramm_karte

                    m_ = diagramm_karte.modus()                  # 0.89: Darstellung wählbar
                    if m_ == "klassisch":
                        _raster_klassisch(reihen, d["skala"] == "gleich")
                    elif m_ == "einfach":
                        _raster_einfach(d["reihen"])
                        an = bool(getattr(a, "mn_diagramme", False))     # 0.93: Diagramme je Maßnahme auf Wunsch
                        knopf("Diagramme je Maßnahme ausblenden" if an else "Diagramme je Maßnahme zeigen",
                              lambda: a.setzen(mn_diagramme=not an, laden=False), "", "expand_less" if an else "expand_more")
                        if an:
                            _raster(a, reihen, d["skala"] == "gleich", pv)
                    else:
                        _raster(a, reihen, d["skala"] == "gleich", pv)
                tr = next((t for t in d["tests"] if t.verfahren == d["verfahren"]), None)
                if tr and tr.treffer80[1]:
                    ui.label(f"Rückwärtstest (gepunktet): In {tr.treffer80[0]} von {tr.treffer80[1]} vergangenen Wellen lag "
                             f"das Ist im 80-%-Band, in {tr.treffer95[0]} von {tr.treffer95[1]} im 95-%-Band – mit Spannen, die "
                             "damals bekannt waren.").classes("m-ptext")
                ui.label("Werte beim Darüberfahren · durchgezogen = Ist · gepunktet = Rückwärtstest (was das Verfahren damals "
                         "geschätzt hätte) · gestrichelt = erwartet (schon gebucht + erwartete Nachbuchung, ohne "
                         f"Buchungen: {mk.VERFAHREN[d['verfahren']]}) · hell hinterlegt = Prognose · Neuanmeldung = wer in "
                         f"den ersten {mk.NACHRUECK_TAGE // 7} Wochen eines Kurses dabei ist.").classes("m-zweite").style(
                    "white-space:normal")
            _anteile(a, d)                                   # 0.96: welche Maßnahmen den größten Anteil haben – und wann
            _plan_tabelle(a, d)
            _test(a, d)
            _versteckt(a, d)


def _anteile(a, d: dict) -> None:
    from . import anteile_kern as ank
    from . import anteile_ui

    reihen = d["reihen"]
    if len(reihen) < 2:
        return
    erste = next(iter(reihen.values()))
    achse = [mk.hj_kurz(z.hj) for z in erste.zeilen]
    prog = [z.art != "ist" for z in erste.zeilen]
    werte = {}
    for fam, r in reihen.items():
        je = {mk.hj_kurz(z.hj): z.erwartet for z in r.zeilen}
        werte[fam] = [je.get(x) for x in achse]
    an = ank.berechnen(werte, achse, prog)
    fb = {fam: f for fam, f in zip(reihen, _farben() * 4)}
    anteile_ui.zeigen(a, "Anteile der Maßnahmen an den Neuanmeldungen", an, fb,
                      "je Startwelle (W = Winter, S = Sommer, P = Prognose)")


def _farben() -> list[str]:
    from . import seite_auswertung as sa

    t = sa._T()
    return _ds.kategorien(t) + FARBEN_EXTRA          # 0.97: deutlich verschiedene Farbtöne (nicht Grün neben Türkis)


def _achsen(r) -> tuple[list[str], int]:
    x = [mk.hj_kurz(z.hj) for z in r.zeilen]
    h = next((i for i, z in enumerate(r.zeilen) if z.art != "ist"), len(x) - 1)
    return x, h


def _linien(name: str, r, farbe: str, h: int, werte_zeigen: bool = True) -> list[dict]:
    werte = [round(z.erwartet, 1) for z in r.zeilen]
    ist = [w if k < h else None for k, w in enumerate(werte)]
    prog = [w if k >= h - 1 else None for k, w in enumerate(werte)]
    rueck = [round(z.rueck, 1) if z.art == "ist" and z.rueck is not None else None for z in r.zeilen]
    serien = [{"name": name, "type": "line", "symbol": "circle", "symbolSize": 6, "data": ist,
               "lineStyle": {"color": farbe, "width": 2.5}, "itemStyle": {"color": farbe}},
              {"name": name, "type": "line", "symbol": "emptyCircle", "symbolSize": 6, "data": prog,
               "lineStyle": {"color": farbe, "width": 2.5, "type": "dashed"}, "itemStyle": {"color": farbe},
               "label": {"show": werte_zeigen, "position": "top", "fontSize": 10, "color": farbe,
                         ":formatter": f"(p) => p.dataIndex >= {h} ? Math.round(p.value) : ''"}}]
    if any(v is not None for v in rueck):
        serien.append({"name": "Rückwärtstest", "type": "line", "symbol": "diamond", "symbolSize": 5, "data": rueck,
                       "lineStyle": {"color": farbe, "width": 1.2, "type": "dotted", "opacity": .8},
                       "itemStyle": {"color": farbe, "opacity": .7}})
    return serien


def _tooltip(reihen: dict, farben: list[str]) -> str:
    """0.58: Beim Darüberfahren je Welle: Ist bzw. erwartet, 80-%- und 95-%-Band, Rückwärtstest (damals geschätzt)."""
    breite = max(len(r.zeilen) for r in reihen.values())
    d = []
    for k in range(breite):
        eintraege = []
        for i, (fam, r) in enumerate(reihen.items()):
            if k >= len(r.zeilen):
                continue
            z = r.zeilen[k]
            b = z.rueck_band
            eintraege.append({"n": fam, "f": farben[i % len(farben)], "a": z.art, "e": z.erwartet, "i": z.ist, "g": z.gebucht,
                              "l8": z.klein, "h8": z.gross, "l9": z.klein95, "h9": z.gross95, "p": z.geplant,
                              "r": z.rueck, "b": list(b) if b else None, "m8": z.im80, "m9": z.im95})
        d.append({"t": mk.hj_text(next(iter(reihen.values())).zeilen[min(k, len(next(iter(reihen.values())).zeilen) - 1)].hj),
                  "z": eintraege})
    return ("(ps) => { const D = " + json.dumps(d) + "; const d = D[ps[0].dataIndex]; if (!d) return '';"
            " const f = v => v == null ? '–' : Math.round(v).toLocaleString('de-DE');"
            " const zl = (t, v) => `<div style=\"display:flex;gap:16px;justify-content:space-between;line-height:1.6\">"
            "<span style=\"opacity:.75\">${t}</span><b style=\"font-variant-numeric:tabular-nums\">${v}</b></div>`;"
            " let h = `<div style=\"font-weight:600;margin-bottom:4px\">${d.t}</div>`;"
            " for (const x of d.z) { h += `<div style=\"margin-top:6px;font-weight:600\"><span style=\"display:inline-block;"
            "width:10px;height:10px;border-radius:3px;background:${x.f};margin-right:6px\"></span>${x.n}</div>`;"
            " if (x.a == 'ist') { h += zl('Ist (Neuanmeldungen)', f(x.i));"
            "   if (x.r != null) h += zl('Rückwärtstest: damals geschätzt', f(x.r) + (x.b ? ` (80 %: ${f(x.b[0])}–${f(x.b[1])})` : ''));"
            "   if (x.m8 != null) h += zl('Ist im Band?', x.m8 ? '✓ im 80-%-Band' : (x.m9 ? '✓ im 95-%-Band' : '✗ außerhalb')); }"
            " else { if (x.a == 'laufend') h += zl('schon begonnen', f(x.i));"
            "   if (x.g) h += zl('schon gebucht', f(x.g));"
            "   h += zl(x.p ? 'eigene Planung' : 'erwartet', f(x.e));"
            "   if (!x.p) { h += zl('80 %-Band', f(x.l8) + ' – ' + f(x.h8)); h += zl('95 %-Band', f(x.l9) + ' – ' + f(x.h9)); } } }"
            " return h; }")


def _baender(r, farbe: str, h: int) -> list[dict]:
    """0.57: Wahrscheinlichkeitsbänder als gestapelte Flächen – außen 95 %, innen 80 % (nur im Prognoseteil)."""
    def reihe(fn):
        return [round(fn(z), 2) if k >= h else None for k, z in enumerate(r.zeilen)]
    basis = {"type": "line", "symbol": "none", "stack": f"band-{r.familie}", "lineStyle": {"opacity": 0},
             "tooltip": {"show": False}, "silent": True, "name": r.familie, "legendHoverLink": False}
    return [{**basis, "data": reihe(lambda z: z.klein95)},
            {**basis, "data": reihe(lambda z: z.klein - z.klein95), "areaStyle": {"color": _ds.band_flaeche(_tt(), "band95", farbe)}},
            {**basis, "data": reihe(lambda z: z.gross - z.klein), "areaStyle": {"color": _ds.band_flaeche(_tt(), "band", farbe)}},
            {**basis, "data": reihe(lambda z: z.gross95 - z.gross), "areaStyle": {"color": _ds.band_flaeche(_tt(), "band95", farbe)}}]


def _tt() -> dict:
    from . import themes
    return themes.farben(themes.AKTIV)


def _prognosebereich(t: dict, x: list, h: int) -> dict:
    return {"silent": True, "itemStyle": {"color": t["akzent"], "opacity": .05},
            "label": {"show": True, "position": "insideTopLeft", "color": t["text3"], "formatter": "Prognose"},
            "data": [[{"xAxis": x[h]}, {"xAxis": x[-1]}]]}


def _ein_diagramm(reihen: dict) -> None:
    from . import seite_auswertung as sa

    t = sa._T()
    farben = _farben()
    x, h = _achsen(next(iter(reihen.values())))
    opt = sa._chart_basis()
    opt["xAxis"]["data"] = x
    opt["xAxis"]["name"] = "Start"
    opt["yAxis"]["scale"] = False
    opt["yAxis"]["name"] = "Neuanmeldungen"
    opt["grid"]["top"] = 50
    opt["legend"]["type"] = "scroll"
    serien = []
    for i, (fam, r) in enumerate(reihen.items()):
        serien += _linien(fam, r, farben[i % len(farben)], h, len(reihen) <= 3)
    opt["tooltip"][":formatter"] = _tooltip(reihen, farben)
    if len(reihen) == 1:                                   # bei mehreren Linien wären die Bänder unlesbar
        r = next(iter(reihen.values()))
        serien += _baender(r, farben[0], h)
    serien[0]["markArea"] = _prognosebereich(t, x, h)
    opt["series"] = serien
    opt["legend"]["data"] = list(reihen) + (["Rückwärtstest"] if any(se["name"] == "Rückwärtstest" for se in serien) else [])
    sa._chart(opt)


def _raster(a, reihen: dict, gleiche_skala: bool, pivot: dict | None = None) -> None:
    """0.87: Jede Maßnahme als kompakte Diagramm-Karte – Neuanmeldungen sind Zählwerte → Balken (Prognose heller,
    gestrichelter Rand), 80-%-Spanne als helle Fläche, Rückwärtstest gepunktet, „Auf einen Blick“ je Maßnahme."""
    from datetime import date

    from . import blick_kern as bk
    from . import diagramm_karte, diagramm_stil
    from . import seite_auswertung as sa

    t = sa._T()
    hoch = max((z.gross for r in reihen.values() for z in r.zeilen), default=0) * 1.12 or None
    try:
        stand = date.fromisoformat(str((pivot or {}).get("importiert_am") or "")[:10])
    except ValueError:
        stand = date.today()
    with ui.element("div").classes("m-mn-raster"):
        for fam, r in reihen.items():
            x, h = _achsen(r)
            werte = [round(z.erwartet, 1) for z in r.zeilen]
            opt = sa._chart_basis()
            opt["xAxis"]["data"] = x
            opt["xAxis"]["boundaryGap"] = True
            opt["yAxis"]["scale"] = False
            if gleiche_skala and hoch:
                opt["yAxis"]["max"] = round(hoch)
            opt["grid"] = {"left": 34, "right": 10, "top": 18, "bottom": 22}
            band = {"type": "line", "stack": f"band-{fam}", "symbol": "none", "silent": True, "rolle": "band",
                    "tooltip": {"show": False}, "name": "_80"}
            rueck = [round(z.rueck, 1) if z.art == "ist" and z.rueck is not None else None for z in r.zeilen]
            serien = [{"name": "Ist", "rolle": "balken_ist", "type": "bar", "data": [w if k < h else None for k, w in enumerate(werte)]},
                      {"name": "erwartet", "rolle": "balken_prognose", "type": "bar",
                       "data": [w if k >= h else None for k, w in enumerate(werte)]},
                      {**band, "data": [round(z.klein, 1) if k >= h else None for k, z in enumerate(r.zeilen)]},
                      {**{k_: v for k_, v in band.items() if k_ != "tooltip"}, "name": "80-%-Spanne",
                       "data": [round(z.gross - z.klein, 1) if k >= h else None for k, z in enumerate(r.zeilen)],
                       "areaStyle": {"opacity": .16}}]
            if any(v is not None for v in rueck):
                serien.append({"name": "Rückwärtstest", "rolle": "test", "type": "line", "data": rueck, "symbol": "diamond",
                               "symbolSize": 5, "lineStyle": {"color": t["text3"]}, "itemStyle": {"color": t["text3"]}})
            opt["series"] = serien
            opt["tooltip"] = {"trigger": "axis", ":formatter": _tooltip({fam: r}, [t["akzent"]])}
            opt = diagramm_stil.einheitlich(opt, t, x[h - 1] if 0 < h <= len(x) else None, x[h] if h < len(x) else None,
                                            legende=False)
            imm = [z.im80 for z in r.zeilen if z.art == "ist" and z.im80 is not None]
            blick = bk.wellen(x, werte, [k < h for k in range(len(x))], stand,
                              [z.klein for z in r.zeilen], [z.gross for z in r.zeilen],
                              (sum(imm), len(imm)) if imm else None, r.naechstes_jahr,
                              je_monat=bool(r.zeilen) and len(r.zeilen[0].hj) == 3)
            with ui.element("div").classes("m-mn-kachel"):
                with diagramm_karte.Karte(a, fam, f"12 Mon. {_z(r.letzte12)} · nächstes Jahr ≈ {_z(r.naechstes_jahr)} · "
                                                  f"Datenstand {stand:%d.%m.%Y}", blick, klein=True) as k:
                    k.anbinden(k.chart(opt))


def _raster_klassisch(reihen: dict, gleiche_skala: bool) -> None:
    """Darstellung „Klassisch“ – wie bis 0.86: Linien je Maßnahme mit 80/95-%-Bändern."""
    from . import seite_auswertung as sa

    t = sa._T()
    farben = _farben()
    hoch = max((z.gross95 for r in reihen.values() for z in r.zeilen), default=0) * 1.05 or None
    with ui.element("div").classes("m-mn-raster"):
        for i, (fam, r) in enumerate(reihen.items()):
            x, h = _achsen(r)
            with ui.element("div").classes("m-mn-kachel"):
                with ui.element("div").classes("m-zeile-flex"):
                    ui.label(fam).classes("m-name")
                    ui.label(f"12 Mon. {_z(r.letzte12)} · nächstes Jahr ≈ {_z(r.naechstes_jahr)}"
                             ).classes("m-zweite").style("margin-left:auto")
                opt = sa._chart_basis()
                opt["xAxis"]["data"] = x
                opt["yAxis"]["scale"] = False
                if gleiche_skala and hoch:
                    opt["yAxis"]["max"] = round(hoch)
                opt["grid"] = {"left": 34, "right": 8, "top": 10, "bottom": 22}
                opt["legend"] = {"show": False}
                serien = _linien(fam, r, farben[i % len(farben)], h) + _baender(r, farben[i % len(farben)], h)
                opt["tooltip"] = {"trigger": "axis", ":formatter": _tooltip({fam: r}, [farben[i % len(farben)]])}
                opt["grid"]["top"] = 18
                serien[0]["markArea"] = {**_prognosebereich(t, x, h), "label": {"show": False}}
                opt["series"] = serien
                sa._chart(opt)


def _raster_einfach(reihen: dict) -> None:
    """Darstellung „Einfach“ (Geschäftsführung): EINE sortierte Balkenliste – je Maßnahme „nächstes Jahr“, die Marke
    zeigt die letzten 12 Monate. Die Aussage steht als Überschrift darüber."""
    from . import blick_kern as bk

    zeilen = sorted(reihen.items(), key=lambda x: -(x[1].naechstes_jahr or 0))
    summe = sum(r.naechstes_jahr or 0 for _f, r in zeilen)
    vorher = sum(r.letzte12 or 0 for _f, r in zeilen)
    hoch = max([r.naechstes_jahr or 0 for _f, r in zeilen] + [r.letzte12 or 0 for _f, r in zeilen] + [1])
    with ui.element("section").classes("m-einfach"):
        ui.label(f"Nächstes Jahr rund {bk.zahl(summe)} Neuanmeldungen – "
                 f"{bk.vergleich(summe - vorher, bk.schwelle_fuer(vorher, None), 'in den letzten 12 Monaten')} "
                 f"({bk.zahl(vorher)}).").classes("m-einfach-titel")
        with ui.element("div").classes("m-einfach-liste"):
            for fam, r in zeilen:
                n, v = r.naechstes_jahr or 0, r.letzte12 or 0
                with ui.element("div").classes("m-einfach-zeile"):
                    ui.label(fam).classes("m-einfach-name")
                    with ui.element("div").classes("m-einfach-spur"):
                        ui.element("div").classes("m-einfach-balken").style(f"width:{100 * n / hoch:.1f}%")
                        attr(ui.element("div").classes("m-einfach-marke").style(f"left:{100 * v / hoch:.1f}%"),
                             title=f"letzte 12 Monate: {bk.zahl(v)}")
                    ui.label(f"≈ {bk.zahl(n)} · zuletzt {bk.zahl(v)}").classes("m-einfach-wert")
        ui.label("Balken = erwartet im nächsten Jahr · Strich = letzte 12 Monate. Verlauf je Maßnahme: „Diagramme je "
                 "Maßnahme zeigen“ oder Darstellung „Karte“ bzw. „Klassisch“.").classes("m-zweite")


def _kpis(d: dict) -> None:
    from .seite_steuerung import _kpi

    reihen = list(d["reihen"].values())
    mit_trend = [r for r in reihen if r.trend is not None]
    naechst = sum(r.naechstes_jahr for r in reihen)
    with ui.element("div").classes("m-kpis"):
        if reihen:
            alle = [z for r in reihen for z in r.zeilen if z.hj[0] == d["plan_jahr"]]
            a80, b80 = mk.summen_spanne(alle, 80)
            a95, b95 = mk.summen_spanne(alle, 95)
            _kpi(f"Erwartet {d['plan_jahr']}", _z(naechst), f"80 %: {_z(a80)}–{_z(b80)} · 95 %: {_z(a95)}–{_z(b95)}")
        if mit_trend:
            hoch = max(mit_trend, key=lambda r: r.trend)
            tief = min(mit_trend, key=lambda r: r.trend)
            _kpi("Am stärksten gewachsen", hoch.familie, f"{_pfeil(hoch.trend)[0]} Neuanmeldungen (12 Mon. zum Vorjahr)")
            _kpi("Am stärksten geschrumpft", tief.familie, f"{_pfeil(tief.trend)[0]} Neuanmeldungen (12 Mon. zum Vorjahr)",
                 "krit" if tief.trend <= -.1 else "")
        t = next((t for t in d["tests"] if t.verfahren == d["verfahren"]), None)
        if t and t.wape is not None:
            _kpi("Treffsicherheit", f"± {round(100 * t.wape)} %", f"{mk.VERFAHREN[t.verfahren]} (Rückwärtstest)")


def _plan_tabelle(a, d) -> None:
    """Für den Wirtschaftsplan: je Maßnahme die erwarteten Neuanmeldungen der kommenden Halbjahre mit Spanne."""
    reihen = d["reihen"]
    r0 = next(iter(reihen.values()))
    kommend = [z.hj for z in r0.zeilen if z.art != "ist"]
    gr = {f: g for f, g, _t in d["liste"]}
    with ui.element("section").classes("m-block m-breit"):
        with ui.element("div").classes("m-zeile-flex"):
            ui.label("Für den Wirtschaftsplan – erwartete Neuanmeldungen je Startwelle").classes("m-btitel")
            ui.element("div").style("flex:1")
            segmente({80: "Spanne 80 %", 95: "Spanne 95 %"}, d["stufe"], lambda v: a.setzen(mn_stufe=v, nur_seite=True),
                     sofort=True)
        st = d["stufe"]
        lo_a, hi_a = ("klein", "gross") if st == 80 else ("klein95", "gross95")
        with ui.element("div").classes("m-tab-scroll"):
            sp = "minmax(110px, 1.2fr) minmax(110px, 1fr) auto auto auto 96px " + " ".join("auto" for _ in kommend) + " 44px"
            with tabelle(sp):
                with ui.element("div").classes("m-raster m-tkopf"):
                    for t in ("Maßnahme", "Gruppe", "Ø je Jahr (3 J.)", "letzte 12 Mon.", "Trend", "max. je Welle"):
                        ui.label(t)
                    for h in kommend:
                        ui.label(mk.hj_text(h) + (" (läuft)" if h == kommend[0] else ""))
                    ui.label("")
                spalten: list[list] = [[] for _ in kommend]
                for fam, r in sorted(reihen.items(), key=lambda x: -x[1].jahr_mittel):
                    with ui.element("div").classes("m-raster m-zeile"):
                        ui.label(fam).classes("m-name")
                        ui.select(mk.GRUPPEN, value=gr.get(fam, r.gruppe),
                                  on_change=lambda e, fam=fam: a.aendern(mk.zuordnung_schritt, fam, e.value)).classes(
                            "m-feld").props('dense borderless dark options-dense popup-content-class="m-popup"')
                        ui.label(_z(r.jahr_mittel)).classes("m-mono")
                        ui.label(_z(r.letzte12)).classes("m-mono")
                        txt, kl = _pfeil(r.trend)
                        ui.label(txt).classes(f"m-mono {kl}")
                        kap = ui.number(value=r.kapazitaet if r.kap_quelle == "eigene Angabe" else None, min=1, step=1,
                                        format="%d", placeholder=str(r.kapazitaet or "–")).classes("m-feld").props(
                            "dense outlined dark").style("max-width:90px")
                        kap.tooltip("Höchstens so viele Neuanmeldungen je Startwelle (Plätze). Leer = automatisch: "
                                    f"höchste Welle der letzten 5 Jahre + 15 % ({r.kapazitaet or '–'}).")

                        async def kap_speichern(e=None, fam=fam, feld=kap, alt=r.kapazitaet if r.kap_quelle == "eigene Angabe"
                                                else None):
                            neu = int(feld.value) if feld.value else None
                            if neu != alt:
                                await a.aendern(mk.kapazitaet_schritt, fam, neu)
                        kap.on("blur", kap_speichern)
                        kap.on("keydown.enter", kap_speichern)
                        zs = {z.hj: z for z in r.zeilen}
                        for i, h in enumerate(kommend):
                            z = zs.get(h)
                            if z is None:
                                ui.label("–")
                                continue
                            spalten[i].append(z)
                            wo = " · eigene Planung" if z.geplant else (f" · {_z(z.ist + z.gebucht)} schon gebucht/begonnen"
                                                                         if z.ist + z.gebucht else "")
                            el = ui.label(f"{_z(z.erwartet)} ({_z(getattr(z, lo_a))}–{_z(getattr(z, hi_a))})").classes("m-mono")
                            el.props(f'title="{mk.hj_text(h)}: erwartet {_z(z.erwartet)} · 80 %: {_z(z.klein)}–'
                                     f'{_z(z.gross)} · 95 %: {_z(z.klein95)}–{_z(z.gross95)}{wo}"')
                        knopf("", lambda fam=fam: a.aendern(mk.sichtbar_schritt, fam, False), "leise", "visibility_off",
                              "Diese Maßnahme ausblenden")
                with ui.element("div").classes("m-raster m-zeile m-summe"):
                    ui.label("Summe").classes("m-name")
                    for _ in range(5):
                        ui.label("")
                    for zs_ in spalten:
                        u, o = mk.summen_spanne(zs_, st)
                        ui.label(f"{_z(sum(z.erwartet for z in zs_))} ({_z(u)}–{_z(o)})").classes("m-mono")
                    ui.label("")
        ui.label("Alle Teilnehmenden (Pendler und Internat) · Neuanmeldung = in den ersten 6 Wochen eines Kurses dabei · "
                 "Trend = letzte 12 Monate gegen die 12 davor (grün ab +10 %, rot ab −10 %) · in Klammern die Spanne: "
                 "mit 80 % (bzw. 95 %) Wahrscheinlichkeit liegt das Ergebnis darin – berechnet aus den Fehlern des "
                 "Rückwärtstests, in Personen passend zur Größe der Maßnahme (Abweichungen wachsen etwa mit der Wurzel, nicht im "
                 "festen Prozentsatz) und nie über „max. je Welle“; im Diagramm innen 80 %, außen 95 % · Summe: Abweichungen gleichen sich teils aus, "
                 "deshalb schmaler als die Summe der Spannen · schon gebuchte Starts zählen fest, dazu die erwartete Nachbuchung "
                 f"({d['quelle']}) · eigene geplante Plätze ersetzen die Schätzung.").classes("m-xk-hinweis")


def _test(a, d) -> None:
    tests = d["tests"]
    with ui.expansion("Welches Verfahren schätzt am besten? (Rückwärtstest)").classes("m-block m-breit m-rv-exp"):
        if not tests or all(t.n == 0 for t in tests):
            ui.label("Dafür braucht es mindestens drei Jahre im Maßnahmen-Pivot.").classes("m-zweite")
            return
        with tabelle("minmax(200px, 2fr) auto auto auto auto auto auto"):
            with ui.element("div").classes("m-raster m-tkopf"):
                for t in ("Verfahren", "mittlerer Fehler", "Neigung", "verglichene Wellen", "im 80-%-Band", "im 95-%-Band", ""):
                    ui.label(t)
            for t in tests:
                with ui.element("div").classes("m-raster m-zeile" + (" an" if t.verfahren == d["verfahren"] else "")):
                    ui.label(t.text + (" ✓" if t.verfahren == d["verfahren"] else "")).classes("m-name")
                    ui.label(f"± {round(100 * t.wape)} %" if t.wape is not None else "–").classes("m-mono")
                    ui.label(_pz(100 * t.bias) + (" zu hoch" if (t.bias or 0) > .02 else " zu niedrig" if (t.bias or 0) < -.02
                                                  else "") if t.bias is not None else "–").classes("m-mono")
                    ui.label(str(t.n)).classes("m-mono")
                    for k, n in (t.treffer80, t.treffer95):
                        ui.label(f"{k} von {n} ({round(100 * k / n)} %)" if n else "–").classes("m-mono")
                    if t.verfahren != d["verfahren"]:
                        knopf("verwenden", lambda v=t.verfahren: a.setzen(mn_verfahren=v, nur_seite=True), "leise")
                    else:
                        ui.label("automatisch gewählt" if d["auto"] else "von Hand gewählt").classes("m-zweite")
        if not d["auto"]:
            knopf("Automatisch wählen", lambda: a.setzen(mn_verfahren=None, nur_seite=True), "leise", "auto_mode")
        ui.label("Für jedes vergangene Halbjahr mit mindestens zwei Vorjahren wurde geschätzt – nur mit dem, was vorher "
                 "bekannt war, und ohne Buchungen (eher streng) – und mit dem Ist verglichen, über die Hauptmaßnahmen. "
                 "Mittlerer Fehler = Summe der Abweichungen / Summe Ist. Neigung = ob das Verfahren eher zu hoch oder zu "
                 "niedrig liegt. „Im Band“ = wie oft das Ist in der Spanne lag, die damals bekannt war (nur aus Fehlern "
                 "früherer Wellen) – ideal sind etwa 80 % bzw. 95 %; deutlich weniger heißt: die Spanne ist zu eng. Das Verfahren mit dem kleinsten Fehler wird automatisch verwendet. Wenige Jahre an Daten "
                 "→ die Zahlen sind ein Anhaltspunkt, keine Garantie.").classes("m-xk-hinweis")


def _versteckt(a, d) -> None:
    v = d["versteckt"]
    if not v:
        return
    with ui.expansion(f"Ausgeblendete Maßnahmen ({len(v)})").classes("m-block m-breit m-rv-exp"):
        ui.label(f"Automatisch ausgeblendet: UWT (eigene Planung), seit {mk.AKTIV_MONATE} Monaten kein Start (eingestellt) "
                 f"oder weniger als {mk.AKTIV_MIN} Neuanmeldungen in {mk.AKTIV_MONATE} Monaten (Kleinstmaßnahme) – oder von "
                 "Hand.").classes(
            "m-zweite").style("white-space:normal")
        with ui.element("div").classes("m-zeile").style("gap:8px; flex-wrap:wrap"):
            segmente({False: "Ausgeblendete nicht anbieten", True: "In der Auswahl anbieten"}, d["alle"],
                     lambda x: a.setzen(mn_alle=x, nur_seite=True), sofort=True)
        for f in sorted(v):
            with ui.element("div").classes("m-liste-zeile"):
                ui.label(f).classes("m-name")
                ui.label("von Hand" if d["eigen"].get(f) is False else d["gruende"].get(f) or "nach Regel").classes("m-zweite")
                knopf("immer zeigen", lambda f=f: a.aendern(mk.sichtbar_schritt, f, True), "leise", "visibility")
                if d["eigen"].get(f) is False:
                    knopf("Regel gilt", lambda f=f: a.aendern(mk.sichtbar_schritt, f, None), "leise", "rule")


def _pz(x: float | None) -> str:
    if x is None:
        return "–"
    return "±0 %" if round(x) == 0 else f"{round(x):+d} %".replace("-", "−")


def _pfeil(x: float | None) -> tuple[str, str]:
    if x is None:
        return "–", ""
    p = round(100 * x)
    return (f"{p:+d} %".replace("-", "−") if p else "±0 %"), ("m-krit" if p <= -10 else "m-ok" if p >= 10 else "")


def _plaetze_panel(a) -> None:
    familien = list(a.daten.get("arten") or [])
    eintraege = mk.stand()["plaetze"]
    wahl = {"familie": familien[0] if familien else "", "monat": f"{a.heute.year + 1}-06", "plaetze": 20}

    def bauen():
        ui.label("Geplante Plätze ersetzen die Schätzung der Neuanmeldungen für das Halbjahr des Startmonats (gleiche "
                 "Art) – z. B. wenn ein Kurs schon fest zugesagt oder gestrichen ist.").classes("m-ptext")
        for p in eintraege:
            with ui.element("div").classes("m-liste-zeile"):
                ui.label(f"{p['familie']} · {p['monat']}").classes("m-name")
                ui.label(f"{p['plaetze']} Plätze").classes("m-mono")
                knopf("", lambda p=p: a.aendern(mk.plaetze_schritt, p["familie"], p["monat"], None), "leise", "delete",
                      "Eintrag entfernen")
        with ui.element("div").classes("m-kap").style("grid-template-columns: 2fr 1fr 1fr"):
            ui.select(familien, value=wahl["familie"] or None, label="Art",
                      on_change=lambda e: wahl.__setitem__("familie", e.value)).classes("m-feld").props(
                'dense outlined dark popup-content-class="m-popup"')
            ui.input("Startmonat (JJJJ-MM)", value=wahl["monat"], on_change=lambda e: wahl.__setitem__("monat", e.value)).classes(
                "m-feld").props("dense outlined dark")
            ui.number("Plätze", value=wahl["plaetze"], min=1, step=1, format="%d",
                      on_change=lambda e: wahl.__setitem__("plaetze", e.value)).classes("m-feld").props("dense outlined dark")

        async def speichern():
            if not wahl["familie"] or len(str(wahl["monat"])) != 7:
                a.toast("Bitte Art und Startmonat (z. B. 2027-06) angeben.", fehler=True)
                return
            if await a.aendern(mk.plaetze_schritt, wahl["familie"], wahl["monat"], int(wahl["plaetze"] or 0)):
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            knopf("Hinzufügen", speichern, "primaer", "add")
            knopf("Schließen", a.panel_zu, "leise")
    a.panel("Geplante Plätze", bauen)
