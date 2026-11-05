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
