"""1.29: Belegungsprognose – Diagramm-Bausteine: ECharts-Optionen (Trend, Status, Vorjahr, Reserve, Vergleich, Leitung),
Kartenstil, Lesehilfe, Rechenweg je Monat und die Einfach-Ansicht.

Aus seite_prognose.py ausgelagert (nur verschoben, keine Funktionsänderung); dort weiter erreichbar."""

from __future__ import annotations

import json
from nicegui import ui
from belegung import konfig
from . import analytik_kern as an
from . import auswertung_kern as ak
from . import diagramm_stil as _ds
from . import themes
from .ui_bausteine import knopf


BACKTEST_FARBE = {True: "#B35C00", False: "#FFB347"}        # 0.97: Bernstein – hell / dunkel, je ≥ 3:1
VORJAHR_FARBE = {True: "#7B3FB5", False: "#C39BFF"}
BACKTEST_EINFACH = "so lag die Vorhersage 1 Monat vorher"


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
            "tooltip": {"trigger": "axis", "confine": True, "transitionDuration": 0.2, "backgroundColor": _rgba(t.get("fls", "#15171C"), .86), "borderColor": t["rand2"],
                        "borderWidth": 1, "padding": [10, 12], "textStyle": {"color": t["text"], "fontSize": 12},
                        "axisPointer": {"type": "line", "lineStyle": {"color": t["text3"], "type": "dashed"}},
                        "extraCssText": "backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-radius: 10px; "
                                        "box-shadow: 0 10px 28px rgba(0,0,0,.22); min-width: 240px;"},
            "legend": {"type": "scroll", "textStyle": {"color": t["text2"], "fontSize": 11}, "top": 26, "left": 8, "right": 8,
                       "itemWidth": 18, "itemHeight": 8, "pageIconColor": t["text2"], "pageTextStyle": {"color": t["text3"]}},
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
    """0.66: Diagrammstil aus den Optionen (Linie/Fläche/Säulen, Gitter, Legende …) auf die Prognose anwenden."""
    from . import diagramm_stil

    o = diagramm_stil.anwenden(_option_roh(c), themes.AKTIV)
    return _karten_stil(o, c) if c.get("karte") else o


def _karten_stil(o: dict, c: dict) -> dict:
    """0.87: In der Diagramm-Karte gilt der einheitliche Stil (Farben, Beschriftung, eine Legende oben, Endbeschriftung).
    Im Vorjahresvergleich kommen Datenstand-Linie und Prognosebereich dazu; Trend und Reserve haben eigene Marker."""
    from . import diagramm_stil

    stand = prog_ab = None
    if c["art"] == "trend" and c.get("status") and c.get("sm"):
        return o                                           # eigene Gestaltung (zwei Flächen), schon einheitlich
    if c["art"] == "jahr" and c.get("vj_tage") is not None and c["vj_tage"].tage:
        labels, si = jahr_achse(c["vj_tage"])
        if si is not None and si + 1 < len(labels):
            stand, prog_ab = labels[si], labels[si + 1]
        o = diagramm_stil.einheitlich(o, _t(), stand, prog_ab)
        for se in o["series"]:
            if se.get("type") == "line":
                se["connectNulls"] = True
                if se.get("name") != "Aktuell (Prognose)":      # Linien enden vor dem Rand – sonst NaN-Position
                    se.pop("endLabel", None)
                else:                                          # Tageswerte: keine Punkte und Zahlen an jedem Tag
                    se["showSymbol"] = False
                    se["label"] = {**(se.get("label") or {}), "show": False}
                if se.get("name") == "_tag":
                    se.update({"symbol": "none", "showSymbol": False, "lineStyle": {"opacity": 0}, "label": {"show": False},
                               "endLabel": {"show": False}})
        return o
    if c["art"] == "jahr":
        vj = an.vorjahr(c.get("pg_lang") or c["pg"])
        labels = [f"{ak.MONATE[m.month - 1]} {str(m.year)[2:]}" for m in vj.monate]
        ist = [i for i, x in enumerate(vj.aktuell_ist) if x]
        if ist and ist[-1] + 1 < len(labels):
            stand, prog_ab = labels[ist[-1]], labels[ist[-1] + 1]
    o = diagramm_stil.einheitlich(o, _t(), stand, prog_ab)
    if c["art"] == "trend" and not c.get("parallel"):    # 12 Monate zurück + 12 voraus, mehr über den Schieber
        xs = o["xAxis"]["data"] if isinstance(o.get("xAxis"), dict) else []
        li = max((i for i, z in enumerate(ak.szenario(c["pg"], c["pg"].kapazitaet or 0, 0)) if z.art == "ist"), default=None)
        o["dataZoom"] = zoom(xs, li)
        o["dataZoom"][0]["filterMode"] = "none" if o["dataZoom"] else None   # gestapelte Bänder nicht zerschneiden
        o["grid"]["bottom"] = 58
        for se in o["series"]:
            if se.get("type") == "line" and len(se.get("data") or []) > 24:
                se["showSymbol"] = False
        o = _lesbar(o, c)
    return o


BAND80, BAND95 = "sehr wahrscheinlich (8 von 10)", "fast sicher (19 von 20)"


def _fragen(pg, kap: int) -> None:
    from . import blick_kern as bk

    zs = ak.szenario(pg, kap, 0)
    fr = bk.prognose_fragen([z.monat for z in zs], [z.ist if z.art == "ist" and z.ist is not None else z.erwartet for z in zs],
                            [z.art == "ist" for z in zs], kap or None, [z.hi80 for z in zs], pg.mae_1m, pg.abdeckung80)
    if not fr:
        return
    with ui.element("div").classes("m-bp-kacheln").style("margin-bottom:12px"):
        for f in fr:
            with ui.element("div").classes("m-bp-kachel"):
                ui.label(f.frage).classes("m-zweite")
                with ui.element("div").classes("m-bp-antwort"):
                    ui.icon(f.symbol)
                    ui.label(f.antwort)
                ui.label(f.zeile).classes("m-zweite")


def _lesehilfe() -> None:
    with ui.element("div").classes("m-bp-lesehilfe").style("margin:8px 2px 4px"):
        for text in ("Gestrichelte Linie: so wird es voraussichtlich – links davon durchgezogen: so war es.",
                     "Dunkles Band: sehr wahrscheinlich – in 8 von 10 Fällen liegt der Wert darin.",
                     "Helles Band: fast sicher – in 19 von 20 Fällen.",
                     "Das Band wird breiter: je weiter in der Zukunft, desto unsicerer."):
            ui.label(text).classes("m-zweite")


def _lesbar(o: dict, c: dict) -> dict:
    """0.95 (Auftrag „Diagramme für Laien“): Achse ab 0 bis „Voll“, gelbe Warnzone ab 85 %, zwei klar unterscheidbare
    Bänder, Ist dunkel durchgezogen, Prognose gestrichelt in Akzentfarbe, Vorjahr dünn grau, höchstens vier
    Beschriftungen, „rund N Plätze Luft“, Zahlen des letzten Monats am rechten Rand, ab Monat 13 nur grau gepunktet."""
    from . import blick_kern as bk

    t = _t()
    pg = c["pg"]
    kap = pg.kapazitaet or 0
    zs = ak.szenario(pg, kap, 0)
    labels = list(o["xAxis"]["data"])
    if len(labels) != len(zs):
        return o
    if not c.get("backtest"):                         # 0.97: eingeschaltet bleibt der Backtest auch in der Karte
        o["series"] = [se for se in o["series"] if se.get("name") != "Backtest (1 Monat vorher)"]
    nach = {se.get("name"): se for se in o["series"]}
    li = max((i for i, z in enumerate(zs) if z.art == "ist"), default=None)
    prog = [i for i, z in enumerate(zs) if z.art != "ist"]
    ende = min(prog[-1], (li if li is not None else -1) + 12) if prog else None     # letzter geprüfter Monat
    for alt, neu, r_ in (("80 %-Band", BAND80, "band"), ("95 %-Band", BAND95, "band95")):
        se = nach.get(alt)
        if se is not None:
            se["name"] = neu
            _ds.band_reihe(se, t, r_)
    ist_se, prog_se = nach.get("Ist"), nach.get("Prognose (erwartet)")
    if ist_se is not None:
        ist_se.update({"color": t["text"], "symbol": "none", "showSymbol": False,
                       "lineStyle": {"color": t["text"], "width": 3, "type": "solid"}, "itemStyle": {"color": t["text"]},
                       "label": {"show": False}, "endLabel": {"show": False}})
    if prog_se is not None and ende is not None:
        daten = list(prog_se["data"])
        fort = [w if i >= ende else None for i, w in enumerate(daten)]
        prog_se["data"] = [w if i <= ende else None for i, w in enumerate(daten)]
        prog_se.update({"symbol": "none", "showSymbol": False, "label": {"show": False},
                        "lineStyle": {"color": t["akzent"], "width": 3, "type": "dashed"}})
        z = zs[ende]
        prog_se["endLabel"] = {"show": True, "fontSize": 13, "color": t["text"], "lineHeight": 18, "distance": 10,
                               "formatter": f"{labels[ende]}\nerwartet {bk.zahl(z.erwartet)}\nsehr wahrscheinlich "
                                            f"{bk.zahl(z.lo80)}–{bk.zahl(z.hi80)}\nfast sicher {bk.zahl(z.lo95)}–{bk.zahl(z.hi95)}"}
        if any(w is not None for w in fort[ende + 1:]):
            o["series"].append({"name": "Fortschreibung, nicht geprüft", "type": "line", "data": fort, "symbol": "none",
                                "lineStyle": {"color": t["text3"], "width": 2, "type": "dotted"}, "color": t["text3"]})
        # höchstens vier Beschriftungen: heute, höchster und tiefster erwarteter Monat (ohne laufenden Monat)
        kommend = [i for i in prog if zs[i].art == "prognose" and i <= ende]
        marken = []
        if li is not None and zs[li].ist is not None:
            marken.append((li, zs[li].ist, f"heute {bk.zahl(zs[li].ist)}", "top"))
        if kommend:
            hoch = max(kommend, key=lambda i: zs[i].erwartet)
            tief = min(kommend, key=lambda i: zs[i].erwartet)
            marken.append((hoch, zs[hoch].erwartet, f"höchstens erwartet {bk.zahl(zs[hoch].erwartet)}", "top"))
            if tief != hoch:
                marken.append((tief, zs[tief].erwartet, f"Tiefpunkt {labels[tief]}: {bk.zahl(zs[tief].erwartet)}", "bottom"))
        prog_se["markPoint"] = {"silent": True, "symbol": "circle", "symbolSize": 8, "data": [
            {"coord": [labels[i], round(w, 1)], "itemStyle": {"color": t["akzent"]},
             "label": {"show": True, "formatter": text, "position": pos, "fontSize": 13, "fontWeight": 600,
                       "color": t["text"], "distance": 10}} for i, w, text, pos in marken]}
        # „rund N Plätze Luft“ bis zur Warnschwelle
        if kap and kommend:
            warn = .85 * kap
            hoch_o = max(kommend, key=lambda i: zs[i].hi80)
            luft = warn - zs[hoch_o].hi80
            if luft > 0:
                x = labels[hoch_o]
                prog_se["markLine"] = {"silent": True, "symbol": ["none", "arrow"], "symbolSize": 9,
                                       "lineStyle": {"color": t["gruen"], "width": 1.6, "type": "solid"},
                                       "label": {"show": True, "formatter": f"rund {bk.zahl(round(luft / 10) * 10 or luft)} "
                                                                            "Plätze Luft bis zur Warnschwelle",
                                                 "position": "end", "fontSize": 13, "color": t["text"], "distance": 6},
                                       "data": [[{"coord": [x, round(zs[hoch_o].hi80, 1)]}, {"coord": [x, round(warn, 1)]}]]}
    # gleicher Monat im Vorjahr (dünn, grau) – macht das Sommertief als Muster sichtbar
    vj = [round(zs[i - 12].ist, 1) if i in prog and i >= 12 and zs[i - 12].ist is not None and (ende is None or i <= ende)
          else None for i in range(len(zs))]
    if any(v is not None for v in vj):
        o["series"].append({"name": "gleicher Monat im Vorjahr", "type": "line", "data": vj, "symbol": "none",
                            "lineStyle": {"color": t["text3"], "width": 1.4}, "color": t["text3"], "z": 3})
    # Kapazität = „Voll“, Warnzone ab 85 %
    kse = nach.get("Kapazität")
    if kse is not None and kap:
        kse.update({"lineStyle": {"color": t["text"], "width": 2.5, "type": "solid"}, "color": t["text"],
                    "endLabel": {"show": True, "formatter": f"Voll: {bk.zahl(kap)} Plätze", "fontSize": 13,
                                 "fontWeight": 600, "color": t["text"], "distance": 8}})
        kse["markArea"] = {"silent": True, "itemStyle": {"color": "rgba(245,180,0,0.16)"},
                           "label": {"show": True, "position": "insideTopLeft", "color": t["text"], "fontSize": 13,
                                     "formatter": f"ab {bk.zahl(.85 * kap)} wird es eng"},
                           "data": [[{"yAxis": round(.85 * kap, 1)}, {"yAxis": kap}]]}
    o["yAxis"]["min"] = 0
    werte = [kap] + [z.hi95 for z in zs if z.art != "ist"] + [z.ist for z in zs if z.ist is not None]
    o["yAxis"]["max"] = int(max(werte) * 1.06) + 1
    o["grid"]["right"] = max(o["grid"].get("right", 0) if isinstance(o["grid"].get("right"), (int, float)) else 0, 190)
    o["legend"]["data"] = [n for n in ("Ist", "Prognose (erwartet)", BAND80, BAND95, "gleicher Monat im Vorjahr",
                                       "Fortschreibung, nicht geprüft") if any(se.get("name") == n for se in o["series"])]
    o["tooltip"]["confine"] = True
    o["tooltip"][":position"] = ("(p, params, dom, rect, size) => [Math.min(p[0] + 24, size.viewSize[0] - "
                                 "size.contentSize[0] - 8), 8]")
    return o


def _einfach(a, pg, kap: int, ort: str, neu_zeichnen) -> None:
    """0.91 (Entwurf Seite 4): „Einfach“ für die Geschäftsführung – die Aussage als Überschrift, ein Satz darunter, das
    Diagramm ab 0 mit „voll“ und Warnzone, wenige Beschriftungen, vier Zahlen, ein Hinweis zur Sicht. „Details anzeigen“
    öffnet darunter die Diagramm-Karte."""
    from . import blick_kern as bk

    # 1.58: Die Leitungsansicht zählt standardmäßig ALLE Bewohner (Teilnehmende, UWT, Mieter) – sonst lag „heute“ um
    # die UWT und Mieter zu niedrig (z. B. 208 statt 253). „Nur Teilnehmende“ bleibt als Schalter.
    nur_tn = not alle_bewohner(a)              # a.daten enthält bereits die passende Sicht (seite_prognose.daten)
    zs = ak.szenario(pg, kap, 0)
    monate_ = [z.monat for z in zs]
    ist = [z.art == "ist" for z in zs]
    werte = [z.ist if z.art == "ist" and z.ist is not None else z.erwartet for z in zs]
    lo, hi = [z.lo80 for z in zs], [z.hi80 for z in zs]
    g = bk.gf(monate_, werte, ist, a.daten["stichtag"], kap or None, lo, hi, None, pg.mae_1m)
    heute = heute_belegt(a, nur_tn)                       # 1.58: „Heute belegt“ = heutiger Stand, nicht der Vormonat
    if heute is not None and g.zahlen and g.zahlen[0].titel == "Heute belegt":
        g.zahlen[0] = bk.GfZahl("Heute belegt", bk.zahl(heute), f"· {round(100 * heute / kap)} %" if kap else "Plätze",
                                f"Stand {a.daten['stichtag']:%d.%m.%Y}" + (" · mit UWT und Mietern" if not nur_tn
                                                                            and a.daten.get("gruppen_da") else ""))
    with ui.element("section").classes("m-gf"):
        ui.label(g.titel).classes("m-gf-titel")
        if g.untertitel:
            ui.label(g.untertitel).classes("m-gf-unter")
        blind = None
        if getattr(a, "aw_backtest", False) and pg.rueckblick:      # 0.97: Backtest auch in „Einfach“
            zusatz = {z.monat: z.vertraege for z in pg.zeilen}
            blind = {mon: p_ + zusatz.get(mon, 0.0) for mon, _i, p_ in pg.rueckblick}
        with ui.element("div").classes("m-gf-reihe"):
            ui.echart(_gf_option(zs, werte, ist, g, kap, a.daten["stichtag"], blind, bool(getattr(a, "gf_95", False))),
                      renderer="svg").classes("m-gf-chart")
            ab = gf_ausblick(zs, ist, a.daten["stichtag"])
            if ab:                                         # 1.58: rechts neben dem letzten Monat
                f_ = _ds.prognose_farben(not _ds.dunkel(themes.farben(themes.AKTIV)))
                with ui.element("div").classes("m-gf-ausblick"):
                    ui.label(f"In einem Jahr ({ab['monat']})").classes("m-zweite")
                    ui.html(f'<div class="m-gf-ab"><i style="background:{f_["prognose"]};height:3px"></i>erwartet '
                            f'<b>{ab["erwartet"]}</b></div>'
                            f'<div class="m-gf-ab"><i style="background:{f_["band80"]}"></i>sehr wahrscheinlich '
                            f'<b>{ab["b80"]}</b></div>'
                            + (f'<div class="m-gf-ab"><i style="background:{f_["band95"]}"></i>fast sicher '
                               f'<b>{ab["b95"]}</b></div>' if ab["b95"] and getattr(a, "gf_95", False) else ""),
                            sanitize=False)
        with ui.element("div").classes("m-zeile-flex"):
            ui.label("Das Band wird breiter: je weiter in der Zukunft, desto unsicherer. · Durchschnittlich belegte "
                     "Plätze je Monat · Achse ab 0, damit der Füllstand stimmt").classes("m-gf-fuss")
            gf95 = bool(getattr(a, "gf_95", False))
            knopf("„fast sicher“ ausblenden" if gf95 else "auch „fast sicher“ (19 von 20) zeigen",
                  lambda: (setattr(a, "gf_95", not gf95), neu_zeichnen(False)), "leise")
    with ui.element("div").classes("m-gf-zahlen"):
        for z in g.zahlen:
            with ui.element("div").classes("m-gf-zahl"):
                ui.label(z.titel).classes("m-zweite")
                with ui.element("div").classes("m-gf-wertzeile"):
                    ui.label(z.wert).classes("m-gf-wert")
                    ui.label(z.einheit).classes("m-gf-einheit")
                ui.label(z.zusatz).classes("m-zweite")
    if a.daten.get("gruppen_da"):
        with ui.element("div").classes("m-gf-hinweis"):
            ui.icon("info_outline")
            ui.label("Gezählt werden nur Teilnehmende – Umschüler und Mieter belegen zusätzlich Zimmer." if nur_tn else
                     "Gezählt werden alle Bewohner: Teilnehmende, Umschüler (UWT) und Mieter – wie in der Belegung.")
            knopf("Alle Bewohner zählen" if nur_tn else "Nur Teilnehmende zählen",
                  lambda: a.setzen(aw_nur_tn=not nur_tn, nur_seite=True), "")
    with ui.element("div").classes("m-zeile-flex").style("margin-top:6px"):
        knopf("Details ausblenden" if a.dg_details else "Details anzeigen (Diagramm-Karte, Rechenweg)",
              lambda: (setattr(a, "dg_details", not a.dg_details), neu_zeichnen(False)), "leise",
              "expand_less" if a.dg_details else "expand_more")


GF_LEGENDE = {"ist": "Ist", "prognose": "Prognose", "band80": "sehr wahrscheinlich: in 8 von 10 Fällen",
              "band95": "fast sicher: in 19 von 20 Fällen", "vorjahr": "gleicher Monat im Vorjahr", "eng": "Eng-Zone"}
# Legendensymbol = Form im Diagramm: Linie, gestrichelte Linie, Feld, gepunktete Linie
_ICON = {"linie": "path://M0,4h26v3H0z", "strich": "path://M0,4h7v3H0zM10,4h7v3h-7zM20,4h6v3h-6z",
         "punkt": "path://M0,4h2v2H0zM6,4h2v2H6zM12,4h2v2h-2zM18,4h2v2h-2zM24,4h2v2h-2z", "feld": "rect"}


def gf_fenster(zs, ist: list[bool], stichtag, zurueck: int = 12, vor: int = 12) -> tuple[int, int, int]:
    """(Anfang, Heute-Index, Ende exkl.): 12 Monate zurück, 12 voraus. „Heute“ = der laufende Monat (enthält den
    Stichtag) – dort treffen sich Ist und Prognose; ohne ihn der letzte Ist-Monat."""
    h = next((i for i, z in enumerate(zs) if z.monat.year == stichtag.year and z.monat.month == stichtag.month), None)
    if h is None:
        h = max((i for i, x in enumerate(ist) if x), default=0)
    return max(0, h - zurueck), h, min(len(zs), h + vor + 1)


def alle_bewohner(a) -> bool:
    """1.58: Zählt die Belegungsprognose alle Bewohner (mit UWT und Mietern)? Standard ja – „nur Teilnehmende“ ist ein
    Schalter; die Ansicht „Nach Status“ zeigt die Gruppen ohnehin."""
    return bool(getattr(a, "aw_status", False)) or not bool(getattr(a, "aw_nur_tn", False))


def heute_belegt(a, nur_tn: bool) -> float | None:
    """1.58: Heute belegte Plätze laut Datenstand (Stichtag). Die Gesamtbelegung enthält UWT und Mieter aus den Listen;
    die Gruppen-Aufteilung ergänzt Mietverträge (alle Bewohner) bzw. zieht UWT und Mieter ab (nur Teilnehmende)."""
    try:
        ds = a.daten["ds"]
        wert = float(ds.aufschluesselung(a.aw_standort, ds.stichtag, a.aw_brutto).belegt)
        if a.daten.get("gruppen_da"):
            andere = a.daten.get("alt") or a.daten
            mit, ohne = (a.daten, andere) if alle_bewohner(a) else (andere, a.daten)
            g = (ohne if nur_tn else mit).get("gruppen")
            if g is not None:
                wert += (g.tag(ds.stichtag) or {}).get("delta", 0.0)
        return wert
    except Exception:                                  # noqa: BLE001 – dann die Monatszahl wie bisher
        return None


def _gf_option(zs, werte, ist, g, kap, stichtag, blind: dict | None = None, b95: bool = False,
               hell: bool | None = None) -> dict:
    """1.58: Belegungsprognose für Laien – feste Farben (``DIAGRAMM_FARBEN``, nie aus dem Farbschema), jede Farbe genau
    eine Bedeutung; 80-%-Band als Fläche (95 % auf Wunsch), Vorjahr gepunktet, Eng-Zone mit Kanten, höchstens fünf
    Beschriftungen in ganzen Zahlen; 12 Monate zurück, 12 voraus; Heute-Linie mit „so war es“ / „so wird es
    voraussichtlich“; der laufende Monat einmal als hohler Punkt, dort treffen sich Ist und Prognose."""
    from . import blick_kern as bk

    if hell is None:
        hell = not _ds.dunkel(themes.farben(themes.AKTIV))
    f = _ds.prognose_farben(hell)
    an_, h, en = gf_fenster(zs, ist, stichtag)
    alle = {z.monat: w for z, w in zip(zs, werte)}             # auch vor dem Fenster – für „Vorjahr“
    zs, werte, ist = zs[an_:en], werte[an_:en], ist[an_:en]
    h -= an_
    marken_g = [(m.index - an_, m) for m in g.marken if an_ <= m.index < en]
    labels = [f"{bk.MONATE_KURZ[z.monat.month - 1]} {z.monat.year}" for z in zs]
    r1 = lambda x: None if x is None else round(float(x), 1)          # noqa: E731 – Tooltip: eine Nachkommastelle
    ist_r = [r1(w) if (ist[i] or i == h) else None for i, w in enumerate(werte)]
    prog_r = [r1(w) if i >= h else None for i, w in enumerate(werte)]
    kuenftig = lambda i, z: i > h or (i == h and not ist[i])          # noqa: E731
    lo = [r1(z.lo80) if kuenftig(i, z) and z.lo80 is not None else None for i, z in enumerate(zs)]
    br = [r1(z.hi80 - z.lo80) if kuenftig(i, z) and z.lo80 is not None and z.hi80 is not None else None
          for i, z in enumerate(zs)]
    lo95 = [r1(z.lo95) if b95 and kuenftig(i, z) and z.lo95 is not None else None for i, z in enumerate(zs)]
    br95 = [r1(z.hi95 - z.lo95) if b95 and kuenftig(i, z) and z.lo95 is not None and z.hi95 is not None else None
            for i, z in enumerate(zs)]
    # Vorjahr: gleicher Monat ein Jahr vorher – nur im Prognoseteil (dort ist er der Vergleich)
    vj = [r1(alle.get(z.monat.replace(year=z.monat.year - 1))) if i >= h else None for i, z in enumerate(zs)]
    oben = max([kap or 0] + [(z.hi95 if b95 and z.hi95 is not None else z.hi80) or 0 for z in zs]
               + [w for w in werte if w is not None])
    ymax, schritt = _ds.runde_achse(oben)
    schrift = {"color": f["text"], "fontSize": 13}
    kasten = {"backgroundColor": f["grund"], "padding": [2, 4], "borderRadius": 3}
    # ---- Linien und Flächen im Hintergrund: Kapazität, Eng-Zone, Heute
    linien, flaechen = [], []
    if kap:
        linien.append({"yAxis": kap, "lineStyle": {"color": f["kapazitaet"], "type": "solid", "width": 2.5},
                       "label": {"formatter": f"voll: {bk.zahl(kap)} Plätze", "position": "end", **schrift,
                                 "color": f["kapazitaet"], "fontWeight": 700}})
    if g.warn is not None and kap:
        linien.append({"yAxis": round(g.warn), "lineStyle": {"color": f["eng"], "type": "dashed", "width": 1.5},
                       "label": {"formatter": f"eng ab {bk.zahl(g.warn)}", "position": "end", **schrift,
                                 "color": f["kapazitaet"], "fontWeight": 600}})
        flaechen.append([{"yAxis": round(g.warn), "itemStyle": {"color": f["eng_flaeche"]}}, {"yAxis": kap}])
    linien.append({"xAxis": labels[h], "lineStyle": {"color": f["heute"], "type": "solid", "width": 1.5},
                   "label": {"show": False}})
    if h > 0:                                      # Lesehilfe über dem Diagramm: links Vergangenheit, rechts Zukunft
        flaechen.append([{"xAxis": labels[0], "itemStyle": {"color": "transparent"},
                          "label": {"show": True, "position": "insideTopRight", "formatter": "so war es ◂",
                                    **schrift, "color": f["achse"]}}, {"xAxis": labels[h]}])
    if h < len(labels) - 1:
        flaechen.append([{"xAxis": labels[h], "itemStyle": {"color": "transparent"},
                          "label": {"show": True, "position": "insideTopLeft", "formatter": "▸ so wird es voraussichtlich",
                                    **schrift, "color": f["achse"]}}, {"xAxis": labels[-1]}])
    # ---- höchstens fünf Beschriftungen: heute, höchster, tiefster, letzter Prognosemonat (+ „Vorjahr“ am Linienende)
    lage = ["top", "bottom", "top"]
    laufend = getattr(zs[h], "art", "") == "laufend"
    marken = [{"coord": [labels[h], r1(werte[h])], "value": f"{labels[h]}: {bk.zahl(werte[h])}" +
               ("\nnoch nicht abgeschlossen" if laufend else ""),
               "symbol": "circle", "symbolSize": 11,
               "itemStyle": {"color": f["grund"], "borderColor": f["ist"], "borderWidth": 2.5},
               "label": {"show": True, "position": "left", "distance": 10, "formatter": "{c}", **schrift, **kasten,
                         "fontWeight": 600, "align": "right"}}]
    for j, (i, m) in enumerate(marken_g[:3]):
        if i == h:
            continue
        marken.append({"coord": [labels[i], r1(m.wert)], "value": m.text + (f"\n{m.unter}" if m.unter else ""),
                       "symbol": "circle", "symbolSize": 7, "itemStyle": {"color": f["prognose"]},
                       "label": {"show": True, "position": lage[j] if i < len(labels) - 1 else "bottom", "distance": 10,
                                 "formatter": "{c}", **schrift, **kasten, "fontWeight": 600, "lineHeight": 17}})
    # „Vorjahr“ einmal an der Vorjahreslinie – an ihrem tiefsten Punkt, darunter (stört dort keine andere Beschriftung)
    belegt_ = {h} | {i for i, _m in marken_g}
    vj_i = [i for i, v in enumerate(vj) if v is not None and all(abs(i - j) > 1 for j in belegt_)]
    vj_marke = []
    if vj_i:                                   # dort, wo die Vorjahreslinie am deutlichsten von der Prognose abweicht
        k_ = max(vj_i, key=lambda i: abs(vj[i] - (prog_r[i] if prog_r[i] is not None else vj[i])))
        vj_marke = [{"coord": [labels[k_], vj[k_]], "value": "Vorjahr", "symbol": "none",
                     "label": {"show": True, "position": "bottom" if prog_r[k_] is None or vj[k_] <= prog_r[k_] else "top",
                               "distance": 8, "formatter": "{c}", **schrift, "color": f["vorjahr"]}}]
    reihen = []
    if b95:
        reihen += [{"name": "_u95", "type": "line", "data": lo95, "stack": "b95", "symbol": "none", "silent": True,
                    "lineStyle": {"width": 0}, "tooltip": {"show": False}, "z": 1},
                   {"name": GF_LEGENDE["band95"], "type": "line", "data": br95, "stack": "b95", "symbol": "none",
                    "silent": True, "lineStyle": {"width": 0}, "areaStyle": {"color": f["band95"], "opacity": 1},
                    "itemStyle": {"color": f["band95"]}, "z": 1}]
    reihen += [
        {"name": "_u80", "type": "line", "data": lo, "stack": "b80", "symbol": "none", "silent": True,
         "lineStyle": {"width": 0}, "tooltip": {"show": False}, "z": 2},
        {"name": GF_LEGENDE["band80"], "type": "line", "data": br, "stack": "b80", "symbol": "none", "silent": True,
         "lineStyle": {"width": 0}, "areaStyle": {"color": f["band80"], "opacity": 1}, "itemStyle": {"color": f["band80"]},
         "z": 2},
        {"name": GF_LEGENDE["vorjahr"], "type": "line", "data": vj, "symbol": "none", "z": 3,
         "lineStyle": {"color": f["vorjahr"], "width": 1.5, "type": "dotted"}, "itemStyle": {"color": f["vorjahr"]},
         "markPoint": {"silent": True, "data": vj_marke}},
        {"name": GF_LEGENDE["ist"], "type": "line", "data": ist_r, "symbol": "none", "z": 4,
         "lineStyle": {"color": f["ist"], "width": 3}, "itemStyle": {"color": f["ist"]},
         "markLine": {"silent": True, "symbol": "none", "data": linien},
         "markArea": {"silent": True, "data": flaechen}},
        {"name": GF_LEGENDE["prognose"], "type": "line", "data": prog_r, "symbol": "none", "z": 5,
         "lineStyle": {"color": f["prognose"], "width": 3, "type": "dashed"}, "itemStyle": {"color": f["prognose"]},
         "markPoint": {"silent": True, "data": marken}},
    ]
    if g.warn is not None and kap:                 # nur für die Legende (Feld = Fläche der Eng-Zone)
        reihen.append({"name": GF_LEGENDE["eng"], "type": "line", "data": [], "silent": True,
                       "itemStyle": {"color": f["eng_flaeche"], "borderColor": f["eng"], "borderWidth": 1.5}})
    legende = [{"name": GF_LEGENDE["ist"], "icon": _ICON["linie"]}, {"name": GF_LEGENDE["prognose"], "icon": _ICON["strich"]},
               {"name": GF_LEGENDE["band80"], "icon": _ICON["feld"]}]
    if b95:
        legende.append({"name": GF_LEGENDE["band95"], "icon": _ICON["feld"]})
    legende.append({"name": GF_LEGENDE["vorjahr"], "icon": _ICON["punkt"]})
    if g.warn is not None and kap:
        legende.append({"name": GF_LEGENDE["eng"], "icon": _ICON["feld"]})
    if blind:                                          # 0.97: so lag die Vorhersage einen Monat vorher
        bt = BACKTEST_FARBE[hell]
        reihen.append({"name": BACKTEST_EINFACH, "type": "line", "symbol": "diamond", "symbolSize": 8, "z": 6,
                       "data": [r1(blind[z.monat]) if z.monat in blind else None for z in zs],
                       "color": bt, "itemStyle": {"color": bt}, "lineStyle": {"color": bt, "width": 2, "type": [3, 3]}})
        legende.append({"name": BACKTEST_EINFACH, "icon": "diamond"})
    tip = {"labels": labels, "ist": ist_r, "prog": prog_r, "lo": lo, "br": br, "lo95": lo95, "br95": br95, "vj": vj,
           "h": h, "kap": kap or 0}
    formatter = ("(ps) => { const d = " + json.dumps(tip) + "; const i = ps[0].dataIndex; "
                 "const z = v => v == null ? '–' : v.toLocaleString('de-DE', {maximumFractionDigits: 1}); "
                 "let s = '<b>' + d.labels[i] + '</b>' + (i === d.h ? ' · laufender Monat' : '') + '<br>'; "
                 "if (d.ist[i] != null && i < d.h) s += 'Ist: <b>' + z(d.ist[i]) + '</b> Plätze<br>'; "
                 "if (d.prog[i] != null && i >= d.h) s += 'Prognose: <b>' + z(d.prog[i]) + '</b> Plätze<br>'; "
                 "if (d.lo[i] != null) s += 'sehr wahrscheinlich: ' + z(d.lo[i]) + ' – ' + z(d.lo[i] + d.br[i]) + '<br>'; "
                 "if (d.lo95[i] != null) s += 'fast sicher: ' + z(d.lo95[i]) + ' – ' + z(d.lo95[i] + d.br95[i]) + '<br>'; "
                 "if (d.vj[i] != null) s += 'Vorjahr: ' + z(d.vj[i]) + '<br>'; "
                 "if (d.kap) { const w = (i < d.h ? d.ist[i] : d.prog[i]); "
                 "if (w != null) s += 'frei: ' + z(d.kap - w) + ' von ' + z(d.kap); } return s; }")
    return {"m_eigen": True, "animation": False, "backgroundColor": f["grund"],
            "textStyle": {"fontFamily": "Segoe UI, Inter, sans-serif", "fontSize": 13, "color": f["text"]},
            "grid": {"left": 56, "right": 150, "top": 64, "bottom": 40},
            "legend": {"top": 0, "left": 0, "right": 0, "data": legende, "selectedMode": False, "itemWidth": 26,
                       "itemHeight": 12, "itemGap": 18, "textStyle": {"color": f["text"], "fontSize": 13}},
            "tooltip": {"trigger": "axis", "confine": True, ":formatter": formatter, "backgroundColor": f["grund"],
                        "borderColor": f["achse"], "textStyle": {"color": f["text"], "fontSize": 13},
                        "axisPointer": {"type": "line", "lineStyle": {"color": f["achse"], "type": "dashed"}}},
            "xAxis": {"type": "category", "data": labels, "boundaryGap": False,
                      "axisLabel": {"color": f["achse"], "fontSize": 13, "interval": 2},
                      "axisLine": {"lineStyle": {"color": f["achse"]}}, "axisTick": {"show": False}},
            "yAxis": {"type": "value", "min": 0, "max": ymax, "interval": schritt,
                      "axisLabel": {"color": f["achse"], "fontSize": 13, ":formatter": "(v) => v.toLocaleString('de-DE')"},
                      "splitLine": {"lineStyle": {"color": f["gitter"]}}},
            "series": reihen}


def gf_ausblick(zs, ist, stichtag) -> dict | None:
    """Block rechts: „In einem Jahr: erwartet N · sehr wahrscheinlich N–N · fast sicher N–N“ (letzter Monat im Fenster)."""
    _an, _h, en = gf_fenster(zs, ist, stichtag)
    if not zs or en < 1:
        return None
    z = zs[en - 1]
    if z.art == "ist" or z.erwartet is None:
        return None
    from . import blick_kern as bk

    return {"monat": f"{bk.MONATE_LANG[z.monat.month - 1]} {z.monat.year}", "erwartet": bk.zahl(z.erwartet),
            "b80": f"{bk.zahl(z.lo80)}–{bk.zahl(z.hi80)}" if z.lo80 is not None else "",
            "b95": f"{bk.zahl(z.lo95)}–{bk.zahl(z.hi95)}" if z.lo95 is not None and z.hi95 is not None else ""}


def blick_gruppen(sm, pg, kap: int, stichtag, kont: dict | None):
    """0.87: „Auf einen Blick“ für „inkl. UWTler und Mieter“ – Gesamt gegen Kapazität, Kontingente, Vertragsende."""
    from . import blick_kern as bk

    k = pg.kapazitaet or kap or 0
    li = max((i for i, m in enumerate(sm) if m.art == "ist"), default=None)
    gr = [m.uwt + m.mieter for m in sm]
    blick = bk.gruppen([m.monat for m in sm], [m.art == "ist" for m in sm], [m.gesamt for m in sm], [m.uwt for m in sm],
                       [m.mieter for m in sm], stichtag, k or None, k * kont["UWT"] / 100 if kont and k else None,
                       k * (kont["UWT"] + kont["Mieter"]) / 100 if kont and k else None, bk.vertrags_grenze(gr, li),
                       "Alle Bewohner")
    return blick, {i: [ak.monat_text(m.monat)] for i, m in enumerate(sm)}


def blick_daten(pg, pg_lang, kap: int, stichtag):
    """0.87: „Auf einen Blick“ der Belegungsprognose – aus dem Vorjahresvergleich (12 Monate) und den 80-%-Grenzen."""
    from . import blick_kern as bk

    vj = an.vorjahr(pg_lang or pg)
    oben = {z.monat: z.hi80 for z in ak.szenario(pg, kap, 0) if z.art != "ist"}
    blick = bk.monate(vj.monate, vj.aktuell, vj.aktuell_ist, vj.vorjahr, stichtag, kap or None, pg.mae_1m,
                      [oben.get(m) for m in vj.monate])
    alt = {i: [f"{ak.MONATE[m.month - 1]} {str(m.year)[2:]}", ak.monat_text(m), an.tag_text(m.replace(day=15))]
           for i, m in enumerate(vj.monate)}
    return blick, alt


def _option_roh(c: dict) -> dict:
    """c: pg, kap, offset, art, standort, brutto, b95, backtest, schritt, animation, pg_lang, stichtag."""
    t = _t()
    o = _basis(t, c["animation"])
    pg, kap, offset = c["pg"], c["kap"], c["offset"]
    ort = konfig.STANDORT_LABEL.get(c["standort"], c["standort"])
    zaehl = ("Brutto" if c["brutto"] else "Netto") + (f" · {c['gruppen_text']}" if c.get("gruppen_text") else "")
    szen = " · SZENARIO" if (kap != (pg.kapazitaet or 0) or offset) else ""
    if c["art"] == "jahr":
        return _vorjahr(o, t, c, ort, zaehl, szen)
    zs = ak.szenario(pg, kap, offset)
    if c["art"] == "reserve":
        return _reserve(o, t, c, zs, ort, zaehl, szen)
    if c.get("parallel") and c.get("sv"):
        return _parallel(o, t, c, zaehl)
    if c.get("status") and c.get("sm"):
        return _status_karte(o, t, c) if c.get("karte") else _status(o, t, c, zs, ort, zaehl, szen)
    return _trend(o, t, c, zs, ort, zaehl, szen)


def _berechnung_monat(a, pg, kap: int, i: int) -> list:
    """0.75: Berechnung eines Monats für Detailpanel und ƒx – (Schlüssel, Werte, Aktionen) aus dem Kennzahlen-Katalog."""
    zs = ak.szenario(pg, kap, 0)
    if not 0 <= i < len(zs):
        return []
    z, pz = zs[i], pg.zeilen[i]
    zu_zimmern = [("Nicht nutzbare Zimmer ansehen", lambda: a.oeffnen("zimmer", ansicht="uebersicht", zu_tag=a.heute,
                                                                       zu_filter=frozenset({"nicht_nutzbar"})))]
    erg = []
    if z.art == "ist" and z.ist is not None:
        erg.append(("belegung", {}, []))
        if kap:
            erg.append(("auslastung", {"belegung": z.ist, "kapazitaet": kap}, []))
        rueck = {m: (ist, p) for m, ist, p in pg.rueckblick}
        if z.monat in rueck:
            ist, p = rueck[z.monat]
            erg.append(("backtest", {"ist": ist, "vorher": p}, []))
    else:
        erg.append(("prognose", {"erwartet": z.erwartet, "vertraege": pz.vertraege, "gesichert": pz.gesichert},
                    [("Anreisen ansehen", lambda: a.oeffnen("anreisen", ansicht="zuteilen"))]))
        erg.append(("band80", {"lo": z.lo80, "hi": z.hi80}, []))
        if kap:
            erg.append(("auslastung", {"belegung": z.erwartet, "kapazitaet": kap}, []))
            erg.append(("reserve", {"belegung": z.erwartet, "kapazitaet": kap}, []))
    if kap:
        erg.append(("kapazitaet", {}, zu_zimmern))
    if z.art != "ist":                                     # 1.23: genauer Rechenweg mit allen Zwischenwerten
        try:
            from . import rechenweg_kern as rw

            schritte = rw.rechenweg((a.daten or {}).get("ds"), a.aw_standort, z.monat, pz.vertraege,
                                    {"erwartet": z.erwartet, "lo80": z.lo80, "hi80": z.hi80, "lo95": z.lo95, "hi95": z.hi95})
        except Exception:                                  # noqa: BLE001 – der Rechenweg ist Zusatz
            schritte = []
        if schritte:
            erg.append(("rechenweg", {"schritte": schritte, "titel": ak.monat_text(z.monat)}, []))
    return erg


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


def _spotlights(t, zs, labels, kap: int) -> dict:
    """Dezente Badges an den entscheidenden Punkten der nächsten 12 Monate: Höchststand, erster Engpass bzw. Tiefpunkt."""
    kommend = [(i, z) for i, z in [(i, z) for i, z in enumerate(zs) if z.art != "ist"][:12]
               if z.art == "prognose"]                 # 0.95: der laufende Monat ist unvollständig – nie „Höchststand“
    if not kommend:
        return {}
    quote = lambda z: f" · {round(100 * z.erwartet / kap)} %" if kap else ""  # noqa: E731
    punkte = []
    i_max, z_max = max(kommend, key=lambda p: p[1].erwartet)
    punkte.append((i_max, z_max.erwartet, f"Höchststand {labels[i_max]}: {_z(z_max.erwartet)}{quote(z_max)}", t["akzent"], "top"))
    eng = next(((i, z) for i, z in kommend if z.stufe in ("kritisch", "ueber")), None)
    if eng and eng[0] != i_max:
        punkte.append((eng[0], eng[1].erwartet, f"Engpass ab {labels[eng[0]]}{quote(eng[1])}", t["rot"], "top"))
    elif not eng:
        i_min, z_min = min(kommend, key=lambda p: p[1].erwartet)
        if i_min != i_max:
            punkte.append((i_min, z_min.erwartet, f"Tiefpunkt {labels[i_min]}: {_z(z_min.erwartet)}{quote(z_min)}", t["text2"],
                           "bottom"))
    return {"symbol": "circle", "symbolSize": 9, "animationDuration": 450, "animationEasing": "backOut", "silent": True,
            "data": [{"coord": [labels[i], round(w, 1)], "itemStyle": {"color": farbe, "borderColor": t.get("fls", "#111"),
                                                                         "borderWidth": 2},
                      "label": {"show": True, "formatter": text, "position": pos, "distance": 10, "color": t["text"],
                                "fontSize": 11, "fontWeight": 600, "padding": [4, 8], "borderRadius": 9,
                                "backgroundColor": _rgba(t.get("fls", "#15171C"), .92), "borderColor": farbe, "borderWidth": 1}}
                     for i, w, text, farbe, pos in punkte]}


def _parallel(o, t, c, zaehl) -> dict:
    """Gesamt: Auslastung der drei Standorte parallel (Ist durchgezogen, Prognose gestrichelt, Standortfarben)."""
    sv = c["sv"]
    farben = an.STANDORT_FARBEN[bool(t.get("hell"))]
    monate = sorted({m for v in sv for m, _w, _i in v.verlauf})
    labels = [ak.monat_text(m) for m in monate]
    o["xAxis"]["data"] = labels
    o["yAxis"].update({"scale": False, "min": 0, "axisLabel": {"color": t["text3"], "formatter": "{value} %"}})
    _titel(o, t, f"Auslastung je Standort · {zaehl}", "Ø belegte Plätze ÷ Kapazität je Monat · Ist durchgezogen, Prognose "
           "gestrichelt · Linien: knapp 70 %, kritisch 85 %, voll 100 %")
    li = max((i for i, m in enumerate(monate) if any(mm == m and ist for v in sv for mm, _w, ist in v.verlauf)), default=None)
    reihen, tip = [], {}
    for n, v in enumerate(sv):
        if not v.kapazitaet:
            continue
        werte = {m: (100 * w / v.kapazitaet, ist) for m, w, ist in v.verlauf}
        ist_ = [round(werte[m][0], 1) if m in werte and werte[m][1] else None for m in monate]
        prog = [round(werte[m][0], 1) if m in werte and not werte[m][1] else None for m in monate]
        if li is not None and ist_[li] is not None and li + 1 < len(monate):
            prog[li] = ist_[li]
        f = farben[v.standort]
        verz = 250 * n
        reihen.append({"name": v.name, "type": "line", "data": ist_, "symbol": "circle", "symbolSize": 4, "color": f,
                       "lineStyle": {"color": f, "width": 2.4}, "animationDelay": verz, "animationDuration": 1200,
                       "animationEasing": "cubicOut"})
        reihen.append({"name": v.name + " (Prognose)", "type": "line", "data": prog, "symbol": "none", "color": f,
                       "lineStyle": {"color": f, "width": 2.2, "type": [7, 5]}, "animationDelay": 1300 + verz,
                       "animationDuration": 900, "animationEasing": "cubicOut",
                       "endLabel": {"show": True, "formatter": v.name, "color": f, "fontSize": 11, "fontWeight": 600}})
        for i, m in enumerate(monate):
            if m in werte:
                tip.setdefault(i, []).append([v.name, f, round(werte[m][0]), round(werte[m][0] * v.kapazitaet / 100),
                                              v.kapazitaet, werte[m][1]])
    if reihen:
        reihen[0]["markLine"] = {"silent": True, "symbol": "none", "animationDelay": 1200,
                                 "lineStyle": {"color": t["text3"], "type": "dashed", "width": 1},
                                 "label": {"color": t["text3"], "fontSize": 10, "formatter": "{b}", "position": "insideEndTop"},
                                 "data": [{"yAxis": round(100 * konfig.AMPEL_GELB), "name": "knapp"},
                                          {"yAxis": round(100 * konfig.AMPEL_ROT), "name": "kritisch",
                                           "lineStyle": {"color": t["orange"]}},
                                          {"yAxis": 100, "name": "voll", "lineStyle": {"color": t["rot"]}}]
                                 + ([{"xAxis": labels[li + 1], "name": f"Stichtag {c['stichtag']:%d.%m.}",
                                      "lineStyle": {"color": t["text2"], "type": [2, 3]}}] if li is not None and li + 1 < len(labels) else [])}
    o["series"] = reihen
    o["grid"]["right"] = 110
    o["legend"]["data"] = [v.name for v in sv if v.kapazitaet]
    d = [{"m": labels[i], "z": sorted(tip.get(i, []), key=lambda x: -x[2])} for i in range(len(labels))]
    o["tooltip"][":formatter"] = (
        "(ps) => { const D = " + json.dumps(d) + "; const d = D[ps[0].dataIndex]; if (!d) return '';"
        " let h = `<div style=\"font-weight:600;margin-bottom:6px\">${d.m}</div>`;"
        " for (const [n, f, p, w, k, ist] of d.z) h += `<div style=\"display:flex;gap:18px;justify-content:space-between;line-height:1.75\">"
        "<span><span style=\"display:inline-block;width:10px;height:10px;border-radius:3px;background:${f};margin-right:7px\"></span>${n}"
        "<span style=\"opacity:.6\"> · ${ist ? 'Ist' : 'Prognose'}</span></span>"
        "<b style=\"font-variant-numeric:tabular-nums\">${p} % <span style=\"opacity:.6;font-weight:400\">(${w} von ${k})</span></b></div>`;"
        " return h; }")
    return o


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
    fort_ab = (li + 1 if li is not None else 0) + 12      # ab hier nur fortgeschrieben (Backtest prüft 12 Monate)

    def prog(feld):
        w = [None if z.art == "ist" else round(getattr(z, feld), 1) for z in zs]
        if li is not None and zs[li].ist is not None and li + 1 < len(zs):
            w[li] = round(zs[li].ist, 1)          # an die Ist-Linie anschließen
        return w
    def band(feld):          # 0.86: Bänder nur, solange der Backtest prüft (12 Monate) – danach nur der Verlauf
        return [None if i >= fort_ab else w for i, w in enumerate(prog(feld))]
    u80, o80, u95, o95 = band("lo80"), band("hi80"), band("lo95"), band("hi95")
    breite = lambda u, ob: [None if x is None or y is None else round(y - x, 1) for x, y in zip(u, ob)]  # noqa: E731
    b95 = c["b95"] and zeig(3)
    start = c.get("phase") == "start"           # Story-Aufbau, 1. Teil: Bänder noch auf dem Prognosestrich zusammengelegt
    if start:
        e_ = prog("erwartet")
        u80 = u95 = e_
        o80 = o95 = e_
    d = lambda n, s: {"animationDelay": n, "animationDuration": s, "animationEasing": "cubicOut"}  # noqa: E731
    reihen = [
        {"name": "u95", "type": "line", "data": u95 if b95 else leer_, "stack": "b95", "symbol": "none", "lineStyle": {"opacity": 0},
         "tooltip": {"show": False}, "silent": True, **d(1700, 1000)},
        {"name": "95 %-Band", "type": "line", "data": breite(u95, o95) if b95 else leer_, "stack": "b95", "symbol": "none",
         "color": t["text3"], "lineStyle": {"opacity": 0}, "areaStyle": {"color": _rgba(t["akzent"], .07)}, **d(1700, 1000)},
        {"name": "u80", "type": "line", "data": u80 if zeig(3) else leer_, "stack": "b80", "symbol": "none", "lineStyle": {"opacity": 0},
         "tooltip": {"show": False}, "silent": True, **d(1700, 1000)},
        {"name": "80 %-Band", "type": "line", "data": breite(u80, o80) if zeig(3) else leer_, "stack": "b80", "symbol": "none",
         "color": t["akzent"], "lineStyle": {"opacity": 0}, "areaStyle": {"color": _rgba(t["akzent"], .17)}, **d(1700, 1000)},
        {"name": "Ist", "type": "line", "color": t["text"], "symbol": "circle", "symbolSize": 4, "z": 5,
         "data": [round(z.ist, 1) if z.art == "ist" and z.ist is not None else None for z in zs],
         "lineStyle": {"color": t["text"], "width": 2.4}, "itemStyle": {"color": t["text"]}, **d(0, 1400)},
        {"name": "laufender Monat", "type": "line", "color": t["text"], "symbol": "emptyCircle", "symbolSize": 10, "z": 7,
         "data": [round(z.erwartet, 1) if z.art == "laufend" else None for z in zs] if zeig(2) else leer_,
         "itemStyle": {"color": t["text"], "borderWidth": 2}, "lineStyle": {"opacity": 0}, **d(1450, 350)},
        {"name": "Prognose (erwartet)", "type": "line", "color": t["akzent"], "symbol": "none", "z": 6,
         "data": prog("erwartet") if zeig(2) else leer_, "lineStyle": {"color": t["akzent"], "width": 2.4, "type": [7, 5]},
         **d(1700, 1000)},
        {"name": "Kapazität", "type": "line", "symbol": "none", "color": t["rot"], "z": 4,
         "data": [kap] * len(zs) if kap and zeig(4) else leer_, "lineStyle": {"color": t["rot"], "width": 1.4, "type": [5, 4]},
         "endLabel": {"show": bool(kap and zeig(4)), "formatter": "Kapazität {c}", "color": t["rot"], "fontSize": 11}, **d(0, 700)},
    ]
    for i_, r_ in ((0, "band95"), (1, "band95"), (2, "band"), (3, "band")):      # 0.96: deutlich, mit Kante
        _ds.band_reihe(reihen[i_], t, r_)
    if li is not None and li + 1 < len(zs) and zeig(2):
        reihen[6]["markArea"] = {"silent": True, "itemStyle": {"color": _rgba(t["akzent"], .045)},
                                 "label": {"show": True, "position": "insideTopLeft", "color": t["text3"], "fontSize": 11,
                                           "formatter": "Prognose →"},
                                 "data": [[{"xAxis": labels[li]}, {"xAxis": labels[-1]}]]}
    if fort_ab < len(zs) and zeig(2):
        reihen.append({"name": "", "type": "line", "data": leer_, "silent": True, "showSymbol": False,
                       "markArea": {"silent": True, "itemStyle": {"color": _rgba(t["text3"], .07)},
                                    "label": {"show": True, "position": "insideTop", "color": t["text3"], "fontSize": 11,
                                              "formatter": "ab Monat 13: nur fortgeschrieben, nicht geprüft"},
                                    "data": [[{"xAxis": labels[fort_ab]}, {"xAxis": labels[-1]}]]}})
    if li is not None and li + 1 < len(zs) and zeig(2):  # Stichtag-Marker trennt Vergangenheit und Zukunft
        reihen[4]["markLine"] = {"silent": True, "symbol": "none", "animationDelay": 1400, "animationDuration": 500,
                                 "lineStyle": {"color": t["text2"], "type": [2, 3], "width": 1.2},
                                 "label": {"formatter": f"Datenstand {c['stichtag']:%d.%m.%Y}", "color": t["text2"],
                                           "fontSize": 12, "position": "end"},
                                 "data": [{"xAxis": labels[li + 1]}]}
    if zeig(2) and not start:
        reihen[6]["markPoint"] = _spotlights(t, zs, labels, kap)
    # 0.78: Die Engpass-Zone aus 0.75 ist wieder entfernt – sie lag als dritte Fläche über „Prognose →“ und „ab Monat 13“
    # und wiederholte nur das Abzeichen „Engpass ab …“. Das Diagramm ist so wieder ruhig.
    zusatz = {z.monat: z.vertraege for z in c["pg"].zeilen}
    blind = {mon: p + zusatz.get(mon, 0.0) for mon, _i, p in c["pg"].rueckblick} if c["backtest"] else {}
    bt = BACKTEST_FARBE[not _ds.dunkel(t)]           # 0.97: eigener, klar abgesetzter Farbton (nicht Akzent/Orange)
    reihen.append({"name": "Backtest (1 Monat vorher)", "type": "line", "symbol": "diamond", "symbolSize": 8, "color": bt,
                   "data": [round(blind[z.monat], 1) if z.monat in blind else None for z in zs] if blind else leer_,
                   "itemStyle": {"color": bt}, "lineStyle": {"color": bt, "width": 2, "type": [3, 3]}, **d(1600, 500)})
    reihen += _geist(t, zs_sz, zs, li, kap, kap_sz, aktiv and zeig(2))
    o["series"] = reihen
    if c.get("phase") == "voll" and c["animation"]:      # Story-Aufbau, 2. Teil: Bänder fächern sich auf, Badges erscheinen
        o["animationDurationUpdate"], o["animationEasingUpdate"] = 1100, "cubicOut"
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
    labels = [ak.monat_text(m.monat) for m in sm]
    li = max((i for i, m in enumerate(sm) if m.art == "ist"), default=None)
    o["xAxis"]["data"] = labels
    o["yAxis"]["scale"] = False
    _titel(o, t, f"Belegung {ort} nach Status · {zaehl}" + (" · mit SZENARIO als Schattenkurve" if aktiv else ""),
           f"Ø Plätze je Monat · {_zeitraum(sm)} · UWT und Mieter: Ist bzw. gebucht · Rest: Ist bzw. Prognose")
    # 0.98: ruhiger Sockel (UWTler, Mieter) ohne Punkte und Zahlen, oben EINE Kurve mit der Gesamtzahl als ganze Zahl
    hell = bool(t.get("hell"))
    hg = t.get("fls") or t.get("bg") or ("#ffffff" if hell else "#15171c")
    gesamt = [round(m.gesamt) for m in sm]
    reihen = []
    for schl in ("UWT", "Mieter", "uebrige"):
        farbe, deckung, breite = STATUS_SOCKEL[schl]
        if not hell:                                   # im Dunkeln denselben Farbton heller – sonst unsichtbar
            farbe = _ds.angleichen(farbe, hg, _ds.LINIE_MIN)
        oben = schl == "uebrige"
        se = {"name": an.STATUS_NAMEN[schl], "type": "line", "stack": "status", "smooth": True, "color": farbe,
              "symbol": "circle" if oben else "none", "symbolSize": 5, "showSymbol": oben,
              "data": [round(getattr(m, schl.lower()), 1) for m in sm],
              "lineStyle": {"width": breite, "color": farbe}, "itemStyle": {"color": farbe},
              "areaStyle": {"color": farbe, "opacity": deckung}, "animationDuration": 900,
              "label": {"show": False}}
        if oben:                                       # Beschriftung = Gesamtzahl (Höhe des Stapels), ganze Plätze
            se["label"] = {"show": True, "position": "top", "distance": 6, "fontSize": 11, "fontWeight": 500,
                           "color": t["text"], ":formatter": "(p) => { const G = " + json.dumps(gesamt) + "; "
                           "const v = G[p.dataIndex]; return v == null ? '' : v.toLocaleString('de-DE'); }"}
            se["labelLayout"] = {"hideOverlap": True}
        reihen.append(se)
    if li is not None and li + 1 < len(sm):
        reihen[-1]["markArea"] = {"silent": True, "itemStyle": {"color": _rgba(t["akzent"], .045)},
                                  "label": {"show": True, "position": "insideTopLeft", "color": t["text2"], "fontSize": 11,
                                            "offset": [10, 8], "formatter": "Prognose →"},
                                  "data": [[{"xAxis": labels[li]}, {"xAxis": labels[-1]}]]}
    # Kapazität und Kontingente als Bezugslinien (markLine) – kein Punkt und keine Zahl je Monat mehr
    bezug = []
    if kap:
        bezug.append({"yAxis": kap, "lineStyle": {"color": t["rot"], "type": "dashed", "width": 1.2},
                      "label": {"position": "end", "formatter": f"Kapazität {_z(kap)}", "color": t["rot"], "fontSize": 11}})
    kont = c.get("kontingent")
    if kont and kap:                                    # Kontingentgrenzen: UWT unten, darüber UWT + Mieter
        for name, wert in (("Kontingent UWT + Mieter", kap * (kont["UWT"] + kont["Mieter"]) / 100),
                           ("Kontingent UWT", kap * kont["UWT"] / 100)):
            bezug.append({"yAxis": round(wert, 1),
                          "lineStyle": {"color": KONTINGENT_LINIE if hell else t["text2"], "type": "dashed", "width": 1},
                          "label": {"position": "end", "formatter": f"{name} {round(wert)}", "color": t["text2"],
                                    "fontSize": 11}})
    if bezug:
        reihen[-1]["markLine"] = {"symbol": ["none", "none"], "silent": True, "data": bezug}
    zs0 = ak.szenario(c["pg"], kap, 0)
    if aktiv:
        reihen += _geist(t, zs_sz, zs0, li, kap, kap_sz, True)
    o["series"] = reihen
    o["grid"]["right"] = 165 if kont else 110          # Beschriftungen rechts nie abgeschnitten
    if kap:                                            # Bezugslinien zählen nicht für die Achse → Kapazität sichtbar halten
        o["yAxis"]["max"] = int(-(-max(kap * 1.08, max(gesamt or [0]) * 1.08) // 20) * 20)
    o["legend"]["show"] = False                        # Legende steht als HTML unter dem Diagramm
    o["tooltip"]["trigger"] = "axis"
    o["tooltip"]["axisPointer"] = {"type": "line", "lineStyle": {"color": t["text3"], "type": "dashed"}}
    d = [{"m": ak.monat_text(m.monat), "a": m.art, "u": m.uwt, "mi": m.mieter, "r": m.uebrige, "g": m.gesamt,
          "se": zs_sz[i].erwartet if aktiv and m.art != "ist" else None} for i, m in enumerate(sm)]
    fc = {"u": reihen[0]["color"], "mi": reihen[1]["color"], "r": reihen[2]["color"], "sz": t["orange"], "b": t["text3"]}
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


STATUS_SOCKEL = {"UWT": (_ds.GRUPPEN_FARBEN["UWT"], .28, 1.5), "Mieter": (_ds.GRUPPEN_FARBEN["Mieter"], .22, 1.5),
                 "uebrige": (_ds.GRUPPEN_FARBEN["uebrige"], .20, 2.0)}       # 0.98/0.99: Farbe, Deckung, Linie
KONTINGENT_LINIE = "#64748b"


# ---- 0.87: Belegung inkl. UWTler und Mieter als Diagramm-Karte ---------------------------------------------------
NETTO_TEXT = {False: "Netto (Internatsplätze ohne FRAI, Jugendhilfe und andere Bereiche)",
              True: "Brutto (alle Plätze inkl. FRAI, Jugendhilfe und andere Bereiche)"}


def zoom(labels: list[str], li: int | None, zurueck: int = 12, vor: int = 12) -> list[dict]:
    """Standard-Ausschnitt: 12 Monate zurück und 12 voraus; mehr über den Schieber unter dem Diagramm."""
    if not labels:
        return []
    m = li if li is not None else 0
    return [{"type": "slider", "xAxisIndex": "all", "startValue": labels[max(0, m - zurueck)],
             "endValue": labels[min(len(labels) - 1, m + vor)], "bottom": 6, "height": 18, "filterMode": "filter",
             "brushSelect": False, "showDetail": False}]


def _status_karte(o, t, c) -> dict:
    """Zwei Flächen mit gemeinsamer Zeitachse. Oben: alle Bewohner gegen die Kapazität – die graue Linie zeigt nur die
    Teilnehmenden, die farbige Fläche dazwischen ist der Anteil von UWTlern und Mietern. Unten: UWTler und Mieter als
    gestapelte Balken gegen ihre Kontingente. Wo die bekannten Verträge enden, ist der Bereich schraffiert."""
    from . import blick_kern as bk
    from . import diagramm_stil as ds

    sm = c["sm"]
    pg = c["pg"]
    kap = pg.kapazitaet or 0
    n = len(sm)
    labels = [ak.monat_text(m.monat) for m in sm]
    li = max((i for i, m in enumerate(sm) if m.art == "ist"), default=None)
    zs = {z.monat: z for z in ak.szenario(pg, kap, 0)}
    gr = [m.uwt + m.mieter for m in sm]
    grenze = bk.vertrags_grenze(gr, li)
    kont = c.get("kontingent")
    k_uwt = kap * kont["UWT"] / 100 if kont and kap else None
    k_beide = kap * (kont["UWT"] + kont["Mieter"]) / 100 if kont and kap else None
    fu, fm, warn, akz, grau = (_ds.gruppen_farbe("UWT"), _ds.gruppen_farbe("Mieter"), t["rot"], t["akzent"],
                               t["text3"])
    r1 = lambda x: None if x is None else round(x, 1)  # noqa: E731
    nach = lambda i: li is not None and i > li  # noqa: E731
    ende = lambda i, x: None if nach(i) and x <= .05 else r1(x)  # noqa: E731   Reihe endet mit dem letzten Vertrag
    band = [zs.get(m.monat) for m in sm]
    lo = [r1(b.lo80) if b is not None and nach(i) else None for i, b in enumerate(band)]
    br = [r1(b.hi80 - b.lo80) if b is not None and nach(i) else None for i, b in enumerate(band)]
    end = lambda name, farbe: {"show": True, "formatter": name, "color": farbe, "fontSize": 12, "fontWeight": 600}  # noqa: E731
    reihen = [
        {"name": "_u80", "type": "line", "stack": "b80", "data": lo, "symbol": "none", "silent": True, "lineStyle": {"opacity": 0},
         "tooltip": {"show": False}},
        {"name": "80-%-Spanne", "type": "line", "stack": "b80", "data": br, "symbol": "none", "silent": True,
         "lineStyle": {"opacity": 0}, "areaStyle": {"color": _ds.band_flaeche(_t())}},
        {"name": "nur Teilnehmende", "type": "line", "stack": "g", "data": [r1(m.uebrige) for m in sm], "showSymbol": False,
         "smooth": False, "color": grau, "lineStyle": {"color": grau, "width": 1.5}, "endLabel": end("nur Teilnehmende", grau),
         "labelLayout": {"moveOverlap": "shiftY"}},
        {"name": "UWTler + Mieter", "type": "line", "stack": "g", "data": [r1(x) for x in gr], "showSymbol": False, "smooth": False,
         "color": fu, "lineStyle": {"opacity": 0}, "areaStyle": {"color": fu, "opacity": .18}, "silent": True},
        {"name": "Alle Bewohner (Ist)", "type": "line", "data": [r1(m.gesamt) if li is not None and i <= li else None
                                                               for i, m in enumerate(sm)],
         "showSymbol": False, "smooth": False, "color": akz, "lineStyle": {"color": akz, "width": 3}, "z": 5},
        {"name": "Alle Bewohner", "type": "line", "data": [r1(m.gesamt) if li is not None and i >= li else None
                                                         for i, m in enumerate(sm)],
         "showSymbol": False, "smooth": False, "color": akz, "lineStyle": {"color": akz, "width": 2.5, "type": "dashed"}, "z": 5,
         "endLabel": end("Alle Bewohner", akz), "labelLayout": {"moveOverlap": "shiftY"}},
    ]
    if kap:
        reihen.append({"name": "Kapazität", "type": "line", "data": [kap] * n, "showSymbol": False, "color": warn,
                       "lineStyle": {"color": warn, "width": 1.5}, "endLabel": end(f"Kapazität {_z(kap)}", warn), "z": 4})
    # unten: Gruppen gegen Kontingente (Monate darüber in Warnfarbe)
    unten = {"xAxisIndex": 1, "yAxisIndex": 1}
    reihen += [
        {**unten, "name": "UWTler", "type": "bar", "stack": "gb", "barMaxWidth": 16, "color": fu,
         "data": [{"value": ende(i, m.uwt), "itemStyle": {"color": warn if k_uwt and m.uwt > k_uwt + .5 else fu}}
                  for i, m in enumerate(sm)]},
        {**unten, "name": "Mieter", "type": "bar", "stack": "gb", "barMaxWidth": 16, "color": fm,
         "data": [{"value": ende(i, m.mieter), "itemStyle": {"color": warn if k_beide and m.uwt + m.mieter > k_beide + .5 else fm,
                                                             "borderRadius": [3, 3, 0, 0]}} for i, m in enumerate(sm)]},
    ]
    for name, wert, farbe in (("Kontingent UWT", k_uwt, fu), ("Kontingent UWT + Mieter", k_beide, fm)):
        if wert:
            reihen.append({**unten, "name": name, "type": "line", "data": [round(wert, 1)] * n, "showSymbol": False, "silent": True,
                           "color": farbe, "lineStyle": {"color": farbe, "width": 1.2, "type": [6, 4]},
                           "endLabel": end(f"{name} {_z(wert)}", farbe), "labelLayout": {"moveOverlap": "shiftY"}})
    # Datenstand, Prognosebereich und schraffiert „noch keine Verträge“ – auf unsichtbaren Hilfsreihen (oben und unten)
    # Schraffur als Kachelmuster (Canvas im Browser) – „noch keine Verträge“
    schraffur = {":color": "(() => { const c = document.createElement('canvas'); c.width = c.height = 8;"
                           " const x = c.getContext('2d'); x.strokeStyle = 'rgba(128,128,128,.45)'; x.lineWidth = 1;"
                           " x.beginPath(); x.moveTo(0, 8); x.lineTo(8, 0); x.stroke(); return { image: c, repeat: 'repeat' }; })()"}
    flaechen = []
    if li is not None and li + 1 < n:
        flaechen.append([{"xAxis": labels[li + 1], "itemStyle": {"color": _rgba(akz, .05)}}, {"xAxis": labels[-1]}])
    if grenze is not None:
        flaechen.append([{"xAxis": labels[grenze], "itemStyle": schraffur, "name": "noch keine Verträge"},
                         {"xAxis": labels[-1]}])
    fokus = {"id": ds.FOKUS_ID, "name": "", "type": "line", "data": [], "symbol": "none", "silent": True, "smooth": False,
             "tooltip": {"show": False}, "z": 9}
    if li is not None:
        fokus["markLine"] = {"silent": True, "symbol": "none", "lineStyle": {"color": t["text2"], "type": [3, 3], "width": 1.2},
                             "label": {"formatter": f"Datenstand {c['stichtag']:%d.%m.%Y}", "position": "end", "fontSize": 12,
                                       "color": t["text2"]}, "data": [{"xAxis": labels[li]}]}
    if flaechen:
        fokus["markArea"] = {"silent": True, "label": {"show": True, "position": "insideTopLeft", "fontSize": 12, "color": grau},
                             "data": flaechen}
    unten_hilfe = {**unten, "name": "", "type": "line", "data": [], "symbol": "none", "silent": True, "tooltip": {"show": False}}
    if grenze is not None:
        unten_hilfe["markArea"] = {"silent": True, "data": [[{"xAxis": labels[grenze], "itemStyle": schraffur}, {"xAxis": labels[-1]}]]}
    reihen += [fokus, unten_hilfe]
    oben_max = max([m.gesamt for m in sm] + [kap or 0])
    unten_max = max(gr + [k_beide or 0, k_uwt or 0, 1])
    achse = {"axisLine": {"lineStyle": {"color": t["rand2"]}}, "splitLine": {"lineStyle": {"color": t["rand"], "type": [3, 3]}},
             "axisLabel": {"color": grau, "fontSize": 12, ":formatter": ds.ZAHL_JS}}
    o.pop("title", None)
    o["legend"] = {"show": False}
    o["grid"] = [{"left": 52, "right": 190, "top": 16, "height": "52%"}, {"left": 52, "right": 190, "top": "66%", "bottom": 52}]
    o["xAxis"] = [{"type": "category", "gridIndex": 0, "data": labels, "boundaryGap": True, "axisLabel": {"show": False},
                   "axisTick": {"show": False}, "axisLine": {"lineStyle": {"color": t["rand2"]}}},
                  {"type": "category", "gridIndex": 1, "data": labels, "boundaryGap": True,
                   "axisLabel": {"color": grau, "fontSize": 12}, "axisLine": {"lineStyle": {"color": t["rand2"]}}}]
    o["yAxis"] = [{"type": "value", "gridIndex": 0, "min": 0, "max": int(round(oben_max * 1.1 / 50 + .5) * 50), **achse,
                   "name": "alle Bewohner", "nameTextStyle": {"color": grau, "fontSize": 12, "align": "left"}},
                  {"type": "value", "gridIndex": 1, "min": 0, "max": int(round(unten_max * 1.2 / 10 + .5) * 10), **achse,
                   "name": "UWTler · Mieter", "nameTextStyle": {"color": grau, "fontSize": 12, "align": "left"}}]
    o["axisPointer"] = {"link": [{"xAxisIndex": "all"}]}
    o["dataZoom"] = zoom(labels, li)
    o["series"] = reihen
    d = [{"m": ak.monat_text(m.monat), "a": m.art, "u": m.uwt, "mi": m.mieter, "r": m.uebrige, "g": m.gesamt,
          "ku": k_uwt, "kb": k_beide, "off": grenze is not None and i >= grenze} for i, m in enumerate(sm)]
    fc = {"u": fu, "mi": fm, "r": grau, "g": akz, "w": warn}
    o["tooltip"] = {"trigger": "axis", "confine": True, "axisPointer": {"type": "line"}, ":formatter": (
        "(ps) => { const D = " + json.dumps(d) + "; const C = " + json.dumps(fc) + "; const K = " + str(kap or 0) + ";"
        " const d = D[ps[0].dataIndex]; if (!d) return '';"
        " const f = v => v == null ? '–' : Number(v).toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 1});"
        " const z = (c, t, v) => `<div style=\"display:flex;gap:18px;justify-content:space-between;line-height:1.7\">"
        "<span><span style=\"display:inline-block;width:10px;height:10px;border-radius:2px;background:${c};margin-right:7px;vertical-align:-1px\"></span>${t}</span>"
        "<b style=\"font-variant-numeric:tabular-nums\">${v}</b></div>`;"
        " const art = d.a == 'ist' ? 'Ist' : (d.a == 'laufend' ? 'laufender Monat' : 'Prognose');"
        " let h = `<div style=\"font-weight:600;margin-bottom:6px\">${d.m} <span style=\"opacity:.65;font-weight:400\">· ${art}</span></div>`;"
        " h += z(C.g, 'Alle Bewohner', f(d.g)) + z(C.r, 'davon Teilnehmende' + (d.a == 'ist' ? '' : ' (Prognose)'), f(d.r))"
        " + z(d.ku && d.u > d.ku + .5 ? C.w : C.u, 'UWTler' + (d.a == 'ist' ? '' : ' (gebucht)'), f(d.u) + (d.ku ? ' / ' + Math.round(d.ku) : ''))"
        " + z(d.kb && d.u + d.mi > d.kb + .5 ? C.w : C.mi, 'Mieter' + (d.a == 'ist' ? '' : ' (Verträge)'), f(d.mi));"
        " if (d.kb) h += z('transparent', 'UWT + Mieter / Kontingent', f(d.u + d.mi) + ' / ' + Math.round(d.kb));"
        " if (K) h += z('transparent', 'Auslastung', Math.round(100 * d.g / K) + ' %');"
        " if (d.off) h += '<div style=\"opacity:.75;margin-top:4px\">Verträge UWT/Mieter hier noch nicht bekannt – nur Teilnehmende prognostiziert</div>';"
        " return h; }")}
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
    if c.get("vj_tage") is not None and c["vj_tage"].tage:       # 1.22: tagesgenau, Prognose ab dem Stichtag
        return _vorjahr_taeglich(o, t, c, ort, zaehl, szen)
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
    band = {z.monat: (z.lo80, z.hi80) for z in ak.szenario(c["pg"], c["kap"], c["offset"]) if z.art != "ist"}
    lo = [round(band[m][0], 1) if m in band and not i else None for m, i in zip(vj.monate, vj.aktuell_ist)]
    br = [round(band[m][1] - band[m][0], 1) if m in band and not i else None for m, i in zip(vj.monate, vj.aktuell_ist)]
    o["series"] = [
        {"name": "_u80", "rolle": "band", "type": "line", "stack": "vjb", "data": lo, "symbol": "none", "silent": True,
         "lineStyle": {"opacity": 0}, "tooltip": {"show": False}},
        {"name": "80-%-Spanne", "rolle": "band", "type": "line", "stack": "vjb", "data": br, "symbol": "none", "silent": True,
         "lineStyle": {"opacity": 0}, "areaStyle": {"color": _ds.band_flaeche(t)}},
        {"name": "Vorvorjahr (Ist)", "type": "line", "data": rnd(vj.vorvorjahr), "symbol": "none", "color": t["text3"],
         "lineStyle": {"color": t["text3"], "width": 1.2, "type": "dotted"}, "animationDuration": 700},
        {"name": "Vorjahr (Ist)", "type": "line", "data": rnd(vj.vorjahr), "symbol": "circle", "symbolSize": 4,
         "color": VORJAHR_FARBE[not _ds.dunkel(t)],                          # 0.97: Violett statt Blau neben Türkis
         "lineStyle": {"color": VORJAHR_FARBE[not _ds.dunkel(t)], "width": 2}, "animationDuration": 800},
        {"name": "Aktuell (Ist)", "type": "line", "data": akt_ist, "symbol": "circle", "symbolSize": 5, "color": t["text"],
         "lineStyle": {"color": t["text"], "width": 2.6}, "animationDelay": 300, "animationDuration": 800},
        {"name": "Aktuell (Prognose)", "type": "line", "data": akt_prog, "symbol": "none", "color": t["akzent"],
         "lineStyle": {"color": t["akzent"], "width": 2.4, "type": [7, 5]}, "animationDelay": 900, "animationDuration": 600},
    ]
    # keine Kapazitätslinie: hier geht es um den saisonalen Vergleich – sie würde die Unterschiede flach drücken
    o["legend"]["data"] = [s["name"] for s in o["series"] if not s["name"].startswith("_")]
    o["tooltip"]["valueFormatter"] = None
    d = [{"m": l, "a": a, "v": v, "vv": vv, "ist": i, "b": list(band[m]) if m in band and not i else None}
         for l, a, v, vv, i, m in zip(labels, vj.aktuell, vj.vorjahr, vj.vorvorjahr, vj.aktuell_ist, vj.monate)]
    o["tooltip"][":formatter"] = (
        "(ps) => { const D = " + json.dumps(d) + "; const d = D[ps[0].dataIndex]; if (!d) return '';"
        " const f = v => v == null ? '–' : Math.round(v).toLocaleString('de-DE');"
        " const dl = (a, b) => (a == null || b == null) ? 'Vorjahr fehlt' : ((a - b >= 0 ? '+' : '−') + f(Math.abs(a - b)) + ' (' + (a - b >= 0 ? '+' : '−') + Math.abs(Math.round(100 * (a - b) / b)) + ' %)');"
        " const f1 = v => v == null ? '–' : Number(v).toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 1});"
        " return `<b>${d.m}</b><br>${d.ist ? 'Ist' : 'Prognose'}: <b>${f1(d.a)}</b>"
        "${d.b ? '<br>80-%-Spanne: ' + f1(d.b[0]) + ' – ' + f1(d.b[1]) : ''}<br>Vorjahr (Ist): ${f1(d.v)}<br>"
        "Vorvorjahr (Ist): ${f1(d.vv)}<br><span style=\"opacity:.75\">Differenz zum Vorjahr: ${dl(d.a, d.v)}</span>`; }")
    return o


def jahr_achse(vt) -> tuple[list[str], int | None]:
    """1.22: Beschriftungen der Tagesachse und Index des Stichtags (letzter Ist-Tag)."""
    labels = [an.tag_text(d) for d in vt.tage]
    si = max((i for i, d in enumerate(vt.tage) if d <= vt.stichtag and vt.ist[i] is not None), default=None)
    return labels, si


def _vorjahr_taeglich(o, t, c, ort, zaehl, szen) -> dict:
    """1.22: Vorjahresvergleich je Tag. Ist bis zum Stichtag, danach Prognose – sie beginnt beim Ist-Wert des Stichtags
    (Spanne 0) und läuft zu den Monatswerten der Prognose (80 % und 95 %). Vorjahr/Vorvorjahr am gleichen Wochentag."""
    vt = c["vj_tage"]
    vj = an.vorjahr(c.get("pg_lang") or c["pg"])
    labels, si = jahr_achse(vt)
    n = len(labels)
    zs = ak.szenario(c["pg"], c["kap"], c["offset"])
    pt = an.prognose_tage(vt, zs)
    ersten = [i for i, d in enumerate(vt.tage) if d.day == 1]
    monat_je_i = {i: f"{ak.MONATE[vt.tage[i].month - 1]} {str(vt.tage[i].year)[2:]}" for i in ersten}
    o["xAxis"]["data"] = labels
    o["xAxis"]["boundaryGap"] = False
    o["xAxis"]["axisLabel"] = {**(o["xAxis"].get("axisLabel") or {}), ":interval": f"(i) => {json.dumps(ersten)}.includes(i)",
                               ":formatter": f"(v, i) => ({json.dumps(monat_je_i)})[i] || ''", "hideOverlap": False}
    o["xAxis"]["axisTick"] = {":interval": f"(i) => {json.dumps(ersten)}.includes(i)"}
    stich = vt.stichtag
    _titel(o, t, f"Vorjahresvergleich · {ort} · {zaehl}{szen}",
           f"Belegte Plätze je Tag · Ist bis {stich:%d.%m.%Y}, danach Prognose · Vorjahr und Vorvorjahr am gleichen Wochentag")
    r1 = lambda xs: [round(x, 1) if x is not None else None for x in xs]  # noqa: E731
    ist = [round(v, 1) if v is not None and (si is None or i <= si) else None for i, v in enumerate(vt.ist)]
    # Linien: Monatsmittel zur Monatsmitte (ruhig, vergleichbar); die Tageswerte stehen im Tooltip
    idx = {d: i for i, d in enumerate(vt.tage)}
    mitte = [idx.get(m.replace(day=15)) for m in vj.monate]
    leer = lambda: [None] * n  # noqa: E731
    l_vj, l_vvj, l_ist = leer(), leer(), leer()
    for _m, i_m, a_, ist_m, v_, vv_ in zip(vj.monate, mitte, vj.aktuell, vj.aktuell_ist, vj.vorjahr, vj.vorvorjahr):
        if i_m is None:
            continue
        l_vj[i_m] = round(v_, 1) if v_ is not None else None
        l_vvj[i_m] = round(vv_, 1) if vv_ is not None else None
        if ist_m and a_ is not None and (si is None or i_m < si):
            l_ist[i_m] = round(a_, 1)
    if si is not None:
        l_ist[si] = {"value": ist[si], "label": {"show": False}}   # Ist läuft bis zum Stichtag (Tageswert, Marke s. u.) …
    # … dort beginnt die Prognose (Spanne 0); zwischen den Monatswerten linear – ruhig und ohne Lücken
    l_prog, b = pt["erwartet"], {k: pt[k] for k in ("lo80", "hi80", "lo95", "hi95")}
    breite = lambda lo, hi: [round(y - x, 1) if x is not None and y is not None else None for x, y in zip(lo, hi)]  # noqa: E731
    linie = {"type": "line", "connectNulls": True, "symbolSize": 5, "m_fest": True}
    reihen = []
    if c.get("b95"):
        reihen += [
            {**linie, "name": "_u95", "rolle": "band95", "stack": "vj95", "data": b["lo95"], "symbol": "none", "silent": True,
             "lineStyle": {"opacity": 0}, "tooltip": {"show": False}},
            {**linie, "name": "95-%-Spanne", "rolle": "band95", "stack": "vj95", "data": breite(b["lo95"], b["hi95"]),
             "symbol": "none", "silent": True, "lineStyle": {"opacity": 0}, "tooltip": {"show": False}}]
    reihen += [
        {**linie, "name": "_u80", "rolle": "band", "stack": "vj80", "data": b["lo80"], "symbol": "none", "silent": True,
         "lineStyle": {"opacity": 0}, "tooltip": {"show": False}},
        {**linie, "name": "80-%-Spanne", "rolle": "band", "stack": "vj80", "data": breite(b["lo80"], b["hi80"]), "symbol": "none",
         "silent": True, "lineStyle": {"opacity": 0}, "areaStyle": {"color": _ds.band_flaeche(t)}, "tooltip": {"show": False}},
        {**linie, "name": "Vorvorjahr (Ist)", "data": l_vvj, "symbol": "none", "color": t["text3"],
         "lineStyle": {"color": t["text3"], "width": 1.2, "type": "dotted"}},
        {**linie, "name": "Vorjahr (Ist)", "data": l_vj, "symbol": "circle", "color": VORJAHR_FARBE[not _ds.dunkel(t)],
         "lineStyle": {"color": VORJAHR_FARBE[not _ds.dunkel(t)], "width": 2}},
        {**linie, "name": "Aktuell (Ist)", "data": l_ist, "symbol": "circle", "color": t["text"], "lineStyle": {"color": t["text"], "width": 2.6}},
        {**linie, "name": "Aktuell (Prognose)", "data": l_prog, "symbol": "none", "color": t["akzent"],
         "lineStyle": {"color": t["akzent"], "width": 2.4, "type": [7, 5]}},
        # unsichtbar, an jedem Tag: damit der Tooltip jeden Tag zeigt (Tageswerte stehen im Formatter)
        {"type": "line", "name": "_tag", "rolle": "hilfe", "data": [ist[i] if ist[i] is not None else
                                                                    (pt["erwartet"][i] if pt["erwartet"][i] is not None else vt.vorjahr[i])
                                                                    for i in range(n)],
         "symbol": "none", "showSymbol": False, "lineStyle": {"opacity": 0}, "silent": True, "m_fest": True, "z": 0},
    ]
    if si is not None:
        reihen[-3]["markPoint"] = {"symbol": "circle", "symbolSize": 10, "silent": True,
                                   "itemStyle": {"color": t["text"], "borderColor": "#fff", "borderWidth": 2},
                                   "label": {"show": True, "position": "top", "distance": 8, "fontWeight": "bold", "fontSize": 13,
                                             "color": t["text"], "formatter": f"{stich:%d.%m.}: {_z(ist[si])}"},
                                   "data": [{"coord": [labels[si], ist[si]]}]}
        if not c.get("karte"):                                  # Klassisch: Stichtag als senkrechte Linie
            reihen[-3]["markLine"] = {"silent": True, "symbol": "none", "lineStyle": {"color": t["text2"], "type": [3, 3], "width": 1.2},
                                      "label": {"formatter": f"Stichtag {stich:%d.%m.%Y}", "position": "end", "color": t["text2"]},
                                      "data": [{"xAxis": labels[si]}]}
    o["series"] = reihen
    o["legend"]["data"] = [r["name"] for r in reihen if not r["name"].startswith("_")]
    o["tooltip"]["valueFormatter"] = None
    # Tooltip: der Tag (Ist oder Prognose mit Spannen), Vorjahr am gleichen Wochentag, dazu die Monatsmittel
    mon = {}
    for m, a_, i_, v_, vv_ in zip(vj.monate, vj.aktuell, vj.aktuell_ist, vj.vorjahr, vj.vorvorjahr):
        mon[f"{m:%Y-%m}"] = {"n": f"{ak.MONATE[m.month - 1]} {m.year}", "a": a_, "ist": i_, "v": v_, "vv": vv_}
    d = []
    for i, tg in enumerate(vt.tage):
        vd = tg - an.timedelta(days=an.VJ_TAGE)
        d.append({"l": labels[i], "s": i == si, "i": ist[i], "p": pt["erwartet"][i] if (si is None or i > si) else None,
                  "b8": [pt["lo80"][i], pt["hi80"][i]] if pt["lo80"][i] is not None and i != si else None,
                  "b9": [pt["lo95"][i], pt["hi95"][i]] if c.get("b95") and pt["lo95"][i] is not None and i != si else None,
                  "v": r1([vt.vorjahr[i]])[0], "vv": r1([vt.vorvorjahr[i]])[0], "vd": an.tag_text(vd), "m": f"{tg:%Y-%m}"})
    o["tooltip"][":formatter"] = (
        "(ps) => { const D = " + json.dumps(d) + "; const M = " + json.dumps(mon) + ";"
        " const d = ps && ps.length ? D[ps[0].dataIndex] : null; if (!d) return '';"
        " const f0 = v => v == null ? '–' : Math.round(v).toLocaleString('de-DE');"
        " const f1 = v => v == null ? '–' : Number(v).toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 1});"
        " let h = `<b>${d.l}</b>` + (d.s ? ' <span style=\"opacity:.7\">· Stichtag</span>' : '');"
        " if (d.i != null) h += `<br>Belegt (Ist): <b>${f0(d.i)}</b>`;"
        " else if (d.p != null) h += `<br>Prognose: <b>${f0(d.p)}</b>`"
        "   + (d.b8 ? `<br>80-%-Spanne: ${f0(d.b8[0])} – ${f0(d.b8[1])}` : '') + (d.b9 ? `<br>95-%-Spanne: ${f0(d.b9[0])} – ${f0(d.b9[1])}` : '');"
        " h += `<br>Vorjahr (${d.vd}): ${f0(d.v)}`; if (d.vv != null) h += `<br>Vorvorjahr: ${f0(d.vv)}`;"
        " const a = d.i != null ? d.i : d.p;"
        " if (a != null && d.v != null) h += `<br><span style=\"opacity:.75\">Differenz zum Vorjahr: ${a - d.v >= 0 ? '+' : '−'}${f0(Math.abs(a - d.v))}</span>`;"
        " const m = M[d.m]; if (m) h += `<div style=\"opacity:.75;margin-top:6px\">Monat ${m.n} · Ø ${m.ist ? 'Ist' : 'erwartet'} ${f1(m.a)}`"
        "   + ` · Vorjahr ${f1(m.v)}</div>`;"
        " return h; }")
    return o


def _zeitraum_m(ms) -> str:
    return f"{ak.monat_text(ms[0])} – {ak.monat_text(ms[-1])}" if ms else ""


def vergleich_option(sv: list, aktiv: str, hell: bool, animation: bool) -> dict:
    from . import diagramm_stil

    return diagramm_stil.anwenden(_vergleich_roh(sv, aktiv, hell, animation), themes.AKTIV)


def _vergleich_roh(sv: list, aktiv: str, hell: bool, animation: bool) -> dict:
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
