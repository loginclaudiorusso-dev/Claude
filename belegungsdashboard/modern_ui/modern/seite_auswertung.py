"""Seite „Auswertung“: Lage (heute + Verlauf), Belegung im Zeitraum, Prognose je Monat und Zimmer & Engpässe.
Standort und Netto/Brutto gelten für die ersten drei Ansichten."""

from __future__ import annotations

from datetime import date, timedelta

from nicegui import run, ui

from . import auswertung_kern as ak
from . import seiten
from . import themes
from .ui_bausteine import attr, knopf, leer, segmente


def _T() -> dict:
    """Diagrammfarben des gewählten Designs (ECharts nimmt Farben aus Python, nicht aus dem CSS)."""
    return themes.farben(themes.AKTIV)


ANSICHTEN = {"lage": "Lage", "belegung": "Belegung", "prognose": "Prognose", "zimmer": "Zimmer & Engpässe"}
AMPEL = {"ok": "ok", "knapp": "warn", "kritisch": "krit", "ueber": "krit", "unbekannt": "neutral"}


def _zahl(x: float | None, nk: int = 0) -> str:
    if x is None:
        return "–"
    return f"{x:,.{nk}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def daten(a) -> None:
    ansicht = a.ansicht_von("auswertung", "lage")
    if ansicht == "zimmer":
        seiten.aw_daten(a)
        return
    ds, fehler = ak.datenstand()
    if ds is None:
        a.daten = {"fehler": fehler}
        return
    if ansicht == "lage":
        a.daten = {"lage": ak.lage(ds, a.aw_standort, a.aw_brutto)}
    elif ansicht == "belegung":
        a.daten = {"zr": ak.zeitraum(ds, a.aw_standort, a.aw_von, a.aw_bis, a.aw_brutto), "stichtag": ds.stichtag,
                   "det": ak.belegung_details(ds, a.aw_standort, a.aw_von, a.aw_bis, a.aw_brutto)}
    else:
        a.daten = {"pg": ak.prognose(ds, a.aw_standort, a.aw_brutto, 24, a.aw_horizont)}
        if a.aw_chart == "jahr":                   # Vorjahresvergleich: drei Jahre zurück
            a.daten["pg_lang"] = ak.prognose(ds, a.aw_standort, a.aw_brutto, 36, a.aw_horizont)


def zeichnen(a) -> None:
    ansicht = a.ansicht_von("auswertung", "lage")
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("auswertung", ansicht=v))
    if ansicht == "zimmer":
        seiten.aw_zeichnen(a)
        return
    with a.leiste:
        segmente(ak.STANDORTE, a.aw_standort, lambda s: a.setzen(aw_standort=s))
        segmente({False: "Netto", True: "Brutto"}, a.aw_brutto, lambda b: a.setzen(aw_brutto=b))
    if "fehler" in a.daten:
        with a.inhalt:
            leer(a.daten["fehler"])
        return
    {"lage": _lage, "belegung": _belegung, "prognose": _prognose}[ansicht](a)


def _chart_basis() -> dict:
    achse = {"axisLine": {"lineStyle": {"color": _T()["rand2"]}}, "axisLabel": {"color": _T()["text3"]},
             "splitLine": {"lineStyle": {"color": _T()["rand"]}}}
    return {"backgroundColor": "transparent", "textStyle": {"color": _T()["text2"], "fontFamily": "Segoe UI, sans-serif"},
            "grid": {"left": 48, "right": 20, "top": 30, "bottom": 30}, "tooltip": {"trigger": "axis"},
            "legend": {"textStyle": {"color": _T()["text2"]}, "top": 0, "right": 10},
            "xAxis": {"type": "category", **achse}, "yAxis": {"type": "value", **achse, "scale": True}}


def _chart(opt: dict) -> None:
    """Legende in den Farben der Linien/Flächen (sonst nimmt ECharts seine Standardpalette)."""
    for se in opt["series"]:
        se["color"] = se.get("lineStyle", {}).get("color") or se.get("areaStyle", {}).get("color") or _T()["text3"]
        if se.get("lineStyle", {}).get("opacity") == 0 and "areaStyle" in se:
            se["color"] = se["areaStyle"]["color"]
    ui.echart(opt).classes("m-chart")


def _kpi(titel: str, wert: str, unter: str = "", stufe: str = "") -> None:
    with ui.element("div").classes("m-kpikarte"):
        ui.label(titel).classes("m-zweite")
        ui.label(wert).classes("m-kpiwert" + (f" m-{stufe}" if stufe in ("krit", "warn") else ""))
        if unter:
            ui.label(unter).classes("m-zweite")


# ---- Lage --------------------------------------------------------------------------------

def _lage(a) -> None:
    lg: ak.Lage = a.daten["lage"]
    stufe, text = ak.einschaetzung(lg.belegt, lg.kapazitaet)
    with a.inhalt:
        with ui.element("div").classes("m-kpis"):
            _kpi(f"Belegt am {lg.stichtag:%d.%m.%Y}", _zahl(lg.belegt), "Personen laut Pivot und Listen")
            _kpi("Kapazität", _zahl(lg.kapazitaet) if lg.kapazitaet else "–", "Netto" if not a.aw_brutto else "Brutto")
            _kpi("Auslastung", f"{round(100 * lg.anteil)} %" if lg.anteil is not None else "–", text.split(" · ")[0],
                 AMPEL.get(stufe, ""))
            _kpi("Frei", _zahl(lg.kapazitaet - lg.belegt) if lg.kapazitaet else "–", "Plätze")
        with ui.element("div").classes("m-zwei"):
            with ui.element("section").classes("m-block").style("grid-column: 1 / -1"):
                ui.label("Verlauf – 4 Monate zurück, 6 Monate Prognose").classes("m-btitel")
                v = lg.verlauf
                opt = _chart_basis()
                opt["xAxis"]["data"] = v["tage"]
                opt["series"] = [
                    {"name": "80 %-Spanne unten", "type": "line", "data": v["lo80"], "stack": "band", "lineStyle": {"opacity": 0},
                     "symbol": "none", "tooltip": {"show": False}},
                    {"name": "80 %-Spanne", "type": "line", "data": [None if h is None else round(h - l, 1) for h, l in
                                                                      zip(v["hi80"], v["lo80"])],
                     "stack": "band", "lineStyle": {"opacity": 0}, "symbol": "none", "areaStyle": {"color": _T()["akzent"], "opacity": .15}},
                    {"name": "Ist", "type": "line", "data": v["ist"], "symbol": "none", "lineStyle": {"color": _T()["text"], "width": 2}},
                    {"name": "Prognose", "type": "line", "data": v["prognose"], "symbol": "none",
                     "lineStyle": {"color": _T()["akzent"], "width": 2, "type": "dashed"}},
                ]
                if lg.kapazitaet:
                    opt["series"].append({"name": "Kapazität", "type": "line", "data": [lg.kapazitaet] * len(v["tage"]),
                                          "symbol": "none", "lineStyle": {"color": _T()["rot"], "width": 1, "type": "dotted"}})
                opt["legend"]["data"] = ["Ist", "Prognose", "80 %-Spanne", "Kapazität"]
                _chart(opt)
            with ui.element("section").classes("m-block"):
                ui.label("Zusammensetzung heute").classes("m-btitel")
                gesamt = max(lg.belegt, 1)
                for k, v_ in lg.teile.items():
                    with ui.element("div").classes("m-aw-haus"):
                        ui.label(k).classes("m-name")
                        with ui.element("div").classes("m-aw-balken"):
                            with ui.element("div").classes("m-spur"):
                                ui.element("div").classes("m-bar akzent").style(f"width:{max(1, round(100 * v_ / gesamt))}%")
                            ui.label(_zahl(v_)).classes("m-mono")
            with ui.element("section").classes("m-block"):
                ui.label("Häuser laut Pivot").classes("m-btitel")
                if not lg.haeuser:
                    ui.label("Keine Hausaufteilung im Pivot.").classes("m-ptext")
                hoechst = max([w for _h, w in lg.haeuser] + [1])
                for h, w in lg.haeuser:
                    with ui.element("div").classes("m-aw-haus"):
                        ui.label(h).classes("m-name")
                        with ui.element("div").classes("m-aw-balken"):
                            with ui.element("div").classes("m-spur"):
                                ui.element("div").classes("m-bar ok").style(f"width:{max(1, round(100 * w / hoechst))}%")
                            ui.label(_zahl(w)).classes("m-mono")
            with ui.element("section").classes("m-block"):
                ui.label("Anstehende Anreisen – nächste 21 Tage").classes("m-btitel")
                if not lg.anreisen:
                    ui.label("In den nächsten drei Wochen sind keine Anreisen geplant.").classes("m-ptext")
                else:
                    summe, tage = sum(x[2] for x in lg.anreisen), len({x[0] for x in lg.anreisen})
                    ui.label(f"{_zahl(summe)} Personen mit Internat an {tage} Anreisetag{'en' if tage > 1 else ''}").classes("m-ptext")
                    with ui.element("div").classes("m-aw-tab").style("grid-template-columns: 60px minmax(90px,1fr) 60px minmax(120px,2fr)"):
                        for t in ("Datum", "Standort", "Anzahl", "Bezeichnung"):
                            ui.label(t).classes("m-zweite")
                        for d, st, n, bez in lg.anreisen[:12]:
                            ui.label(f"{d:%d.%m.}").classes("m-mono")
                            ui.label(st).classes("m-zweite")
                            ui.label(str(n)).classes("m-mono")
                            attr(ui.label(bez).classes("m-zweite"), title=bez)
            if lg.hinweise:
                with ui.element("section").classes("m-block").style("grid-column: 1 / -1"):
                    ui.label("Hinweise zu den Daten").classes("m-btitel")
                    for h in lg.hinweise:
                        ui.label(h).classes("m-ptext")


# ---- Belegung im Zeitraum ----------------------------------------------------------------

def _belegung(a) -> None:
    zr: ak.Zeitraum = a.daten["zr"]
    with a.leiste:
        von = ui.input("von", value=a.aw_von.isoformat()).classes("m-feld").props("dense outlined dark type=date").style("width:160px")
        bis = ui.input("bis", value=a.aw_bis.isoformat()).classes("m-feld").props("dense outlined dark type=date").style("width:160px")

        def anwenden():
            try:
                return a.setzen(aw_von=date.fromisoformat(von.value), aw_bis=date.fromisoformat(bis.value))
            except (TypeError, ValueError):
                a.toast("Bitte gültige Tage wählen.", fehler=True)

        knopf("Anzeigen", anwenden, "primaer")
        st = a.daten["stichtag"]
        for text, v, b in (("Letzter Monat", (st.replace(day=1) - timedelta(days=1)).replace(day=1), st.replace(day=1) - timedelta(days=1)),
                           ("Dieses Jahr", date(st.year, 1, 1), st), ("Nächste 3 Monate", st, st + timedelta(days=91))):
            knopf(text, lambda v=v, b=b: a.setzen(aw_von=v, aw_bis=b), "leise")
    det: ak.BDetails = a.daten["det"]
    with a.inhalt:
        with ui.element("div").classes("m-kpis"):
            _kpi("Zeitraum", f"{zr.tage} Tage", f"{zr.von:%d.%m.%Y} – {zr.bis:%d.%m.%Y}")
            _kpi("Personentage", _zahl(zr.gesamt), f"Ø {_zahl(zr.mittel)} pro Tag")
            _kpi("Ø belegt", _zahl(zr.mittel, 1), "inkl. Prognose" if not all(det.ist) else f"{zr.tage} Tage Ist")
            _kpi("Ø Auslastung", f"{round(100 * det.auslastung)} %" if det.auslastung is not None else "–",
                 f"Spitze {round(100 * det.spitze)} %" if det.spitze is not None else "Kapazität fehlt")
            _kpi("Höchststand", _zahl(zr.hoechst), f"am {zr.hoechst_tag:%d.%m.%Y}" if zr.hoechst_tag else "")
            _kpi("Tiefststand", _zahl(det.tiefst), f"am {det.tiefst_tag:%d.%m.%Y}" if det.tiefst_tag else "")
        _belegung_charts(a, det, zr)
        with ui.element("div").classes("m-zwei"):
            with ui.element("section").classes("m-block"):
                ui.label("Personentage nach Kategorie").classes("m-btitel")
                ges = max(zr.gesamt, 1)
                for k, v in zr.personentage.items():
                    with ui.element("div").classes("m-aw-haus"):
                        ui.label(k).classes("m-name")
                        with ui.element("div").classes("m-aw-balken"):
                            with ui.element("div").classes("m-spur"):
                                ui.element("div").classes("m-bar akzent").style(f"width:{max(1, round(100 * v / ges))}%")
                            ui.label(_zahl(v)).classes("m-mono")
            with ui.element("section").classes("m-block"):
                ui.label("Gut zu wissen").classes("m-btitel")
                ui.label(f"{zr.anreisen} Anreise-Einträge im Zeitraum (Listen). Nach dem Pivot-Stichtag sind die Werte "
                         "Prognose plus Verträge – vorher Ist-Werte.").classes("m-ptext")


def _belegung_charts(a, det: ak.BDetails, zr) -> None:
    farben = [_T()["akzent"], _T()["blau"], _T()["gruen"], _T()["orange"], _T()["rot"], _T()["text2"], _T()["text3"]]
    with ui.element("div").classes("m-zwei"):
        with ui.element("section").classes("m-block m-breit"):
            ui.label(f"Tagesverlauf {ak.STANDORTE.get(a.aw_standort, '')} nach Belegungsart"
                     + (" – ab dem Stichtag Prognose" if not all(det.ist) else "")).classes("m-btitel")
            opt = _chart_basis()
            opt["xAxis"]["data"] = det.tage
            opt["yAxis"]["scale"] = False
            opt["series"] = [{"name": k, "type": "line", "stack": "art", "data": v, "symbol": "none",
                              "lineStyle": {"color": farben[i % len(farben)], "width": 1},
                              "areaStyle": {"color": farben[i % len(farben)], "opacity": .35}}
                             for i, (k, v) in enumerate(det.kategorien.items())]
            if zr.kapazitaet:
                opt["series"].append({"name": "Kapazität", "type": "line", "data": [zr.kapazitaet] * len(det.tage),
                                      "symbol": "none", "lineStyle": {"color": _T()["rot"], "width": 1, "type": "dotted"}})
            if not all(det.ist) and any(det.ist):
                stich = det.tage[sum(det.ist) - 1]
                opt["series"][0]["markLine"] = {"symbol": "none", "label": {"formatter": "Stichtag", "color": _T()["text3"]},
                                                "lineStyle": {"color": _T()["text3"], "type": "dashed"}, "data": [{"xAxis": stich}]}
            _chart(opt)
        with ui.element("section").classes("m-block"):
            ui.label("Personentage je Monat").classes("m-btitel")
            ui.label("Summe der belegten Plätze über alle Tage – hell = Prognose").classes("m-ptext")
            opt = _chart_basis()
            opt["xAxis"]["data"] = [m for m, _w, _i in det.monate]
            opt["yAxis"]["scale"] = False
            opt["series"] = [{"name": "Personentage", "type": "bar", "barMaxWidth": 28,
                              "data": [{"value": w_, "itemStyle": {"color": _T()["akzent"], "opacity": 1 if i_ else .4}}
                                       for _m, w_, i_ in det.monate], "lineStyle": {"color": _T()["akzent"]}}]
            _chart(opt)
        with ui.element("section").classes("m-block"):
            ui.label("Häuser").classes("m-btitel")
            ui.label("Belegung laut Pivot (nur Reha)" + (f", Stand {det.haeuser_stand:%d.%m.%Y}" if det.haeuser_stand else "")
                     ).classes("m-ptext")
            if not det.haeuser:
                ui.label("Für diesen Zeitraum keine Werte je Haus.").classes("m-zweite")
            else:
                with ui.element("div").classes("m-aw-tab").style("grid-template-columns: minmax(120px,1.4fr) 1fr 70px 70px 70px"):
                    for t in ("Haus", "Standort", "zuletzt", "Ø", "Höchst"):
                        ui.label(t).classes("m-zweite")
                    for h, st, zuletzt, mittel, hoch in det.haeuser:
                        ui.label(h).classes("m-name")
                        ui.label(st).classes("m-zweite")
                        ui.label(_zahl(zuletzt)).classes("m-mono")
                        ui.label(_zahl(mittel)).classes("m-mono")
                        ui.label(_zahl(hoch)).classes("m-mono")
        with ui.element("section").classes("m-block m-breit"):
            ui.label("Wochentags- und Saisonmuster").classes("m-btitel")
            ui.label("Ø Ist-Belegung (Reha) je Monat und Wochentag, letzte 4 Jahre").classes("m-ptext")
            werte = [[mi, wi, v] for wi, zeile in enumerate(det.muster) for mi, v in enumerate(zeile) if v is not None]
            if not werte:
                ui.label("Noch keine Ist-Werte.").classes("m-zweite")
            else:
                vs = [v for *_x, v in werte]
                opt = _chart_basis()
                opt["tooltip"] = {"position": "top"}
                opt["grid"] = {"left": 40, "right": 20, "top": 10, "bottom": 60}
                opt["xAxis"] = {**opt["xAxis"], "data": ak.MONATE, "splitArea": {"show": False}}
                opt["yAxis"] = {"type": "category", "data": ak.WOCHENTAGE, "inverse": True,
                                "axisLabel": {"color": _T()["text3"]}, "axisLine": {"lineStyle": {"color": _T()["rand2"]}}}
                opt["visualMap"] = {"min": min(vs), "max": max(vs), "calculable": False, "orient": "horizontal",
                                    "left": "center", "bottom": 0, "textStyle": {"color": _T()["text3"]},
                                    "inRange": {"color": [_T()["fl2"], _T()["akzent"]]}}
                opt["series"] = [{"name": "Ø belegt", "type": "heatmap", "data": werte,
                                  "label": {"show": True, "color": _T()["text"], "fontSize": 10},
                                  "lineStyle": {"color": _T()["akzent"]}}]
                opt.pop("legend", None)
                ui.echart(opt).classes("m-chart")


# ---- Prognose ----------------------------------------------------------------------------

CHARTS = {"trend": "Trend & Spanne", "reserve": "Kapazitäts-Reserve", "jahr": "Vorjahresvergleich"}


def _rgba(farbe: str, alpha: float) -> str:
    f = farbe.lstrip("#")
    if len(f) != 6:
        return farbe
    return f"rgba({int(f[0:2], 16)},{int(f[2:4], 16)},{int(f[4:6], 16)},{alpha})"


def _verlauf(farbe: str, oben: float, unten: float) -> dict:
    return {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
            "colorStops": [{"offset": 0, "color": _rgba(farbe, oben)}, {"offset": 1, "color": _rgba(farbe, unten)}]}


def _tooltip(t: dict) -> dict:
    """Glas-Tooltip in den Farben des Themes."""
    return {"trigger": "axis", "backgroundColor": _rgba(t.get("fls", t.get("fl", "#15171C")), .80), "borderColor": t["rand2"],
            "borderWidth": 1, "padding": [10, 12], "textStyle": {"color": t["text"], "fontSize": 12},
            "axisPointer": {"type": "line", "lineStyle": {"color": t["text3"], "type": "dashed"}},
            "extraCssText": "backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border-radius: 12px; "
                            "box-shadow: 0 14px 34px rgba(0,0,0,.28); min-width: 230px;"}


def _formatter(zs: list, kap: int, t: dict) -> str:
    """Smart-Tooltip: Ist, Erwartet, 80/95 %-Spanne und Rest-Kapazität – geordnet und farbig."""
    import json

    d = [{"m": ak.monat_text(z.monat), "p": z.art != "ist", "ist": z.ist if z.art == "ist" else None, "e": z.erwartet,
          "l8": z.lo80, "h8": z.hi80, "l9": z.lo95, "h9": z.hi95, "r": z.reserve} for z in zs]
    c = {"ist": t["text"], "e": t["akzent"], "b80": t["akzent"], "b95": t["text3"], "ok": t["gruen"], "rot": t["rot"]}
    return ("(ps) => { const D = " + json.dumps(d) + "; const C = " + json.dumps(c) + "; const K = " + str(kap or 0) + ";"
            " const i = ps[0].dataIndex; const d = D[i]; if (!d) return '';"
            " const f = v => v == null ? '–' : Math.round(v).toLocaleString('de-DE');"
            " const z = (c, t, v) => `<div style=\"display:flex;gap:18px;justify-content:space-between;line-height:1.7\">"
            "<span><span style=\"display:inline-block;width:8px;height:8px;border-radius:50%;background:${c};margin-right:7px\"></span>${t}</span>"
            "<b style=\"font-variant-numeric:tabular-nums\">${v}</b></div>`;"
            " let h = `<div style=\"font-weight:600;margin-bottom:6px\">${d.m} <span style=\"opacity:.6;font-weight:400\">"
            "${d.p ? '· Prognose' : '· Ist'}</span></div>`;"
            " if (d.ist != null) h += z(C.ist, 'Ist', f(d.ist));"
            " if (d.p) { h += z(C.e, 'Erwartet', f(d.e)); h += z(C.b80, '80 %-Spanne', f(d.l8) + ' – ' + f(d.h8));"
            " h += z(C.b95, '95 %-Spanne', f(d.l9) + ' – ' + f(d.h9)); }"
            " if (K) h += `<div style=\"border-top:1px solid ${C.b95}55;margin:6px 0 2px\"></div>` + z(d.r < 0 ? C.rot : C.ok,"
            " 'Rest-Kapazität', f(d.r) + ' von ' + f(K));"
            " return h; }")


def _basis(t: dict) -> dict:
    achse = {"axisLine": {"lineStyle": {"color": t["rand2"]}}, "axisLabel": {"color": t["text3"]},
             "splitLine": {"lineStyle": {"color": t["rand"]}}}
    return {"backgroundColor": "transparent", "textStyle": {"color": t["text2"], "fontFamily": "Segoe UI, Inter, sans-serif"},
            "grid": {"left": 52, "right": 86, "top": 46, "bottom": 34}, "tooltip": _tooltip(t),
            "legend": {"textStyle": {"color": t["text2"]}, "top": 4, "right": 10, "icon": "roundRect", "itemWidth": 14, "itemHeight": 8},
            "xAxis": {"type": "category", "boundaryGap": False, **achse}, "yAxis": {"type": "value", **achse},
            "animation": True, "animationDuration": 1200, "animationEasing": "cubicOut", "animationDurationUpdate": 250}


def _option(a, pg, kap: int, offset: float, art: str, pg_lang=None) -> dict:
    t = _T()
    o = _basis(t)
    titel = f"Belegung {ak.STANDORTE.get(a.aw_standort, '')} · {'Brutto' if a.aw_brutto else 'Netto'}"
    o["title"] = {"text": titel, "left": 8, "top": 4, "textStyle": {"color": t["text2"], "fontSize": 12, "fontWeight": 500}}
    kap_linie = {"name": "Kapazität", "type": "line", "symbol": "none", "color": t["rot"],
                 "lineStyle": {"color": t["rot"], "width": 1.5, "type": [6, 4]},
                 "endLabel": {"show": True, "formatter": "Kapazität {c}", "color": t["rot"], "fontSize": 11}}
    if art == "jahr":
        jv = ak.jahresvergleich(pg_lang or pg)
        o["xAxis"]["data"] = ak.MONATE
        o["xAxis"]["boundaryGap"] = False
        farben = [t["text3"], t["blau"], t["akzent"], t["orange"], t["gruen"]]
        reihen, legende = [], []
        bis_jahr = max((z.monat.year for z in (pg_lang or pg).zeilen if z.art != "prognose"), default=date.today().year) + 1
        jahre = [j for j, (ist, prog) in jv.items() if sum(v is not None for v in ist + prog) >= 3 and j <= bis_jahr][-4:]
        for n, jahr in enumerate(jahre):
            ist, prog = jv[jahr]
            f = farben[n % len(farben)]
            if any(v is not None for v in ist):
                reihen.append({"name": str(jahr), "type": "line", "data": ist, "color": f, "symbolSize": 5, "smooth": .25,
                               "lineStyle": {"color": f, "width": 2.5 if jahr == jahre[-1] or n == len(jahre) - 2 else 1.8}})
            if any(v is not None for v in prog):
                name = f"{jahr} Prognose" if any(v is not None for v in ist) else f"{jahr} (Prognose)"
                reihen.append({"name": name, "type": "line", "data": prog, "color": f, "symbol": "none", "smooth": .25,
                               "lineStyle": {"color": f, "width": 2, "type": "dashed"}})
            legende += [r["name"] for r in reihen[-2:] if r["name"] not in legende]
        if kap:
            reihen.append({**kap_linie, "data": [kap] * 12})
        o["series"], o["legend"]["data"] = reihen, legende + (["Kapazität"] if kap else [])
        o["yAxis"]["scale"] = True
        o["tooltip"]["valueFormatter"] = None
        return o
    zs = ak.szenario(pg, kap, offset)
    labels = [ak.monat_text(z.monat) for z in zs]
    o["xAxis"]["data"] = labels
    letzte_ist = max((i for i, z in enumerate(zs) if z.art == "ist"), default=None)
    o["tooltip"][":formatter"] = _formatter(zs, kap, t)
    if art == "reserve":
        belegt = [round(z.ist if z.art == "ist" and z.ist is not None else z.erwartet, 1) for z in zs]
        o["series"] = [
            {"name": "Belegt", "type": "line", "stack": "k", "data": belegt, "symbol": "none", "color": t["blau"],
             "lineStyle": {"color": t["blau"], "width": 2}, "areaStyle": {"color": _verlauf(t["blau"], .55, .25)}},
            {"name": "Freie Reserve", "type": "line", "stack": "k", "symbol": "none", "color": t["gruen"],
             "data": [round(max(kap - b, 0), 1) if kap else None for b in belegt], "lineStyle": {"width": 0},
             "areaStyle": {"color": _verlauf(t["gruen"], .32, .10)}},
            {"name": "Über Kapazität", "type": "line", "stack": "k", "symbol": "none", "color": t["rot"],
             "data": [round(max(b - kap, 0), 1) if kap else None for b in belegt], "lineStyle": {"width": 0},
             "areaStyle": {"color": _verlauf(t["rot"], .55, .30)}},
        ]
        if kap:
            o["series"].append({**kap_linie, "data": [kap] * len(zs)})
        o["legend"]["data"] = ["Belegt", "Freie Reserve", "Über Kapazität"] + (["Kapazität"] if kap else [])
        if letzte_ist is not None and letzte_ist + 1 < len(zs):
            o["series"][0]["markLine"] = {"symbol": "none", "silent": True, "data": [{"xAxis": labels[letzte_ist]}],
                                          "label": {"formatter": "Prognose →", "color": t["text3"], "position": "insideEndTop"},
                                          "lineStyle": {"color": t["text3"], "type": "dashed"}}
        return o

    def prog(feld):
        werte = [None if z.art == "ist" else round(getattr(z, feld), 1) for z in zs]
        if letzte_ist is not None and zs[letzte_ist].ist is not None and letzte_ist + 1 < len(zs):
            werte[letzte_ist] = round(zs[letzte_ist].ist, 1)        # an die Ist-Linie anschließen
        return werte
    u80, o80, u95, o95 = prog("lo80"), prog("hi80"), prog("lo95"), prog("hi95")
    breite = lambda u, ob: [None if x is None or y is None else round(y - x, 1) for x, y in zip(u, ob)]  # noqa: E731
    reihen = []
    if a.aw_95:
        reihen += [{"name": "u95", "type": "line", "data": u95, "stack": "b95", "symbol": "none", "lineStyle": {"opacity": 0},
                    "tooltip": {"show": False}, "silent": True},
                   {"name": "95 %-Spanne", "type": "line", "data": breite(u95, o95), "stack": "b95", "symbol": "none",
                    "color": t["text3"], "lineStyle": {"opacity": 0}, "areaStyle": {"color": _verlauf(t["akzent"], .16, .04)}}]
    reihen += [{"name": "u80", "type": "line", "data": u80, "stack": "b80", "symbol": "none", "lineStyle": {"opacity": 0},
                "tooltip": {"show": False}, "silent": True},
               {"name": "80 %-Spanne", "type": "line", "data": breite(u80, o80), "stack": "b80", "symbol": "none",
                "color": t["akzent"], "lineStyle": {"opacity": 0}, "areaStyle": {"color": _verlauf(t["akzent"], .34, .10)}},
               {"name": "Ist", "type": "line", "color": t["text"], "symbol": "circle", "symbolSize": 5, "z": 5,
                "data": [round(z.ist, 1) if z.art == "ist" and z.ist is not None else None for z in zs],
                "lineStyle": {"color": t["text"], "width": 2.5}, "itemStyle": {"color": t["text"]}},
               {"name": "Erwartet", "type": "line", "color": t["akzent"], "symbol": "none", "z": 6, "data": prog("erwartet"),
                "lineStyle": {"color": t["akzent"], "width": 2.5, "type": [7, 5]}}]
    if letzte_ist is not None and letzte_ist + 1 < len(zs):
        reihen[-1]["markLine"] = {"symbol": "none", "silent": True, "data": [{"xAxis": labels[letzte_ist]}],
                                  "label": {"formatter": "Prognose →", "color": t["text3"], "position": "insideEndTop"},
                                  "lineStyle": {"color": t["text3"], "type": "dashed"}}
    if kap:
        reihen.append({**kap_linie, "data": [kap] * len(zs)})
    if a.aw_backtest and pg.rueckblick:
        zusatz = {z.monat: z.vertraege for z in pg.zeilen}
        blind = {mon: p + zusatz.get(mon, 0.0) for mon, _ist, p in pg.rueckblick}
        reihen.append({"name": "Backtest (1 Monat vorher)", "type": "line", "symbolSize": 6, "color": t["orange"],
                       "data": [round(blind[z.monat], 1) if z.monat in blind else None for z in zs],
                       "lineStyle": {"color": t["orange"], "width": 1.5, "type": "dotted"}})
    o["series"] = reihen
    o["yAxis"]["scale"] = True                     # Ausschnitt um die Werte – Spannen bleiben sichtbar
    o["legend"]["data"] = ["Ist", "Erwartet", "80 %-Spanne"] + (["95 %-Spanne"] if a.aw_95 else []) + \
        (["Kapazität"] if kap else []) + (["Backtest (1 Monat vorher)"] if a.aw_backtest and pg.rueckblick else [])
    return o


def _prognose(a) -> None:
    pg: ak.Prognose | None = a.daten["pg"]
    with a.leiste:
        segmente({12: "12 Monate", 24: "24 Monate", 36: "36 Monate"}, a.aw_horizont, lambda h: a.setzen(aw_horizont=h))
        segmente({True: "95 %-Spanne an", False: "aus"}, a.aw_95, lambda v: a.setzen(aw_95=v, laden=False))
        segmente({False: "Backtest aus", True: "Backtest zeigen"}, a.aw_backtest, lambda v: a.setzen(aw_backtest=v, laden=False))
    with a.inhalt:
        if pg is None or not pg.zeilen:
            leer("Die Prognose ist noch nicht berechnet.")
            return
    kap_basis = pg.kapazitaet or 0
    if a.aw_kap is None or a.aw_kap_basis != kap_basis:       # neuer Standort/Netto-Brutto → zurück auf die echte Kapazität
        a.aw_kap, a.aw_kap_basis = kap_basis, kap_basis
    zustand = {"kap": a.aw_kap, "offset": a.aw_offset}
    with a.leiste:
        chart_box = {}

        async def png():
            chart = chart_box.get("c")
            if chart is None:
                return
            t = _T()
            try:
                url = await chart.run_chart_method("getDataURL", {"type": "png", "pixelRatio": 2,
                                                                  "backgroundColor": t.get("fls", t.get("fl"))}, timeout=10)
                pfad = await run.io_bound(ak.png_speichern, url, a.aw_standort)
            except Exception as exc:              # noqa: BLE001
                a.toast(f"Bild nicht gespeichert: {exc}", fehler=True)
                return
            a.toast("Diagramm als PNG gespeichert" if seiten._datei_oeffnen(pfad) else f"PNG gespeichert: {pfad}", rueck=False)

        async def export(art: str):
            try:
                pfad = await run.io_bound(ak.prognose_export, pg, zustand["kap"], zustand["offset"], a.aw_standort, a.aw_brutto, art)
            except PermissionError:
                a.toast("Die Datei ist noch geöffnet – bitte schließen und erneut versuchen.", fehler=True)
                return
            a.toast(("Excel" if art == "xlsx" else "CSV") + " gespeichert" if seiten._datei_oeffnen(pfad) else f"Gespeichert: {pfad}",
                    rueck=False)

        knopf("Chart als PNG", png, "", "image", "Diagramm ohne Bedienelemente als Bild – z. B. für PowerPoint").style("margin-left:auto")
        with knopf("Daten exportieren", None, "", "download"):
            with ui.menu().props('dark class="m-menue"'):
                ui.menu_item("Als Excel (.xlsx)", lambda: export("xlsx"))
                ui.menu_item("Als CSV (Excel-kompatibel, ;)", lambda: export("csv"))
    kuenftig = [z for z in pg.zeilen if z.art != "ist"]
    naechst = kuenftig[1] if len(kuenftig) > 1 else (kuenftig[0] if kuenftig else None)
    with a.inhalt:
        # Kernaussagen (einklappbar)
        with ui.element("section").classes("m-takeaways"):
            kopf = ui.element("button").classes("m-tk-kopf")
            with kopf:
                ui.icon("insights")
                ui.label("Kernaussagen").classes("m-btitel")
                ui.label("für die Geschäftsführung").classes("m-zweite")
                pfeil = ui.icon("expand_less" if a.aw_summary else "expand_more").style("margin-left:auto")
            punkte = ui.element("ul").classes("m-tk-liste")
            punkte.set_visibility(a.aw_summary)

            def kernaussagen_zeichnen():
                punkte.clear()
                with punkte:
                    for satz in ak.kernaussagen(pg, zustand["kap"], zustand["offset"]):
                        ui.html(f"<li>{satz}</li>", sanitize=False)

            def umklappen():
                a.aw_summary = not a.aw_summary
                punkte.set_visibility(a.aw_summary)
                pfeil.props(f'name={"expand_less" if a.aw_summary else "expand_more"}')
            kopf.on("click", umklappen)
            kernaussagen_zeichnen()
        spitze = max(kuenftig[:12], key=lambda z: z.hi80, default=None)
        with ui.element("div").classes("m-kpis"):
            if naechst:
                _kpi(f"Erwartet {ak.monat_text(naechst.monat)}", _zahl(naechst.erwartet),
                     f"80 %: {_zahl(naechst.lo80)} – {_zahl(naechst.hi80)}")
            if spitze and pg.kapazitaet:
                st, tx = ak.einschaetzung(spitze.hi80, pg.kapazitaet)
                _kpi("Höchste Auslastung (12 Monate)", f"{round(100 * spitze.hi80 / pg.kapazitaet)} %",
                     f"{ak.monat_text(spitze.monat)}, vorsichtig geschätzt", AMPEL.get(st, ""))
            _kpi("Ø Fehler 1 Monat voraus", f"± {_zahl(pg.mae_1m, 1)}" if pg.mae_1m is not None else "–",
                 f"12 Monate voraus: ± {_zahl(pg.mae, 1)}" if pg.mae is not None else "")
            _kpi("Treffer 80 %-Spanne", f"{round(100 * pg.abdeckung80)} %" if pg.abdeckung80 is not None else "–",
                 "Backtest-Fälle innerhalb (Soll 80 %)")
        with ui.element("div").classes("m-zwei"):
            with ui.element("section").classes("m-block").style("grid-column: 1 / -1"):
                with ui.element("div").classes("m-paktionen").style("align-items:center"):
                    ui.label({"trend": "Monatsverlauf – Ø belegte Plätze je Monat", "reserve": "Belegt und freie Reserve bis zur Kapazität",
                              "jahr": "Saisonaler Vorjahresvergleich – Ø belegte Plätze je Monat"}[a.aw_chart]).classes("m-btitel")
                    with ui.element("div").style("margin-left:auto"):
                        segmente(CHARTS, a.aw_chart, lambda c: a.setzen(aw_chart=c, laden=c == "jahr" or a.aw_chart == "jahr"))
                if a.aw_chart == "trend" and a.aw_backtest and not pg.rueckblick:
                    ui.label("Den Backtest gibt es je Standort – bitte oben einen Standort wählen.").classes("m-pille warn")
                elif a.aw_chart == "trend" and a.aw_backtest:
                    ui.label("Backtest: was das Modell für jeden der letzten Monate einen Monat vorher vorhergesagt hätte – nur "
                             "mit den damaligen Daten. Je näher an „Ist“, desto verlässlicher.").classes("m-ptext")
                chart = ui.echart(_option(a, pg, zustand["kap"], zustand["offset"], a.aw_chart, a.daten.get("pg_lang"))).classes(
                    "m-chart m-chart-gross")
                chart_box["c"] = chart
            # Was wäre wenn
            with ui.element("section").classes("m-block").style("grid-column: 1 / -1"):
                with ui.element("div").classes("m-paktionen").style("align-items:center"):
                    ui.label("Reicht die Kapazität? – Was wäre, wenn …").classes("m-btitel")
                    knopf("Zurücksetzen", lambda: setzen_szenario(kap_basis, 0.0, True), "leise", "restart_alt").style("margin-left:auto")
                lo, hi = min(400, int(kap_basis * .5) or 400), max(1200, int(kap_basis * 1.5) or 1200)
                with ui.element("div").classes("m-szenario"):
                    with ui.element("div").classes("m-sz-zeile"):
                        ui.label("Kapazität").classes("m-name")
                        regler = ui.slider(min=lo, max=hi, step=1, value=zustand["kap"]).props("dark label color=indigo-4").classes("m-sz-regler")
                        wenn = ui.number(value=zustand["kap"], min=0, max=5000, step=1, format="%d").classes("m-feld klein").props(
                            "dense outlined dark")
                        ui.label(f"Plätze (echt: {kap_basis})").classes("m-zweite")
                    with ui.element("div").classes("m-sz-zeile"):
                        ui.label("Auslastung").classes("m-name")
                        off = ui.slider(min=-15, max=15, step=1, value=zustand["offset"]).props("dark label color=indigo-4").classes("m-sz-regler")
                        off_text = ui.label("").classes("m-mono").style("width:60px")
                        ui.label("gegenüber der Prognose (nur Prognosemonate)").classes("m-zweite")
                tabelle = ui.element("div")

                def tabelle_zeichnen():
                    tabelle.clear()
                    sp = "minmax(120px,1fr) 90px 130px 130px 90px 90px minmax(180px,1.2fr)"
                    zs = [z for z in ak.szenario(pg, zustand["kap"], zustand["offset"]) if z.art != "ist"][:a.aw_horizont]
                    with tabelle:
                        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
                            for t_ in ("Monat", "Erwartet", "80 %-Spanne", "95 %-Spanne", "Gesichert", "Reserve", "Einschätzung"):
                                ui.label(t_)
                        for z in zs:
                            with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                                ui.label(ak.monat_text(z.monat) + (" (laufend)" if z.art == "laufend" else "")).classes("m-name")
                                ui.label(_zahl(z.erwartet)).classes("m-mono")
                                ui.label(f"{_zahl(z.lo80)} – {_zahl(z.hi80)}").classes("m-mono")
                                ui.label(f"{_zahl(z.lo95)} – {_zahl(z.hi95)}").classes("m-mono")
                                ui.label(_zahl(z.gesichert)).classes("m-mono")
                                ui.label(_zahl(z.reserve) if z.reserve is not None else "–").classes(
                                    "m-mono" + (" m-krit" if z.reserve is not None and z.reserve < 0 else ""))
                                with ui.element("div"):
                                    ui.label(z.text).classes(f"m-pille {AMPEL.get(z.stufe, '')}")

                def setzen_szenario(kap: int | None = None, offset: float | None = None, regler_mit: bool = False):
                    if kap is not None:
                        zustand["kap"] = a.aw_kap = max(0, int(kap))
                    if offset is not None:
                        zustand["offset"] = a.aw_offset = float(offset)
                    if regler_mit or (kap is not None and regler.value != zustand["kap"]):
                        regler.set_value(min(max(zustand["kap"], lo), hi))
                    if regler_mit or (kap is not None and int(wenn.value or 0) != zustand["kap"]):
                        wenn.set_value(zustand["kap"])
                    if regler_mit:
                        off.set_value(zustand["offset"])
                    off_text.set_text(f"{zustand['offset']:+.0f} %")
                    neu = _option(a, pg, zustand["kap"], zustand["offset"], a.aw_chart, a.daten.get("pg_lang"))
                    neu["animationDuration"] = 0           # beim Schieben ohne Neuaufbau-Animation – sofort
                    chart.options.clear()
                    chart.options.update(neu)
                    chart.update()
                    tabelle_zeichnen()
                    kernaussagen_zeichnen()

                regler.on("update:model-value", lambda e: setzen_szenario(kap=e.args), throttle=0.05, leading_events=False)
                off.on("update:model-value", lambda e: setzen_szenario(offset=e.args), throttle=0.05, leading_events=False)
                wenn.on_value_change(lambda e: setzen_szenario(kap=int(e.value or 0)) if (e.value or 0) != zustand["kap"] else None)
                off_text.set_text(f"{zustand['offset']:+.0f} %")
                tabelle_zeichnen()
            with ui.element("section").classes("m-block"):
                ui.label("So wurde gerechnet").classes("m-btitel")
                if pg.modell:
                    ui.label(f"Gewählt: {pg.modell} – {pg.beschreibung}. Alle Kandidaten wurden für vergangene Monate blind "
                             "gerechnet (nur mit damaligen Daten); gewählt wurde das Modell mit dem kleinsten mittleren "
                             "Fehler. Die Spanne wächst mit dem Abstand zur Gegenwart. Die Prognose fällt nie unter den "
                             "gesicherten Bestand; Mieter, Gäste und Verträge werden fest addiert.").classes("m-ptext")
                for name, fehler in pg.kandidaten[:6]:
                    with ui.element("div").classes("m-liste-zeile"):
                        ui.label("")
                        ui.label(name).classes("m-name")
                        ui.label(f"± {_zahl(fehler, 1)}").classes("m-mono")
            with ui.element("section").classes("m-block"):
                ui.label("Backtest: Blind-Prognosen je Monat").classes("m-btitel")
                if not pg.rueckblick:
                    ui.label("Den Backtest gibt es je Standort – bitte oben einen Standort wählen.").classes("m-ptext")
                else:
                    abw = [abs(p - ist) for _m, ist, p in pg.rueckblick]
                    ui.label(f"Jeweils einen Monat vorher gerechnet, nur mit damaligen Daten · Ø Abweichung ± {_zahl(sum(abw) / len(abw), 1)} "
                             f"· größte ± {_zahl(max(abw), 1)}").classes("m-ptext")
                    knopf("Im Diagramm zeigen" if not a.aw_backtest else "Im Diagramm ausblenden",
                          lambda: a.setzen(aw_backtest=not a.aw_backtest, laden=False), "leise", "show_chart")
                for mon, ist, p in list(reversed(pg.rueckblick)):
                    with ui.element("div").classes("m-liste-zeile"):
                        ui.label(ak.monat_text(mon)).classes("m-zweite").style("width:80px")
                        ui.label(f"Ist {_zahl(ist)} · Prognose {_zahl(p)}").classes("m-name")
                        ui.label(("+" if p > ist else "−") + _zahl(abs(p - ist))).classes("m-mono")
