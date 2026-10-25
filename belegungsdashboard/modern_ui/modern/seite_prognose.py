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
from . import kern, seiten, themes
from .ui_bausteine import attr, knopf, leer, segmente

GOSLAR = "BFW GS"
OFFSET_MAX = 25                       # Auslastungs-Annahme im Szenario: ± Prozent
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
    if c.get("status") and c.get("sm"):
        return _status(o, t, c, zs, ort, zaehl, szen)
    return _trend(o, t, c, zs, ort, zaehl, szen)


def _szenario_aktiv(c) -> bool:
    return c["kap"] != (c["pg"].kapazitaet or 0) or bool(c["offset"])


def _geist(t, zs_sz, zs0, li, kap_echt: int, kap: int, zeigen: bool) -> list[dict]:
    """Szenario als transparente Schattenkurve über der echten Prognose (und ggf. Schatten-Kapazität)."""
    leer_ = [None] * len(zs_sz)
    werte = [None if z.art == "ist" else round(z.erwartet, 1) for z in zs_sz]
    if li is not None and zs0[li].ist is not None and li + 1 < len(zs_sz):
        werte[li] = round(zs0[li].ist, 1)
    f = t["orange"]
    return [
        {"name": "Szenario (Simulation)", "type": "line", "symbol": "none", "z": 8, "color": _rgba(f, .75),
         "data": werte if zeigen else leer_, "lineStyle": {"color": _rgba(f, .7), "width": 3.2, "type": [2, 4], "cap": "round"},
         "areaStyle": {"color": _rgba(f, .06), "origin": "start"} if False else None, "animationDuration": 350},
        {"name": "Kapazität Szenario", "type": "line", "symbol": "none", "z": 4, "color": _rgba(f, .7),
         "data": [kap] * len(zs_sz) if zeigen and kap and kap != kap_echt else leer_,
         "lineStyle": {"color": _rgba(f, .65), "width": 1.4, "type": [2, 4]},
         "endLabel": {"show": bool(zeigen and kap and kap != kap_echt), "formatter": "Szenario {c}", "color": f, "fontSize": 11},
         "animationDuration": 350},
    ]


def _formatter(zs, kap: int, t: dict, zs_sz=None, kap_sz: int | None = None) -> str:
    d = [{"m": ak.monat_text(z.monat), "a": z.art, "ist": z.ist, "e": z.erwartet, "l8": z.lo80, "h8": z.hi80,
          "l9": z.lo95, "h9": z.hi95, "g": z.gesichert, "r": z.reserve, "ru": (kap - z.hi80) if kap and z.art != "ist" else None,
          "se": zs_sz[i].erwartet if zs_sz and z.art != "ist" else None, "sr": zs_sz[i].reserve if zs_sz and z.art != "ist" else None}
         for i, z in enumerate(zs)]
    c = {"ist": t["text"], "e": t["akzent"], "b": t["text3"], "ok": t["gruen"], "rot": t["rot"], "kap": t["rot"], "sz": t["orange"]}
    return ("(ps) => { const D = " + json.dumps(d) + "; const C = " + json.dumps(c) + "; const K = " + str(kap or 0) + ";"
            " const K2 = " + str(kap_sz if kap_sz is not None else (kap or 0)) + ";"
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
            " if (d.se != null) { h += `<div style=\"border-top:1px dashed ${C.sz}88;margin:6px 0 2px;padding-top:4px;color:${C.sz};font-size:11px;font-weight:600;letter-spacing:.04em\">SZENARIO – SIMULATION</div>`"
            " + z(C.sz, 'Erwartet (Szenario)', f(d.se), 'dotted') + (K2 != K ? z(C.sz, 'Kapazität (Szenario)', f(K2), 'dotted') : '')"
            " + z(d.sr < 0 ? C.rot : C.sz, 'Reserve (Szenario)', f(d.sr), 'dotted'); }"
            " return h; }")


def _trend(o, t, c, zs_sz, ort, zaehl, szen) -> dict:
    schritt = c["schritt"]
    kap_sz = c["kap"]
    kap = c["pg"].kapazitaet or 0                    # Hauptlinien: immer die echten Werte
    zs = ak.szenario(c["pg"], kap, 0)
    aktiv = _szenario_aktiv(c)
    zeig = lambda n: schritt >= n  # noqa: E731
    labels = [ak.monat_text(z.monat) for z in zs]
    o["xAxis"]["data"] = labels
    _titel(o, t, f"Belegung {ort} · {zaehl}" + (" · mit SZENARIO als Schattenkurve" if aktiv else ""),
           f"Ø belegte Plätze je Monat · {_zeitraum(zs)} · Ist bis {c['stichtag']:%d.%m.%Y}, danach Prognose")
    o["tooltip"][":formatter"] = _formatter(zs, kap, t, zs_sz if aktiv else None, kap_sz)
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
    reihen += _geist(t, zs_sz, zs, li, kap, kap_sz, aktiv and zeig(2))
    o["series"] = reihen
    # feste Achse über alle Aufbauschritte – sonst „springt“ der Graph, wenn Bänder oder Kapazität dazukommen
    werte = [z.ist for z in zs if z.art == "ist" and z.ist is not None] + [z.lo95 if c["b95"] else z.lo80 for z in zs if z.art != "ist"] \
        + [z.hi95 if c["b95"] else z.hi80 for z in zs if z.art != "ist"] + ([kap] if kap else []) + list(blind.values()) \
        + ([z.erwartet for z in zs_sz if z.art != "ist"] + ([kap_sz] if kap_sz else []) if aktiv else [])
    if werte:
        unten, oben = min(werte), max(werte)
        rand = max(2.0, (oben - unten) * .06)
        schritt_y = 10 if oben - unten > 60 else 5 if oben - unten > 20 else 1
        o["yAxis"]["min"] = max(0, int((unten - rand) // schritt_y * schritt_y))
        o["yAxis"]["max"] = int(-(-(oben + rand) // schritt_y) * schritt_y)
    o["legend"]["data"] = ["Ist", "laufender Monat", "Prognose (erwartet)", "80 %-Band"] + (["95 %-Band"] if c["b95"] else []) + \
        (["Kapazität"] if kap else []) + (["Backtest (1 Monat vorher)"] if blind else []) + \
        (["Szenario (Simulation)"] + (["Kapazität Szenario"] if kap_sz != kap else []) if aktiv else [])
    return o


def _status(o, t, c, zs_sz, ort, zaehl, szen) -> dict:
    """Gestapelte Fläche: UWTler · Mieter · Teilnehmende & Sonstige (Summe = Ist bzw. erwartete Belegung)."""
    sm = c["sm"]
    kap = c["pg"].kapazitaet or 0
    kap_sz = c["kap"]
    aktiv = _szenario_aktiv(c)
    fb = an.STATUS_FARBEN[bool(t.get("hell"))]
    labels = [ak.monat_text(m.monat) for m in sm]
    li = max((i for i, m in enumerate(sm) if m.art == "ist"), default=None)
    o["xAxis"]["data"] = labels
    o["yAxis"]["scale"] = False
    _titel(o, t, f"Belegung {ort} nach Status · {zaehl}" + (" · mit SZENARIO als Schattenkurve" if aktiv else ""),
           f"Ø Plätze je Monat · {_zeitraum(sm)} · UWT und Mieter: Ist bzw. gebucht · Rest: Ist bzw. Prognose")
    reihen = []
    for schl in ("UWT", "Mieter", "uebrige"):
        farbe = fb[schl]
        reihen.append({"name": an.STATUS_NAMEN[schl], "type": "line", "stack": "status", "symbol": "none", "color": farbe,
                       "data": [round(getattr(m, schl.lower()), 1) for m in sm], "lineStyle": {"width": 1, "color": farbe},
                       "areaStyle": {"color": _rgba(farbe, .85 if schl != "uebrige" else .28)},
                       "animationDuration": 900})
    if li is not None and li + 1 < len(sm):
        reihen[-1]["markArea"] = {"silent": True, "itemStyle": {"color": _rgba(t["akzent"], .045)},
                                  "label": {"show": True, "position": "insideTop", "color": t["text3"], "fontSize": 11,
                                            "formatter": "Prognose →"},
                                  "data": [[{"xAxis": labels[li]}, {"xAxis": labels[-1]}]]}
    if kap:
        reihen.append({"name": "Kapazität", "type": "line", "symbol": "none", "color": t["rot"], "z": 6,
                       "data": [kap] * len(sm), "lineStyle": {"color": t["rot"], "width": 1.4, "type": [5, 4]},
                       "endLabel": {"show": True, "formatter": "Kapazität {c}", "color": t["rot"], "fontSize": 11}})
    kont = c.get("kontingent")
    if kont and kap:                                    # Kontingentgrenzen: UWT unten, darüber UWT + Mieter
        for name, wert, farbe in (("Kontingent UWT", kap * kont["UWT"] / 100, fb["UWT"]),
                                  ("Kontingent UWT + Mieter", kap * (kont["UWT"] + kont["Mieter"]) / 100, fb["Mieter"])):
            reihen.append({"name": name, "type": "line", "symbol": "none", "z": 6, "color": farbe, "data": [round(wert, 1)] * len(sm),
                           "lineStyle": {"color": t["text"], "width": 1.1, "type": [6, 3], "opacity": .7},
                           "endLabel": {"show": True, "formatter": f"{name} {round(wert)}", "color": t["text2"], "fontSize": 10}})
    zs0 = ak.szenario(c["pg"], kap, 0)
    if aktiv:
        reihen += _geist(t, zs_sz, zs0, li, kap, kap_sz, True)
    o["series"] = reihen
    o["grid"]["right"] = 150 if kont else 96
    o["legend"]["data"] = [an.STATUS_NAMEN[k] for k in ("UWT", "Mieter", "uebrige")] + (["Kapazität"] if kap else []) + \
        (["Szenario (Simulation)"] + (["Kapazität Szenario"] if kap_sz != kap else []) if aktiv else [])
    d = [{"m": ak.monat_text(m.monat), "a": m.art, "u": m.uwt, "mi": m.mieter, "r": m.uebrige, "g": m.gesamt,
          "se": zs_sz[i].erwartet if aktiv and m.art != "ist" else None} for i, m in enumerate(sm)]
    fc = {"u": fb["UWT"], "mi": fb["Mieter"], "r": fb["uebrige"], "sz": t["orange"], "b": t["text3"]}
    o["tooltip"][":formatter"] = (
        "(ps) => { const D = " + json.dumps(d) + "; const C = " + json.dumps(fc) + "; const K = " + str(kap or 0) + ";"
        " const d = D[ps[0].dataIndex]; if (!d) return '';"
        " const f = v => v == null ? '–' : Math.round(v).toLocaleString('de-DE');"
        " const p = v => d.g ? ' <span style=\"opacity:.6;font-weight:400;margin-left:6px\">(' + Math.round(100 * v / d.g) + ' %)</span>' : '';"
        " const z = (c, t, v, extra) => `<div style=\"display:flex;gap:18px;justify-content:space-between;line-height:1.75\">"
        "<span><span style=\"display:inline-block;width:10px;height:10px;border-radius:2px;background:${c};margin-right:7px;vertical-align:-1px\"></span>${t}</span>"
        "<b style=\"font-variant-numeric:tabular-nums\">${v}${extra || ''}</b></div>`;"
        " const art = d.a == 'ist' ? 'Ist' : (d.a == 'laufend' ? 'laufender Monat' : 'Prognose');"
        " let h = `<div style=\"font-weight:600;margin-bottom:6px\">${d.m} <span style=\"opacity:.65;font-weight:400\">· ${art}</span></div>`;"
        " h += z(C.u, 'UWTler' + (d.a == 'ist' ? '' : ' (gebucht)'), f(d.u), p(d.u)) + z(C.mi, 'Mieter' + (d.a == 'ist' ? '' : ' (Verträge)'), f(d.mi), p(d.mi))"
        " + z(C.r, 'Teilnehmende & Sonstige' + (d.a == 'ist' ? '' : ' (Prognose)'), f(d.r), p(d.r));"
        " h += `<div style=\"border-top:1px solid ${C.b}55;margin:6px 0 2px\"></div>` + z('transparent', 'Gesamt', f(d.g))"
        " + (K ? z('transparent', 'Auslastung', Math.round(100 * d.g / K) + ' %') : '');"
        " if (d.se != null) h += z(C.sz, 'Szenario (Simulation)', f(d.se));"
        " return h; }")
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
                      "label": {"color": t["text3"], "fontSize": 10, "formatter": "{b}", "position": "start"},   # y-Achse ist umgedreht → oben
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
    goslar = a.aw_standort == GOSLAR
    if pg and (a.aw_status or goslar):
        a.daten["sm"] = an.status_monate(ds, a.aw_standort, a.aw_brutto, pg)
    if pg and goslar:
        a.daten["sl"] = an.status_lage(ds, a.aw_standort, a.aw_brutto, a.daten["sm"])
        a.daten["kontingent"] = kern.kontingent_lesen(a.aw_standort)
    a.daten["sanierung"] = an.sanierung_plaetze(getattr(getattr(a, "stand", None), "lage", None), a.aw_standort)


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
                            "schritt": a.aw_schritt if praes and a.aw_chart == "trend" and not a.aw_status else 4, "animation": anim,
                            "pg_lang": a.daten.get("pg_lang"), "stichtag": a.daten["stichtag"],
                            "status": a.aw_status, "sm": a.daten.get("sm"), "kontingent": kontingent()}
    ds = a.daten["ds"]
    box: dict = {}
    sm = a.daten.get("sm") or []

    def kontingent():
        """Geplante Aufteilung (gespeichert) oder Vorschlag aus den gebuchten Zahlen – nur Goslar."""
        if a.aw_standort != GOSLAR or not sm:
            return None
        return a.daten.get("kontingent") or an.kontingent_vorschlag(sm, kap_echt)

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
        # ---- Goslar: Aufteilung UWTler / Mieter und Kontingente (direkt unter der Standortwahl) ----------
        if a.aw_standort == GOSLAR and a.daten.get("sl"):
            gs_box = ui.element("section").classes("m-block m-xgs" + (" kompakt" if praes else ""))

            def goslar_zeichnen():
                gs_box.clear()
                with gs_box:
                    _goslar(a, a.daten["sl"], sm, kap_echt, kontingent(), praes, hell, goslar_neu)

            def goslar_neu(werte):
                a.daten["kontingent"] = werte
                kern.kontingent_setzen(GOSLAR, werte)
                goslar_zeichnen()
                if a._prognose_chart:
                    a._prognose_chart()
            goslar_zeichnen()
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
                trend = a.aw_chart == "trend"
                _umschalter("history", "Backtest", a.aw_backtest and trend and not a.aw_status,
                            lambda: a.setzen(aw_backtest=not a.aw_backtest, laden=False),
                            "Blind-Prognosen der Vergangenheit (je einen Monat vorher gerechnet) im Graph zeigen"
                            if pg.rueckblick else "Für diese Auswahl gibt es keinen Backtest-Verlauf",
                            aus=not (trend and not a.aw_status and pg.rueckblick))
                with ui.element("div").classes("m-xg-status" + ("" if trend else " aus")):
                    attr(ui.label("Ansicht"), title="Gesamtbelegung oder gestapelt nach Status: UWTler · Mieter · übrige")
                    segmente({False: "Gesamt", True: "Nach Status"}, a.aw_status,
                             lambda v: a.setzen(aw_status=v, laden=v and "sm" not in a.daten) if trend else None)
                if praes and a.aw_chart == "trend" and not a.aw_status:
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
                                ui.separator()
                                _schalter("Animation beim Öffnen" + (" (System: weniger Bewegung)" if a.weniger_bewegung else ""),
                                          a.aw_anim and not a.weniger_bewegung, lambda: a.setzen(aw_anim=not a.aw_anim, laden=False),
                                          aus=a.weniger_bewegung)
            chart = ui.echart(option(c(animiert))).classes("m-chart m-xg-chart" + (" gross" if praes else ""))
            box["chart"] = chart
            with ui.element("div").classes("m-xg-fuss"):
                ui.html(_legende_text("status" if a.aw_chart == "trend" and a.aw_status else a.aw_chart,
                                      kap_echt != zustand["kap"] or bool(zustand["offset"])), sanitize=False)

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
            szenario_zeichnen()
            tabelle_zeichnen()

        sanierung = a.daten.get("sanierung")

        def setzen(kap=None, offset=None):
            if kap is not None:
                zustand["kap"] = a.aw_kap = max(0, int(round(kap)))
            if offset is not None:
                zustand["offset"] = a.aw_offset = float(max(-OFFSET_MAX, min(OFFSET_MAX, round(offset))))
            alles_neu()

        def szenario_zeichnen():
            """Management-Szenario: Schnell-Pills, Plus/Minus-Stepper, Vergleich Ausgang ↔ Szenario."""
            kap, off = zustand["kap"], zustand["offset"]
            aktiv = kap != kap_echt or bool(off)
            sz_box.clear()
            sz_box.classes(add="aktiv" if aktiv else "", remove="" if aktiv else "aktiv")
            with sz_box:
                with ui.element("div").classes("m-paktionen").style("align-items:center"):
                    ui.icon("science").classes("m-xs-icon")
                    ui.label("Management-Szenario").classes("m-btitel")
                    ui.label("Was wäre, wenn … – wirkt nur auf die Prognosemonate; Ist bleibt Ist").classes("m-zweite")
                    if aktiv:
                        ui.label("SIMULATION – keine echten Daten").classes("m-xs-banner")
                # Schnellszenarien
                with ui.element("div").classes("m-xs-pills"):
                    _pill("Ausgangslage", "restart_alt", not aktiv, lambda: setzen(kap_echt, 0.0),
                          "Echte Kapazität, Prognose unverändert")
                    _pill("+10 % Auslastung", "trending_up", off == 10, lambda: setzen(offset=0.0 if off == 10 else 10.0),
                          "Erwartete Belegung in allen Prognosemonaten um 10 % höher")
                    _pill("−10 % Auslastung", "trending_down", off == -10, lambda: setzen(offset=0.0 if off == -10 else -10.0),
                          "Erwartete Belegung in allen Prognosemonaten um 10 % niedriger")
                    if sanierung:
                        _pill(f"Kapazitätskürzung Sanierung (−{sanierung})", "construction", kap == kap_echt - sanierung,
                              lambda: setzen(kap=kap_echt if kap == kap_echt - sanierung else kap_echt - sanierung),
                              f"Kapazität um die {sanierung} Betten kürzen, deren Zimmer derzeit wegen eines Mangels unbewohnbar "
                              "sind (Gebäudeplan Goslar)")
                    else:
                        _pill("Kapazitätskürzung Sanierung", "construction", False, None,
                              "Keine Grundlage: für diese Auswahl sind keine unbewohnbaren Zimmer erfasst (Gebäudeplan nur "
                              "Goslar) – eine Kürzung lässt sich unten mit dem Stepper einstellen", aus=True)
                # Feineinstellung
                with ui.element("div").classes("m-xs-stepper"):
                    with ui.element("div").classes("m-xs-step"):
                        ui.label("Kapazität").classes("m-name")
                        for d in (-10, -1):
                            knopf(f"−{-d}", lambda d=d: setzen(kap=zustand["kap"] + d), "leise klein", "", f"Kapazität −{-d} Plätze")
                        feld = ui.number(value=kap, min=0, max=5000, step=1, format="%d").classes("m-feld klein").props(
                            "dense outlined dark")
                        attr(feld, aria_label="Kapazität im Szenario")
                        feld.on("change", lambda: setzen(kap=feld.value or 0) if int(feld.value or 0) != zustand["kap"] else None)
                        for d in (1, 10):
                            knopf(f"+{d}", lambda d=d: setzen(kap=zustand["kap"] + d), "leise klein", "", f"Kapazität +{d} Plätze")
                        ui.label(f"Plätze · echt {_z(kap_echt)}" + (f" · {kap - kap_echt:+d}" if kap != kap_echt else "")).classes("m-zweite")
                    with ui.element("div").classes("m-xs-step"):
                        ui.label("Auslastung").classes("m-name")
                        for d in (-5, -1):
                            knopf(f"−{-d}", lambda d=d: setzen(offset=zustand["offset"] + d), "leise klein", "", f"Auslastung −{-d} %")
                        off_feld = ui.number(value=off, min=-OFFSET_MAX, max=OFFSET_MAX, step=1, format="%d").classes(
                            "m-feld klein").props("dense outlined dark suffix=%")
                        attr(off_feld, aria_label="Auslastungs-Annahme in Prozent")
                        off_feld.on("change", lambda: setzen(offset=off_feld.value or 0)
                                    if float(off_feld.value or 0) != zustand["offset"] else None)
                        for d in (1, 5):
                            knopf(f"+{d}", lambda d=d: setzen(offset=zustand["offset"] + d), "leise klein", "", f"Auslastung +{d} %")
                        ui.label(f"% auf die Prognosemonate · ± {OFFSET_MAX} %").classes("m-zweite")
                with ui.element("div").classes("m-xs-vergleich"):
                    _sz_vergleich(pg, zustand)
                ui.label("Im Graph läuft das Szenario als transparente Schattenkurve über der echten Prognose. Nur Kapazität und "
                         "Auslastung haben eine belastbare Grundlage im Modell; andere Annahmen (z. B. Verweildauer) werden nicht "
                         "scheinbar genau simuliert. Gespeichert wird nichts.").classes("m-zweite").style("white-space:normal")
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


def _legende_text(art: str, szenario: bool = False) -> str:
    sz = "<span><i class='l sz'></i>Szenario (Simulation) – Schattenkurve, keine echten Daten</span>" if szenario else ""
    if art == "trend":
        return ("<span><i class='l ist'></i>Ist (Monatsmittel)</span><span><i class='p hohl'></i>laufender Monat – unvollständig</span>"
                "<span><i class='l prog'></i>Prognose (erwartet)</span><span><i class='f'></i>80 %- / 95 %-Band: so sicher liegt der "
                "Wert darin</span><span><i class='l kap'></i>Kapazität</span>" + sz)
    if art == "status":
        return ("<span><i class='f uwt'></i>UWTler</span><span><i class='f mieter'></i>Mieter</span>"
                "<span><i class='f rest'></i>Teilnehmende & Sonstige</span><span><i class='l kap'></i>Kapazität</span>"
                "<span><i class='l kont'></i>Kontingentgrenzen (Goslar)</span>"
                "<span>Zukunft: UWT und Mieter wie gebucht, nur der Rest ist Prognose</span>" + sz)
    if art == "reserve":
        return ("<span><i class='f ok'></i>Reserve</span><span><i class='f warn'></i>knapp (≥ 70 % obere 80 %)</span>"
                "<span><i class='f krit'></i>kritisch / über Kapazität</span><span><i class='l'></i>ungünstiger Fall</span>"
                "<span>Unter der Nulllinie: rechnerisch mehr Belegung als Plätze</span>")
    return ("<span><i class='l ist'></i>aktuell Ist</span><span><i class='l prog'></i>aktuell Prognose</span>"
            "<span><i class='l vj'></i>Vorjahr</span><span><i class='l vvj'></i>Vorvorjahr</span>"
            "<span>Lücken = keine Daten für diesen Monat</span>")


def _pill(text: str, icon: str, an_: bool, klick, titel: str, aus: bool = False) -> None:
    b = ui.element("button").classes("m-xs-pill" + (" an" if an_ else "") + (" aus" if aus else ""))
    attr(b, title=titel, aria_pressed=str(an_).lower(), **({"disabled": True} if aus else {}))
    with b:
        ui.icon(icon)
        ui.label(text)
    if klick and not aus:
        b.on("click", klick)


def _umschalter(icon: str, text: str, an_: bool, klick, titel: str, aus: bool = False) -> None:
    """Direkter Ein/Aus-Schalter mit Statusanzeige (z. B. Backtest)."""
    b = ui.element("button").classes("m-xg-toggle" + (" an" if an_ else "") + (" aus" if aus else ""))
    attr(b, title=titel, aria_pressed=str(an_).lower(), **({"disabled": True} if aus else {}))
    with b:
        ui.icon(icon)
        ui.label(text)
        ui.label("an" if an_ else "aus").classes("m-xg-toggle-status")
    if not aus:
        b.on("click", klick)


def _goslar(a, sl: an.StatusLage, sm, kap: int, kont: dict | None, kompakt: bool, hell: bool, aendern) -> None:
    """Aufteilung Goslar: heute (UWT · Mieter · übrige · frei), Kontingente in % und Prüfung der nächsten Monate."""
    fb = an.STATUS_FARBEN[hell]
    h = sl.heute
    with ui.element("div").classes("m-paktionen").style("align-items:baseline"):
        ui.label("Goslar · UWTler und Mieter").classes("m-btitel")
        ui.label(f"Stichtag {sl.stichtag:%d.%m.%Y} · Kapazität {_z(kap)} Plätze · UWT und Mieter: gebuchte Plätze").classes("m-zweite")
    # Balken der Kapazität heute
    with ui.element("div").classes("m-xgs-balken"):
        for schl, wert in (("UWT", h["UWT"]), ("Mieter", h["Mieter"]), ("uebrige", h["uebrige"]), ("frei", h["frei"])):
            if kap and wert > 0:
                farbe = _rgba(fb[schl], .45) if schl == "uebrige" else fb.get(schl, "transparent")
                teil = ui.element("div").classes(f"m-xgs-teil {schl}").style(f"flex:{wert}; background:{farbe}")
                attr(teil, title=f"{an.STATUS_NAMEN.get(schl, 'frei')}: {_z(wert)} Plätze ({an._p(wert / kap)})")
    with ui.element("div").classes("m-xgs-zahlen"):
        for schl, wert in (("UWT", h["UWT"]), ("Mieter", h["Mieter"]), ("uebrige", h["uebrige"]), ("frei", h["frei"])):
            with ui.element("div").classes("m-xgs-zahl"):
                ui.element("span").classes(f"m-xgs-punkt {schl}").style(f"background:{fb.get(schl, 'transparent')}")
                ui.label(an.STATUS_NAMEN.get(schl, "frei"))
                ui.label(_z(wert)).classes("m-mono w")
                ui.label(an._p(wert / kap) if kap else "–").classes("m-zweite")
    if kompakt:
        for satz in sl.saetze[:2]:
            ui.label(satz).classes("m-ptext")
        return
    for satz in sl.saetze:
        ui.label(satz).classes("m-ptext")
    if not kont or not kap:
        return
    # Kontingente: geplante prozentuale Aufteilung der Kapazität
    zeilen = an.kontingent_pruefung(sm, kap, kont)
    rest = max(100 - kont["UWT"] - kont["Mieter"], 0)
    with ui.element("div").classes("m-xgs-kont"):
        with ui.element("div").classes("m-paktionen").style("align-items:center"):
            ui.label("Kontingente – geplante Aufteilung der Kapazität").classes("m-name")
            ui.label("gespeichert" if a.daten.get("kontingent") else "Vorschlag aus den gebuchten Spitzen").classes("m-xgs-herkunft")
            if a.daten.get("kontingent"):
                knopf("Vorschlag", lambda: aendern(None), "leise", "auto_fix_high",
                      "Eigene Aufteilung löschen und wieder den Vorschlag aus den Daten zeigen")
        with ui.element("div").classes("m-xgs-stepper"):
            for schl in ("UWT", "Mieter"):
                with ui.element("div").classes("m-xgs-step"):
                    ui.element("span").classes("m-xgs-punkt").style(f"background:{fb[schl]}")
                    ui.label(an.STATUS_NAMEN[schl])
                    for d in (-5, -1):
                        knopf(f"−{-d}", lambda d=d, schl=schl: aendern(_kont_neu(kont, schl, d)), "leise klein")
                    ui.label(f"{kont[schl]:g} %").classes("m-mono w")
                    for d in (1, 5):
                        knopf(f"+{d}", lambda d=d, schl=schl: aendern(_kont_neu(kont, schl, d)), "leise klein")
                    ui.label(f"= {_z(kap * kont[schl] / 100)} Plätze").classes("m-zweite")
            with ui.element("div").classes("m-xgs-step"):
                ui.element("span").classes("m-xgs-punkt").style(f"background:{fb['uebrige']}")
                ui.label("Teilnehmende & Sonstige")
                ui.label(f"{rest:g} %").classes("m-mono w")
                ui.label(f"= {_z(kap * rest / 100)} Plätze (Rest)").classes("m-zweite")
        st = {"ok": "", "knapp": " warn", "ueber": " krit"}
        with ui.element("div").classes("m-xgs-tab"):
            for t in ("Monat", "UWT gebucht", "Mieter gebucht", "Übrige (Prognose)", "Gesamt"):
                ui.label(t).classes("m-zweite")
            for z in zeilen[:6]:
                ui.label(ak.monat_text(z.monat) + (" · laufend" if z.art == "laufend" else "")).classes("m-name")
                for wert, grenze, schl in ((z.uwt, z.k_uwt, "UWT"), (z.mieter, z.k_mieter, "Mieter"), (z.uebrige, z.k_uebrige, "uebrige")):
                    ui.label(f"{_z(wert)} / {_z(grenze)}").classes("m-mono" + st[z.stufe[schl]])
                ui.label(f"{_z(z.uwt + z.mieter + z.uebrige)} / {_z(kap)}").classes("m-mono")
        for satz in an.kontingent_saetze(zeilen, kont):
            ui.label(satz).classes("m-ptext")
        ui.label("Kontingente sind eine Planungsannahme der neuen Oberfläche (gespeichert in modern_ui.json). "
                 "Sie ändern weder Kapazität noch Belegungsdaten.").classes("m-zweite").style("white-space:normal")


def _kont_neu(kont: dict, schl: str, d: float) -> dict:
    neu = dict(kont)
    andere = neu["Mieter" if schl == "UWT" else "UWT"]
    neu[schl] = float(max(0, min(100 - andere, neu[schl] + d)))
    return neu

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
