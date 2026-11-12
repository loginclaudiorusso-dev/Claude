"""Seite „Auswertung“: Lage (heute + Verlauf), Belegung im Zeitraum, Prognose je Monat und Zimmer & Engpässe.
Standort und Netto/Brutto gelten für die ersten drei Ansichten."""

from __future__ import annotations

import json

from datetime import date, timedelta

from nicegui import ui

from . import auswertung_kern as ak
from . import seite_prognose, seiten
from . import diagramm_stil as _ds
from . import themes
from .ui_bausteine import attr, knopf, leer, segmente


def _T() -> dict:
    """Diagrammfarben des gewählten Designs (ECharts nimmt Farben aus Python, nicht aus dem CSS)."""
    return themes.farben(themes.AKTIV)


ANSICHTEN = {"lage": "Überblick", "belegung": "Belegung", "prognose": "Belegungs\u00adprognose", "massnahmen": "Maßnahmen",
             "zimmer": "Engpässe"}                       # 0.69: eindeutiger (kein „Zimmer“ doppelt neben Zimmer & Haus)
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
    if ansicht == "massnahmen":                 # 0.50: eigene Quelle (Maßnahmen-Pivot), Standort-Pivot nur zum Abgleich
        from . import seite_massnahmen

        seite_massnahmen.daten(a)
        return
    ds, fehler = ak.datenstand()
    if ds is None:
        a.daten = {"fehler": fehler}
        return
    if ansicht == "lage":
        a.daten = {"lage": ak.lage(ds, a.aw_standort, a.aw_brutto)}
    elif ansicht == "belegung":
        mzr = _mieter_zr(a)
        a.daten = {"zr": ak.zeitraum(ds, a.aw_standort, a.aw_von, a.aw_bis, a.aw_brutto, mzr), "stichtag": ds.stichtag,
                   "det": ak.belegung_details(ds, a.aw_standort, a.aw_von, a.aw_bis, a.aw_brutto,
                                              mzr)}
    else:
        seite_prognose.daten(a, ds)


def zeichnen(a) -> None:
    ansicht = a.ansicht_von("auswertung", "lage")
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("auswertung", ansicht=v), ansicht=True)
    if ansicht == "zimmer":
        seiten.aw_zeichnen(a)
        return
    if ansicht == "massnahmen":
        from . import seite_massnahmen

        seite_massnahmen.zeichnen(a)
        return
    if ansicht != "prognose":                  # Prognose: Standort, Netto/Brutto und Zeitraum stehen direkt über dem Graph
        with a.leiste:
            segmente(ak.STANDORTE, a.aw_standort, lambda s: a.setzen(aw_standort=s, nur_seite=True), sofort=True)
            segmente({False: "Netto", True: "Brutto"}, a.aw_brutto, lambda b: a.setzen(aw_brutto=b, nur_seite=True), sofort=True)
    if "fehler" in a.daten:
        with a.inhalt:
            leer(a.daten["fehler"])
            if "Pivot" in a.daten["fehler"]:         # 0.68: leerer Zustand mit direktem Weg zur Lösung
                with ui.element("div").style("display:flex; justify-content:center"):
                    knopf("Daten & Import öffnen", lambda: a.oeffnen("daten"), "primaer", "upload_file")
        return
    {"lage": _lage, "belegung": _belegung, "prognose": seite_prognose.zeichnen}[ansicht](a)


def _chart_basis() -> dict:
    achse = {"axisLine": {"lineStyle": {"color": _T()["rand2"]}}, "axisLabel": {"color": _T()["text3"]},
             "splitLine": {"lineStyle": {"color": _T()["rand"]}}}
    return {"backgroundColor": "transparent", "textStyle": {"color": _T()["text2"], "fontFamily": "Segoe UI, sans-serif"},
            "grid": {"left": 48, "right": 20, "top": 30, "bottom": 30}, "tooltip": {"trigger": "axis"},
            "legend": {"textStyle": {"color": _T()["text2"]}, "top": 0, "right": 10},
            "xAxis": {"type": "category", **achse}, "yAxis": {"type": "value", **achse, "scale": True}}


def _chart(opt: dict, a=None) -> None:
    """Legende in den Farben der Linien/Flächen (sonst nimmt ECharts seine Standardpalette)."""
    for se in opt["series"]:
        se["color"] = se.get("lineStyle", {}).get("color") or se.get("areaStyle", {}).get("color") or _T()["text3"]
        if se.get("lineStyle", {}).get("opacity") == 0 and "areaStyle" in se:
            se["color"] = se["areaStyle"]["color"]
    from . import diagramm_stil

    chart = ui.echart(diagramm_stil.anwenden(opt, themes.AKTIV)).classes("m-chart")      # 0.66: Diagrammtyp aus den Optionen
    if a is not None:                          # 0.75: Klick auf einen Monat/Tag → Werte und Berechnung im Detailpanel
        from . import diagramm_ui

        diagramm_ui.anbinden(a, chart)


def _tagesverlauf_karte(a, det: ak.BDetails, zr, farben: list[str]) -> None:
    """0.87: Tagesverlauf als Diagramm-Karte – Tageswerte als gestapelte Stufenflächen je Belegungsart."""
    from . import blick_kern as bk
    from . import diagramm_karte, diagramm_stil

    n = len(det.tage)
    stand = a.daten.get("stichtag") or a.heute
    opt = _chart_basis()
    opt["xAxis"]["data"] = det.tage
    opt["yAxis"]["scale"] = False
    fb = lambda i, k: diagramm_stil.gruppen_farbe(k, i, farben)  # noqa: E731 – 0.94: feste Gruppenfarben
    opt["series"] = [{"name": k, "rolle": "stapel", "type": "line", "stack": "art", "data": v, "symbol": "none",
                      "color": fb(i, k), "lineStyle": {"color": fb(i, k), "width": 1},
                      "areaStyle": {"color": fb(i, k), "opacity": .35}}
                     for i, (k, v) in enumerate(det.kategorien.items())]
    if zr.kapazitaet:
        opt["series"].append({"name": "Kapazität", "rolle": "kapazitaet", "type": "line", "data": [zr.kapazitaet] * n})
    k_ist = sum(det.ist)
    teil = 0 < k_ist < n
    summen = [round(sum(v[i] or 0 for v in det.kategorien.values()), 1) for i in range(n)]
    tage = [zr.von + timedelta(days=i) for i in range(n)]
    if n <= 62:                                       # 0.95: Säulen je Tag (bis zwei Monate) – sonst Flächen wie bisher
        opt = _tage_saeulen(det, zr, tage, summen, farben, k_ist)
    else:
        opt = diagramm_stil.einheitlich(opt, _T(), det.tage[k_ist - 1] if teil else None,
                                        det.tage[k_ist] if teil else None, tageswerte=True)
    blick = bk.tage(tage, summen, list(det.ist), stand, zr.kapazitaet or None)
    ort = ak.STANDORTE.get(a.aw_standort, "")
    with diagramm_karte.Karte(a, "Tagesverlauf nach Belegungsart",
                              f"{ort} · {'Brutto' if a.aw_brutto else 'Netto'} · {zr.von:%d.%m.%Y} – {zr.bis:%d.%m.%Y} · "
                              f"Datenstand {stand:%d.%m.%Y}", blick) as k:
        k.anbinden(k.chart(opt))


def _tage_saeulen(det: ak.BDetails, zr, tage: list, summen: list, farben: list[str], k_ist: int) -> dict:
    """0.95 (Auftrag „Diagramme für Laien“, Diagramm 3): gestapelte Säulen mit 2 px Abstand, feste Gruppenfarben, über
    jeder Säule nur die Summe, Einzelwerte im Tooltip und einmal rechts neben der letzten Säule, Wochenenden grau
    hinterlegt, ab dem Datenstand heller und „Prognose“, x-Achse mit Wochentag."""
    from . import blick_kern as bk
    from . import diagramm_stil

    t = _T()
    n = len(tage)
    x = [bk.tag_beschriftung(d) for d in tage]
    kat = [(k, v) for k, v in det.kategorien.items() if k != "Anreise" and any(v)]
    reihen = []
    for i, (k, v) in enumerate(kat):
        f = diagramm_stil.gruppen_farbe(k, i, farben)
        reihen.append({"name": k, "type": "bar", "stack": "art", "barCategoryGap": "28%",
                       "itemStyle": {"color": f, "borderColor": t.get("fl", "#fff"), "borderWidth": 2},
                       "data": [{"value": round(w or 0, 1), "itemStyle": {"opacity": 1 if j < k_ist else .45}}
                                for j, w in enumerate(v)]})
    if reihen:                                        # Summe über der Säule (nur dort), Einzelwerte rechts der letzten
        reihen[-1]["label"] = {"show": n <= 31, "position": "top", "fontSize": 13, "color": t["text"], "fontWeight": 600,
                               ":formatter": "(p) => " + json.dumps([round(s_) for s_ in summen]) + "[p.dataIndex]"}
        for se, (k, v) in zip(reihen, kat):
            letzt = se["data"][-1]
            letzt["label"] = {"show": True, "position": "right", "fontSize": 13, "color": t["text"],
                              "formatter": f"{k} {bk.zahl(v[-1] or 0)}", "distance": 8}
    wochenende = [[{"xAxis": x[j], "itemStyle": {"color": "rgba(128,128,128,0.12)"}}, {"xAxis": x[j]}]
                  for j, d in enumerate(tage) if d.weekday() >= 5]
    if wochenende:
        wochenende[0][0]["label"] = {"show": True, "formatter": "Wochenende", "position": "insideTop",
                                     "color": t["text2"], "fontSize": 12}
    marken = list(wochenende)
    if 0 < k_ist < n:
        marken.append([{"xAxis": x[k_ist], "itemStyle": {"color": "rgba(0,127,127,0.06)"},
                        "label": {"show": True, "formatter": "Prognose", "position": "insideTopRight", "color": t["text2"],
                                  "fontSize": 13}}, {"xAxis": x[-1]}])
    linien = []
    if zr.kapazitaet:
        linien.append({"yAxis": zr.kapazitaet, "lineStyle": {"color": t["text"], "width": 2, "type": "solid"},
                       "label": {"formatter": f"Voll: {bk.zahl(zr.kapazitaet)} Plätze", "position": "insideEndTop",
                                 "fontSize": 13, "color": t["text"]}})
    if reihen:
        reihen[0]["markArea"] = {"silent": True, "data": marken}
        reihen[0]["markLine"] = {"silent": True, "symbol": "none", "data": linien}
    oben = max(summen + [zr.kapazitaet or 0, 1])
    return {"animation": False, "grid": {"left": 48, "right": 120, "top": 40, "bottom": 34},
            "legend": {"top": 0, "left": 0, "data": [k for k, _v in kat], "textStyle": {"color": t["text"], "fontSize": 13}},
            "tooltip": {"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "textStyle": {"fontSize": 13},
                        ":position": "(p, params, dom, rect, size) => [Math.min(p[0] + 24, size.viewSize[0] - "
                                     "size.contentSize[0] - 8), 8]"},
            "xAxis": {"type": "category", "data": x, "axisLabel": {"color": t["text2"], "fontSize": 13,
                                                                 "interval": 0 if n <= 14 else "auto"}},
            "yAxis": {"type": "value", "min": 0, "max": int(oben * 1.08) + 1,
                      "axisLabel": {"color": t["text2"], "fontSize": 13},
                      "splitLine": {"lineStyle": {"color": t["rand"], "opacity": .5}}},
            "series": reihen}


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
                     "stack": "band", "lineStyle": {"opacity": 0}, "symbol": "none", "areaStyle": {"color": _ds.band_flaeche(_T())}},
                    {"name": "Ist", "type": "line", "data": v["ist"], "symbol": "none", "lineStyle": {"color": _T()["text"], "width": 2}},
                    {"name": "Prognose", "type": "line", "data": v["prognose"], "symbol": "none",
                     "lineStyle": {"color": _T()["akzent"], "width": 2, "type": "dashed"}},
                ]
                if lg.kapazitaet:
                    opt["series"].append({"name": "Kapazität", "type": "line", "data": [lg.kapazitaet] * len(v["tage"]),
                                          "symbol": "none", "lineStyle": {"color": _T()["rot"], "width": 1, "type": "dotted"}})
                opt["legend"]["data"] = ["Ist", "Prognose", "80 %-Spanne", "Kapazität"]
                _chart(opt, a)
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

def _mieter_zr(a) -> list:
    """0.93: Mieter aus den Mietverträgen (und laut Zimmerplan) – dieselbe Quelle wie die Prognose."""
    from . import analytik_kern as an

    try:
        return an.mieter_zeitraeume(getattr(a, "stand", None))
    except Exception:                          # noqa: BLE001 – ohne Verträge bleibt die bisherige Sicht
        return []


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
        # 0.93: vom heutigen Tag aus (nicht vom Datenstand) – im November ist „Letzter Monat“ der Oktober
        h = a.heute
        ende_vormonat = h.replace(day=1) - timedelta(days=1)
        for text, v, b in (("Heute", h, h), ("Dieser Monat", h.replace(day=1), h),
                           ("Letzter Monat", ende_vormonat.replace(day=1), ende_vormonat),
                           ("Dieses Jahr", date(h.year, 1, 1), h), ("Nächste 3 Monate", h, h + timedelta(days=91))):
            knopf(text, lambda v=v, b=b: a.setzen(aw_von=v, aw_bis=b),
                  "" if (a.aw_von, a.aw_bis) == (v, b) else "leise")
        from . import diagramm_karte

        diagramm_karte.modus_wahl(a)                    # 0.89: Klassisch | Karte | Einfach
    det: ak.BDetails = a.daten["det"]
    from . import diagramm_karte as _dk

    if _dk.modus() != "klassisch":                   # 0.95: drei Kennzahlen statt sechs
        with a.inhalt:
            with ui.element("div").classes("m-kpis"):
                with ui.element("div").classes("m-kpikarte"):
                    ui.label("Im Schnitt belegt").classes("m-zweite")
                    ui.label(_zahl(zr.mittel) + (f" von {_zahl(zr.kapazitaet)}" if zr.kapazitaet else "")).classes("m-kpiwert")
                    if zr.kapazitaet:
                        with ui.element("div").classes("m-spur").style("margin:4px 0"):
                            ui.element("div").classes("m-bar akzent").style(
                                f"width:{max(1, min(100, round(100 * zr.mittel / zr.kapazitaet)))}%")
                        ui.label(f"{round(100 * zr.mittel / zr.kapazitaet)} % der Plätze · {zr.tage} Tage").classes("m-zweite")
                _kpi("Vollster Tag", _zahl(zr.hoechst), f"am {zr.hoechst_tag:%d.%m.%Y}" if zr.hoechst_tag else "")
                _kpi("Leerster Tag", _zahl(det.tiefst), f"am {det.tiefst_tag:%d.%m.%Y}" if det.tiefst_tag else "")
            _belegung_charts(a, det, zr)
            _belegung_unten(a, zr)
        return
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
        _belegung_unten(a, zr)


def _belegung_unten(a, zr) -> None:
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


def _belegung_einfach(a, det: ak.BDetails, zr, farben) -> None:
    """0.93 „Einfach“: die Aussage als Überschrift, die Gesamtbelegung als eine Fläche ab 0 gegen „voll“, darunter je
    Gruppe ein Balken mit ihrem Anteil – keine gestapelten Linien."""
    from . import blick_kern as bk

    s = bk.belegung_zeitraum(zr.von, zr.bis, {k: v for k, v in det.kategorien.items() if k != "Anreise"},
                              zr.kapazitaet or None, all(det.ist))
    with ui.element("section").classes("m-gf"):
        ui.label(s.titel).classes("m-gf-titel")
        ui.label(s.untertitel).classes("m-gf-unter")
        summe = [round(sum(v[i] for k, v in det.kategorien.items() if k != "Anreise"), 1) for i in range(len(det.tage))]
        t = _T()
        opt = {"animation": False, "grid": {"left": 44, "right": 120, "top": 24, "bottom": 28},
               "tooltip": {"trigger": "axis"},
               "xAxis": {"type": "category", "data": det.tage, "boundaryGap": False,
                         "axisLabel": {"color": t["text2"]}, "axisLine": {"lineStyle": {"color": t["rand"]}}},
               "yAxis": {"type": "value", "min": 0, "max": round(max([zr.kapazitaet or 0] + summe) * 1.03),
                         "axisLabel": {"color": t["text2"]}, "splitLine": {"lineStyle": {"color": t["rand"], "opacity": .5}}},
               "series": [{"name": "belegt", "type": "line", "data": summe, "symbol": "none",
                           "lineStyle": {"color": t["akzent"], "width": 2}, "areaStyle": {"color": t["akzent"], "opacity": .14},
                           "markLine": {"silent": True, "symbol": "none", "data": ([{
                               "yAxis": zr.kapazitaet, "lineStyle": {"color": t["text"], "type": "solid"},
                               "label": {"formatter": f"voll: {bk.zahl(zr.kapazitaet)} Plätze", "position": "end",
                                         "color": t["text"], "fontWeight": 600}}] if zr.kapazitaet else [])}}]}
        ui.echart(opt).classes("m-gf-chart").style("height:300px !important")
        ui.label("Belegte Plätze je Tag" + ("" if all(det.ist) else " · ab dem Datenstand Prognose")
                 + " · Achse beginnt bei 0").classes("m-gf-fuss")
    with ui.element("section").classes("m-einfach").style("margin-top:14px"):
        ui.label("Wer belegt die Plätze? (Ø je Tag im Zeitraum)").classes("m-btitel")
        hoch = max([g[1] for g in s.gruppen] + [1])
        with ui.element("div").classes("m-einfach-liste"):
            for name, mittel, anteil in s.gruppen:
                with ui.element("div").classes("m-einfach-zeile"):
                    ui.label(name).classes("m-einfach-name")
                    with ui.element("div").classes("m-einfach-spur"):
                        from . import diagramm_stil

                        f_ = diagramm_stil.GRUPPEN_FARBEN.get(name)
                        ui.element("div").classes("m-einfach-balken").style(
                            f"width:{100 * mittel / hoch:.1f}%" + (f";background:{f_}" if f_ else ""))
                    ui.label(f"{bk.zahl(mittel)} · {round(100 * anteil)} %").classes("m-einfach-wert")


def _anteile(a, det: ak.BDetails, farben: list[str]) -> None:
    """0.96: Anteile der Gruppen (Reha, Umschüler, Mieter …) in Personentagen – insgesamt und im Verlauf."""
    from . import anteile_kern as ank
    from . import anteile_ui

    if len([k for k, v in det.kategorien.items() if any(v)]) < 2:
        return
    if len(det.tage) > 45:
        achse, werte, prog = ank.monate_buendeln(det.tage, det.kategorien, det.ist)
        verlauf = "Personentage je Monat (P = Prognose)"
    else:
        achse, werte, prog = list(det.tage), det.kategorien, [not i for i in det.ist]
        verlauf = "je Tag (P = Prognose)"
    an = ank.berechnen(werte, achse, prog, fenster=list(range(len(achse))),
                       fenster_text=f"Personentage {a.aw_von:%d.%m.%Y} – {a.aw_bis:%d.%m.%Y}")
    fb = {k: _ds.gruppen_farbe(k, i, farben) for i, k in enumerate(det.kategorien)}
    with ui.element("div").classes("m-breit"):
        anteile_ui.zeigen(a, "Anteile der Gruppen", an, fb, verlauf)


def _belegung_charts(a, det: ak.BDetails, zr) -> None:
    farben = [_T()["akzent"], _T()["blau"], _T()["gruen"], _T()["orange"], _T()["rot"], _T()["text2"], _T()["text3"]]
    from . import diagramm_karte

    with ui.element("div").classes("m-zwei"):
        if diagramm_karte.modus() == "klassisch":         # 0.89: wie bis 0.86
            with ui.element("section").classes("m-block m-breit"):
                ui.label(f"Tagesverlauf {ak.STANDORTE.get(a.aw_standort, '')} nach Belegungsart"
                         + (" – ab dem Stichtag Prognose" if not all(det.ist) else "")).classes("m-btitel")
                opt = _chart_basis()
                opt["xAxis"]["data"] = det.tage
                opt["yAxis"]["scale"] = False
                from . import diagramm_stil as _ds        # 0.95: feste Gruppenfarben auch hier (Reha ≠ Mieter)

                opt["series"] = [{"name": k, "type": "line", "stack": "art", "data": v, "symbol": "none",
                                  "color": _ds.gruppen_farbe(k, i, farben),
                                  "lineStyle": {"color": _ds.gruppen_farbe(k, i, farben), "width": 1},
                                  "areaStyle": {"color": _ds.gruppen_farbe(k, i, farben), "opacity": .35}}
                                 for i, (k, v) in enumerate(det.kategorien.items())]
                if zr.kapazitaet:
                    opt["series"].append({"name": "Kapazität", "type": "line", "data": [zr.kapazitaet] * len(det.tage),
                                          "symbol": "none", "lineStyle": {"color": _T()["rot"], "width": 1, "type": "dotted"}})
                if not all(det.ist) and any(det.ist):
                    stich = det.tage[sum(det.ist) - 1]
                    opt["series"][0]["markLine"] = {"symbol": "none", "label": {"formatter": "Stichtag", "color": _T()["text3"]},
                                                    "lineStyle": {"color": _T()["text3"], "type": "dashed"},
                                                    "data": [{"xAxis": stich}]}
                _chart(opt, a)
        elif diagramm_karte.modus() == "einfach":         # 0.93: eigene Leitungsansicht statt der Karte
            with ui.element("div").classes("m-breit"):
                _belegung_einfach(a, det, zr, farben)
        else:
            with ui.element("div").classes("m-breit"):
                _tagesverlauf_karte(a, det, zr, farben)
        _anteile(a, det, farben)                           # 0.96: wer macht wie viel aus – Ring/Kreis und 100 %
        with ui.element("section").classes("m-block"):
            ui.label("Personentage je Monat").classes("m-btitel")
            ui.label("Summe der belegten Plätze über alle Tage – hell = Prognose").classes("m-ptext")
            opt = _chart_basis()
            opt["xAxis"]["data"] = [m for m, _w, _i in det.monate]
            opt["yAxis"]["scale"] = False
            opt["series"] = [{"name": "Personentage", "type": "bar", "barMaxWidth": 28,
                              "data": [{"value": w_, "itemStyle": {"color": _T()["akzent"], "opacity": 1 if i_ else .4}}
                                       for _m, w_, i_ in det.monate], "lineStyle": {"color": _T()["akzent"]}}]
            _chart(opt, a)
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


