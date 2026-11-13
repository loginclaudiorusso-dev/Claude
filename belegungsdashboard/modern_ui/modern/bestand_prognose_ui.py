"""Bestandsprognose der Maßnahmen (0.79) – zwei Sichten auf dieselbe Rechnung:

* **Planung (für die Kollegen):** eine klare Ansage je Maßnahmeart – „Plane mit X · davon Y sicher“ – ohne Spannen.
* **Leitung (für die Geschäftsführung):** Verlauf mit 80 %-Spanne, drei Szenarien mit Auslöser, Frühindikator,
  Zerlegung nach Herkunft, Treffsicherheit im Rückblick und **Wenn-dann**: Klick auf einen künftigen Monat →
  „Wenn wir dann X haben – wie geht es weiter?“."""

from __future__ import annotations

import json

from nicegui import run, ui

from . import bestand_kern as bk
from . import bestand_prognose as bp
from . import massnahmen_kern as mk
from .arbeitsflaeche import mehrzahl
from .ui_bausteine import attr, badge, knopf, leer, segmente

MON = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
SPALTEN = (0, 3, 6, 12)


def _m(d) -> str:
    return f"{MON[d.month - 1]} {d.year}"


def _z(x, nk: int = 0) -> str:
    return "–" if x is None else f"{x:,.{nk}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _p(x) -> str:
    return "–" if x is None else f"{round(100 * x)} %"


def daten(a) -> dict:
    from . import bestand_ui

    roh = mk._roh()
    aufenthalte, meta = bk.laden(roh)
    if not aufenthalte:
        return {"leer": True}
    gemessen = bk.anmeldedauern(bestand_ui.eintraege(getattr(a, "stand", None)))
    szen = bp.szenarien_lesen(roh)
    erg = bp.alles(aufenthalte, meta, bk.tabelle(roh), gemessen, szen, a.heute)
    return {"leer": False, "erg": erg, "szen": szen}


def zeichnen(a, d: dict) -> None:
    if d.get("leer"):
        with a.inhalt:
            leer("Für die Bestandsprognose den Maßnahmen-Pivot einmal neu einlesen (Daten & Import → Maßnahmen-Prognose).")
            knopf("Zu Daten & Import", lambda: a.oeffnen("daten"), "", "upload_file")
        return
    erg = d["erg"]
    md: bp.Modell = erg["modell"]
    sicht = getattr(a, "mn_sicht", "planung")
    art = getattr(a, "mn_art", "Alle")
    if art not in md.arten:
        art = "Alle"
    fluss = getattr(a, "mn_fluss", "bestand")
    if fluss not in bp.FLUSS_TEXT:
        fluss = "bestand"
    from .ui_bausteine import im_band

    with a.werkzeuge:
        segmente({"planung": "Planung", "leitung": "Leitung"}, sicht, lambda v: a.setzen(mn_sicht=v, laden=False))
        segmente({"bestand": "Teilnehmende", "zu": "nur Zugänge", "ab": "nur Abgänge"}, fluss,     # 1.06
                 lambda v: a.setzen(mn_fluss=v, laden=False))
        band = im_band()
        if band:
            _art_band(a, md, art)
        else:
            ui.select({"Alle": "Alle Maßnahmen", **{x: bp.kurzname(x) for x in md.arten}}, value=art,
                      on_change=lambda e: a.setzen(mn_art=e.value, laden=False)).props(
                'dense outlined dark options-dense popup-content-class="m-popup"').style("width:230px")
    with a.leiste:
        if band:
            from . import band_ui, symbole
            from . import seite_massnahmen as sm

            with band_ui.gruppe("Bearbeiten"):
                if sicht == "leitung":
                    band_ui.gross("Szenarien", "options", symbole.VIOLETT, lambda: _szenarien_panel(a, d["szen"]),
                                  tipp="Szenarien: wirtschaftlich schwach / normal / gut – mit Auslöser")
                band_ui.gross("Maßnahmen aufräumen", "delete", symbole.ROT, lambda: sm.aufraeumen_panel(a),
                              tipp="Veraltete Maßnahmen aus allen Prognosen nehmen (wiederherstellbar)")
            with ui.element("div").classes("m-bg-rechts"):
                with band_ui.gruppe("Andere Sicht"):
                    band_ui.gross("Belegung des Internats", "building_home", symbole.BLAU,
                                  lambda: a.oeffnen("auswertung", ansicht="prognose"),
                                  tipp="Wechselt zur Belegungsprognose: Betten je Standort – die zweite Sicht auf "
                                       "dieselbe Zukunft")
        else:
            if sicht == "leitung":
                knopf("Szenarien …", lambda: _szenarien_panel(a, d["szen"]), "", "tune")
            knopf("Belegung des Internats", lambda: a.oeffnen("auswertung", ansicht="prognose"), "leise", "hotel",
                  "Belegungsprognose: Betten je Standort (Zeitreihe) – die zweite Sicht auf dieselbe Zukunft")
    a.status_info = (f"Stichtag {erg['letzter']:%d.%m.%Y} · {len(md.faelle)} Aufenthalte · {bp.DURCHLAEUFE} "
                     "durchgerechnete Verläufe")
    with a.inhalt, ui.element("div").classes("m-rv m-bst"):
        if fluss != "bestand":
            _fluss_ansicht(a, d, art, fluss, sicht == "leitung")
        else:
            (_planung if sicht == "planung" else _leitung)(a, d, art)


def _art_band(a, md, art: str) -> None:
    """1.06: Maßnahme-Wahl im Menüband – großer Knopf mit Kurznamen, Menü mit allen Arten."""
    from . import band_ui, symbole

    with band_ui.gruppe("Maßnahme"):
        k = band_ui.gross("Alle" if art == "Alle" else bp.kurzname(art), "people_team", symbole.TEAL, pfeil=True,
                          tipp="Welche Maßnahme gezeigt wird")
        with k, ui.menu().props('anchor="bottom left" self="top left"').classes("m-mn-menue"):
            with ui.element("div").classes("m-mn-liste"):
                for wert, text in [("Alle", "Alle Maßnahmen")] + [(x, bp.kurzname(x)) for x in md.arten]:
                    z = ui.element("button").classes("m-mn-zeile m-mn-wahl" + (" an" if wert == art else ""))
                    with z:
                        ui.element("span").classes("m-bg-punkt")
                        ui.label(text).classes("m-mn-name")
                    z.on("click", lambda w=wert: a.setzen(mn_art=w, laden=False))


def _fluss_ansicht(a, d, art: str, richtung: str, leitung: bool) -> None:
    """1.06: nur Zugänge bzw. nur Abgänge – je Monat, mit Spanne (Leitung) bzw. als klare Zahlen (Planung)."""
    from . import seite_auswertung as sa

    erg = d["erg"]
    e: bp.Ergebnis = erg["szenarien"]["basis"]
    a_ = None if art in (None, "", "Alle") else art
    name = "Alle Maßnahmen" if a_ is None else bp.kurzname(art)
    zu = richtung == "zu"
    wort = "Zugänge" if zu else "Abgänge"
    ist = bp.ist_fluss(erg["faelle"], erg["letzter"], a_, richtung, 12)
    ist12 = sum(n for _d, n in ist if n)
    s3, s6, s12 = (bp.fluss_summe(e, a_, richtung, 1, n) for n in (3, 6, 12))
    ui.label(f"{name}: in den nächsten 6 Monaten etwa {_z(s6[0])} {wort}"
             + (f" (sehr wahrscheinlich {_z(s6[1])} bis {_z(s6[2])})" if leitung else "")).classes("m-bp-titel")
    with ui.element("div").classes("m-bp-kacheln"):
        for titel, (med, lo, hi, bek), bezug in (("Nächste 3 Monate", s3, ""), ("Nächste 6 Monate", s6, ""),
                                                  ("Nächste 12 Monate", s12, f"letzte 12 Monate: {_z(ist12)}")):
            teile = [bezug] if bezug else []
            if leitung:
                teile.insert(0, f"sehr wahrscheinlich {_z(lo)} bis {_z(hi)}")
            if zu and bek >= .5:
                teile.append(f"davon {_z(bek)} schon fest angemeldet")
            _kpi(f"{wort} · {titel}", _z(med), " · ".join(teile))
    f = bp.fluss(e, a_, richtung)
    M = 12
    with ui.element("section").classes("m-block"):
        ui.label(f"{wort} je Monat – links Ist, rechts erwartet").classes("m-btitel")
        t = sa._T()
        x = [_m(dd) for dd, _n in ist] + [_m(m) for m in e.monate[1:M + 1]]
        n_ist = len(ist)
        hist = [n for _d, n in ist] + [None] * M
        prog = [None] * n_ist + [round(float(v), 1) for v in f.median[1:M + 1]]
        lo = [None] * n_ist + [round(float(v), 1) for v in f.p10[1:M + 1]]
        br = [None] * n_ist + [round(float(h - l_), 1) for h, l_ in zip(f.p90[1:M + 1], f.p10[1:M + 1])]
        reihen = [{"name": "Ist", "type": "bar", "data": hist, "barMaxWidth": 26, "stack": "w",
                   "itemStyle": {"color": t["akzent"], "borderRadius": [3, 3, 0, 0]},
                   "label": {"show": True, "position": "top", "fontSize": 12}},
                  {"name": "erwartet", "type": "bar", "data": prog, "barMaxWidth": 26, "stack": "w",
                   "itemStyle": {"color": t["akzent"], "opacity": .45, "borderColor": t["akzent"], "borderWidth": 1.5,
                                 "borderType": "dashed", "borderRadius": [3, 3, 0, 0]},
                   "label": {"show": True, "position": "top", "fontSize": 12, ":formatter": "(p) => Math.round(p.value)"}}]
        if leitung:
            reihen += [{"name": "_lo", "type": "line", "data": lo, "stack": "b", "symbol": "none", "silent": True,
                        "lineStyle": {"opacity": 0}, "tooltip": {"show": False}},
                       {"name": "sehr wahrscheinlich (8 von 10)", "type": "line", "data": br, "stack": "b",
                        "symbol": "none", "silent": True, "lineStyle": {"opacity": 0},
                        "color": t["akzent"], "itemStyle": {"color": t["akzent"], "opacity": .35},
                        "areaStyle": {"color": t["akzent"], "opacity": .16}}]
        opt = {"animation": False, "grid": {"left": 44, "right": 20, "top": 40, "bottom": 30},
               "legend": {"top": 0, "data": ["Ist", "erwartet"] + ([{"name": "sehr wahrscheinlich (8 von 10)",
                                                                       "icon": "roundRect"}] if leitung else [])},
               "tooltip": {"trigger": "axis"},
               "xAxis": {"type": "category", "data": x, "axisLabel": {"fontSize": 13}},
               "yAxis": {"type": "value", "minInterval": 1, "axisLabel": {"fontSize": 13}},
               "series": reihen}
        if n_ist:
            opt["series"][0]["markLine"] = {"symbol": "none", "silent": True, "lineStyle": {"color": t["text2"],
                                                                                           "type": "solid", "width": 1.5},
                                            "label": {"formatter": "Heute", "position": "end"},
                                            "data": [{"xAxis": n_ist - .5}]}
        ui.echart(opt, renderer="svg").classes("m-chart m-dg m-bp-chart")
        ui.label(("Zugang = Eintritt in eine Maßnahme dieser Art (auch aus Assessment/Vorbereitung). " if zu else
                  "Abgang = letzter Tag in der Maßnahme – regulär oder vorzeitig. ") +
                 "Je Zeitraum zwischen zwei Monatsmitten (15.), wie beim Bestand. Erwartet = der mittlere von "
                 f"{bp.DURCHLAEUFE} durchgerechneten Verläufen" + ("; das Band zeigt, wo der Wert in 8 von 10 Fällen "
                                                                  "liegt." if leitung else ".")).classes(
            "m-zweite").style("white-space:normal")
    if not leitung:
        with ui.element("section").classes("m-block"):
            ui.label(f"{wort} je Maßnahmeart").classes("m-btitel")
            sp = "minmax(200px,1.6fr) " + " ".join(["minmax(120px,1fr)"] * 3)
            with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
                for k_ in ("Maßnahmeart", "nächste 3 Monate", "nächste 6 Monate", "nächste 12 Monate"):
                    ui.label(k_)
            for zeile_art in e.arten + ["Alle"]:
                werte = [bp.fluss_summe(e, None if zeile_art == "Alle" else zeile_art, richtung, 1, n) for n in (3, 6, 12)]
                if zeile_art != "Alle" and werte[-1][0] < .5:
                    continue
                with ui.element("div").classes("m-raster m-zeile" + (" m-bp-summe" if zeile_art == "Alle" else "")).style(
                        f"grid-template-columns:{sp}"):
                    ui.label("Alle Maßnahmen" if zeile_art == "Alle" else bp.kurzname(zeile_art)).classes("m-name")
                    for med, _lo, _hi, bek in werte:
                        with ui.element("div").classes("m-bp-zelle"):
                            ui.label(_z(med)).classes("m-name")
                            if zu and bek >= .5:
                                ui.label(f"{_z(bek)} fest angemeldet").classes("m-zweite")


# ---- Planung: klare Ansage -------------------------------------------------------------------------------------------

def _planung(a, d, art: str) -> None:
    e: bp.Ergebnis = d["erg"]["szenarien"]["basis"]
    z = e.zeile(art)
    k = 6
    plan = round(e.median[z, k])
    sicher = round(e.zerlegung[0, z, k] + e.zerlegung[1, z, k])
    with ui.element("section").classes("m-block m-bp-ansage"):
        ui.label(f"{'Alle Maßnahmen' if art == 'Alle' else bp.kurzname(art)} · {_m(e.monate[k])}").classes("m-zweite")
        with ui.element("div").classes("m-bp-satz"):
            ui.html(f"Plane mit <b>{plan}</b> Teilnehmenden – <b>{sicher}</b> davon sind schon da oder angemeldet, "
                    f"mit <b>{max(0, plan - sicher)}</b> weiteren rechnen wir.", sanitize=False)
        ui.label("„Bekannt“ = schon in der Maßnahme oder fest angemeldet – bis zum geplanten Ende, erwartete vorzeitige "
                 "Abgänge sind schon abgezogen. Für Zimmer lieber mit dem oberen Wert der Spanne planen (Leitungssicht): "
                 "ein fehlendes Bett ist teurer als ein leeres.").classes("m-zweite").style("white-space:normal")
    with ui.element("section").classes("m-block"):
        ui.label("Planwerte je Maßnahmeart").classes("m-btitel")
        sp = "minmax(200px,1.6fr) " + " ".join(["minmax(120px,1fr)"] * len(SPALTEN)) + " minmax(160px,1.2fr)"
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            ui.label("Maßnahmeart")
            for s in SPALTEN:
                ui.label("heute" if s == 0 else f"{_m(e.monate[s])}")
            ui.label("Hinweis")
        for zeile_art in e.arten + ["Alle"]:
            zi = e.zeile(zeile_art)
            if zeile_art != "Alle" and e.median[zi].max() < .5:
                continue
            klasse = " m-bp-summe" if zeile_art == "Alle" else ""
            with ui.element("div").classes("m-raster m-zeile" + klasse).style(f"grid-template-columns:{sp}"):
                ui.label("Alle Maßnahmen" if zeile_art == "Alle" else bp.kurzname(zeile_art)).classes("m-name")
                for s in SPALTEN:
                    p = round(e.median[zi, s])
                    si = round(e.zerlegung[0, zi, s] + e.zerlegung[1, zi, s])
                    with ui.element("div").classes("m-bp-zelle"):
                        ui.label(str(p)).classes("m-name")
                        if s:
                            ui.label(f"{si} bekannt").classes("m-zweite")
                hinweis = ""
                if zeile_art in d["erg"]["szenarien"]["basis"].ueber_kapazitaet and \
                        d["erg"]["szenarien"]["basis"].ueber_kapazitaet[zeile_art] >= .5:
                    n = round(d["erg"]["szenarien"]["basis"].ueber_kapazitaet[zeile_art])
                    hinweis = f"Kurse voll ({d['erg']['modell'].kappe[zeile_art]} Plätze) – ca. {n} Anfragen mehr als Plätze"
                ui.label(hinweis).classes("m-zweite m-warn" if hinweis else "m-zweite")
        ui.label("Planwert = der mittlere von 1000 durchgerechneten Verläufen (Szenario „normal“). Die Spanne sieht die "
                 "Leitung.").classes("m-zweite").style("white-space:normal")
    from . import diagramm_ui

    diagramm_ui.fx_kasten([("planwert", {}, []), ("sicher", {}, [])])
    _fx_knopf()


# ---- Leitung: Spektrum, Szenarien, Wenn-dann ------------------------------------------------------------------------

def _leitung(a, d, art: str) -> None:
    """0.94: Aussage als Überschrift, drei Frage-Kacheln, gruppengerechte Kennzahlen, Diagramm für Laien."""
    erg = d["erg"]
    e: bp.Ergebnis = erg["szenarien"]["basis"]
    sicht = bp.leitungssicht(erg, art)
    _ampel(erg, d["szen"])
    for h in sicht.hinweise:
        with ui.element("div").classes("m-bp-hinweis"):
            ui.icon("info_outline")
            ui.label(h)
            if "keiner Maßnahme zugeordnet" in h:
                knopf("Zur Zuordnung", lambda: a.setzen(mn_ansicht="bestand", nur_seite=True), "leise")
    ui.label(sicht.titel).classes("m-bp-titel")
    with ui.element("div").classes("m-bp-kacheln"):
        for k in sicht.kacheln:
            with ui.element("div").classes("m-bp-kachel"):
                ui.label(k.frage).classes("m-zweite")
                with ui.element("div").classes("m-bp-antwort"):
                    ui.icon(k.symbol)
                    ui.label(k.antwort)
                ui.label(k.zeile).classes("m-zweite")
        for titel, wert, bezug in sicht.weitere:
            _kpi(titel, wert, bezug)
    szen_an = bool(getattr(a, "bp_szenarien", False))
    with ui.element("section").classes("m-block"):
        with ui.element("div").classes("m-zeile-flex"):
            ui.label("Verlauf und Prognose" + (" – Säulen, weil es wenige sind" if sicht.klein else "")).classes("m-btitel")
            knopf("Szenarien ausblenden" if szen_an else "Szenarien zeigen",
                  lambda: a.setzen(bp_szenarien=not szen_an, laden=False), "leise", "tune").style("margin-left:auto")
        opt, szen_text = _verlauf_option(erg, d["szen"], art, sicht, szen_an)
        chart = ui.echart(opt, renderer="svg").classes("m-chart m-dg m-bp-chart")
        chart.on("m_achse", lambda ev: _wenn_dann_panel(a, erg, art, ev.args), ["index"])
        if szen_an and szen_text:
            ui.label(szen_text).classes("m-zweite")
        with ui.element("div").classes("m-bp-lesehilfe"):
            if sicht.klein:
                ui.label("So lesen: Die Säulen links von „Heute“ zeigen, wie viele da waren (je am 15. des Monats). Die "
                         "farbigen Säulen rechts sind der erwartete Wert.").classes("m-zweite")
                ui.label("Der senkrechte Strich heißt „sehr wahrscheinlich“: In 8 von 10 Fällen liegt der Wert zwischen "
                         "seinem unteren und oberen Ende.").classes("m-zweite")
                ui.label("Der Strich wird länger: je weiter in der Zukunft, desto unsicerer. Klick auf einen künftigen "
                         "Monat: „Wenn wir dann X Teilnehmende haben – wie geht es weiter?“").classes("m-zweite")
            else:
                ui.label("So lesen: Die durchgezogene Linie ist, was war – bis „Heute“. Die gestrichelte Linie ist der "
                         "erwartete Wert.").classes("m-zweite")
                ui.label("Das dunkle Band heißt „sehr wahrscheinlich“ (in 8 von 10 Fällen liegt der Wert darin), das helle "
                         "„fast sicher“ (19 von 20).").classes("m-zweite")
                ui.label("Das Band wird breiter: je weiter in der Zukunft, desto unsicherer. Klick auf einen künftigen "
                         "Monat: „Wenn wir dann X Teilnehmende haben – wie geht es weiter?“").classes("m-zweite")
    with ui.element("section").classes("m-block"):
        ui.label("Woher die Teilnehmenden kommen (Mittel der Verläufe)").classes("m-btitel")
        ui.echart(_zerlegung_option(e, art)).classes("m-chart")
    with ui.element("div").classes("m-bst-raster"):
        _abgaenge(erg["modell"])
        _rueckblick((erg.get("rueckblick_je") or {}).get(art if art not in (None, "", "Alle") else "Alle")
                    or erg["rueckblick"])
    _diagnose(erg, art)
    from . import diagramm_ui

    diagramm_ui.fx_kasten([("planwert", {}, []), ("sicher", {}, []), ("abgangsquote", {}, []),
                           ("uebergangsquote", {}, []), ("rueckblick", {}, [])])
    _fx_knopf()


def _diagnose(erg, art: str) -> None:
    """0.94: Datenprüfung je Maßnahme – warum die Ist-Linie leer ist oder springt (Zahlen, keine Namen)."""
    dg = (erg.get("diagnose") or {}).get(art)
    if dg is None:
        return
    with ui.element("details").classes("m-block m-bp-diagnose"):
        ui.element("summary").classes("m-btitel").props('innerHTML="Datenprüfung für diese Maßnahme"')
        for t, w in (("Aufenthalte insgesamt", dg.faelle), ("davon vor dem Stichtag eingetreten", dg.vor_stichtag),
                     ("frühester Eintritt", f"{dg.erster:%m.%Y}" if dg.erster else "–"),
                     ("typische Dauer (Tage)", dg.dauer_median if dg.dauer_median is not None else "–"),
                     ("beendet, ohne einen 15. zu berühren (zählen im Ist nicht)", dg.am_15_verfehlt),
                     ("ohne Tageswerte (nur Halbjahr, fallen heraus)", dg.halbjahr)):
            with ui.element("div").classes("m-zeile-flex"):
                ui.label(t).classes("m-zweite")
                ui.label(str(w)).classes("m-name").style("margin-left:auto")


def _fx_knopf() -> None:
    b = ui.element("button").classes("m-dg-knopf")
    with b:
        ui.html("<b>ƒx</b> Berechnung", sanitize=False)
    b.on("click", js_handler="(e) => { const k = e.target.closest('button'); const f = k.parentElement.querySelector(':scope > .m-fx');"
                             " if (f) k.classList.toggle('an', f.classList.toggle('offen')); }")


def _kpi(titel: str, wert: str, unter: str) -> None:
    with ui.element("div").classes("m-bp-kpi"):
        ui.label(titel).classes("m-zweite")
        ui.label(wert).classes("m-bp-wert")
        ui.label(unter).classes("m-zweite")


def _ampel(erg, szen) -> None:
    sz, r, jetzt, vorher = erg["frueh"]
    farbe = {"schwach": "pruefen", "basis": "frei", "stark": "belegt"}[sz]
    with ui.element("div").classes("m-bst-abnahme"):
        badge(farbe, f"Frühindikator: spricht für „{bp.SZENARIO_NAMEN[sz]}“")
        text = (f"Assessment-Eintritte der letzten 90 Tage: {jetzt} – im Vorjahr im selben Zeitraum {vorher}"
                + (f" ({'+' if r >= 1 else '−'}{abs(round(100 * (r - 1)))} %)." if r is not None else "."))
        if r is not None and not bp.ueber_zufall(jetzt, vorher) and abs(r - 1) > .1:
            text += (f" Der Unterschied liegt noch im Rahmen des Zufalls (erst ab ±{round(2 * (jetzt + vorher) ** .5)} "
                     "Eintritten auffällig).")
        if szen[sz].get("ausloeser"):
            text += f" Auslöser laut Szenario: {szen[sz]['ausloeser']}"
        ui.label(text).classes("m-zweite").style("white-space:normal")


def _achse(erg, art: str, monate: int = 12):
    """0.94: Ist (15. der Vormonate, Lücke vor Datenbeginn) + „Heute“ (Stichtag, = Startwert der Prognose) + 12 Monate.
    Index von „Heute“ = n_ist − 1 – so bleibt die Zuordnung für Wenn-dann (k = Index − (n_ist − 1))."""
    a_ = None if art in (None, "", "Alle") else art
    ist = bp.ist_verlauf(erg["faelle"], erg["letzter"], a_)
    ist = ist + [(erg["letzter"], bp.bestand_heute(erg["faelle"], erg["letzter"], a_))]
    e = erg["szenarien"]["basis"]
    kat = [_m(d) for d, _n in ist[:-1]] + ["Heute"] + [_m(d) for d in e.monate[1:monate + 1]]
    return ist, kat, len(ist)


def _gross(x) -> int:
    return int(round(float(x)))


def _verlauf_option(erg, szen, art: str, sicht=None, szen_an: bool = False) -> tuple[dict, str]:
    """Linie mit zwei Bändern (große Maßnahmen, Alle) bzw. Säulen mit Fehlerbalken (unter 10). Keine Glättung, y ab 0,
    nur ganze Zahlen, „Heute“ trennt „so war es“ von „so wird es voraussichtlich“."""
    from . import seite_auswertung as sa

    t = sa._T()
    sicht = sicht or bp.leitungssicht(erg, art)
    M = sicht.monate
    ist, kat, n_ist = _achse(erg, art, M)
    h = n_ist - 1                                      # Index „Heute“
    e = erg["szenarien"]["basis"]
    a_ = None if art in (None, "", "Alle") else art
    z = e.zeile(a_)
    plan = [_gross(x) for x in e.median[z, :M + 1]]
    lo, hi = [_gross(x) for x in e.p10[z, :M + 1]], [_gross(x) for x in e.p90[z, :M + 1]]
    lo95 = [_gross(x) for x in (e.p025 if e.p025 is not None else e.p10)[z, :M + 1]]
    hi95 = [_gross(x) for x in (e.p975 if e.p975 is not None else e.p90)[z, :M + 1]]
    leer_ = [None] * h
    ist_w = [n for _d, n in ist] + [None] * M
    reihen: list[dict] = []
    schrift = {"fontSize": 13, "color": t["text"]}
    fx = lambda xs: leer_ + xs                         # noqa: E731 – Prognose ab „Heute“
    if sicht.klein:
        reihen.append({"name": "so war es", "type": "bar", "data": [v if i <= h else None for i, v in enumerate(ist_w)],
                       "itemStyle": {"color": t["text"]}, "barMaxWidth": 22, "barGap": "-100%",
                       "label": {"show": True, "position": "top", **schrift}})
        reihen.append({"name": "erwartet", "type": "bar", "data": fx([None] + plan[1:]),
                       "itemStyle": {"color": t["akzent"], "opacity": .6}, "barMaxWidth": 22,
                       "label": {"show": True, "position": "insideBottom", "distance": 4, **schrift, "fontWeight": 600}})
        balken = [[h + i, lo[i], hi[i]] for i in range(1, M + 1)]
        reihen.append({"name": "sehr wahrscheinlich (8 von 10)", "type": "custom", "data": balken,
                       "itemStyle": {"color": t["text"]}, "z": 5, "tooltip": {"show": False},
                       ":renderItem": "(p, api) => { const x = api.value(0), a = api.coord([x, api.value(1)]),"
                                      " b = api.coord([x, api.value(2)]), w = 7; const st = {stroke: api.visual('color'),"
                                      " lineWidth: 1.6}; return {type: 'group', children: ["
                                      "{type: 'line', shape: {x1: a[0], y1: a[1], x2: b[0], y2: b[1]}, style: st},"
                                      "{type: 'line', shape: {x1: a[0] - w, y1: a[1], x2: a[0] + w, y2: a[1]}, style: st},"
                                      "{type: 'line', shape: {x1: b[0] - w, y1: b[1], x2: b[0] + w, y2: b[1]}, style: st}]}; }"})
    else:
        from . import diagramm_stil as _ds
        band = lambda name, u, o, r_: [                                     # noqa: E731   0.96: zentral, mit Kante
            _ds.band_reihe({"name": f"_{name}", "type": "line", "data": fx(u), "stack": name, "smooth": False,
                            "tooltip": {"show": False}, "silent": True}, t, r_),
            _ds.band_reihe({"name": name, "type": "line", "data": fx([b_ - a_x for a_x, b_ in zip(u, o)]), "stack": name,
                            "smooth": False, "areaStyle": {}, "silent": True}, t, r_)]
        reihen += band("fast sicher (19 von 20)", lo95, hi95, "band95")
        reihen += band("sehr wahrscheinlich (8 von 10)", lo, hi, "band")
        reihen.append({"name": "so war es", "type": "line", "data": [v if i <= h else None for i, v in enumerate(ist_w)],
                       "smooth": False, "symbol": "none", "lineStyle": {"color": t["text"], "width": 3},
                       "itemStyle": {"color": t["text"]}, "connectNulls": False})
        reihen.append({"name": "erwartet", "type": "line", "data": fx(plan), "smooth": False, "symbol": "none",
                       "lineStyle": {"color": t["akzent"], "width": 3, "type": "dashed"}, "itemStyle": {"color": t["akzent"]}})
        # höchstens vier Beschriftungen: heute, höchster und tiefster Planwert, letzter Monat
        idx = {0, max(range(1, M + 1), key=lambda i: plan[i]), min(range(1, M + 1), key=lambda i: plan[i])}
        marken = [{"coord": [kat[h + i], plan[i]], "value": plan[i], "symbol": "circle", "symbolSize": 7,
                   "label": {"show": True, "position": "top", "formatter": "{c}", **schrift}}
                  for i in sorted(idx) if i != M]
        reihen[-1]["markPoint"] = {"silent": True, "data": marken, "itemStyle": {"color": t["akzent"]}}
    # Szenarien (zuschaltbar) – nur wenn sie sich überhaupt unterscheiden
    szen_text = ""
    if szen_an:
        unterschied = False
        for k, farbe, art_ in (("schwach", t["orange"], "dotted"), ("stark", t["blau"], "dashed")):
            s_ = erg["szenarien"][k]
            werte = [_gross(x) for x in s_.median[s_.zeile(a_), :M + 1]]
            if any(abs(w - p) >= 1 for w, p in zip(werte, plan)):
                unterschied = True
                reihen.append({"name": f"{bp.SZENARIO_NAMEN[k]} ({'+' if szen[k]['faktor'] >= 0 else '−'}"
                                       f"{abs(round(szen[k]['faktor']))} %)", "type": "line", "data": fx(werte),
                               "smooth": False, "symbol": "none", "lineStyle": {"color": farbe, "width": 2, "type": art_},
                               "itemStyle": {"color": farbe}})
        if not unterschied:
            szen_text = "Die Szenarien ändern hier praktisch nichts."
    # „Heute“, Bereiche „so war es“ / „so wird es voraussichtlich“, „Voll“
    erste = next((i for i, (_d, n) in enumerate(ist) if n is not None), None)
    linien = [{"xAxis": "Heute", "lineStyle": {"color": t["text2"], "type": "solid", "width": 1.5},
               "label": {"formatter": "Heute", "position": "end", **schrift, "fontWeight": 600}}]
    voll = next((e_.get("max_plaetze") for e_ in bk.tabelle() if e_.get("art") == art), None) if a_ else None
    if voll:
        linien.append({"yAxis": voll, "lineStyle": {"color": t["text"], "type": "solid", "width": 2},
                       "label": {"formatter": f"Voll: {voll} Plätze", "position": "insideEndTop", **schrift}})
    flaechen = [[{"xAxis": kat[0], "itemStyle": {"color": "rgba(0,0,0,0)"},
                  "label": {"show": True, "position": "insideTop", "formatter": "so war es", "color": t["text2"],
                            "fontSize": 13}}, {"xAxis": "Heute"}],
                [{"xAxis": "Heute", "itemStyle": {"color": "rgba(0,127,127,0.04)"},
                  "label": {"show": True, "position": "insideTop", "formatter": "so wird es voraussichtlich",
                            "color": t["text2"], "fontSize": 13}}, {"xAxis": kat[-1]}]]
    if erste is None or erste > 0:
        bis = kat[erste] if erste is not None else "Heute"
        flaechen.append([{"xAxis": kat[0], "itemStyle": {"color": "rgba(128,128,128,0.08)"},
                          "label": {"show": True, "position": "inside", "color": t["text2"], "fontSize": 13,
                                    "formatter": f"keine Daten vor {ist[erste][0]:%m.%Y}" if erste is not None
                                    else "keine Daten"}}, {"xAxis": bis}])
    ziel = next(r for r in reihen if r["name"] == "so war es")
    ziel["markLine"] = {"silent": True, "symbol": "none", "data": linien}
    ziel["markArea"] = {"silent": True, "data": flaechen}
    # rechter Rand: Zahlen des letzten Monats
    rand = (f"{kat[-1]}\nerwartet {plan[M]}\nsehr wahrscheinlich {lo[M]}–{hi[M]}"
            + ("" if sicht.klein else f"\nfast sicher {lo95[M]}–{hi95[M]}"))
    pfad = fx(plan)
    reihen.append({"name": "_rand", "type": "line", "data": [None] * (len(pfad) - 1) + [plan[M]], "symbol": "none",
                   "tooltip": {"show": False}, "silent": True,
                   "endLabel": {"show": True, "formatter": rand, "fontSize": 13, "color": t["text"], "lineHeight": 18,
                                "align": "left", "distance": 10}})
    oben = max([v for v in ist_w if v is not None] + hi95 + [voll or 0, 1])
    namen = [r["name"] for r in reihen if not r["name"].startswith("_")]
    tip = json.dumps({"kat": kat, "h": h, "ist": [n for _d, n in ist], "plan": plan, "lo": lo, "hi": hi,
                      "lo95": lo95, "hi95": hi95})
    opt = {"animation": False, "grid": {"left": 48, "right": 200, "top": 56, "bottom": 36},
           "legend": {"top": 0, "left": 0, "data": namen, "textStyle": {"color": t["text"], "fontSize": 13}},
           "tooltip": {"trigger": "axis", "confine": True, "textStyle": {"fontSize": 13},
                       ":position": "(p, params, dom, rect, size) => [Math.min(p[0] + 24, size.viewSize[0] - "
                                    "size.contentSize[0] - 8), 8]",
                       ":formatter": "(ps) => { const D = " + tip + "; const i = ps[0].dataIndex; const f = v => v == null ?"
                                     " 'keine Daten' : v; if (i <= D.h) return '<b>' + D.kat[i] + '</b><br>so war es: ' + "
                                     "f(D.ist[i]); const k = i - D.h; return '<b>' + D.kat[i] + '</b><br>erwartet: ' + "
                                     "D.plan[k] + '<br>sehr wahrscheinlich: ' + D.lo[k] + ' bis ' + D.hi[k] + "
                                     "'<br>fast sicher: ' + D.lo95[k] + ' bis ' + D.hi95[k]; }"},
           "xAxis": {"type": "category", "data": kat, "boundaryGap": bool(sicht.klein),
                     "axisLabel": {"color": t["text"], "fontSize": 13}, "axisLine": {"lineStyle": {"color": t["text2"]}}},
           "yAxis": {"type": "value", "min": 0, "max": int(oben * 1.15) + 1, "minInterval": 1,
                     "axisLabel": {"color": t["text"], "fontSize": 13},
                     "splitLine": {"lineStyle": {"color": t["rand"], "opacity": .6}}},
           "series": reihen}
    return opt, szen_text


def _zerlegung_option(e: bp.Ergebnis, art: str) -> dict:
    from . import seite_auswertung as sa

    t = sa._T()
    z = e.zeile(art)
    farben = [t["text2"], t["blau"], t["akzent"], t["orange"]]
    opt = sa._chart_basis()
    opt["xAxis"]["data"] = ["heute"] + [_m(d) for d in e.monate[1:]]
    opt["yAxis"]["scale"] = False
    opt["series"] = [{"name": bp.QUELLE_TEXT[q], "type": "bar", "stack": "q", "barMaxWidth": 26, "color": farben[i],
                      "data": [round(float(x), 1) for x in e.zerlegung[i, z]]} for i, q in enumerate(bp.QUELLEN)]
    opt["tooltip"] = {"trigger": "axis"}
    return opt


def _abgaenge(md: bp.Modell) -> None:
    with ui.element("section").classes("m-block"):
        ui.label("Verbleib und Übergänge").classes("m-btitel")
        for a_ in md.arten:
            q = bp.abgangsquote(md, a_)
            kv = md.kurven[a_]
            with ui.element("div").classes("m-bst-zeile"):
                ui.label(a_).classes("m-name")
                ui.label(f"vorzeitig: {_p(q)}" if q is not None else "vorzeitig: – (keine Solldauer)").classes("m-zweite")
                if a_ in md.abgang_alt and q is not None:      # 0.86: Rechnung korrigiert – Unterschied sichtbar machen
                    attr(ui.label(f"bis 0.85: {_p(md.abgang_alt[a_])}").classes("m-zweite"),
                         title="Bis Version 0.85 zählten geplante, noch nicht erlebte Tage und künftige Anmeldungen in "
                               "der Verbleibskurve mit – die Abgangsquote fiel dadurch zu niedrig aus.")
                attr(ui.label(f"Kurve: {md.kurve_quelle[a_]} · {kv.n} Fälle").classes("m-zweite"),
                     title="Unter 30 Fällen wird die Kurve der Gruppe bzw. aller Maßnahmen genutzt.")
        for von, u in md.uebergaenge.items():
            ziele = ", ".join(f"{z} {round(100 * n / sum(u.ziele.values()))} %" for z, n in u.ziele.most_common(3))
            ui.label(f"{von} → nächste Stufe: {_p(u.quote)} von {u.basis} · nach Ø "
                     f"{_z(float(u.verzoegerung.mean()) / 30.44, 1) if len(u.verzoegerung) else '–'} Monaten"
                     + (f" · {ziele}" if ziele else "")).classes("m-ptext")


def _rueckblick(rb: list) -> None:
    with ui.element("section").classes("m-block"):
        ui.label("Treffsicherheit im Rückblick").classes("m-btitel")
        for r in rb:
            if r.mae is None:
                ui.label(f"{r.horizont} Monat(e) voraus: noch zu wenig Historie").classes("m-zweite")
                continue
            vergleich = r.mae_bleibt if r.mae_bleibt is not None else r.mae_vorjahr
            besser = vergleich is not None and r.mae < vergleich
            ui.label(f"{r.horizont} Monat(e) voraus: im Schnitt ± {_z(r.mae, 1)} Teilnehmende daneben ({_p(r.wape)}) · "
                     f"{r.treffer} von {r.n} Stichtagen in der 80 %-Spanne · „Bestand bleibt wie heute“: "
                     f"± {_z(r.mae_bleibt, 1)} · „wie vor 12 Monaten“: ± {_z(r.mae_vorjahr, 1)} "
                     f"{'→ Modell besser' if besser else '→ Modell nicht besser als die einfache Annahme'}"
                     + (" · wenige Stichtage – nur ein grober Anhalt" if r.n < 10 else "")).classes("m-ptext")


def _wenn_dann_panel(a, erg, art: str, args) -> None:
    try:
        i = int((args or {}).get("index"))
    except (TypeError, ValueError):
        return
    _ist, kat, n_ist = _achse(erg, art)
    k = i - (n_ist - 1)
    e: bp.Ergebnis = erg["szenarien"]["basis"]
    if k < 1 or k >= len(e.monate):
        a.toast("Wenn-dann geht für künftige Monate – bitte rechts vom Stichtag klicken.")
        return
    z = e.zeile(art)
    vorschlag = round(float(e.median[z, k]))

    def bauen():
        ui.label(f"{'Alle Maßnahmen' if art == 'Alle' else art} · {_m(e.monate[k])}").classes("m-name")
        ui.label(f"Erwartet: {vorschlag} (80 %: {round(float(e.p10[z, k]))}–{round(float(e.p90[z, k]))}). Welche Zahl "
                 "soll angenommen werden?").classes("m-ptext")
        feld = ui.number("Teilnehmende in diesem Monat", value=vorschlag, min=0, step=1).props("dense outlined").classes("m-feld")
        ausgabe = ui.element("div").classes("m-bp-wd")

        async def rechnen():
            ausgabe.clear()
            with ausgabe:
                with ui.element("div").classes("m-zeile-flex"):
                    ui.spinner(size="sm")
                    ui.label("rechnet …").classes("m-zweite")
            w = await run.io_bound(bp.wenn_dann, erg["modell"], k, float(feld.value or 0), None if art == "Alle" else art)
            ausgabe.clear()
            with ausgabe:
                lo, hi = w.spanne
                if w.erreichbar:
                    ui.html(f"<b>{round(w.ziel)}</b> im {_m(w.monat)} kam in etwa <b>{max(1, round(100 * w.anteil))} von "
                            f"100</b> durchgerechneten Verläufen vor. Gezeigt wird, wie es in genau diesen Verläufen "
                            "weiterging.", sanitize=False).classes("m-ptext")
                else:
                    ui.html(f"<b>{round(w.ziel)}</b> liegt außerhalb dessen, was das Modell für möglich hält (im "
                            f"{_m(w.monat)} rund {round(lo)} bis {round(hi)}; schon da bzw. fest angemeldet: "
                            f"{round(w.sicher_im_monat)}). Gezeigt werden die Verläufe, die am nächsten lagen "
                            f"({round(w.erreicht)}).", sanitize=False).classes("m-ptext")
                ui.label("Geht es so weiter:").classes("m-btitel")
                for d_, med, lo, hi in w.verlauf[k::3] + ([w.verlauf[-1]] if (len(w.verlauf) - 1 - k) % 3 else []):
                    with ui.element("div").classes("m-bst-zeile"):
                        ui.label(_m(d_)).classes("m-name")
                        ui.label(f"Planwert {round(med)}").classes("m-zweite")
                        ui.label(f"80 %: {round(lo)}–{round(hi)}").classes("m-zweite")
                ui.label("Ein schwacher (oder starker) Jahrgang wirkt bei zweijährigen Maßnahmen rund zwei Jahre nach – "
                         "das zeigt dieser Verlauf.").classes("m-zweite").style("white-space:normal")
        knopf("Durchrechnen", rechnen, "primaer", "play_arrow")
    a.panel("Wenn-dann", bauen, breit=True)


def _szenarien_panel(a, szen: dict) -> None:
    werte = {k: dict(v) for k, v in szen.items()}

    def bauen():
        ui.label("Szenarien wirken nur auf die weiteren Zugänge (nicht auf Bestand und Pipeline). Je Szenario ein "
                 "Auslöser, der quartalsweise geprüft wird. Welches gerade passt, zeigt der Frühindikator.").classes("m-ptext")
        for k in ("schwach", "stark"):
            ui.label(bp.SZENARIO_NAMEN[k]).classes("m-btitel")
            ui.number("Weitere Zugänge in %", value=werte[k]["faktor"], step=5,
                      on_change=lambda ev, k=k: werte[k].update(faktor=ev.value)).props("dense outlined").classes("m-feld")
            ui.input("Auslöser", value=werte[k]["ausloeser"], placeholder="z. B. Kürzung der Mittel für Eingliederung",
                     on_change=lambda ev, k=k: werte[k].update(ausloeser=ev.value)).props("dense outlined").classes("m-feld")
        ui.label("Normal").classes("m-btitel")
        ui.input("Auslöser / Annahme", value=werte["basis"]["ausloeser"],
                 on_change=lambda ev: werte["basis"].update(ausloeser=ev.value)).props("dense outlined").classes("m-feld")

        async def speichern():
            if await a.aendern(bp.szenarien_schritt, werte):
                a.panel_zu()
        knopf("Speichern", speichern, "primaer", "check")
    a.panel("Szenarien", bauen)


CSS = r"""
.m-bp-ansage { gap: 6px; }
.m-bst > .m-dg-knopf { align-self: flex-start; }
.m-bp-satz { font-size: 20px; line-height: 30px; }
.m-bp-satz b { font-size: 24px; font-weight: 600; color: var(--akzent); }
.m-bp-zelle { display: flex; align-items: baseline; gap: 8px; }
.m-bp-summe { background: color-mix(in srgb, var(--akzent) 6%, transparent); font-weight: 600; }
.m-bp-titel { font-size: 20px; font-weight: 600; color: var(--text); margin: 6px 0 2px; }
.m-bp-kacheln { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }
.m-bp-kachel { border: 1px solid var(--rand); border-radius: 8px; background: var(--fl); padding: 12px 16px;
  display: flex; flex-direction: column; gap: 4px; }
.m-bp-kachel .m-zweite { white-space: normal; }
.m-bp-antwort { display: flex; align-items: center; gap: 8px; font-size: 20px; font-weight: 600; color: var(--text); }
.m-bp-antwort .q-icon { color: var(--akzent); font-size: 24px; }
.m-bp-hinweis { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 8px;
  background: color-mix(in srgb, var(--orange) 10%, transparent); color: var(--text); }
.m-bp-hinweis > :nth-child(2) { flex: 1; white-space: normal; }
.m-bp-hinweis .q-icon { color: var(--orange); }
.m-bp-chart { height: 440px !important; }
.m-bp-lesehilfe { display: flex; flex-direction: column; gap: 2px; margin-top: 6px; }
.m-bp-lesehilfe .m-zweite { white-space: normal; font-size: 13px; }
.m-bp-diagnose summary { cursor: pointer; }
.m-bp-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }
.m-bp-kpi { border: 1px solid var(--rand); border-radius: 8px; background: var(--fl); padding: 10px 14px; display: flex;
  flex-direction: column; gap: 2px; }
.m-bp-kpi .m-zweite { white-space: normal; }
.m-bp-wert { font-size: 24px; line-height: 32px; font-weight: 600; font-variant-numeric: tabular-nums; }
.m-bp-wd { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
"""
