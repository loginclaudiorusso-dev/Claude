"""Seite „Auswertung“: Lage (heute + Verlauf), Belegung im Zeitraum, Prognose je Monat und Zimmer & Engpässe.
Standort und Netto/Brutto gelten für die ersten drei Ansichten."""

from __future__ import annotations

from datetime import date, timedelta

from nicegui import ui

from . import auswertung_kern as ak
from . import seiten
from .stil import T
from .ui_bausteine import knopf, leer, segmente

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
        a.daten = {"zr": ak.zeitraum(ds, a.aw_standort, a.aw_von, a.aw_bis, a.aw_brutto), "stichtag": ds.stichtag}
    else:
        a.daten = {"pg": ak.prognose(ds, a.aw_standort, a.aw_brutto, 24, a.aw_horizont)}


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
    achse = {"axisLine": {"lineStyle": {"color": T["rand2"]}}, "axisLabel": {"color": T["text3"]},
             "splitLine": {"lineStyle": {"color": T["rand"]}}}
    return {"backgroundColor": "transparent", "textStyle": {"color": T["text2"], "fontFamily": "Segoe UI, sans-serif"},
            "grid": {"left": 48, "right": 20, "top": 30, "bottom": 30}, "tooltip": {"trigger": "axis"},
            "legend": {"textStyle": {"color": T["text2"]}, "top": 0, "right": 10},
            "xAxis": {"type": "category", **achse}, "yAxis": {"type": "value", **achse, "scale": True}}


def _chart(opt: dict) -> None:
    """Legende in den Farben der Linien/Flächen (sonst nimmt ECharts seine Standardpalette)."""
    for se in opt["series"]:
        se["color"] = se.get("lineStyle", {}).get("color") or se.get("areaStyle", {}).get("color") or T["text3"]
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
                     "stack": "band", "lineStyle": {"opacity": 0}, "symbol": "none", "areaStyle": {"color": T["akzent"], "opacity": .15}},
                    {"name": "Ist", "type": "line", "data": v["ist"], "symbol": "none", "lineStyle": {"color": T["text"], "width": 2}},
                    {"name": "Prognose", "type": "line", "data": v["prognose"], "symbol": "none",
                     "lineStyle": {"color": T["akzent"], "width": 2, "type": "dashed"}},
                ]
                if lg.kapazitaet:
                    opt["series"].append({"name": "Kapazität", "type": "line", "data": [lg.kapazitaet] * len(v["tage"]),
                                          "symbol": "none", "lineStyle": {"color": T["rot"], "width": 1, "type": "dotted"}})
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
    with a.inhalt:
        with ui.element("div").classes("m-kpis"):
            _kpi("Zeitraum", f"{zr.tage} Tage", f"{zr.von:%d.%m.%Y} – {zr.bis:%d.%m.%Y}")
            _kpi("Personentage", _zahl(zr.gesamt), "Summe aller Kategorien")
            _kpi("Ø belegt", _zahl(zr.mittel, 1), f"Auslastung {round(100 * zr.mittel / zr.kapazitaet)} %" if zr.kapazitaet else "")
            _kpi("Höchststand", _zahl(zr.hoechst), f"am {zr.hoechst_tag:%d.%m.%Y}" if zr.hoechst_tag else "")
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


# ---- Prognose ----------------------------------------------------------------------------

def _prognose(a) -> None:
    pg: ak.Prognose | None = a.daten["pg"]
    with a.leiste:
        segmente({12: "12 Monate", 24: "24 Monate", 36: "36 Monate"}, a.aw_horizont, lambda h: a.setzen(aw_horizont=h))
    with a.inhalt:
        if pg is None or not pg.zeilen:
            leer("Die Prognose ist noch nicht berechnet.")
            return
        kuenftig = [z for z in pg.zeilen if z.art != "ist"]
        naechst = kuenftig[1] if len(kuenftig) > 1 else (kuenftig[0] if kuenftig else None)
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
                ui.label("Monatsverlauf – Ø belegte Plätze je Monat").classes("m-btitel")
                opt = _chart_basis()
                opt["xAxis"]["data"] = [ak.monat_text(z.monat) for z in pg.zeilen]
                band = lambda lo, hi, f: [None if z.art == "ist" else round(getattr(z, hi) - getattr(z, lo), 1) for z in pg.zeilen]  # noqa: E731
                unten = lambda lo: [None if z.art == "ist" else round(getattr(z, lo), 1) for z in pg.zeilen]  # noqa: E731
                opt["series"] = [
                    {"name": "u95", "type": "line", "data": unten("lo95"), "stack": "b95", "lineStyle": {"opacity": 0}, "symbol": "none",
                     "tooltip": {"show": False}},
                    {"name": "95 %-Spanne", "type": "line", "data": band("lo95", "hi95", 0), "stack": "b95", "lineStyle": {"opacity": 0},
                     "symbol": "none", "areaStyle": {"color": T["akzent"], "opacity": .08}},
                    {"name": "u80", "type": "line", "data": unten("lo80"), "stack": "b80", "lineStyle": {"opacity": 0}, "symbol": "none",
                     "tooltip": {"show": False}},
                    {"name": "80 %-Spanne", "type": "line", "data": band("lo80", "hi80", 0), "stack": "b80", "lineStyle": {"opacity": 0},
                     "symbol": "none", "areaStyle": {"color": T["akzent"], "opacity": .18}},
                    {"name": "Ist", "type": "line", "data": [round(z.ist, 1) if z.ist is not None and z.art != "prognose" else None
                                                             for z in pg.zeilen], "lineStyle": {"color": T["text"], "width": 2},
                     "symbolSize": 4},
                    {"name": "Erwartet", "type": "line", "data": [None if z.art == "ist" else round(z.erwartet, 1) for z in pg.zeilen],
                     "lineStyle": {"color": T["akzent"], "width": 2, "type": "dashed"}, "symbolSize": 4},
                ]
                if pg.kapazitaet:
                    opt["series"].append({"name": "Kapazität", "type": "line", "data": [pg.kapazitaet] * len(pg.zeilen),
                                          "symbol": "none", "lineStyle": {"color": T["rot"], "width": 1, "type": "dotted"}})
                opt["legend"]["data"] = ["Ist", "Erwartet", "80 %-Spanne", "95 %-Spanne", "Kapazität"]
                _chart(opt)
            with ui.element("section").classes("m-block").style("grid-column: 1 / -1"):
                with ui.element("div").classes("m-paktionen").style("align-items:center"):
                    ui.label("Reicht die Kapazität?").classes("m-btitel")
                    ui.label("Was wäre, wenn die Kapazität").classes("m-ptext").style("margin-left:auto")
                    wenn = ui.number(value=pg.kapazitaet or 0, min=0, max=5000, step=1, format="%d").classes(
                        "m-feld klein").props("dense outlined dark")
                    ui.label("wäre? (nur testweise)").classes("m-ptext")
                tabelle = ui.element("div")

                def tabelle_zeichnen():
                    kap = int(wenn.value or 0)
                    tabelle.clear()
                    sp = "minmax(120px,1fr) 90px 130px 130px 90px minmax(160px,1.2fr)"
                    with tabelle:
                        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
                            for t in ("Monat", "Erwartet", "80 %-Spanne", "95 %-Spanne", "Gesichert", "Einschätzung"):
                                ui.label(t)
                        for z in kuenftig[:a.aw_horizont]:
                            st, tx = ak.einschaetzung(z.hi80, kap)
                            with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                                ui.label(ak.monat_text(z.monat) + (" (laufend)" if z.art == "laufend" else "")).classes("m-name")
                                ui.label(_zahl(z.erwartet)).classes("m-mono")
                                ui.label(f"{_zahl(z.lo80)} – {_zahl(z.hi80)}").classes("m-mono")
                                ui.label(f"{_zahl(z.lo95)} – {_zahl(z.hi95)}").classes("m-mono")
                                ui.label(_zahl(z.gesichert)).classes("m-mono")
                                with ui.element("div"):
                                    ui.label(tx).classes(f"m-pille {AMPEL.get(st, '')}")

                wenn.on_value_change(lambda _e: tabelle_zeichnen())
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
                ui.label("Rückblick: Blind-Prognosen").classes("m-btitel")
                if not pg.rueckblick:
                    ui.label("Nur je Standort verfügbar.").classes("m-ptext")
                for mon, ist, p in list(reversed(pg.rueckblick))[:8]:
                    with ui.element("div").classes("m-liste-zeile"):
                        ui.label(ak.monat_text(mon)).classes("m-zweite").style("width:80px")
                        ui.label(f"Ist {_zahl(ist)} · Prognose {_zahl(p)}").classes("m-name")
                        ui.label(("+" if p > ist else "−") + _zahl(abs(p - ist))).classes("m-mono")
