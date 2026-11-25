"""Auswertung → Prognose als Executive-Analytics-Ansicht (Darstellung; Daten: ``analytik_kern`` / ``auswertung_kern``).

Aufbau (Analysemodus): KPI-Karten → Erkenntnisse → Prognosegraph (Trend · Reserve · Vorjahr) → Szenario (Simulation)
→ Standortvergleich → Monatstabelle (kompakt/ausführlich) → Methodik und Backtest.
Präsentationsmodus: reduzierte Oberfläche, große KPIs, dominanter Graph, schrittweiser Aufbau, optional Standorte.

1.29: Die Diagramm-Bausteine liegen in ``prognose_diagramm`` (nur verschoben).
"""

from __future__ import annotations

import json

from nicegui import background_tasks, run, ui

from belegung import konfig

from . import analytik_kern as an
from . import auswertung_kern as ak
from . import kern, seiten
from .ui_bausteine import attr, knopf, leer, segmente

# 1.29: aufgeteilt – diese Namen liegen jetzt in prognose_diagramm.py (hier weiter erreichbar)
from .prognose_diagramm import (  # noqa: F401
    BACKTEST_EINFACH, BACKTEST_FARBE, BAND80, BAND95, KONTINGENT_LINIE, NETTO_TEXT, STATUS_SOCKEL, VORJAHR_FARBE,
    _basis, _berechnung_monat, _einfach, alle_bewohner, _formatter, _fragen, _geist, _gf_option, _karten_stil, _lesbar, _lesehilfe,
    _option_roh, _parallel, _reserve, _rgba, _spotlights, _status, _status_karte, _szenario_aktiv, _t, _titel,
    _trend, _vergleich_roh, _vorjahr, _vorjahr_taeglich, _z, _zeitraum, _zeitraum_m, blick_daten, blick_gruppen,
    jahr_achse, option, vergleich_option, zoom,
)

GOSLAR = "BFW GS"
OFFSET_MAX = 25                       # Auslastungs-Annahme im Szenario: ± Prozent
CHARTS = {"trend": "Trend & Prognose", "reserve": "Kapazitätsreserve", "jahr": "Vorjahresvergleich"}
SCHRITTE = {1: "Ist-Verlauf", 2: "+ Prognose", 3: "+ Unsicherheit (80/95 %)", 4: "+ Kapazität"}
TAG = {"Fakt": "fakt", "Prognose": "prognose", "Einschätzung": "einsch", "Hinweis": "hinweis"}


def _probe_karte(a, pg, kap: int) -> None:
    """0.95: Backtest als eigene Karte – ein Punkt je Monat: Abweichung echter Wert minus Vorhersage um die Nulllinie
    „Treffer“, das 80-%-Band dahinter; im Band grüne Kreise, außerhalb orange Rauten mit Beschriftung."""
    from . import blick_kern as bk
    from . import diagramm_karte

    rueck = list(pg.rueckblick or [])
    if not rueck:
        return
    zs = ak.szenario(pg, kap, 0)
    erst = next((z for z in zs if z.art == "prognose"), None)
    halb = max((erst.hi80 - erst.lo80) / 2 if erst else (pg.mae_1m or 0), 1.0)   # mindestens ± 1 Platz
    pr = bk.probe(rueck, halb)
    t = _t()
    labels = [f"{ak.MONATE[m.month - 1]} {str(m.year)[2:]}" for m, _d, _i in pr.punkte]
    aussen = sorted([(abs(d), i) for i, (_m, d, drin) in enumerate(pr.punkte) if not drin], reverse=True)[:4]
    beschr = {i for _a, i in aussen}
    daten = [{"value": [labels[i], round(d, 1)], "symbol": "circle" if drin else "diamond", "symbolSize": 10 if drin else 13,
              "itemStyle": {"color": t["gruen"] if drin else t["orange"]},
              "label": {"show": i in beschr, "formatter": bk.probe_text(m, d), "position": "top", "fontSize": 13,
                        "color": t["text"]}} for i, (m, d, drin) in enumerate(pr.punkte)]
    oben = max([abs(d) for _m, d, _i in pr.punkte] + [halb, 1]) * 1.3
    opt = {"animation": False, "grid": {"left": 48, "right": 24, "top": 30, "bottom": 30},
           "tooltip": {"trigger": "item", "confine": True,
                       ":formatter": "(p) => p.value[0] + ': ' + (p.value[1] >= 0 ? '+' : '') + "
                                     "p.value[1].toLocaleString('de-DE') + ' gegenüber der Vorhersage'"},
           "xAxis": {"type": "category", "data": labels, "axisLabel": {"color": t["text2"], "fontSize": 13}},
           "yAxis": {"type": "value", "min": -round(oben), "max": round(oben), "name": "echter Wert − Vorhersage",
                     "nameTextStyle": {"color": t["text2"], "fontSize": 13},
                     "axisLabel": {"color": t["text2"], "fontSize": 13},
                     "splitLine": {"lineStyle": {"color": t["rand"], "opacity": .5}}},
           "series": [{"type": "scatter", "data": daten,
                       "markArea": {"silent": True, "itemStyle": {"color": _rgba(t["akzent"], .14)},
                                    "data": [[{"yAxis": -round(halb, 1)}, {"yAxis": round(halb, 1)}]]},
                       "markLine": {"silent": True, "symbol": "none", "lineStyle": {"color": t["text"], "width": 1.5},
                                    "label": {"formatter": "Treffer", "position": "insideEndTop", "color": t["text"],
                                              "fontSize": 13}, "data": [{"yAxis": 0}]}}]}
    with diagramm_karte.Karte(a, pr.titel, pr.satz, None) as k:
        k.chart(opt).style("height:260px")
        k.wurzel.classes(add="blick-zu")              # kein „Auf einen Blick“ – der Titel ist die Aussage


# =======================================================================================
# Ansicht
# =======================================================================================

_GRUPPEN: dict = {}                    # Zwischenspeicher der UWT-/Mieter-Aufteilung je Datenstand und Auswahl


_DATEN: dict = {}                      # fertig gerechnete Seitendaten je Datenstand und Auswahl (Standortwechsel ohne Rechnen)


def daten(a, ds) -> None:
    """Prognose laden und die Schalter „UWTler / Mieter einbeziehen“ einrechnen (echte Listen, Verträge, Zimmerplan).
    Ergebnisse werden je Auswahl zwischengespeichert; die anderen Standorte rechnet ``vorrechnen`` im Hintergrund."""
    stand = getattr(a, "stand", None)
    from .prognose_diagramm import alle_bewohner

    mit = alle_bewohner(a)                  # 1.58: Standard mit UWTlern und Mietern (wie die Belegung); Schalter „nur TN“
    a.aw_uwt = a.aw_mieter = mit
    a.daten = dict(_daten_fuer(ds, stand, a.aw_standort, a.aw_brutto, a.aw_horizont, mit, mit))
    a.daten["alt"] = _daten_fuer(ds, stand, a.aw_standort, a.aw_brutto, a.aw_horizont, not mit, not mit)
    if a.aw_standort == GOSLAR:
        a.daten["kontingent"] = kern.kontingent_lesen(a.aw_standort)     # Planung kann sich ändern – immer frisch


def vorrechnen(a) -> None:
    """Hintergrund: Daten der übrigen Standorte (und Netto/Brutto-Gegenstück) vorbereiten."""
    ds, stand = (a.daten or {}).get("ds"), getattr(a, "stand", None)
    if ds is None:
        return
    for standort in ak.STANDORTE:
        for mit in (False, True):
            _daten_fuer(ds, stand, standort, a.aw_brutto, a.aw_horizont, mit, mit)
    _daten_fuer(ds, stand, a.aw_standort, not a.aw_brutto, a.aw_horizont, a.aw_uwt, a.aw_mieter)


def _daten_fuer(ds, stand, standort: str, brutto: bool, horizont: int, uwt: bool, mieter: bool) -> dict:
    schluessel = (id(ds), id(stand), standort, brutto, horizont, uwt, mieter)
    treffer = _DATEN.get(schluessel)
    if treffer is not None and treffer[0] is ds and treffer[1] is stand:
        return treffer[2]
    d = _daten_rechnen(ds, stand, standort, brutto, horizont, uwt, mieter)
    if len(_DATEN) > 24:
        _DATEN.clear()
    _DATEN[schluessel] = (ds, stand, d)
    return d


def _daten_rechnen(ds, stand, standort: str, brutto: bool, horizont: int, uwt: bool, mieter: bool) -> dict:
    import pandas as pd

    mieter_zr = an.mieter_zeitraeume(stand)

    def gruppen_fuer(st, pg):
        if not pg or not pg.zeilen:
            return None
        bis = (pd.Timestamp(pg.zeilen[-1].monat) + pd.offsets.MonthEnd(0)).date()
        von = min(pg.zeilen[0].monat, ds.stichtag - pd.Timedelta(days=370))
        schluessel = (id(ds), st, brutto, von, bis, tuple(mieter_zr), uwt, mieter)
        if schluessel not in _GRUPPEN:
            if len(_GRUPPEN) > 32:
                _GRUPPEN.clear()
            _GRUPPEN[schluessel] = (ds, an.gruppen(ds, st, brutto, von, bis, mieter_zr, uwt, mieter))
        return _GRUPPEN[schluessel][1]

    roh = ak.prognose(ds, standort, brutto, 36, horizont)      # 36 Monate: der Vorjahresvergleich braucht kein Neuladen
    g = gruppen_fuer(standort, roh)
    voll = an.mit_gruppen(roh, g) if g else roh
    pg = voll
    if voll:                                                    # sonst die üblichen 24 Ist-Monate
        a_ = max(0, len([z for z in voll.zeilen if z.art == "ist"]) - 24)
        pg = type(voll)(**{**voll.__dict__, "zeilen": voll.zeilen[a_:]})
    d = {"pg": pg, "pg_lang": voll, "stichtag": ds.stichtag, "ds": ds, "gruppen": g,
         "gruppen_da": standort in an.GRUPPEN_STANDORTE,
         "sv": an.standort_vergleich(ds, brutto, horizont, gruppen_fn=gruppen_fuer)}
    if voll:                                # 1.22: Tageswerte für den Vorjahresvergleich
        try:
            d["vj_tage"] = an.vorjahr_tage(ds, standort, brutto, an.vorjahr(voll).monate, g)
        except Exception:                   # noqa: BLE001 – dann Monatswerte wie bisher
            d["vj_tage"] = None
    if pg and g:                            # immer: „Nach Status“ schaltet ohne Neuladen um
        d["sm"] = an.status_monate(pg, g)
    if pg and g and standort == GOSLAR:
        d["sl"] = an.status_lage(ds, standort, brutto, d["sm"], g)
    d["sanierung"] = an.sanierung_plaetze(getattr(stand, "lage", None), standort)
    return d


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
    from . import diagramm_karte

    km = diagramm_karte.modus()                       # 0.89: Karte | Klassisch | Einfach (je PC)
    klassisch = praes or km == "klassisch"
    # Animation: beim ersten Öffnen und auf Wunsch – nicht bei jedem Filterwechsel, nie bei „weniger Bewegung“
    animiert = not a.weniger_bewegung and ((a.aw_anim and not a.aw_anim_gezeigt) or a._anim_jetzt)
    a.aw_anim_gezeigt, a._anim_jetzt = True, False
    hell = bool(_t().get("hell"))
    zustand = {"kap": a.aw_kap, "offset": a.aw_offset}
    par = lambda: a.aw_parallel and a.aw_standort == konfig.GESAMT  # noqa: E731
    def c(anim=False, phase="voll", **ueber):
        return {"pg": pg, "phase": phase, "parallel": par(), "sv": a.daten.get("sv"), "kap": zustand["kap"], "offset": zustand["offset"], "art": a.aw_chart,
                            "standort": a.aw_standort, "brutto": a.aw_brutto, "b95": a.aw_95,
                            "backtest": a.aw_backtest,    # 0.97: in jeder Darstellung, wenn eingeschaltet (Karte: dazu „Probe“)
                            "schritt": a.aw_schritt if praes and a.aw_chart == "trend" and not a.aw_status and not par() else 4, "animation": anim,
                            "pg_lang": a.daten.get("pg_lang"), "stichtag": a.daten["stichtag"],
                            "vj_tage": a.daten.get("vj_tage"),
                            "status": a.aw_status, "sm": a.daten.get("sm"), "kontingent": kontingent() if a.aw_uwt and a.aw_mieter else None,
                            "gruppen_text": a.daten["gruppen"].text() if a.daten.get("gruppen") else "",
                            "karte": not klassisch, **ueber}
    ds = a.daten["ds"]
    box: dict = {}
    sm = a.daten.get("sm") or []

    def kontingent():
        """Geplante Aufteilung (gespeichert) oder Vorschlag aus den gebuchten Zahlen – nur Goslar."""
        if a.aw_standort != GOSLAR or not sm:
            return None
        return a.daten.get("kontingent") or an.kontingent_vorschlag(sm, kap_echt)

    def ex():
        return an.executive(ds, a.aw_standort, a.aw_brutto, pg, zustand["kap"], zustand["offset"], a.aw_horizont,
                            a.daten.get("gruppen"))

    # ---- Kopfleiste (Analyse) ----------------------------------------------------------
    from . import menueband_ui as _mbu

    if not praes and _mbu.werkzeuge_oben(a):         # 1.00: Office-Gruppen im Menüband
        from . import band_ui as bu

        with a.werkzeuge:
            with bu.gruppe("Ansicht"):
                for k_, (sym, farbe) in BEREICH_SYMBOL.items():
                    # 1.59: nochmal klicken schließt Szenarien bzw. Details wieder (zurück zum Dashboard)
                    bu.gross(BEREICHE.get(k_, k_), sym, farbe,
                             lambda k_=k_: a.setzen(aw_bereich="dashboard" if a.aw_bereich == k_ else k_, laden=False),
                             an=a.aw_bereich == k_,
                             tipp=(f"{BEREICHE.get(k_, k_)} – nochmal klicken: zurück zum Dashboard"
                                   if k_ != "dashboard" else "Dashboard"))
                bu.gross("Rückblick", "history", "amber",
                         lambda: a.setzen(aw_backtest=not a.aw_backtest, laden=False), an=bool(a.aw_backtest),
                         tipp="Rückblick (Backtest) ein/aus: so lag die Vorhersage einen Monat vorher")
            with bu.gruppe("Wechsel"):
                bu.gross("Teilnehmer je Maßnahme", "people_team", "blau",
                         lambda: a.oeffnen("auswertung", ansicht="massnahmen", mn_ansicht="prognose",
                                           von=("Belegungs\u00adprognose", "auswertung", "prognose")),
                         tipp="Teilnehmer-Prognose je Maßnahmeart (Bestandsmodell) – die zweite Sicht")
            with bu.gruppe("Ausgabe"):
                _export_menue(a, pg, zustand, box, ex)
                bu.gross("Präsentation", "slide_play", "amber", lambda: _modus(a, "praes"),
                         tipp="Reduzierte Ansicht für Bildschirmfreigabe und Beamer (P) – Esc beendet")
    elif not praes:
        with a.leiste:
            with ui.element("div").classes("m-xbereich"):
                segmente(BEREICHE, a.aw_bereich, lambda v: a.setzen(aw_bereich=v, laden=False))
            knopf("Teilnehmer je Maßnahme", lambda: a.oeffnen("auswertung", ansicht="massnahmen", mn_ansicht="prognose",
                                           von=("Belegungs\u00adprognose", "auswertung", "prognose")),
                  "leise", "groups", "Teilnehmer-Prognose je Maßnahmeart (Bestandsmodell) – die zweite Sicht")
            knopf("Präsentation", lambda: _modus(a, "praes"), "primaer", "slideshow",
                  "Reduzierte Ansicht für Bildschirmfreigabe und Beamer (P) – Esc beendet").style("margin-left:auto")
            _export_menue(a, pg, zustand, box, ex)

    with a.inhalt:
        wurzel = ui.element("div").classes("m-ex" + (" praes" if praes else "") + (" still" if getattr(a, "_still", False) else ""))
    a._still = False
    bereich = "dashboard" if praes else a.aw_bereich
    wurzel.classes(add=f"b-{bereich}")
    with wurzel:
        if praes:
            _praes_kopf(a, pg)
        sz_raster = None
        if bereich == "szenario":                 # links der Graph mit Schattenkurve, rechts die Stellschrauben
            sz_raster = ui.element("div").classes("m-xsz")
        # ---- Goslar: Aufteilung UWTler / Mieter und Kontingente (Detail – steht unter dem Graph) ----------
        gs_box = None
        gs = a.daten if alle_bewohner(a) else (a.daten.get("alt") or {})   # Goslar-Detail zeigt immer UWTler und Mieter
        gs_sm = gs.get("sm") or []
        if a.aw_standort == GOSLAR and gs.get("sl") and bereich in ("szenario",) or (praes and a.aw_standort == GOSLAR
                                                                                    and gs.get("sl")):
            gs_box = ui.element("section").classes("m-block m-xgs" + (" kompakt" if praes else ""))

            def goslar_zeichnen():
                gs_box.clear()
                with gs_box:
                    _goslar(a, gs["sl"], gs_sm, kap_echt,
                            a.daten.get("kontingent") or an.kontingent_vorschlag(gs_sm, kap_echt), praes, hell, goslar_neu)

            def goslar_neu(werte):
                a.daten["kontingent"] = werte
                kern.kontingent_setzen(GOSLAR, werte)
                goslar_zeichnen()
                if a._prognose_chart:
                    a._prognose_chart()
            goslar_zeichnen()
        # ---- Ebene A: KPI-Karten ----------------------------------------------------------
        kpi_box = ui.element("div").classes("m-xk") if bereich == "dashboard" else None

        def kpis_zeichnen():
            if kpi_box is None:
                return ex()
            kpi_box.clear()
            e = ex()
            with kpi_box:
                for k in (e.kpis[:4] if praes else e.kpis):
                    _kpi_karte(k)
            return e
        e0 = kpis_zeichnen()
        # ---- Ebene B: Erkenntnisse – Dashboard: drei Insight-Badges; Details: alle; Präsentation: unter dem Graph ----
        er_box = ui.element("section").classes("m-xe" if praes or bereich == "details" else "m-xi")

        def erkenntnisse_zeichnen(e=None):
            e = e or ex()
            er_box.clear()
            if not praes and bereich == "dashboard":
                with er_box:
                    _insights(a, e, zustand, kap_echt)
                return
            with er_box:
                kopf = ui.element("button").classes("m-xe-kopf")
                with kopf:
                    ui.label("Erkenntnisse").classes("m-btitel")
                    ui.label("aus den Daten erzeugt – Fakt, Prognose oder Einschätzung").classes("m-zweite")
                    if not praes:
                        ui.icon("expand_less" if a.aw_summary else "expand_more").style("margin-left:auto")
                if not praes:
                    kopf.on("click", lambda: (setattr(a, "aw_summary", not a.aw_summary), erkenntnisse_zeichnen()))
                if a.aw_summary or praes or bereich == "details":
                    with ui.element("ul").classes("m-xe-liste"):
                        for art, text in (e.erkenntnisse[:4] if praes else e.erkenntnisse):
                            with ui.element("li"):
                                ui.label(art).classes(f"m-xe-tag {TAG.get(art, '')}")
                                ui.label(text)
        erkenntnisse_zeichnen(e0)
        if bereich in ("szenario", "details"):
            er_box.set_visibility(bereich == "details")

        # ---- Hauptgraph (wird bei Reiter-/Ansichtswechsel allein neu gebaut – ohne Neuladen, ohne Seitenaufbau) ----
        if sz_raster is not None:
            with sz_raster:
                graph_box = ui.element("section").classes("m-block m-xg kompakt")
        else:
            graph_box = ui.element("section").classes("m-block m-xg")
        if bereich == "details":
            graph_box.set_visibility(False)          # Details: keine Grafik – nur Tabellen und Protokoll

        def variante(mit: bool) -> dict:
            """Daten der Ansicht „Belegung“ (ohne UWTler/Mieter) bzw. „Nach Status“ (mit) – eine liegt immer vor."""
            if not a.daten.get("gruppen_da"):
                return {}
            d = a.daten if alle_bewohner(a) == mit else (a.daten.get("alt") or a.daten)
            g = d.get("gruppen")
            kont = None
            if mit and a.aw_standort == GOSLAR and d.get("sm"):
                kont = a.daten.get("kontingent") or an.kontingent_vorschlag(d["sm"], kap_echt)
            return {"pg": d["pg"], "pg_lang": d.get("pg_lang"), "sm": d.get("sm"), "sv": d.get("sv"),
                    "gruppen_text": g.text() if g else "", "kontingent": kont}

        def modi() -> dict:
            """Fertige Diagramm-Optionen aller Ansichten – der Browser schaltet damit ohne Rückfrage um (< 50 ms)."""
            anim = a.aw_anim and not a.weniger_bewegung
            ohne, mit_ = variante(False), variante(True)
            d = {"reserve": option(c(anim, art="reserve")), "jahr": option(c(anim, art="jahr")),
                 "kurve": option(c(anim, art="trend", status=False, parallel=False, **ohne))}
            if anim and not praes:
                d["kurve_start"] = option(c(True, "start", art="trend", status=False, parallel=False, **ohne))
            if mit_.get("sm"):
                d["status"] = option(c(anim, art="trend", status=True, parallel=False, **mit_))
            if a.aw_standort == konfig.GESAMT and a.daten.get("sv"):
                d["standorte"] = option(c(anim, art="trend", status=False, parallel=True))
            return d

        def modi_senden():
            if "daten" in box and not box["daten"].is_deleted:
                box["daten"]._props["data-modi"] = json.dumps(modi())
                box["daten"].update()

        async def graph_sync(e):
            """Der Browser hat umgeschaltet – Zustand nachziehen (der Graph ist schon richtig)."""
            d = (e.args or {}).get("detail") or {}
            war_mit = bool(a.aw_status)
            a.aw_chart = d.get("tab", a.aw_chart)
            a.aw_status, a.aw_parallel = d.get("ansicht") == "status", d.get("ansicht") == "standorte"
            if a.daten.get("gruppen_da") and bool(a.aw_status) != war_mit:
                a._still = True                      # Kennzahlen, Tabelle, Goslar folgen dem Personenkreis – ohne Einblenden
                await a.setzen(nur_seite=True)
            elif praes:
                graph_zeichnen(False)                # Schrittsteuerung der Präsentation hängt am Modus
            elif "chart" in box:
                box["chart"].options.clear()
                box["chart"].options.update(option(c(False)))

        def graph_wechsel(**werte):
            """Reiter, Ansicht, Backtest, 95 %-Band: Daten liegen schon vor → nur den Graph neu zeichnen."""
            neu_aufbau = any(k in werte and werte[k] != getattr(a, k) for k in ("aw_chart", "aw_status", "aw_parallel"))
            for k, v in werte.items():
                setattr(a, k, v)
            graph_zeichnen(neu_aufbau and a.aw_anim and not a.weniger_bewegung)

        def werkzeuge():
            """Aufbau abspielen und Optionen – als Symbole, rechts in der Filterleiste."""
            if not a.weniger_bewegung:
                knopf("", lambda: graph_zeichnen(True), "leise m-xg-symbol", "play_arrow",
                      "Aufbau abspielen – Graph neu aufbauen (geführte Animation)")
            if oben and not praes:                   # 0.96: Optionen stehen im Menüband
                return
            _optionen(a, pg, True, graph_wechsel)
            if not praes:
                diagramm_karte.modus_wahl(a)

        from . import menueband_ui
        oben = menueband_ui.band_sichtbar(a)

        def graph_zeichnen(animiert_: bool):
            graph_box.clear()
            box.pop("schritt", None)
            parallel = par()
            trend = a.aw_chart == "trend"
            jetzt = "standorte" if parallel else "status" if a.aw_status else "kurve"
            attr(graph_box, data_tab=a.aw_chart, data_ansicht=jetzt, data_anim="1" if a.aw_anim and not a.weniger_bewegung else "0")
            with graph_box:
                if not praes and oben:               # 0.96: Filter im Menüband – hier nur, was eingestellt ist
                    with ui.element("div").classes("m-xg-filter m-xg-stand"):
                        _stand_zeile(a, jetzt)
                        with ui.element("div").classes("m-xg-filter-rechts"):
                            werkzeuge()
                elif not praes:                      # eine Filterleiste: Standort links, Netto/Brutto und Zeitraum rechts
                    with ui.element("div").classes("m-xg-filter").props('role="toolbar" aria-label="Filter der Prognose"'):
                        segmente(ak.STANDORTE, a.aw_standort, lambda s_: a.setzen(aw_standort=s_, nur_seite=True), sofort=True)
                        with ui.element("div").classes("m-xg-filter-rechts"):
                            segmente({False: "Netto", True: "Brutto"}, a.aw_brutto,
                                     lambda b_: a.setzen(aw_brutto=b_, nur_seite=True), sofort=True)
                            segmente({12: "12M", 24: "24M"}, a.aw_horizont,        # 0.86: 36 Monate entfallen
                                     lambda h: a.setzen(aw_horizont=h, nur_seite=True), sofort=True)
                            werkzeuge()
                with ui.element("div").classes("m-xg-kopf" + (" m-weg" if km == "einfach" and not praes and not a.dg_details
                                                              else "")):
                    if not oben or praes:
                        _js_segmente(CHARTS, a.aw_chart, "tab")
                    with ui.element("div").classes("m-xg-status" + ("" if trend and (not oben or praes) else " aus")):
                        if oben and not praes:
                            pass                     # 0.96: Ansicht steht im Menüband (Diagrammentwurf → Diagramm)
                        elif klassisch:
                            attr(ui.label("Ansicht"), title="Belegung als Kurve, gestapelt nach Status (UWTler · Mieter · "
                                                            "übrige) oder – bei „Gesamt“ – die drei Standorte parallel")
                            ansichten = {"kurve": "Belegung", "status": "Nach Status"}
                            if a.aw_standort == konfig.GESAMT:
                                ansichten["standorte"] = "Standorte parallel"
                            _js_segmente(ansichten, jetzt, "ansicht")
                        else:                        # 0.87: EIN Schalter statt „Belegung / Nach Status“ + Hinweis-Chip
                            if a.daten.get("gruppen_da"):
                                _js_schalter("status", "inkl. UWTler und Mieter", "group_add", jetzt == "status",
                                             "Einschalten: Die Gesamtlinie zeigt alle Bewohner – die graue Linie bleibt bei "
                                             "den Teilnehmenden, die farbige Fläche dazwischen sind UWTler und Mieter; "
                                             "darunter beide Gruppen gegen ihre Kontingente")
                            if a.aw_standort == konfig.GESAMT:
                                _js_schalter("standorte", "Standorte einzeln", "stacked_line_chart", jetzt == "standorte",
                                             "Die drei Standorte nebeneinander statt der Summe")
                    _status_badge(a, pg, True, klassisch)
                    if praes and trend and not a.aw_status and not parallel:
                        with ui.element("div").classes("m-xg-schritte"):
                            knopf("", lambda: praes_schritt(a, -1), "leise", "chevron_left", "Schritt zurück (←)")
                            box["schritt"] = ui.label(f"{a.aw_schritt}/4 · {SCHRITTE[a.aw_schritt]}").classes("m-zweite")
                            knopf("", lambda: praes_schritt(a, 1), "leise", "chevron_right", "Nächster Schritt (→)")
                            knopf("Alles", lambda: praes_schritt(a, 4), "leise")
                    if praes:
                        with ui.element("div").style("margin-left:auto; display:flex; gap:6px; align-items:center"):
                            werkzeuge()
                story = (animiert_ and trend and not a.aw_status and not parallel and (not praes or a.aw_schritt == 4))
                if klassisch:                        # Präsentation und Darstellung „Klassisch“ (wie bis 0.86)
                    chart = ui.echart(option(c(animiert_, "start" if story else "voll"))).classes(
                        "m-chart m-xg-chart" + (" gross" if praes else ""))
                    if not praes:
                        from . import diagramm_ui

                        diagramm_ui.anbinden(a, chart, lambda i: _berechnung_monat(a, c()["pg"], zustand["kap"], i))
                        zs_k = ak.szenario(c()["pg"], zustand["kap"], 0)
                        n_k = next((i for i, z in enumerate(zs_k) if z.art == "prognose"), None)
                        if n_k is not None:
                            diagramm_ui.fx_kasten(_berechnung_monat(a, c()["pg"], zustand["kap"], n_k))
                else:                                # 0.87: Diagramm-Karte – Kopf, Knöpfe, „Auf einen Blick“, ƒx
                    pg_, kap_ = c()["pg"], zustand["kap"]
                    halter = None
                    if km == "einfach":              # 0.89: Leitungsansicht; „Details“ öffnet die Karte darunter
                        sz_ = bereich == "szenario"        # 1.59: schmale Spalte neben dem Szenario, Szenario-Kurve
                        _einfach(a, pg_, kap_, konfig.STANDORT_LABEL.get(a.aw_standort, a.aw_standort), graph_zeichnen,
                                 zustand["offset"] if sz_ else 0.0, sz_, getattr(a, "aw_zusatz", None) if sz_ else None)
                        halter = ui.element("div").classes("m-einfach-details" + (" offen" if a.dg_details else ""))
                        halter.__enter__()
                    if km == "karte":                # 0.95: drei Fragen, Antwort in Worten
                        _fragen(pg_, kap_)
                    blick, alt = blick_daten(pg_, c().get("pg_lang"), kap_, a.daten["stichtag"])
                    ort = konfig.STANDORT_LABEL.get(a.aw_standort, a.aw_standort)
                    v_ = variante(True)
                    if jetzt == "status" and v_.get("sm"):           # „inkl. UWTler und Mieter“: eigene Sätze
                        blick, alt = blick_gruppen(v_["sm"], pg_, kap_, a.daten["stichtag"], v_.get("kontingent"))
                    unter = f"{NETTO_TEXT[bool(a.aw_brutto)]} · Datenstand {a.daten['stichtag']:%d.%m.%Y}"
                    titel_je = {"trend": f"Belegung {ort}" + ((" · alle Bewohner" if alle_bewohner(a) else " · nur Teilnehmende") if a.daten.get("gruppen_da") else ""),
                                "trend-status": f"Belegung {ort} · inkl. UWTler und Mieter",
                                "trend-standorte": "Belegung je Standort", "reserve": CHARTS["reserve"],
                                "jahr": CHARTS["jahr"]}
                    karte = diagramm_karte.Karte(a, CHARTS.get(a.aw_chart, ""), unter, blick, titel_je=titel_je,
                                                 monate_alt=alt)
                    chart = karte.chart(option(c(animiert_, "start" if story else "voll")), "m-xg-chart")
                    vj_monate = an.vorjahr(c().get("pg_lang") or pg_).monate
                    zs_ = ak.szenario(pg_, kap_, 0)

                    vt_ = a.daten.get("vj_tage")

                    def details(i: int):
                        if a.aw_chart == "jahr" and vt_ is not None and vt_.tage:     # 1.22: Tag → sein Monat
                            if not 0 <= i < len(vt_.tage):
                                return []
                            m_ = vt_.tage[i].replace(day=1)
                            i = next((j for j, z in enumerate(zs_) if z.monat == m_), -1)
                        elif a.aw_chart == "jahr":               # Vorjahresvergleich: andere Monatsachse
                            if not 0 <= i < len(vj_monate):
                                return []
                            i = next((j for j, z in enumerate(zs_) if z.monat == vj_monate[i]), -1)
                        return _berechnung_monat(a, pg_, kap_, i)
                    karte.anbinden(chart, details)
                    naechster = next((i for i, z in enumerate(zs_) if z.art == "prognose"), None)
                    if naechster is not None:
                        karte.fx(_berechnung_monat(a, pg_, kap_, naechster))
                    if km == "karte":                # 0.95: Lesehilfe und Backtest als eigene „Probe“
                        _lesehilfe()
                        _probe_karte(a, pg_, kap_)
                    if halter is not None:
                        halter.__exit__(None, None, None)
                box["chart"] = chart
                if story:
                    ui.timer(2.75, lambda: _story_weiter(chart, option(c(True, "voll"))), once=True)
                schluessel = jetzt if trend else a.aw_chart
                with ui.element("div").classes("m-xg-fuss" + ("" if klassisch else " m-weg")):     # 0.87: eine Legende (oben)
                    for k, art in (("kurve", "trend"), ("status", "status"), ("standorte", "standorte"), ("reserve", "reserve"),
                                   ("jahr", "jahr")):
                        leg = ui.html(_legende_text(art, kap_echt != zustand["kap"] or bool(zustand["offset"])), sanitize=False)
                        attr(leg, data_legende=k)
                        if k != schluessel:
                            leg.style("display:none")
                box["daten"] = ui.element("div").classes("m-xg-daten").style("display:none")
                box["daten"]._props["data-modi"] = json.dumps(modi())
                melder = ui.element("div").classes("m-xg-melder").style("display:none")
                melder.on("mgraph", graph_sync, args=["detail"])

        graph_zeichnen(animiert and bereich != "details")
        a._graph_zeichnen = graph_zeichnen
        if not getattr(a, "_vorrechnen_laeuft", False):   # Standortwechsel vorbereiten (Hintergrund, einmal zur Zeit)
            async def _vor():
                a._vorrechnen_laeuft = True
                try:
                    await run.io_bound(vorrechnen, a)
                finally:
                    a._vorrechnen_laeuft = False
            background_tasks.create(_vor(), name="prognose-vorrechnen")

        def chart_neu(schritt_animation: bool = False):
            """Optionen ersetzen – ohne erneuten Aufbau; nur ein Präsentationsschritt darf weich einblenden."""
            neu = option(c(schritt_animation and a.aw_anim and not a.weniger_bewegung))
            if "schritt" in box:
                box["schritt"].set_text(f"{a.aw_schritt}/4 · {SCHRITTE[a.aw_schritt]}")
            chart = box["chart"]
            chart.options.clear()
            chart.options.update(neu)
            chart.update()
            modi_senden()                            # Szenario/Kontingent: auch die vorbereiteten Ansichten erneuern
        a._prognose_chart = chart_neu
        if sz_raster is None:
            graph_box.move(wurzel, target_index=1 if praes else 0)    # der Graph steht immer ganz oben

        if praes:
            er_box.move(wurzel)
            if gs_box is not None:
                gs_box.move(wurzel)
            if a.aw_vergleich_praes and a.daten["sv"]:
                _standortvergleich(a, hell, kompakt=True)
            return

        if bereich == "dashboard":
            return
        if bereich == "details":
            _details(a, pg, zustand, hell, wurzel, er_box)
            return
        # ---- Szenario (Simulation) -----------------------------------------------------------
        with sz_raster:
            sz_box = ui.element("section").classes("m-block m-xs")

        def alles_neu():
            if km == "einfach" and not praes:        # 1.59: Leitungsansicht – Szenario-Kurve und Zahlen neu aufbauen
                graph_zeichnen(False)
            else:
                chart_neu()
            szenario_zeichnen()

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
            extra = list(getattr(a, "aw_zusatz", None) or [])
            aktiv = kap != kap_echt or bool(off) or bool(extra)
            sz_box.clear()
            sz_box.classes(add="aktiv" if aktiv else "", remove="" if aktiv else "aktiv")
            with sz_box:
                with ui.element("div").classes("m-paktionen").style("align-items:center"):
                    ui.icon("science").classes("m-xs-icon")
                    ui.label("Management-Szenario").classes("m-btitel")
                    ui.label("Was wäre, wenn … – wirkt nur auf die Prognosemonate; Ist bleibt Ist").classes("m-zweite")
                    if aktiv:
                        ui.label("SIMULATION – keine echten Daten").classes("m-xs-banner")
                    knopf("", lambda: a.setzen(aw_bereich="dashboard", laden=False), "leise", "close",
                          "Szenarien schließen – zurück zum Dashboard (das Szenario bleibt eingestellt)").style(
                        "margin-left:auto")                  # 1.59
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
                _zusatz_planen(a, extra, alles_neu)          # 1.59: Mieter, Events, Gruppen planen
                with ui.element("div").classes("m-xs-vergleich"):
                    _sz_vergleich(pg, zustand, a.aw_horizont, extra)
                ui.label("Im Graph läuft das Szenario als transparente Schattenkurve über der echten Prognose. Nur Kapazität und "
                         "Auslastung haben eine belastbare Grundlage im Modell; andere Annahmen (z. B. Verweildauer) werden nicht "
                         "scheinbar genau simuliert. Gespeichert wird nichts.").classes("m-zweite").style("white-space:normal")
        szenario_zeichnen()
        if gs_box is not None:                                   # Goslar: Kontingente planen – unter Graph und Szenario
            gs_box.move(wurzel)


BEREICHE = {"dashboard": "Dashboard", "szenario": "Szenarien & Simulation", "details": "Details & Protokoll"}
BEREICH_SYMBOL = {"dashboard": ("gauge", "blau"), "szenario": ("options", "violett"),          # 1.00: Fluent
                  "details": ("clipboard_task_list_ltr", "teal")}


def _insights(a, e, zustand, kap_echt: int) -> None:
    """Dashboard: die drei wichtigsten Erkenntnisse als schmale Badges (ganzer Text als Tooltip), Rest unter „Details“."""
    wichtig = [x for x in e.erkenntnisse if x[0] != "Hinweis"][:3] or e.erkenntnisse[:3]
    for art, text in wichtig:
        with ui.element("div").classes("m-xi-badge") as b:
            ui.label(art).classes(f"m-xe-tag {TAG.get(art, '')}")
            ui.label(text).classes("m-xi-text")
        attr(b, title=text)
    if zustand["kap"] != kap_echt or zustand["offset"]:
        knopf("Szenario aktiv", lambda: a.setzen(aw_bereich="szenario", laden=False), "leise m-xi-szenario", "science",
              "Im Graph läuft eine Simulation – bearbeiten unter „Szenarien & Simulation“")
    rest = len(e.erkenntnisse) - len(wichtig)
    if rest > 0:
        knopf(f"+{rest}", lambda: a.setzen(aw_bereich="details", laden=False), "leise m-xi-mehr", "",
              "Alle Erkenntnisse unter „Details & Protokoll“")


def _details(a, pg, zustand, hell: bool, wurzel, er_box) -> None:
    """Details & Protokoll: aufklappbare Abschnitte – Monate im Detail offen, der Rest geschlossen."""
    with wurzel:
        with ui.element("div").classes("m-xd"):
            with ui.expansion("Monate im Detail", icon="table_rows", value=True).classes("m-xd-teil"):
                tab_box = ui.element("section").classes("m-xt")
                _tabelle(a, tab_box, pg, zustand)
            with ui.expansion("Erkenntnisse – vollständig", icon="lightbulb").classes("m-xd-teil") as ex_:
                pass
            er_box.move(ex_)
            if a.daten.get("sv"):
                with ui.expansion("Standortvergleich", icon="leaderboard").classes("m-xd-teil"):
                    _standortvergleich(a, hell)
            with ui.expansion("So wurde gerechnet & Backtest", icon="fact_check").classes("m-xd-teil"):
                _methodik(a, pg)


def _modus(a, modus: str) -> None:
    a.aw_modus = modus
    if modus == "praes":
        a.aw_schritt = 4
    a.zeichnen()


def _story_weiter(chart, neu: dict) -> None:
    """2. Teil des geführten Aufbaus: Optionen weich ersetzen (Bänder fächern auf, Spotlights erscheinen)."""
    if chart.is_deleted:
        return
    chart.options.clear()
    chart.options.update(neu)
    chart.update()


async def _abspielen(a) -> None:
    """Graph bewusst neu aufbauen (verändert keine Daten) – nur der Graph, nicht die Seite."""
    if a.aw_modus == "praes" and a.aw_chart == "trend":
        a.aw_schritt = 4
    if getattr(a, "_graph_zeichnen", None):
        a._graph_zeichnen(not a.weniger_bewegung)
    else:
        a._anim_jetzt = True
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
    if art == "standorte":
        return ("<span><i class='l ist'></i>Ist (durchgezogen)</span><span><i class='l prog'></i>Prognose (gestrichelt)</span>"
                "<span>Farbe = Standort (wie überall)</span><span><i class='l kont'></i>knapp 70 % · kritisch 85 % · voll 100 %</span>"
                "<span>Prozent = Ø belegte Plätze ÷ Kapazität – so sind unterschiedlich große Standorte vergleichbar</span>")
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
            "<span>Je Tag · Vorjahr am gleichen Wochentag · Prognose ab dem Stichtag · Lücken = keine Daten</span>")


def _js_segmente(optionen: dict, aktiv, art: str) -> None:
    """Segmented Control, das im Browser umschaltet (mGraph) – ohne Rückfrage beim Server."""
    with ui.element("div").classes("m-segm").props('role="group"'):
        for wert, text in optionen.items():
            b = ui.element("button").classes("an" if wert == aktiv else "")
            attr(b, aria_pressed=str(wert == aktiv).lower(), **{f"data_{art}": wert})
            with b:
                ui.label(str(text))
            b.on("click", js_handler=f"(e) => mGraph.wechsel(e, {json.dumps(wert) if art == 'tab' else 'null'}, "
                                     f"{json.dumps(wert) if art == 'ansicht' else 'null'})")


GRAPH_JS = """<script>
window.mSofort = (e) => {   // Filterknopf: sofort hervorheben und Inhalt weich abblenden, bis die Daten da sind
  const b = e && e.currentTarget; if (!b) return;
  b.parentElement.querySelectorAll('button').forEach(x => { x.classList.toggle('an', x === b); x.setAttribute('aria-pressed', x === b); });
  const ex = document.querySelector('.m-ex'); if (ex) ex.classList.add('m-wechselt');
};
window.mGraph = {   // Prognosegraph: Reiter und Ansichten im Browser umschalten (vorbereitete Optionen, < 50 ms)
  umwandeln(o) {
    if (Array.isArray(o)) return o.map(x => this.umwandeln(x));
    if (o && typeof o === 'object') { const r = {};
      for (const [k, v] of Object.entries(o)) { if (k[0] === ':') r[k.slice(1)] = new Function('return ' + v)(); else r[k] = this.umwandeln(v); }
      return r; }
    return o;
  },
  wechsel(ev, tab, ansicht) {
    const box = ev.currentTarget.closest('.m-xg'); if (!box) return;
    const st = box.dataset;
    tab = tab || st.tab;
    if (ansicht && tab !== 'trend') return;
    ansicht = ansicht || st.ansicht;
    if (tab === st.tab && ansicht === st.ansicht) return;
    st.tab = tab; st.ansicht = ansicht;
    const key = tab === 'trend' ? ansicht : tab;
    const roh = box.querySelector('.m-xg-daten').dataset.modi || '{}';
    if (box.__roh !== roh) { box.__roh = roh; box.__modi = JSON.parse(roh); box.__fertig = {}; }
    const modi = box.__modi, fertig = box.__fertig;
    const opt = k => fertig[k] || (fertig[k] = this.umwandeln(modi[k]));
    const el = box.querySelector('.m-xg-chart'); const comp = el && getElement(el.id.replace(/^c/, ''));
    if (comp && comp.chart) {
      clearTimeout(box.__story);
      if (key === 'kurve' && st.anim === '1' && modi.kurve_start) {
        comp.chart.setOption(opt('kurve_start'), { notMerge: true });
        box.__story = setTimeout(() => comp.chart.setOption(opt('kurve')), 2750);
      } else if (modi[key]) {
        comp.chart.setOption(opt(key), { notMerge: true });
      }
    }
    box.querySelectorAll('[data-tab]').forEach(b => { const an = b.dataset.tab === tab; b.classList.toggle('an', an); b.setAttribute('aria-pressed', an); });
    box.querySelectorAll('[data-ansicht]').forEach(b => { const an = b.dataset.ansicht === ansicht; b.classList.toggle('an', an); b.setAttribute('aria-pressed', an); });
    const sa = box.querySelector('.m-xg-status'); if (sa) sa.classList.toggle('aus', tab !== 'trend');
    box.querySelectorAll('[data-legende]').forEach(l => l.style.display = l.dataset.legende === key ? '' : 'none');
    box.querySelectorAll('[data-nur]').forEach(l => l.style.display = l.dataset.nur === key ? '' : 'none');
    const badge = box.querySelector('.m-xg-ansicht');
    if (badge && (ansicht === 'status' || ansicht === 'kurve')) { const mit = ansicht === 'status';
      badge.textContent = mit ? badge.dataset.mit : badge.dataset.ohne; badge.classList.toggle('leuchtet', mit); badge.classList.toggle('rein', !mit); }
    const m = box.querySelector('.m-xg-melder');
    if (m) m.dispatchEvent(new CustomEvent('mgraph', { detail: { tab, ansicht } }));
  },
};
</script>"""


def _js_schalter(wert: str, text: str, symbol: str, an: bool, tip: str) -> None:
    """0.87: Ein-/Aus-Schalter für eine Ansicht des Trends – schaltet im Browser um (mGraph), aus = Belegung."""
    b = ui.element("button").classes("m-xg-schalter" + (" an" if an else ""))
    attr(b, type="button", data_ansicht=wert, aria_pressed=str(an).lower(), title=tip)
    with b:
        ui.icon(symbol)
        ui.label(text)
    b.on("click", js_handler="(e) => mGraph.wechsel(e, null, e.currentTarget.classList.contains('an') ? 'kurve' : "
                             f"'{wert}')")


def _status_badge(a, pg, backtest_moeglich: bool, praes: bool = True) -> None:
    """Kompakter Status statt Checkboxen: welche Gruppen in der Kurve stecken, ob der Backtest läuft."""
    # 0.98: Das Abzeichen „Ansicht: Inklusive UWTler und Mieter“ / „Reine Teilnehmer-Sicht“ entfällt – die Ansicht
    # steht in der Filterzeile („… · inkl. UWTler und Mieter“) bzw. im Umschalter und in der Legende unter dem Diagramm.
    if a.aw_backtest and backtest_moeglich and pg.rueckblick:
        b = ui.label("Backtest an").classes("m-xg-gruppen-hinweis bt")
        attr(b, data_nur="kurve")
        if a.aw_chart != "trend" or a.aw_status or a.aw_parallel:
            b.style("display:none")


def _stand_zeile(a, jetzt: str) -> None:
    """0.96: Was gerade eingestellt ist – als ruhige Zeile; Klick öffnet die Registerkarte „Diagrammentwurf“."""
    teile = [ak.STANDORTE.get(a.aw_standort, a.aw_standort), "Brutto" if a.aw_brutto else "Netto",
             f"{a.aw_horizont} Monate", CHARTS.get(a.aw_chart, "")]
    if a.aw_chart == "trend" and jetzt == "status":
        teile.append("inkl. UWTler und Mieter")
    elif a.aw_chart == "trend" and jetzt == "standorte":
        teile.append("Standorte einzeln")
    b = ui.element("button").classes("m-xg-standzeile")
    attr(b, title="Ändern im Menüband: Diagrammentwurf → Daten, Diagramm, Darstellung")
    with b:
        ui.icon("tune")
        ui.label(" · ".join(t for t in teile if t))
        ui.label("ändern").classes("m-xg-aendern")

    async def oeffnen():
        from . import menueband_ui

        a.band_tab = "diagramm"
        a._ob_seite = a.seite
        menueband_ui.fuellen(a, erzwingen=True)
    b.on("click", oeffnen)


def _optionen(a, pg, backtest_moeglich: bool, graph_wechsel) -> None:
    """Erweiterte Optionen im Menü: Backtest, Bänder, UWTler/Mieter einbeziehen, Animation."""
    with knopf("", None, "leise m-xg-symbol m-xg-optionen", "tune", "Optionen – Backtest, 95 %-Band, Animation"):
        with ui.menu().props('dark class="m-menue m-optionen"'):
            ui.label("Graph").classes("m-menue-kopf")
            _schalter("Backtest im Graph (Blind-Prognosen)" + ("" if pg.rueckblick else " – kein Verlauf"),
                      a.aw_backtest and backtest_moeglich, lambda: graph_wechsel(aw_backtest=not a.aw_backtest),
                      aus=not (backtest_moeglich and pg.rueckblick))
            _schalter("95 %-Band zeigen", a.aw_95, lambda: graph_wechsel(aw_95=not a.aw_95))
            ui.separator()
            _schalter("Animation beim Öffnen" + (" (System: weniger Bewegung)" if a.weniger_bewegung else ""),
                      a.aw_anim and not a.weniger_bewegung, lambda: graph_wechsel(aw_anim=not a.aw_anim), aus=a.weniger_bewegung)


def _ansicht_text(uwt: bool, mieter: bool) -> str:
    if not uwt and not mieter:
        return "Ansicht: Reine Teilnehmer-Sicht"
    return "Ansicht: Inklusive " + " und ".join(n for n, an_ in (("UWTler", uwt), ("Mieter", mieter)) if an_)


def _pill(text: str, icon: str, an_: bool, klick, titel: str, aus: bool = False) -> None:
    b = ui.element("button").classes("m-xs-pill" + (" an" if an_ else "") + (" aus" if aus else ""))
    attr(b, title=titel, aria_pressed=str(an_).lower(), **({"disabled": True} if aus else {}))
    with b:
        ui.icon(icon)
        ui.label(text)
    if klick and not aus:
        b.on("click", klick)


def _goslar(a, sl: an.StatusLage, sm, kap: int, kont: dict | None, kompakt: bool, hell: bool, aendern) -> None:
    """Aufteilung Goslar: heute (UWT · Mieter · übrige · frei), Kontingente in % und Prüfung der nächsten Monate."""
    fb = an.STATUS_FARBEN[hell]
    h = sl.heute
    with ui.element("div").classes("m-paktionen").style("align-items:baseline"):
        ui.label("Goslar · UWTler, Mieter und Kontingente" + ("" if kompakt else " (Detail)")).classes("m-btitel")
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
        k0 = zeilen[0] if zeilen else None
        with ui.element("div").classes("m-xgs-tab"):
            ui.label("Monat").classes("m-zweite")
            for titel, grenze in (("UWTler gebucht", k0.k_uwt if k0 else 0), ("Mieter (Verträge)", k0.k_mieter if k0 else 0),
                                  ("Teilnehmende & Sonstige", k0.k_uebrige if k0 else 0)):
                attr(ui.label(f"{titel} · Plan {_z(grenze)}").classes("m-zweite"),
                     title="Echte Werte; „Plan“ = Kontingent aus der Aufteilung oben. Orange: ≥ 90 % des Plans, rot: darüber")
            ui.label("Gesamt · Auslastung").classes("m-zweite")
            for z in zeilen[:6]:
                ui.label(ak.monat_text(z.monat) + (" · laufend" if z.art == "laufend" else "")).classes("m-name")
                for wert, schl in ((z.uwt, "UWT"), (z.mieter, "Mieter"), (z.uebrige, "uebrige")):
                    ui.label(_z(wert)).classes("m-mono" + st[z.stufe[schl]])
                summe = z.uwt + z.mieter + z.uebrige
                ui.label(f"{_z(summe)} · {an._p(summe / kap)}").classes("m-mono")
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
        if k.hinweis:                                  # Erklärung sichtbar – nicht nur beim Darüberfahren
            ui.label(k.hinweis).classes("m-xk-hinweis")


def _zusatz_planen(a, extra: list, neu) -> None:
    """1.59: Zusätzliche Belegungen im Szenario – z. B. 5 Mieter ab Januar für 12 Monate, eine Tagung mit 20 Plätzen im
    Mai. Wirken additiv auf die Prognosemonate (Anteil der Tage je Monat); gespeichert wird nichts."""
    from . import szenario_zusatz as sz

    ui.label("Zusätzliche Belegung planen").classes("m-name").style("margin-top:10px")
    for i, z in enumerate(extra):
        with ui.element("div").classes("m-paktionen").style("align-items:center;gap:6px"):
            ui.icon("add_circle_outline").style("color:var(--akzent)")
            ui.label(z.text).classes("m-ptext")

            def weg(i=i):
                liste = list(getattr(a, "aw_zusatz", None) or [])
                liste.pop(i)
                a.aw_zusatz = liste
                neu()
            knopf("", weg, "leise", "close", "Diese Planung entfernen")
    with ui.element("div").classes("m-xs-zusatz"):
        art = ui.select(sz.ARTEN, value="mieter", label="Was").classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"').style("width:150px")
        name = ui.input("Bezeichnung (optional)").classes("m-feld").props("dense outlined dark").style("width:170px")
        n = ui.number("Plätze", value=5, min=1, max=2000, step=1, format="%d").classes("m-feld").props(
            "dense outlined dark").style("width:90px")
        naechster = (a.heute.replace(year=a.heute.year + 1, month=1, day=1) if a.heute.month == 12 else
                     a.heute.replace(month=a.heute.month + 1, day=1))
        von = ui.input("ab", value=naechster.isoformat()).classes(
            "m-feld").props("dense outlined dark type=date").style("width:150px")
        dauer = ui.number("Monate", value=12, min=0, max=60, step=1, format="%d").classes("m-feld").props(
            "dense outlined dark").style("width:90px")

        def dazu():
            from datetime import date as _d

            try:
                z = sz.neu(art.value, name.value or "", n.value, _d.fromisoformat(von.value), int(dauer.value or 0))
            except (ValueError, TypeError) as exc:
                a.toast(str(exc) if str(exc) else "Bitte ein gültiges Datum eintragen.", fehler=True)
                return
            a.aw_zusatz = list(getattr(a, "aw_zusatz", None) or []) + [z]
            neu()
        knopf("Hinzufügen", dazu, "", "add", "Zur Simulation hinzufügen – Graph und Vergleich rechnen sofort neu")
    ui.label("Beispiele: 5 Mieter ab Januar für 12 Monate · Tagung mit 20 Plätzen für 1 Monat · Gruppe 15 Plätze "
             "3 Monate. Zählt zusätzlich zur Prognose, je Monat anteilig nach Tagen.").classes("m-zweite").style(
        "white-space:normal")


def _sz_vergleich(pg, zustand, horizont, extra: list | None = None) -> None:
    zeilen = an.szenario_vergleich(pg, zustand["kap"], zustand["offset"], horizont, extra)
    with ui.element("div").classes("m-xs-tab"):
        for t in ("", "Ausgang (echt)", "Szenario"):
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
                        b.on("click", lambda v=v: a.setzen(aw_standort=v.standort, nur_seite=True))
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
        for i, z in enumerate(zs):
            with ui.element("div").classes("m-raster m-zeile" + (" m-fortgeschrieben" if i >= 12 else "")).style(
                    f"grid-template-columns:{sp}"):
                for s in spalten:
                    if s == "monat":
                        m_ = ui.label(ak.monat_text(z.monat) + (" · laufend" if z.art == "laufend" else "")
                                      + (" · fortgeschrieben" if i >= 12 else "")).classes("m-name")
                        if i >= 12:
                            attr(m_, title="Der Backtest prüft nur bis 12 Monate – dieser Monat ist rechnerisch fortgeschrieben.")
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
            segmente(ak.STANDORTE, a.aw_standort, lambda s: a.setzen(aw_standort=s, nur_seite=True))
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
        except PermissionError as exc:
            from .export_ziel import meldung

            a.toast(meldung(exc), fehler=True)   # 1.63
            return
        a.toast(("Excel" if art == "xlsx" else "CSV") + " gespeichert" if seiten._datei_oeffnen(pfad) else f"Gespeichert: {pfad}",
                rueck=False)

    def summary():
        html = an.summary_html(ex(), pg, a.aw_standort, a.aw_brutto, zustand["kap"], zustand["offset"], a.daten["sv"],
                               a.aw_horizont)
        seiten.html_drucken(a, html, f"Executive_Summary_{konfig.STANDORT_LABEL.get(a.aw_standort, a.aw_standort)}")

    def inhalt():
        with ui.menu().props('dark class="m-menue"'):
            ui.menu_item("Diagramm als PNG (hochauflösend)", png)
            ui.menu_item("Executive Summary – Druck / PDF", summary)
            ui.separator()
            ui.menu_item("Prognosedaten als Excel (.xlsx)", lambda: daten_("xlsx"))
            ui.menu_item("Prognosedaten als CSV", lambda: daten_("csv"))

    from . import menueband_ui

    if menueband_ui.werkzeuge_oben(a):              # 1.00: im Menüband – Excel-Tabelle mit Pfeil
        from . import band_ui as bu

        with bu.gross("Export", "table_arrow_up", "gruen", pfeil=True, tipp="Diagramm als Bild, Summary, Excel, CSV"):
            inhalt()
        return
    with knopf("Export", None, "", "ios_share"):
        inhalt()


def praes_umschalten(a) -> None:
    if a.aw_modus == "praes":
        praes_beenden(a)
    else:
        _modus(a, "praes")
