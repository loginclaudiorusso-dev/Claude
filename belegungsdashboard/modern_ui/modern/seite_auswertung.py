"""Seite „Auswertung“: Lage (heute + Verlauf), Belegung im Zeitraum, Prognose je Monat und Zimmer & Engpässe.
Standort und Netto/Brutto gelten für die ersten drei Ansichten."""

from __future__ import annotations

from datetime import date, timedelta

from nicegui import ui

from . import auswertung_kern as ak
from . import seite_prognose, seiten
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
        seite_prognose.daten(a, ds)


def zeichnen(a) -> None:
    ansicht = a.ansicht_von("auswertung", "lage")
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("auswertung", ansicht=v))
    if ansicht == "zimmer":
        seiten.aw_zeichnen(a)
        return
    if ansicht != "prognose":                  # Prognose: Standort, Netto/Brutto und Zeitraum stehen direkt über dem Graph
        with a.leiste:
            segmente(ak.STANDORTE, a.aw_standort, lambda s: a.setzen(aw_standort=s, nur_seite=True), sofort=True)
            segmente({False: "Netto", True: "Brutto"}, a.aw_brutto, lambda b: a.setzen(aw_brutto=b, nur_seite=True), sofort=True)
    if "fehler" in a.daten:
        with a.inhalt:
            leer(a.daten["fehler"])
        return
    {"lage": _lage, "belegung": _belegung, "prognose": seite_prognose.zeichnen}[ansicht](a)


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


