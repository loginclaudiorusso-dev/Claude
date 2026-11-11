"""Diagrammstil (0.66) wie „Diagrammtyp ändern“ in Office – zentral auf jede ECharts-Option angewandt. Rein.

Umgewandelt werden nur die **Datenreihen** (Ist, Prognose, Belegung je Art …). Unverändert bleiben:
* Unsicherheitsbänder (gestapelte, unsichtbare Hilfslinien) – sie sind eine Spanne, keine Reihe,
* Bezugs- und Vergleichslinien (gepunktet: Kapazität, Rückwärtstest/Backtest),
* Diagramme, die keine Linien sind (Heatmap, Balken bleiben Balken).
"""

from __future__ import annotations

import copy

WERTE_MAX = 40          # Datenbeschriftungen nur bei kurzen Reihen – sonst wird es unlesbar


def _band(se: dict) -> bool:
    st = str(se.get("stack") or "")
    return (st.startswith("band") or st in ("b80", "b95") or (se.get("lineStyle") or {}).get("opacity") == 0
            or "Spanne" in str(se.get("name", "")) or "Band" in str(se.get("name", "")))


def _werte(se: dict) -> list:
    out = []
    for x in se.get("data") or []:
        if isinstance(x, dict):
            x = x.get("value")
        if isinstance(x, (list, tuple)):
            x = x[-1] if x else None
        out.append(x)
    return out


def _bezug(se: dict) -> bool:
    """Bezugslinie: gepunktet (Kapazität, Rückwärtstest) oder ausdrücklich „Kapazität“ – auch wenn die Werte schwanken."""
    return (se.get("lineStyle") or {}).get("type") == "dotted" or "Kapazität" in str(se.get("name", ""))


def datenreihe(se: dict) -> bool:
    return se.get("type") == "line" and not _band(se) and not _bezug(se) and bool(se.get("name", "") or se.get("data"))


def anwenden(opt: dict, d: dict) -> dict:
    """Gibt eine angepasste Kopie zurück. ``d``: Darstellung (dg_typ, dg_glatt, dg_punkte, dg_werte, dg_gitter,
    dg_legende, dg_anim)."""
    typ = d.get("dg_typ", "linie")
    if (typ == "linie" and not d.get("dg_glatt") and not d.get("dg_punkte") and not d.get("dg_werte")
            and d.get("dg_gitter", True) and d.get("dg_legende", "oben") == "oben" and d.get("dg_anim", True)):
        return opt
    o = copy.deepcopy(opt)
    reihen = o.get("series") or []
    saeule = False
    for se in reihen:
        if se.get("type") == "line" and d.get("dg_glatt"):
            se["smooth"] = True
        if not datenreihe(se):
            continue
        gestrichelt = (se.get("lineStyle") or {}).get("type") == "dashed"          # Prognose
        if typ == "flaeche" and "areaStyle" not in se:
            se["areaStyle"] = {"opacity": 0.10 if gestrichelt else 0.18}
        elif typ == "saeule":
            saeule = True
            farbe = (se.get("lineStyle") or {}).get("color") or se.get("color")
            se["type"] = "bar"
            se["barMaxWidth"] = 22
            se.pop("smooth", None)
            se.pop("symbol", None)
            se.pop("symbolSize", None)
            stil = dict(se.get("itemStyle") or {})
            if farbe:
                stil["color"] = farbe
            if gestrichelt:
                stil["opacity"] = 0.55               # Prognose als hellere Säulen – erkennbar, aber nicht „Ist“
            se["itemStyle"] = stil
            se.pop("lineStyle", None)
        if d.get("dg_punkte") and se.get("type") == "line":
            se["showSymbol"] = True
            if se.get("symbol") in (None, "none"):
                se["symbol"] = "circle"
            se.setdefault("symbolSize", 5)
        if d.get("dg_werte") and len(_werte(se)) <= WERTE_MAX:
            se["label"] = {"show": True, "position": "top", "fontSize": 10}
    if saeule:
        for achse in _liste(o.get("xAxis")):
            if achse.get("type") == "category":
                achse["boundaryGap"] = True
    if not d.get("dg_gitter", True):
        for achse in _liste(o.get("yAxis")) + _liste(o.get("xAxis")):
            achse["splitLine"] = {**(achse.get("splitLine") or {}), "show": False}
    leg = d.get("dg_legende", "oben")
    if leg != "oben":
        for lg in _liste(o.get("legend")):
            if leg == "aus":
                lg["show"] = False
            else:
                lg.pop("top", None)
                lg["bottom"] = 0
        if leg == "unten":
            for g in _liste(o.get("grid")):
                if isinstance(g.get("bottom"), (int, float)):
                    g["bottom"] = g["bottom"] + 24
    if not d.get("dg_anim", True):
        o["animation"] = False
    return o


def _liste(x) -> list[dict]:
    if isinstance(x, dict):
        return [x]
    if isinstance(x, list):
        return [y for y in x if isinstance(y, dict)]
    return []


# =====================================================================================================================
# 0.87 Einheitlicher Diagrammstil – EINE Farb- und Beschriftungslogik für die Diagramm-Karten
# =====================================================================================================================
# Rolle einer Reihe: ausdrücklich ``se["rolle"]`` oder aus dem Namen erkannt (so gilt die Logik auch für ältere Bauweisen).
#   ist        Aktuell Ist          Akzentfarbe, 3 px, durchgezogen, beschriftet
#   prognose   Prognose             Akzentfarbe, gestrichelt, beschriftet
#   band       80-%-Band            helle Akzentfläche (unsichtbare Hilfslinien)
#   band95     95-%-Band            noch hellere Fläche (nur, wenn eingeschaltet)
#   vorjahr    Vorjahr              neutrales Grau, 1,5 px
#   vorvorjahr Vorvorjahr           dunkleres Grau, 1 px, gepunktet
#   kapazitaet Kapazität            rot, 1,5 px, am rechten Rand „Kapazität 330“
#   test       Rückwärtstest        dünn gepunktet, ohne Beschriftung
#   stapel     Anteile (Tageswerte) gestapelte Stufenflächen in eigenen Farben
#   balken_ist / balken_prognose    Zählwerte als Balken (Prognose heller, gestrichelter Rand)

FOKUS_ID = "m-fokus"
# 0.94: feste Gruppenfarben – eine Gruppe sieht überall gleich aus (Karte und Einfach). Klassisch bleibt wie bisher.
GRUPPEN_FARBEN = {"Reha": "#00929A", "UWT": "#5B5BD6", "Umschüler": "#5B5BD6", "UWTler": "#5B5BD6",
                  "Mieter": "#B8650A"}


def gruppen_farbe(name: str, i: int, sonst: list[str]) -> str:
    """Feste Farbe für Reha, Umschüler und Mieter – alle übrigen Kategorien aus der Liste ``sonst``."""
    return GRUPPEN_FARBEN.get(name) or sonst[i % len(sonst)]
SCHRIFT = "Segoe UI, Inter, sans-serif"
ZAHL_JS = "(v) => (v == null || isNaN(v)) ? '' : Math.round(v).toLocaleString('de-DE')"
WERT_JS = ("(p) => { const v = Array.isArray(p.value) ? p.value[p.value.length - 1] : p.value; "
           "return (v == null || isNaN(v)) ? '' : Math.round(v).toLocaleString('de-DE'); }")


def rolle(se: dict) -> str:
    if se.get("rolle"):
        return se["rolle"]
    n = str(se.get("name") or "")
    st = str(se.get("stack") or "")
    if st == "b95" or "95" in n and ("Band" in n or "Spanne" in n):
        return "band95"
    if _band(se):
        return "band"
    if "Vorvorjahr" in n:
        return "vorvorjahr"
    if "Vorjahr" in n:
        return "vorjahr"
    if "Kapazität" in n:
        return "kapazitaet"
    if "Backtest" in n or "Rückwärtstest" in n:
        return "test"
    if se.get("type") == "line" and ("Prognose" in n or (se.get("lineStyle") or {}).get("type") in ("dashed", [7, 5])):
        return "prognose"
    if se.get("type") == "line" and ("Ist" in n or n == "Belegung"):
        return "ist"
    return ""


def _label(farbe_hg: str) -> dict:
    return {"show": True, "position": "top", "distance": 6, "fontSize": 12, "fontWeight": "bold", "color": "#fff",
            "backgroundColor": farbe_hg, "padding": [2, 5], "borderRadius": 3, "textBorderWidth": 0,
            ":formatter": WERT_JS}


def _endlabel(text_js: str, farbe: str) -> dict:
    return {"show": True, "fontSize": 12, "fontWeight": 600, "color": farbe, "distance": 6, ":formatter": text_js}


def einheitlich(opt: dict, t: dict, stand: str | None = None, prognose_ab: str | None = None,
                spanne: dict | None = None, tageswerte: bool = False, legende: bool = True) -> dict:
    """Gibt eine Kopie im einheitlichen Stil zurück. ``stand``/``prognose_ab``: Kategorie der x-Achse für die Linie
    „Datenstand“ bzw. den Beginn des hinterlegten Prognosebereichs. ``spanne``: {Index: (unten, oben)} für den Tooltip."""
    o = copy.deepcopy(opt)
    o.pop("title", None)
    akzent, rot, grau, grau2 = t["akzent"], t.get("rot", "#d64545"), t.get("text3", "#8a8f98"), t.get("text2", "#5f6670")
    label_hg = "rgba(24,28,34,.82)"
    o["textStyle"] = {"color": t.get("text2", "#555"), "fontFamily": SCHRIFT, "fontSize": 12}
    for ax in _liste(o.get("xAxis")) + _liste(o.get("yAxis")):
        al = dict(ax.get("axisLabel") or {})
        al.update({"fontSize": 12, "color": grau})
        if ax.get("type") == "value":
            al[":formatter"] = ZAHL_JS
            al.pop("formatter", None)
        ax["axisLabel"] = al
    namen, rollen = [], {}
    for se in o.get("series") or []:
        r = rolle(se)
        rollen[se.get("name") or ""] = r
        if se.get("type") == "line":
            se["smooth"] = False
            if tageswerte and r in ("ist", "prognose", "stapel", ""):
                se["step"] = "end"
        if r == "ist":
            se.update({"color": akzent, "symbol": "circle", "symbolSize": 5, "showSymbol": not tageswerte,
                       "lineStyle": {**(se.get("lineStyle") or {}), "color": akzent, "width": 3, "type": "solid"},
                       "itemStyle": {"color": akzent}, "label": {**_label(label_hg), "show": not tageswerte},
                       "labelLayout": {"hideOverlap": True}, "z": 5})
        elif r == "prognose":
            se.update({"color": akzent, "symbol": "emptyCircle", "symbolSize": 5, "showSymbol": not tageswerte,
                       "lineStyle": {**(se.get("lineStyle") or {}), "color": akzent, "width": 2.5, "type": "dashed"},
                       "itemStyle": {"color": akzent}, "label": {**_label(label_hg), "show": not tageswerte},
                       "labelLayout": {"hideOverlap": True}, "z": 5})
        elif r in ("band", "band95"):
            se["lineStyle"] = {"opacity": 0}
            se["symbol"] = "none"
            if se.get("areaStyle") is not None:
                se["areaStyle"] = {"color": akzent, "opacity": .16 if r == "band" else .07}
            se["color"] = akzent
        elif r == "vorjahr":
            se.update({"color": grau, "symbol": "none", "lineStyle": {"color": grau, "width": 1.5, "type": "solid"},
                       "label": {"show": False}})
        elif r == "vorvorjahr":
            se.update({"color": grau2, "symbol": "none", "lineStyle": {"color": grau2, "width": 1, "type": "dotted"},
                       "label": {"show": False}})
        elif r == "kapazitaet":
            werte = [v for v in _werte(se) if v is not None]
            k = f"{round(max(werte)):,}".replace(",", ".") if werte else ""
            se.update({"color": rot, "symbol": "none", "lineStyle": {"color": rot, "width": 1.5, "type": "solid"},
                       "label": {"show": False}, "z": 4,
                       "endLabel": _endlabel(f"() => {json_str(('Kapazität ' + k).strip())}", rot),
                       "labelLayout": {"moveOverlap": "shiftY"}})
        elif r == "test":
            ls = dict(se.get("lineStyle") or {})
            ls.update({"width": 1.2, "type": "dotted"})
            se.update({"lineStyle": ls, "label": {"show": False}})
        elif r == "balken_ist":
            se.update({"type": "bar", "color": akzent, "itemStyle": {"color": akzent, "borderRadius": [3, 3, 0, 0]},
                       "label": {**_label(label_hg), "position": "top"}, "labelLayout": {"hideOverlap": True},
                       "barMaxWidth": 26, "barGap": "-100%"})
        elif r == "balken_prognose":
            se.update({"type": "bar", "color": akzent,
                       "itemStyle": {"color": akzent, "opacity": .45, "borderColor": akzent, "borderWidth": 1.2,
                                     "borderType": "dashed", "borderRadius": [3, 3, 0, 0]},
                       "label": {**_label(label_hg), "position": "top"}, "labelLayout": {"hideOverlap": True},
                       "barMaxWidth": 26, "barGap": "-100%"})
        if r in ("ist", "prognose", "vorjahr", "vorvorjahr") and se.get("name") and se.get("type") == "line" and legende:
            farbe = {"vorjahr": grau, "vorvorjahr": grau2}.get(r, akzent)
            se["endLabel"] = _endlabel(f"() => {json_str(kurzname(se['name']))}", farbe)
            se["labelLayout"] = {"hideOverlap": r in ("ist", "prognose"), "moveOverlap": "shiftY"}   # Enden nicht übereinander
        if se.get("name") and r not in ("band", "band95") and not str(se["name"]).startswith("_") \
                and (se.get("tooltip") or {}).get("show", True) is not False and se["name"] not in namen \
                and any(v is not None for v in _werte(se)):            # leere Reihen nicht in die Legende
            namen.append(se["name"])
    # EINE Legende, oben, anklickbar
    o["legend"] = {"show": legende and len(namen) > 1, "type": "scroll", "top": 2, "left": 4, "right": 4, "data": namen,
                   "textStyle": {"color": t.get("text2", "#555"), "fontSize": 12}, "itemWidth": 18, "itemHeight": 8,
                   "selectedMode": True}
    g = o.get("grid") if isinstance(o.get("grid"), dict) else {}
    hat_end = any((se.get("endLabel") or {}).get("show") for se in o.get("series") or [])
    o["grid"] = {**g, "top": 40 if o["legend"]["show"] else 22, "left": g.get("left", 52), "bottom": g.get("bottom", 30),
                 "right": max(g.get("right", 20) if isinstance(g.get("right"), (int, float)) else 20, 120 if hat_end else 24)}
    # Tooltip: alle Werte mit einer Nachkommastelle, Differenz zum Vorjahr – vorhandene eigene Tooltips bleiben
    tt = dict(o.get("tooltip") or {})
    tt["trigger"] = "axis"
    tt["confine"] = True
    if ":formatter" not in tt and "formatter" not in tt:
        tt[":formatter"] = tooltip_js(rollen, spanne)
    o["tooltip"] = tt
    # Datenstand (senkrechte Linie) und hinterlegter Prognosebereich auf einer eigenen, unsichtbaren Reihe – an ihr
    # setzt auch „Auf einen Blick“ den hervorgehobenen Punkt (markPoint)
    fokus = {"id": FOKUS_ID, "name": "", "type": "line", "data": [], "symbol": "none", "silent": True, "smooth": False,
             "tooltip": {"show": False}, "z": 9}
    if stand is not None:
        fokus["markLine"] = {"silent": True, "symbol": "none", "lineStyle": {"color": grau2, "type": [3, 3], "width": 1.2},
                             "label": {"formatter": "Datenstand", "position": "end", "fontSize": 12,
                                       "color": grau2}, "data": [{"xAxis": stand}]}
    if prognose_ab is not None:
        xs = _liste(o.get("xAxis"))[0].get("data") if _liste(o.get("xAxis")) else None
        ende = xs[-1] if xs else None
        if ende is not None:
            fokus["markArea"] = {"silent": True, "itemStyle": {"color": akzent, "opacity": .05},
                                 "label": {"show": True, "position": "insideTopRight", "formatter": "Prognose",
                                           "fontSize": 12, "color": grau},
                                 "data": [[{"xAxis": prognose_ab}, {"xAxis": ende}]]}
    o["series"] = [se for se in (o.get("series") or []) if se.get("id") != FOKUS_ID] + [fokus]
    return o


def json_str(s: str) -> str:
    import json

    return json.dumps(s, ensure_ascii=False)


def kurzname(n: str) -> str:
    """Name am Linienende kurz halten: „Aktuell (Prognose)“ → „Prognose“, „Vorjahr (Ist)“ → „Vorjahr“."""
    for alt, neu in (("Aktuell (Ist)", "Aktuell"), ("Aktuell (Prognose)", "Prognose"), ("Prognose (erwartet)", "Prognose"),
                     ("Vorvorjahr (Ist)", "Vorvorjahr"), ("Vorjahr (Ist)", "Vorjahr")):
        if n == alt:
            return neu
    return n


def tooltip_js(rollen: dict, spanne: dict | None = None) -> str:
    import json

    return ("(ps) => { if (!ps || !ps.length) return ''; const R = " + json.dumps(rollen, ensure_ascii=False) + ";"
            " const S = " + json.dumps({str(k): v for k, v in (spanne or {}).items()}) + ";"
            " const f1 = v => (v == null || isNaN(v)) ? '–' : Number(v).toLocaleString('de-DE', {minimumFractionDigits: 1,"
            " maximumFractionDigits: 1});"
            " const wert = p => Array.isArray(p.value) ? p.value[p.value.length - 1] : (p.value && typeof p.value === 'object'"
            " ? p.value.value : p.value);"
            " const zl = (m, n, v) => `<div style=\"display:flex;justify-content:space-between;gap:18px;line-height:1.6\">"
            "<span>${m}${n}</span><b style=\"font-variant-numeric:tabular-nums\">${v}</b></div>`;"
            " let h = `<div style=\"font-weight:600;margin-bottom:4px\">${ps[0].axisValueLabel}</div>`; let akt = null, vj = null, summe = 0, stapel = 0;"
            " const gesehen = {};"
            " for (const p of ps) { const n = p.seriesName; const r = R[n]; if (!n || n[0] === '_' || r === 'band' || r === 'band95'"
            " || gesehen[n]) continue; const v = wert(p); if (v == null || v === '-') continue; gesehen[n] = 1;"
            " h += zl(p.marker, n, f1(v)); if ((r === 'ist' || r === 'prognose' || r === 'balken_ist' || r === 'balken_prognose')"
            " && akt == null) akt = v; if (r === 'vorjahr') vj = v; if (r === 'stapel') { summe += Number(v) || 0; stapel++; } }"
            " if (stapel > 1) h += zl('', 'Zusammen', f1(summe));"
            " const s = S[ps[0].dataIndex]; if (s) h += zl('', '80-%-Spanne', f1(s[0]) + ' – ' + f1(s[1]));"
            " if (akt != null && vj != null) { const d = akt - vj; h += `<div style=\"opacity:.75;margin-top:2px\">Differenz zum"
            " Vorjahr: ${d >= 0 ? '+' : '−'}${f1(Math.abs(d))}</div>`; }"
            " return h; }")
