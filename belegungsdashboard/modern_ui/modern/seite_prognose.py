"""Auswertung → Prognose als Executive-Analytics-Ansicht (Darstellung; Daten: ``analytik_kern`` / ``auswertung_kern``).

Aufbau (Analysemodus): KPI-Karten → Erkenntnisse → Prognosegraph (Trend · Reserve · Vorjahr) → Szenario (Simulation)
→ Standortvergleich → Monatstabelle (kompakt/ausführlich) → Methodik und Backtest.
Präsentationsmodus: reduzierte Oberfläche, große KPIs, dominanter Graph, schrittweiser Aufbau, optional Standorte.
"""

from __future__ import annotations

import json

from nicegui import run, ui

from belegung import konfig

from . import analytik_kern as an
from . import auswertung_kern as ak
from . import seiten, themes
from .ui_bausteine import attr, knopf, leer, segmente

CHARTS = {"trend": "Trend & Prognose", "reserve": "Kapazitätsreserve", "jahr": "Vorjahresvergleich"}
SCHRITTE = {1: "Ist-Verlauf", 2: "+ Prognose", 3: "+ Unsicherheit (80/95 %)", 4: "+ Kapazität"}
TAG = {"Fakt": "fakt", "Prognose": "prognose", "Einschätzung": "einsch", "Hinweis": "hinweis"}


def _t() -> dict:
    return themes.farben(themes.AKTIV)


def _rgba(farbe: str, alpha: float) -> str:
    f = farbe.lstrip("#")
    if len(f) != 6:
        return farbe
    return f"rgba({int(f[0:2], 16)},{int(f[2:4], 16)},{int(f[4:6], 16)},{alpha})"


def _z(x) -> str:
    return an._z(x)


# =======================================================================================
# Diagramm-Optionen (reine Darstellung – rechnet nur, was ak/an liefern)
# =======================================================================================

def _basis(t: dict, animation: bool) -> dict:
    achse = {"axisLine": {"lineStyle": {"color": t["rand2"]}}, "axisLabel": {"color": t["text3"], "fontSize": 11},
             "splitLine": {"lineStyle": {"color": t["rand"], "type": [3, 3]}}}
    return {"backgroundColor": "transparent", "textStyle": {"color": t["text2"], "fontFamily": "Segoe UI, Inter, sans-serif"},
            "grid": {"left": 52, "right": 96, "top": 56, "bottom": 36},
            "tooltip": {"trigger": "axis", "backgroundColor": _rgba(t.get("fls", "#15171C"), .86), "borderColor": t["rand2"],
                        "borderWidth": 1, "padding": [10, 12], "textStyle": {"color": t["text"], "fontSize": 12},
                        "axisPointer": {"type": "line", "lineStyle": {"color": t["text3"], "type": "dashed"}},
                        "extraCssText": "backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-radius: 10px; "
                                        "box-shadow: 0 10px 28px rgba(0,0,0,.22); min-width: 240px;"},
            "legend": {"textStyle": {"color": t["text2"], "fontSize": 11}, "top": 26, "left": 8, "itemWidth": 18, "itemHeight": 8},
            "xAxis": {"type": "category", "boundaryGap": False, **achse}, "yAxis": {"type": "value", "scale": True, **achse},
            "animation": animation, "animationDuration": 900, "animationEasing": "cubicOut", "animationDurationUpdate": 280}


def _titel(o: dict, t: dict, titel: str, unter: str) -> None:
    o["title"] = {"text": titel, "subtext": unter, "left": 8, "top": 0, "itemGap": 3,
                  "textStyle": {"color": t["text"], "fontSize": 13, "fontWeight": 600},
                  "subtextStyle": {"color": t["text3"], "fontSize": 11}}
    o["legend"]["top"] = 40
    o["grid"]["top"] = 76


def _zeitraum(zs) -> str:
    return f"{ak.monat_text(zs[0].monat)} – {ak.monat_text(zs[-1].monat)}" if zs else ""


def option(c: dict) -> dict:
    """c: pg, kap, offset, art, standort, brutto, b95, backtest, schritt, animation, pg_lang, stichtag."""
    t = _t()
    o = _basis(t, c["animation"])
    pg, kap, offset = c["pg"], c["kap"], c["offset"]
    ort = konfig.STANDORT_LABEL.get(c["standort"], c["standort"])
    zaehl = "Brutto" if c["brutto"] else "Netto"
    szen = " · SZENARIO" if (kap != (pg.kapazitaet or 0) or offset) else ""
    if c["art"] == "jahr":
        return _vorjahr(o, t, c, ort, zaehl, szen)
    zs = ak.szenario(pg, kap, offset)
    if c["art"] == "reserve":
        return _reserve(o, t, c, zs, ort, zaehl, szen)
    return _trend(o, t, c, zs, ort, zaehl, szen)


def _formatter(zs, kap: int, t: dict) -> str:
    d = [{"m": ak.monat_text(z.monat), "a": z.art, "ist": z.ist, "e": z.erwartet, "l8": z.lo80, "h8": z.hi80,
          "l9": z.lo95, "h9": z.hi95, "g": z.gesichert, "r": z.reserve, "ru": (kap - z.hi80) if kap and z.art != "ist" else None}
         for z in zs]
    c = {"ist": t["text"], "e": t["akzent"], "b": t["text3"], "ok": t["gruen"], "rot": t["rot"], "kap": t["rot"]}
    return ("(ps) => { const D = " + json.dumps(d) + "; const C = " + json.dumps(c) + "; const K = " + str(kap or 0) + ";"
            " const d = D[ps[0].dataIndex]; if (!d) return '';"
            " const f = v => v == null ? '–' : Math.round(v).toLocaleString('de-DE');"
            " const z = (c, t, v, st) => `<div style=\"display:flex;gap:18px;justify-content:space-between;line-height:1.75\">"
            "<span><span style=\"display:inline-block;width:14px;height:0;border-top:2px ${st||'solid'} ${c};margin-right:7px;vertical-align:middle\"></span>${t}</span>"
            "<b style=\"font-variant-numeric:tabular-nums\">${v}</b></div>`;"
            " const art = d.a == 'ist' ? 'Ist' : (d.a == 'laufend' ? 'laufender Monat (unvollständig)' : 'Prognose');"
            " let h = `<div style=\"font-weight:600;margin-bottom:6px\">${d.m} <span style=\"opacity:.65;font-weight:400\">· ${art}</span></div>`;"
            " if (d.a == 'ist') h += z(C.ist, 'Ist (Ø belegt)', f(d.ist));"
            " if (d.a == 'laufend' && d.ist != null) h += z(C.ist, 'Ist bisher', f(d.ist));"
            " if (d.a != 'ist') { h += z(C.e, 'Erwartet', f(d.e), 'dashed'); h += z(C.b, '80 %-Band', f(d.l8) + ' – ' + f(d.h8));"
            " h += z(C.b, '95 %-Band', f(d.l9) + ' – ' + f(d.h9), 'dotted'); if (d.g != null) h += z(C.b, 'Gebucht (Untergrenze)', f(d.g), 'dotted'); }"
            " if (K) { h += `<div style=\"border-top:1px solid ${C.b}55;margin:6px 0 2px\"></div>` + z(C.kap, 'Kapazität', f(K), 'dashed')"
            " + z(d.r < 0 ? C.rot : C.ok, 'Reserve (erwartet)', f(d.r)) + (d.ru != null ? z(d.ru < 0 ? C.rot : C.b, 'Reserve ungünstig', f(d.ru)) : ''); }"
            " return h; }")


def _trend(o, t, c, zs, ort, zaehl, szen) -> dict:
    kap, schritt = c["kap"], c["schritt"]
    zeig = lambda n: schritt >= n  # noqa: E731
    labels = [ak.monat_text(z.monat) for z in zs]
    o["xAxis"]["data"] = labels
    _titel(o, t, f"Belegung {ort} · {zaehl}{szen}", f"Ø belegte Plätze je Monat · {_zeitraum(zs)} · Ist bis "
                                                   f"{c['stichtag']:%d.%m.%Y}, danach Prognose")
    o["tooltip"][":formatter"] = _formatter(zs, kap, t)
    li = max((i for i, z in enumerate(zs) if z.art == "ist"), default=None)
    leer_ = [None] * len(zs)

    def prog(feld):
        w = [None if z.art == "ist" else round(getattr(z, feld), 1) for z in zs]
        if li is not None and zs[li].ist is not None and li + 1 < len(zs):
            w[li] = round(zs[li].ist, 1)          # an die Ist-Linie anschließen
        return w
    u80, o80, u95, o95 = prog("lo80"), prog("hi80"), prog("lo95"), prog("hi95")
    breite = lambda u, ob: [None if x is None or y is None else round(y - x, 1) for x, y in zip(u, ob)]  # noqa: E731
    b95 = c["b95"] and zeig(3)
    d = lambda n, s: {"animationDelay": n, "animationDuration": s}  # noqa: E731
    reihen = [
        {"name": "u95", "type": "line", "data": u95 if b95 else leer_, "stack": "b95", "symbol": "none", "lineStyle": {"opacity": 0},
         "tooltip": {"show": False}, "silent": True, **d(1300, 500)},
        {"name": "95 %-Band", "type": "line", "data": breite(u95, o95) if b95 else leer_, "stack": "b95", "symbol": "none",
         "color": t["text3"], "lineStyle": {"opacity": 0}, "areaStyle": {"color": _rgba(t["akzent"], .07)}, **d(1300, 500)},
        {"name": "u80", "type": "line", "data": u80 if zeig(3) else leer_, "stack": "b80", "symbol": "none", "lineStyle": {"opacity": 0},
         "tooltip": {"show": False}, "silent": True, **d(1200, 500)},
        {"name": "80 %-Band", "type": "line", "data": breite(u80, o80) if zeig(3) else leer_, "stack": "b80", "symbol": "none",
         "color": t["akzent"], "lineStyle": {"opacity": 0}, "areaStyle": {"color": _rgba(t["akzent"], .17)}, **d(1200, 500)},
        {"name": "Ist", "type": "line", "color": t["text"], "symbol": "circle", "symbolSize": 4, "z": 5,
         "data": [round(z.ist, 1) if z.art == "ist" and z.ist is not None else None for z in zs],
         "lineStyle": {"color": t["text"], "width": 2.4}, "itemStyle": {"color": t["text"]}, **d(0, 900)},
        {"name": "laufender Monat", "type": "line", "color": t["text"], "symbol": "emptyCircle", "symbolSize": 10, "z": 7,
         "data": [round(z.erwartet, 1) if z.art == "laufend" else None for z in zs] if zeig(2) else leer_,
         "itemStyle": {"color": t["text"], "borderWidth": 2}, "lineStyle": {"opacity": 0}, **d(850, 300)},
        {"name": "Prognose (erwartet)", "type": "line", "color": t["akzent"], "symbol": "none", "z": 6,
         "data": prog("erwartet") if zeig(2) else leer_, "lineStyle": {"color": t["akzent"], "width": 2.4, "type": [7, 5]},
         **d(900, 700)},
        {"name": "Kapazität", "type": "line", "symbol": "none", "color": t["rot"], "z": 4,
         "data": [kap] * len(zs) if kap and zeig(4) else leer_, "lineStyle": {"color": t["rot"], "width": 1.4, "type": [5, 4]},
         "endLabel": {"show": bool(kap and zeig(4)), "formatter": "Kapazität {c}", "color": t["rot"], "fontSize": 11}, **d(0, 500)},
    ]
    if li is not None and li + 1 < len(zs) and zeig(2):
        reihen[6]["markArea"] = {"silent": True, "itemStyle": {"color": _rgba(t["akzent"], .045)},
                                 "label": {"show": True, "position": "insideTop", "color": t["text3"], "fontSize": 11,
                                           "formatter": "Prognose →"},
                                 "data": [[{"xAxis": labels[li]}, {"xAxis": labels[-1]}]]}
    zusatz = {z.monat: z.vertraege for z in c["pg"].zeilen}
    blind = {mon: p + zusatz.get(mon, 0.0) for mon, _i, p in c["pg"].rueckblick} if c["backtest"] else {}
    reihen.append({"name": "Backtest (1 Monat vorher)", "type": "line", "symbol": "diamond", "symbolSize": 6, "color": t["orange"],
                   "data": [round(blind[z.monat], 1) if z.monat in blind else None for z in zs] if blind else leer_,
                   "lineStyle": {"color": t["orange"], "width": 1.4, "type": "dotted"}, **d(1600, 500)})
    o["series"] = reihen
    # feste Achse über alle Aufbauschritte – sonst „springt“ der Graph, wenn Bänder oder Kapazität dazukommen
    werte = [z.ist for z in zs if z.art == "ist" and z.ist is not None] + [z.lo95 if c["b95"] else z.lo80 for z in zs if z.art != "ist"] \
        + [z.hi95 if c["b95"] else z.hi80 for z in zs if z.art != "ist"] + ([kap] if kap else []) + list(blind.values())
    if werte:
        unten, oben = min(werte), max(werte)
        rand = max(2.0, (oben - unten) * .06)
        schritt_y = 10 if oben - unten > 60 else 5 if oben - unten > 20 else 1
        o["yAxis"]["min"] = max(0, int((unten - rand) // schritt_y * schritt_y))
        o["yAxis"]["max"] = int(-(-(oben + rand) // schritt_y) * schritt_y)
    o["legend"]["data"] = ["Ist", "laufender Monat", "Prognose (erwartet)", "80 %-Band"] + (["95 %-Band"] if c["b95"] else []) + \
        (["Kapazität"] if kap else []) + (["Backtest (1 Monat vorher)"] if blind else [])
    return o


def _reserve(o, t, c, zs, ort, zaehl, szen) -> dict:
    kap = c["kap"]
    li = max((i for i, z in enumerate(zs) if z.art == "ist"), default=-1)
    zs = zs[max(0, li - 5):]                                  # letzte 6 Ist-Monate + Prognose
    labels = [ak.monat_text(z.monat) for z in zs]
    o["xAxis"]["data"] = labels
    o["xAxis"]["boundaryGap"] = True
    o["yAxis"]["scale"] = False
    _titel(o, t, f"Freie Plätze bis zur Kapazität · {ort} · {zaehl}{szen}",
           f"Kapazität {_z(kap)} − Belegung · {_zeitraum(zs)} · Balken: erwartet (Ist blasser) · Linie: ungünstiger Fall (obere 80 %)")
    o["tooltip"][":formatter"] = _formatter(zs, kap, t)
    if not kap:
        o["series"] = []
        o["graphic"] = {"type": "text", "left": "center", "top": "middle",
                        "style": {"text": "Keine Kapazität hinterlegt – Reserve nicht berechenbar", "fill": t["text3"]}}
        return o
    farbe = {"ok": t["gruen"], "knapp": t["orange"], "kritisch": t["rot"], "ueber": t["rot"]}
    balken = [{"value": round(z.reserve, 1), "itemStyle": {"color": _rgba(farbe.get(z.stufe, t["text3"]) if z.art != "ist" else t["text3"],
                                                                         .85 if z.art != "ist" else .45),
                                                         "borderRadius": [3, 3, 0, 0] if z.reserve >= 0 else [0, 0, 3, 3]}}
              for z in zs]
    o["series"] = [
        {"name": "Reserve (erwartet)", "type": "bar", "data": balken, "barMaxWidth": 26, "color": t["gruen"],
         "markLine": {"symbol": "none", "silent": True, "data": [{"yAxis": 0}], "lineStyle": {"color": t["rot"], "width": 1.4},
                      "label": {"formatter": "Kapazitätsgrenze", "color": t["rot"], "position": "insideEndTop"}},
         "animationDelay": 0, "animationDuration": 800},
        {"name": "Reserve ungünstig (obere 80 %)", "type": "line", "symbol": "circle", "symbolSize": 4, "color": t["text2"],
         "data": [round(kap - z.hi80, 1) if z.art != "ist" else None for z in zs],
         "lineStyle": {"color": t["text2"], "width": 1.4, "type": [5, 4]}, "animationDelay": 700, "animationDuration": 500},
    ]
    o["legend"]["data"] = ["Reserve (erwartet)", "Reserve ungünstig (obere 80 %)"]
    return o


def _vorjahr(o, t, c, ort, zaehl, szen) -> dict:
    vj = an.vorjahr(c.get("pg_lang") or c["pg"])
    labels = [f"{ak.MONATE[m.month - 1]} {str(m.year)[2:]}" for m in vj.monate]
    o["xAxis"]["data"] = labels
    _titel(o, t, f"Vorjahresvergleich · {ort} · {zaehl}{szen}",
           f"Aktueller Zeitraum {_zeitraum_m(vj.monate)} gegen dieselben Kalendermonate ein bzw. zwei Jahre früher (Ist)")
    akt_ist = [round(v, 1) if v is not None and i else None for v, i in zip(vj.aktuell, vj.aktuell_ist)]
    akt_prog = [round(v, 1) if v is not None and not i else None for v, i in zip(vj.aktuell, vj.aktuell_ist)]
    letzte = max((n for n, i in enumerate(vj.aktuell_ist) if i), default=None)
    if letzte is not None and letzte + 1 < len(akt_prog):
        akt_prog[letzte] = akt_ist[letzte]
    rnd = lambda xs: [round(x, 1) if x is not None else None for x in xs]  # noqa: E731
    o["series"] = [
        {"name": "Vorvorjahr (Ist)", "type": "line", "data": rnd(vj.vorvorjahr), "symbol": "none", "color": t["text3"],
         "lineStyle": {"color": t["text3"], "width": 1.2, "type": "dotted"}, "animationDuration": 700},
        {"name": "Vorjahr (Ist)", "type": "line", "data": rnd(vj.vorjahr), "symbol": "circle", "symbolSize": 4, "color": t["blau"],
         "lineStyle": {"color": t["blau"], "width": 2}, "animationDuration": 800},
        {"name": "Aktuell (Ist)", "type": "line", "data": akt_ist, "symbol": "circle", "symbolSize": 5, "color": t["text"],
         "lineStyle": {"color": t["text"], "width": 2.6}, "animationDelay": 300, "animationDuration": 800},
        {"name": "Aktuell (Prognose)", "type": "line", "data": akt_prog, "symbol": "none", "color": t["akzent"],
         "lineStyle": {"color": t["akzent"], "width": 2.4, "type": [7, 5]}, "animationDelay": 900, "animationDuration": 600},
    ]
    # keine Kapazitätslinie: hier geht es um den saisonalen Vergleich – sie würde die Unterschiede flach drücken
    o["legend"]["data"] = [s["name"] for s in o["series"]]
    o["tooltip"]["valueFormatter"] = None
    d = [{"m": l, "a": a, "v": v, "vv": vv, "ist": i} for l, a, v, vv, i in zip(labels, vj.aktuell, vj.vorjahr, vj.vorvorjahr, vj.aktuell_ist)]
    o["tooltip"][":formatter"] = (
        "(ps) => { const D = " + json.dumps(d) + "; const d = D[ps[0].dataIndex]; if (!d) return '';"
        " const f = v => v == null ? '–' : Math.round(v).toLocaleString('de-DE');"
        " const dl = (a, b) => (a == null || b == null) ? 'Vorjahr fehlt' : ((a - b >= 0 ? '+' : '−') + f(Math.abs(a - b)) + ' (' + (a - b >= 0 ? '+' : '−') + Math.abs(Math.round(100 * (a - b) / b)) + ' %)');"
        " return `<b>${d.m}</b><br>${d.ist ? 'Ist' : 'Prognose'}: <b>${f(d.a)}</b><br>Vorjahr (Ist): ${f(d.v)}<br>"
        "Vorvorjahr (Ist): ${f(d.vv)}<br><span style=\"opacity:.75\">Δ ggü. Vorjahr: ${dl(d.a, d.v)}</span>`; }")
    return o


def _zeitraum_m(ms) -> str:
    return f"{ak.monat_text(ms[0])} – {ak.monat_text(ms[-1])}" if ms else ""


def vergleich_option(sv: list, aktiv: str, hell: bool, animation: bool) -> dict:
    t = _t()
    o = _basis(t, animation)
    farben = an.STANDORT_FARBEN[hell]
    namen = [v.name for v in sv]
    o["xAxis"] = {"type": "value", "max": 110, "axisLabel": {"color": t["text3"], "formatter": "{value} %"},
                  "splitLine": {"lineStyle": {"color": t["rand"], "type": [3, 3]}}}
    o["yAxis"] = {"type": "category", "data": namen, "inverse": True, "axisLabel": {"color": t["text2"], "fontWeight": 600},
                  "axisLine": {"lineStyle": {"color": t["rand2"]}}}
    o["grid"] = {"left": 96, "right": 40, "top": 26, "bottom": 52}
    o["legend"].pop("top", None)
    o["legend"]["bottom"] = 0
    o["tooltip"]["trigger"] = "item"
    o["tooltip"].pop("axisPointer", None)
    o["series"] = [
        {"name": "Auslastung heute", "type": "bar", "barGap": "20%", "barMaxWidth": 16, "color": t["text2"],
         "data": [{"value": round(100 * v.auslastung) if v.auslastung is not None else None,
                   "itemStyle": {"color": farben[v.standort], "opacity": 1 if aktiv in (v.standort, konfig.GESAMT) else .45,
                                 "borderRadius": [0, 3, 3, 0]}} for v in sv],
         "label": {"show": True, "position": "right", "formatter": "{c} %", "color": t["text2"], "fontSize": 11},
         "markLine": {"symbol": "none", "silent": True,
                      "label": {"color": t["text3"], "fontSize": 10, "formatter": "{b}", "position": "end"},
                      "data": [{"xAxis": round(100 * konfig.AMPEL_GELB), "name": "knapp"},
                               {"xAxis": round(100 * konfig.AMPEL_ROT), "name": "kritisch"}, {"xAxis": 100, "name": "voll"}],
                      "lineStyle": {"color": t["text3"], "type": "dashed"}}},
        {"name": "Spitze 12 Monate (obere 80 %)", "type": "bar", "barMaxWidth": 16, "color": _rgba(t["text3"], .35),
         "data": [{"value": round(100 * v.spitze_quote) if v.spitze_quote is not None else None,
                   "itemStyle": {"color": _rgba(farben[v.standort], .35), "borderColor": farben[v.standort], "borderWidth": 1.2,
                                 "borderType": "dashed", "borderRadius": [0, 3, 3, 0]}} for v in sv],
         "label": {"show": True, "position": "right", "formatter": "{c} %", "color": t["text3"], "fontSize": 11}},
    ]
    o["legend"]["data"] = ["Auslastung heute", "Spitze 12 Monate (obere 80 %)"]
    return o


# =======================================================================================
# Ansicht
# =======================================================================================

def daten(a, ds) -> None:
    pg = ak.prognose(ds, a.aw_standort, a.aw_brutto, 24, a.aw_horizont)
    a.daten = {"pg": pg, "stichtag": ds.stichtag, "ds": ds,
               "sv": an.standort_vergleich(ds, a.aw_brutto, min(12, a.aw_horizont))}
    if a.aw_chart == "jahr":
        a.daten["pg_lang"] = ak.prognose(ds, a.aw_standort, a.aw_brutto, 36, a.aw_horizont)


def _praes_klasse(a, an_: bool) -> None:
    if an_:
        a.body.classes(add="praesentation")
    else:
        a.body.classes(remove="praesentation")


def praes_beenden(a) -> None:
    if a.aw_modus == "praes":
        a.aw_modus = "analyse"
        _praes_klasse(a, False)
        a.zeichnen()


def praes_schritt(a, delta: int) -> None:
    if a.aw_modus == "praes" and a.aw_chart == "trend":
        neu = min(4, max(1, a.aw_schritt + delta))
        if neu != a.aw_schritt:
            a.aw_schritt = neu
            if a._prognose_chart:
                a._prognose_chart(True)


def zeichnen(a) -> None:
    pg: ak.Prognose | None = a.daten["pg"]
    if pg is None or not pg.zeilen:
        with a.inhalt:
            leer("Die Prognose ist noch nicht berechnet.")
        return
    kap_echt = pg.kapazitaet or 0
    if a.aw_kap is None or a.aw_kap_basis != kap_echt:      # neuer Standort/Netto-Brutto → echte Kapazität
        a.aw_kap, a.aw_kap_basis = kap_echt, kap_echt
    praes = a.aw_modus == "praes"
    _praes_klasse(a, praes)
    # Animation: beim ersten Öffnen und auf Wunsch – nicht bei jedem Filterwechsel, nie bei „weniger Bewegung“
    animiert = not a.weniger_bewegung and ((a.aw_anim and not a.aw_anim_gezeigt) or a._anim_jetzt)
    a.aw_anim_gezeigt, a._anim_jetzt = True, False
    hell = bool(_t().get("hell"))
    zustand = {"kap": a.aw_kap, "offset": a.aw_offset}
    c = lambda anim=False: {"pg": pg, "kap": zustand["kap"], "offset": zustand["offset"], "art": a.aw_chart,  # noqa: E731
                            "standort": a.aw_standort, "brutto": a.aw_brutto, "b95": a.aw_95, "backtest": a.aw_backtest,
                            "schritt": a.aw_schritt if praes and a.aw_chart == "trend" else 4, "animation": anim,
                            "pg_lang": a.daten.get("pg_lang"), "stichtag": a.daten["stichtag"]}
    ds = a.daten["ds"]
    box: dict = {}

    def ex():
        return an.executive(ds, a.aw_standort, a.aw_brutto, pg, zustand["kap"], zustand["offset"], min(12, a.aw_horizont))

    # ---- Kopfleiste (Analyse) ----------------------------------------------------------
    if not praes:
        with a.leiste:
            segmente({12: "12 Monate", 24: "24 Monate", 36: "36 Monate"}, a.aw_horizont, lambda h: a.setzen(aw_horizont=h))
            knopf("Präsentation", lambda: _modus(a, "praes"), "primaer", "slideshow",
                  "Reduzierte Ansicht für Bildschirmfreigabe und Beamer (P) – Esc beendet").style("margin-left:auto")
            _export_menue(a, pg, zustand, box, ex)

    with a.inhalt:
        wurzel = ui.element("div").classes("m-ex" + (" praes" if praes else ""))
    with wurzel:
        if praes:
            _praes_kopf(a, pg)
        # ---- Ebene A: KPI-Karten ----------------------------------------------------------
        kpi_box = ui.element("div").classes("m-xk")

        def kpis_zeichnen():
            kpi_box.clear()
            e = ex()
            with kpi_box:
                for k in (e.kpis[:4] if praes else e.kpis):
                    _kpi_karte(k)
            return e
        e0 = kpis_zeichnen()
        # ---- Ebene B: Erkenntnisse (in der Präsentation unter dem Graph) ------------------------
        er_box = ui.element("section").classes("m-xe")

        def erkenntnisse_zeichnen(e=None):
            e = e or ex()
            er_box.clear()
            with er_box:
                kopf = ui.element("button").classes("m-xe-kopf")
                with kopf:
                    ui.label("Erkenntnisse").classes("m-btitel")
                    ui.label("aus den Daten erzeugt – Fakt, Prognose oder Einschätzung").classes("m-zweite")
                    if not praes:
                        ui.icon("expand_less" if a.aw_summary else "expand_more").style("margin-left:auto")
                if not praes:
                    kopf.on("click", lambda: (setattr(a, "aw_summary", not a.aw_summary), erkenntnisse_zeichnen()))
                if a.aw_summary or praes:
                    with ui.element("ul").classes("m-xe-liste"):
                        for art, text in (e.erkenntnisse[:4] if praes else e.erkenntnisse):
                            with ui.element("li"):
                                ui.label(art).classes(f"m-xe-tag {TAG.get(art, '')}")
                                ui.label(text)
        erkenntnisse_zeichnen(e0)

        # ---- Hauptgraph ----------------------------------------------------------------
        with ui.element("section").classes("m-block m-xg"):
            with ui.element("div").classes("m-xg-kopf"):
                segmente(CHARTS, a.aw_chart, lambda k: _chart_art(a, k))
                if praes and a.aw_chart == "trend":
                    with ui.element("div").classes("m-xg-schritte"):
                        knopf("", lambda: praes_schritt(a, -1), "leise", "chevron_left", "Schritt zurück (←)")
                        box["schritt"] = ui.label(f"{a.aw_schritt}/4 · {SCHRITTE[a.aw_schritt]}").classes("m-zweite")
                        knopf("", lambda: praes_schritt(a, 1), "leise", "chevron_right", "Nächster Schritt (→)")
                        knopf("Alles", lambda: praes_schritt(a, 4), "leise")
                with ui.element("div").style("margin-left:auto; display:flex; gap:6px; align-items:center"):
                    if not a.weniger_bewegung:
                        knopf("Aufbau abspielen", lambda: _abspielen(a), "leise", "play_arrow",
                              "Graph neu aufbauen (Animation) – z. B. für die Präsentation")
                    if not praes:
                        with knopf("Optionen", None, "leise", "tune"):
                            with ui.menu().props('dark class="m-menue"'):
                                _schalter("95 %-Band zeigen", a.aw_95, lambda: a.setzen(aw_95=not a.aw_95, laden=False))
                                _schalter("Backtest im Graph" + ("" if pg.rueckblick else " (nur je Standort)"), a.aw_backtest,
                                          lambda: a.setzen(aw_backtest=not a.aw_backtest, laden=False), aus=not pg.rueckblick)
                                ui.separator()
                                _schalter("Animation beim Öffnen" + (" (System: weniger Bewegung)" if a.weniger_bewegung else ""),
                                          a.aw_anim and not a.weniger_bewegung, lambda: a.setzen(aw_anim=not a.aw_anim, laden=False),
                                          aus=a.weniger_bewegung)
            chart = ui.echart(option(c(animiert))).classes("m-chart m-xg-chart" + (" gross" if praes else ""))
            box["chart"] = chart
            with ui.element("div").classes("m-xg-fuss"):
                ui.html(_legende_text(a.aw_chart), sanitize=False)

        def chart_neu(schritt_animation: bool = False):
            """Optionen ersetzen – ohne erneuten Aufbau; nur ein Präsentationsschritt darf weich einblenden."""
            neu = option(c(schritt_animation and a.aw_anim and not a.weniger_bewegung))
            if "schritt" in box:
                box["schritt"].set_text(f"{a.aw_schritt}/4 · {SCHRITTE[a.aw_schritt]}")
            chart.options.clear()
            chart.options.update(neu)
            chart.update()
        a._prognose_chart = chart_neu

        if praes:
            er_box.move(wurzel)
            if a.aw_vergleich_praes and a.daten["sv"]:
                _standortvergleich(a, hell, kompakt=True)
            return

        # ---- Szenario (Simulation) -----------------------------------------------------------
        sz_box = ui.element("section").classes("m-block m-xs")
        tab_box = ui.element("section").classes("m-block m-xt")

        def tabelle_zeichnen():
            _tabelle(a, tab_box, pg, zustand)

        def alles_neu():
            chart_neu()
            e = kpis_zeichnen()
            erkenntnisse_zeichnen(e)
            szenario_zeichnen(nur_vergleich=True)
            tabelle_zeichnen()

        sz_teile: dict = {}

        def szenario_zeichnen(nur_vergleich: bool = False):
            aktiv = zustand["kap"] != kap_echt or bool(zustand["offset"])
            if nur_vergleich and "vergleich" in sz_teile:
                sz_box.classes(add="aktiv" if aktiv else "", remove="" if aktiv else "aktiv")
                sz_teile["banner"].set_visibility(aktiv)
                sz_teile["vergleich"].clear()
                with sz_teile["vergleich"]:
                    _sz_vergleich(pg, zustand)
                return
            sz_box.clear()
            sz_box.classes(add="aktiv" if aktiv else "", remove="" if aktiv else "aktiv")
            lo, hi = min(400, int(kap_echt * .5) or 400), max(1200, int(kap_echt * 1.5) or 1200)
            with sz_box:
                with ui.element("div").classes("m-paktionen").style("align-items:center"):
                    ui.icon("science").classes("m-xs-icon")
                    ui.label("Szenario – was wäre, wenn …").classes("m-btitel")
                    sz_teile["banner"] = ui.label("SIMULATION – keine echten Daten").classes("m-xs-banner")
                    sz_teile["banner"].set_visibility(aktiv)
                    knopf("Zurück zum Ausgangsszenario", lambda: setzen(kap_echt, 0.0, True), "leise", "restart_alt").style("margin-left:auto")
                with ui.element("div").classes("m-szenario"):
                    with ui.element("div").classes("m-sz-zeile"):
                        ui.label("Kapazität").classes("m-name")
                        regler = ui.slider(min=lo, max=hi, step=1, value=min(max(zustand["kap"], lo), hi)).props("label" + ("" if hell else " dark")).classes("m-sz-regler")
                        attr(regler, aria_label="Kapazität (Szenario)")
                        feld = ui.number(value=zustand["kap"], min=0, max=5000, step=1, format="%d").classes("m-feld klein").props(
                            "dense outlined dark")
                        ui.label(f"Plätze · echt {_z(kap_echt)}").classes("m-zweite")
                    with ui.element("div").classes("m-sz-zeile"):
                        ui.label("Auslastung").classes("m-name")
                        off = ui.slider(min=-15, max=15, step=1, value=zustand["offset"]).props("label" + ("" if hell else " dark")).classes("m-sz-regler")
                        attr(off, aria_label="Auslastungs-Annahme in Prozent (Szenario)")
                        off_feld = ui.number(value=zustand["offset"], min=-15, max=15, step=1, format="%d").classes("m-feld klein").props(
                            "dense outlined dark suffix=%")
                        ui.label("% auf die Prognosemonate · Ist bleibt Ist").classes("m-zweite")
                sz_teile["vergleich"] = ui.element("div").classes("m-xs-vergleich")
                with sz_teile["vergleich"]:
                    _sz_vergleich(pg, zustand)
                ui.label("Nur diese beiden Stellschrauben haben eine belastbare Grundlage im Prognosemodell. Andere Annahmen "
                         "(z. B. Verweildauer, Anreisezahlen je Maßnahme) bräuchten ein eigenes Modell und werden deshalb nicht "
                         "scheinbar genau simuliert. Gespeichert wird nichts.").classes("m-zweite").style("white-space:normal")

            def setzen(kap=None, offset=None, alles=False):
                if kap is not None:
                    zustand["kap"] = a.aw_kap = max(0, int(kap))
                if offset is not None:
                    zustand["offset"] = a.aw_offset = float(max(-15, min(15, offset)))
                if alles or (kap is not None and regler.value != zustand["kap"]):
                    regler.set_value(min(max(zustand["kap"], lo), hi))
                if alles or (kap is not None and int(feld.value or 0) != zustand["kap"]):
                    feld.set_value(zustand["kap"])
                if alles or (offset is not None and off.value != zustand["offset"]):
                    off.set_value(zustand["offset"])
                if alles or (offset is not None and (off_feld.value or 0) != zustand["offset"]):
                    off_feld.set_value(zustand["offset"])
                alles_neu()

            regler.on("update:model-value", lambda e: setzen(kap=e.args), throttle=0.05, leading_events=False)
            off.on("update:model-value", lambda e: setzen(offset=e.args), throttle=0.05, leading_events=False)
            feld.on_value_change(lambda e: setzen(kap=int(e.value or 0)) if int(e.value or 0) != zustand["kap"] else None)
            off_feld.on_value_change(lambda e: setzen(offset=float(e.value or 0)) if float(e.value or 0) != zustand["offset"] else None)
        szenario_zeichnen()

        # ---- Standortvergleich ---------------------------------------------------------------
        if a.daten["sv"]:
            _standortvergleich(a, hell)
        # ---- Detailtabelle --------------------------------------------------------------------
        tab_box.move(wurzel)
        tabelle_zeichnen()
        # ---- Methodik und Backtest ------------------------------------------------------------
        _methodik(a, pg)


def _modus(a, modus: str) -> None:
    a.aw_modus = modus
    if modus == "praes":
        a.aw_schritt = 4
    a.zeichnen()


def _chart_art(a, k: str):
    return a.setzen(aw_chart=k, laden=k == "jahr" or a.aw_chart == "jahr")


async def _abspielen(a) -> None:
    """Graph bewusst neu aufbauen: leeren, dann mit Animation zeichnen (verändert keine Daten)."""
    a._anim_jetzt = True
    if a.aw_modus == "praes" and a.aw_chart == "trend":
        a.aw_schritt = 4
    a.zeichnen()


def _schalter(text: str, an_: bool, klick, aus: bool = False) -> None:
    item = ui.menu_item(on_click=klick, auto_close=False).classes("m-mpunkt")
    if aus:
        item.props("disable")
    with item:
        ui.icon("check_box" if an_ else "check_box_outline_blank").classes("m-mhaken" + (" an" if an_ else ""))
        ui.label(text)


def _legende_text(art: str) -> str:
    if art == "trend":
        return ("<span><i class='l ist'></i>Ist (Monatsmittel)</span><span><i class='p hohl'></i>laufender Monat – unvollständig</span>"
                "<span><i class='l prog'></i>Prognose (erwartet)</span><span><i class='f'></i>80 %- / 95 %-Band: so sicher liegt der "
                "Wert darin</span><span><i class='l kap'></i>Kapazität</span>")
    if art == "reserve":
        return ("<span><i class='f ok'></i>Reserve</span><span><i class='f warn'></i>knapp (≥ 70 % obere 80 %)</span>"
                "<span><i class='f krit'></i>kritisch / über Kapazität</span><span><i class='l'></i>ungünstiger Fall</span>"
                "<span>Unter der Nulllinie: rechnerisch mehr Belegung als Plätze</span>")
    return ("<span><i class='l ist'></i>aktuell Ist</span><span><i class='l prog'></i>aktuell Prognose</span>"
            "<span><i class='l vj'></i>Vorjahr</span><span><i class='l vvj'></i>Vorvorjahr</span>"
            "<span>Lücken = keine Daten für diesen Monat</span>")


def _kpi_karte(k: an.Kpi) -> None:
    with ui.element("article").classes(f"m-xk-karte {k.stufe}") as karte:
        attr(karte, title=k.hinweis)
        with ui.element("div").classes("m-xk-kopf"):
            ui.element("span").classes(f"m-xk-punkt {k.stufe}")
            ui.label(k.titel)
        with ui.element("div").classes("m-xk-wert"):
            ui.label(k.wert).classes("w")
            ui.label(k.einheit).classes("e")
        ui.label(k.bezug).classes("m-xk-bezug")
        if k.vergleich:
            with ui.element("div").classes("m-xk-vgl"):
                ui.icon({1: "north_east", -1: "south_east"}.get(k.richtung, "east"))
                ui.label(k.vergleich)


def _sz_vergleich(pg, zustand) -> None:
    zeilen = an.szenario_vergleich(pg, zustand["kap"], zustand["offset"])
    with ui.element("div").classes("m-xs-tab"):
        for t in ("", "Ausgangsszenario (echt)", "Szenario"):
            ui.label(t).classes("m-zweite")
        for z in zeilen:
            ui.label(z.titel).classes("m-name")
            ui.label(z.ausgang).classes("m-mono")
            ui.label(z.szenario).classes("m-mono" + (" m-krit" if z.schlechter else ""))


def _standortvergleich(a, hell: bool, kompakt: bool = False) -> None:
    sv = a.daten["sv"]
    with ui.element("section").classes("m-block m-xv"):
        with ui.element("div").classes("m-paktionen").style("align-items:center"):
            ui.label("Standortvergleich").classes("m-btitel")
            ui.label(f"{'Brutto' if a.aw_brutto else 'Netto'} · Stichtag {a.daten['stichtag']:%d.%m.%Y} · Spitze = höchste obere "
                     "80 %-Grenze der nächsten 12 Monate").classes("m-zweite")
        with ui.element("div").classes("m-xv-raster" + (" kompakt" if kompakt else "")):
            ui.echart(vergleich_option(sv, a.aw_standort, hell, False)).classes("m-xv-chart")
            if not kompakt:
                farben = an.STANDORT_FARBEN[hell]
                with ui.element("div").classes("m-xv-tab"):
                    for t in ("Standort", "Belegt", "Kapazität", "Auslastung", "Reserve", "Spitze (Monat)", "Ø-Fehler"):
                        ui.label(t).classes("m-zweite")
                    for v in sv:
                        with ui.element("button").classes("m-xv-name" + (" an" if a.aw_standort == v.standort else "")) as b:
                            ui.element("span").classes("m-xv-farbe").style(f"background:{farben[v.standort]}")
                            ui.label(v.name)
                        attr(b, title="Diesen Standort im Graph zeigen")
                        b.on("click", lambda v=v: a.setzen(aw_standort=v.standort))
                        ui.label(_z(v.belegt)).classes("m-mono")
                        ui.label(_z(v.kapazitaet)).classes("m-mono")
                        ui.label(an._p(v.auslastung)).classes("m-mono")
                        ui.label(_z(v.reserve)).classes("m-mono")
                        ui.label(f"{an._p(v.spitze_quote)} · {ak.monat_text(v.spitze_monat)}" if v.spitze_monat else "–").classes("m-mono")
                        ui.label(f"± {an._z1(v.mae_1m)}" if v.mae_1m is not None else "–").classes("m-mono")


TAB_SPALTEN = {
    "monat": ("Monat", "Prognosemonat; „laufend“ = aktueller, noch unvollständiger Monat"),
    "erwartet": ("Erwartet", "Ø belegte Plätze laut Prognose (Modell + Verträge, nie unter dem gebuchten Bestand)"),
    "b80": ("80 %-Band", "In 8 von 10 Fällen liegt der tatsächliche Wert in diesem Bereich (aus dem Backtest)"),
    "b95": ("95 %-Band", "In 19 von 20 Fällen liegt der tatsächliche Wert in diesem Bereich"),
    "gebucht": ("Gebucht", "Bereits bekannter Bestand (Teilnehmende mit geplantem Ende + Verträge) – Untergrenze der Prognose; "
                           "im Hauptprogramm „gesichert“"),
    "reserve": ("Reserve", "Kapazität − Erwartet"),
    "ungünstig": ("Reserve ungünstig", "Kapazität − obere 80 %-Grenze"),
    "status": ("Einschätzung", "Ampel auf die obere 80 %-Grenze: ≥ 70 % knapp, ≥ 85 % kritisch, > 100 % über Kapazität"),
}


def _tabelle(a, box, pg, zustand) -> None:
    box.clear()
    zs = [z for z in ak.szenario(pg, zustand["kap"], zustand["offset"]) if z.art != "ist"][:a.aw_horizont]
    kap = zustand["kap"]
    spalten = (["monat", "erwartet", "b80", "b95", "gebucht", "reserve", "ungünstig", "status"] if a.aw_details
               else ["monat", "erwartet", "b80", "reserve", "status"])
    breite = {"monat": "minmax(130px,1fr)", "erwartet": "90px", "b80": "120px", "b95": "120px", "gebucht": "90px",
              "reserve": "90px", "ungünstig": "120px", "status": "minmax(180px,1.3fr)"}
    sp = " ".join(breite[s] for s in spalten)
    with box:
        with ui.element("div").classes("m-paktionen").style("align-items:center"):
            ui.label("Monate im Detail").classes("m-btitel")
            ui.label(f"{len(zs)} Monate · Kapazität {_z(kap)}" + (" · Szenario" if (kap != (pg.kapazitaet or 0) or zustand["offset"]) else ""))\
                .classes("m-zweite")
            with ui.element("div").style("margin-left:auto"):
                segmente({False: "Kompakt", True: "Alle Spalten"}, a.aw_details,
                         lambda v: (setattr(a, "aw_details", v), _tabelle(a, box, pg, zustand)))
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for s in spalten:
                attr(ui.label(TAB_SPALTEN[s][0]), title=TAB_SPALTEN[s][1])
        stufe = {"ok": "ok", "knapp": "warn", "kritisch": "krit", "ueber": "krit"}
        for z in zs:
            with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                for s in spalten:
                    if s == "monat":
                        ui.label(ak.monat_text(z.monat) + (" · laufend" if z.art == "laufend" else "")).classes("m-name")
                    elif s == "erwartet":
                        ui.label(_z(z.erwartet)).classes("m-mono")
                    elif s == "b80":
                        ui.label(f"{_z(z.lo80)} – {_z(z.hi80)}").classes("m-mono")
                    elif s == "b95":
                        ui.label(f"{_z(z.lo95)} – {_z(z.hi95)}").classes("m-mono")
                    elif s == "gebucht":
                        g = ui.label(_z(z.gesichert) + (" *" if z.art == "laufend" else "")).classes("m-mono")
                        if z.art == "laufend":
                            attr(g, title="Laufender Monat: Gebucht gilt für die restlichen Tage, Erwartet für den ganzen Monat "
                                          "(inkl. der bereits vergangenen Tage) – deshalb kann Gebucht hier höher sein.")
                    elif s == "reserve":
                        ui.label(_z(z.reserve) if z.reserve is not None else "–").classes(
                            "m-mono" + (" m-krit" if z.reserve is not None and z.reserve < 0 else ""))
                    elif s == "ungünstig":
                        r = (kap - z.hi80) if kap else None
                        ui.label(_z(r)).classes("m-mono" + (" m-krit" if r is not None and r < 0 else ""))
                    else:
                        with ui.element("div"):
                            ui.label(z.text).classes(f"m-pille {stufe.get(z.stufe, '')}")


def _methodik(a, pg) -> None:
    with ui.element("div").classes("m-xm"):
        with ui.element("section").classes("m-block"):
            ui.label("So wurde gerechnet").classes("m-btitel")
            if pg.modell:
                ui.label(f"Gewählt: {pg.modell} – {pg.beschreibung}. Alle Kandidaten wurden für vergangene Monate blind gerechnet "
                         "(nur mit damaligen Daten); gewählt wurde das Modell mit dem kleinsten mittleren Fehler. Die Bänder wachsen "
                         "mit dem Abstand zur Gegenwart. Die Prognose fällt nie unter den gebuchten Bestand; Mieter, Gäste und "
                         "Verträge werden fest addiert.").classes("m-ptext")
            for name, fehler in pg.kandidaten[:6]:
                with ui.element("div").classes("m-liste-zeile"):
                    ui.label("")
                    ui.label(name).classes("m-name")
                    ui.label(f"± {an._z1(fehler)}").classes("m-mono")
        with ui.element("section").classes("m-block"):
            ui.label("Backtest: Blind-Prognosen je Monat").classes("m-btitel")
            if not pg.rueckblick:
                ui.label("Den Verlauf gibt es je Standort – oben einen Standort wählen. Für „Gesamt“ liegen nur die "
                         "Kennzahlen (Ø-Fehler, Trefferquote) vor.").classes("m-ptext")
            else:
                abw = [abs(p - ist) for _m, ist, p in pg.rueckblick]
                ui.label(f"Jeweils einen Monat vorher gerechnet · Ø Abweichung ± {an._z1(sum(abw) / len(abw))} · größte "
                         f"± {an._z1(max(abw))}").classes("m-ptext")
                for mon, ist, p in list(reversed(pg.rueckblick)):
                    with ui.element("div").classes("m-liste-zeile"):
                        ui.label(ak.monat_text(mon)).classes("m-zweite").style("width:80px")
                        ui.label(f"Ist {_z(ist)} · Prognose {_z(p)}").classes("m-name")
                        ui.label(("+" if p > ist else "−") + an._z1(abs(p - ist))).classes("m-mono")


def _praes_kopf(a, pg) -> None:
    with ui.element("header").classes("m-xp-kopf"):
        with ui.element("div"):
            ui.label(f"Belegungsprognose {konfig.STANDORT_LABEL.get(a.aw_standort, a.aw_standort)}").classes("m-xp-titel")
            ui.label(f"{'Brutto' if a.aw_brutto else 'Netto'} · Ist bis {a.daten['stichtag']:%d.%m.%Y}, danach Prognose · "
                     f"Kapazität {_z(a.aw_kap)} Plätze" + (" · SZENARIO" if (a.aw_kap != (pg.kapazitaet or 0) or a.aw_offset) else ""))\
                .classes("m-zweite")
        with ui.element("div").classes("m-xp-aktionen"):
            segmente(ak.STANDORTE, a.aw_standort, lambda s: a.setzen(aw_standort=s))
            knopf("Standorte", lambda: (setattr(a, "aw_vergleich_praes", not a.aw_vergleich_praes), a.zeichnen()),
                  "leise" if not a.aw_vergleich_praes else "", "leaderboard", "Standortvergleich ein-/ausblenden")
            knopf("", a.vollbild_umschalten, "leise", "fullscreen", "Vollbild")
            knopf("Beenden", lambda: praes_beenden(a), "", "close", "Präsentation beenden (Esc)")


def _export_menue(a, pg, zustand, box, ex) -> None:
    async def png():
        chart = box.get("chart")
        if chart is None:
            return
        t = _t()
        try:
            url = await chart.run_chart_method("getDataURL", {"type": "png", "pixelRatio": 3,
                                                              "backgroundColor": t.get("fls", t.get("fl"))}, timeout=10)
            pfad = await run.io_bound(ak.png_speichern, url, a.aw_standort)
        except Exception as exc:              # noqa: BLE001
            a.toast(f"Bild nicht gespeichert: {exc}", fehler=True)
            return
        a.toast("Diagramm als PNG gespeichert" if seiten._datei_oeffnen(pfad) else f"PNG gespeichert: {pfad}", rueck=False)

    async def daten_(art: str):
        try:
            pfad = await run.io_bound(ak.prognose_export, pg, zustand["kap"], zustand["offset"], a.aw_standort, a.aw_brutto, art)
        except PermissionError:
            a.toast("Die Datei ist noch geöffnet – bitte schließen und erneut versuchen.", fehler=True)
            return
        a.toast(("Excel" if art == "xlsx" else "CSV") + " gespeichert" if seiten._datei_oeffnen(pfad) else f"Gespeichert: {pfad}",
                rueck=False)

    def summary():
        html = an.summary_html(ex(), pg, a.aw_standort, a.aw_brutto, zustand["kap"], zustand["offset"], a.daten["sv"])
        seiten.html_drucken(a, html, f"Executive_Summary_{konfig.STANDORT_LABEL.get(a.aw_standort, a.aw_standort)}")

    with knopf("Export", None, "", "ios_share"):
        with ui.menu().props('dark class="m-menue"'):
            ui.menu_item("Diagramm als PNG (hochauflösend)", png)
            ui.menu_item("Executive Summary – Druck / PDF", summary)
            ui.separator()
            ui.menu_item("Prognosedaten als Excel (.xlsx)", lambda: daten_("xlsx"))
            ui.menu_item("Prognosedaten als CSV", lambda: daten_("csv"))


def praes_umschalten(a) -> None:
    if a.aw_modus == "praes":
        praes_beenden(a)
    else:
        _modus(a, "praes")
