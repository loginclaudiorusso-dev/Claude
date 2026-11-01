"""Seite „Steuerung“ (ganz unten in der Seitenleiste): für die Leitung, selten genutzt – Übersicht, Prognose,
Renovierung, Szenarien, Kennzahlen. Gerechnet wird erst beim Öffnen (im Hintergrund); der Tagesbetrieb merkt nichts.

Daten: ``steuerung_kern`` (Kennzahlen, Prognosegüte, Bericht) und ``renovierung_kern`` (Etagen, Kosten, Fenster).
"""

from __future__ import annotations

from datetime import date

from nicegui import run, ui

from . import renovierung_kern as rk
from . import seiten, standort_kern
from . import steuerung_kern as sk
from .ui_bausteine import attr, knopf, leer, segmente

ANSICHTEN = {"uebersicht": "Übersicht", "prognose": "Prognose", "renovierung": "Renovierung", "szenarien": "Szenarien",
             "kennzahlen": "Kennzahlen"}
GOSLAR = "BFW GS"


def _jahr_standard(heute: date) -> int:
    return heute.year + 1 if heute.month >= 10 else heute.year


# ---- Daten (im Hintergrund) -----------------------------------------------------------------

def _prognose(a):
    from . import auswertung_kern as ak

    ds, fehler = ak.datenstand()
    if ds is None:
        return None, fehler
    try:
        return ak.prognose(ds, GOSLAR, bool(getattr(a, "aw_brutto", False)), 36, 24), ""
    except Exception as exc:                 # noqa: BLE001 – Prognose darf die Seite nicht verhindern
        return None, f"Prognose nicht verfügbar: {exc}"


def daten(a) -> None:
    ansicht = a.ansicht_von("steuerung", "uebersicht")
    if not standort_kern.ist_goslar():
        a.daten = {"fremd": True}
        return
    if getattr(a, "st_jahr", None) is None:
        a.st_jahr = _jahr_standard(a.heute)
    jahr = a.st_jahr
    p = rk.parameter()
    pg, fehler = _prognose(a)
    try:
        sk.buchungsstand_merken(pg, a.heute)
    except Exception:                        # noqa: BLE001 – Mitschreiben ist nur Zugabe
        pass
    prog = sk.prognose_monate(pg)
    fl = rk.flure(a.stand, a.heute, p)
    kap = float(pg.kapazitaet) if pg and pg.kapazitaet else None
    schon = {zid for e in rk.plan() if e["start"][:4] == str(jahr) for zid in (
        e["zimmer"] if e["art"] != "etage" else [z.id for f in fl if f.schluessel == e["flur"] for z in f.zimmer])}
    varianten, empf = rk.varianten(fl, p, jahr, schon=schon)
    wahl = getattr(a, "st_var", None)
    if wahl not in {v.schluessel for v in varianten if v.massnahmen}:
        wahl = empf
    gewaehlt = next((v for v in varianten if v.schluessel == wahl), None)
    vs = rk.vorschlaege_variante(a.stand, fl, jahr, a.heute, p, prog, gewaehlt, kap)
    zeilen = rk.jahresplan(a.stand, jahr, vs, p)
    kap_zeilen = {(z.flur, z.art, z.start): z for y in {a.heute.year, a.heute.year + 1, jahr}
                  for z in rk.jahresplan(a.stand, y, None, p)}
    kap_zeilen.update({(z.flur, z.art, z.start): z for z in zeilen})
    li = sk.linie(pg, list(kap_zeilen.values()), 12, 12 if ansicht == "uebersicht" else 24)
    d = {"p": p, "pg": pg, "fehler": fehler, "fl": fl, "varianten": varianten, "empfehlung": empf, "wahl": wahl,
         "vs": vs, "zeilen": zeilen, "li": li, "guete": sk.guete(pg), "jahr": jahr, "billig": rk.guenstigste(fl, p, jahr)}
    if ansicht in ("uebersicht", "szenarien"):
        d["strategien"] = rk.szenarien_mehrjahr(fl, p, jahr, 5)
    d["kz"] = sk.kennzahlen(a.stand, a.heute, fl, list(kap_zeilen.values()), p)
    d["luecken"] = sk.luecken()
    d["entscheidungen"] = _entscheidungen(d, a.heute)
    if ansicht == "renovierung":
        if getattr(a, "rv_flur", None) not in {f.schluessel for f in fl}:
            a.rv_flur = fl[0].schluessel if fl else None
        f = next((x for x in fl if x.schluessel == a.rv_flur), None)
        if f:
            fs = rk.monatsfenster(a.stand, f, jahr, p, prog)
            rk.engpass_markieren(fs, f, kap, rk.jahresplan(a.stand, jahr, None, p))
            d["monate"] = (f, fs, rk.bester_monat(fs, a.heute))
    if ansicht == "prognose":
        d["staende"] = sk.buchungsstaende()
    if ansicht == "kennzahlen":
        d["werte"] = sk.werte()
        d["noten"] = rk.zustandsnoten()
    a.daten = d


def _entscheidungen(d: dict, heute: date) -> list[str]:
    erg = []
    for v in d["vs"]:
        if v.art != "etage":
            if v.teile:
                erg.append(f"{v.flur.text}: {len(v.teile)} Zimmer {rk.ARTEN[v.art]} – Termine im ersten passenden Leerstand "
                           f"ab {min(t[1] for t in v.teile):%d.%m.%Y} übernehmen?")
            if v.ohne_fenster:
                erg.append(f"{v.flur.text}: für {', '.join(z.kurz for z in v.ohne_fenster)} gibt es {d['jahr']} keinen "
                           "ausreichend langen Leerstand.")
            continue
        if v.fenster:
            fe = v.fenster
            erg.append(f"{v.flur.text}: Vorschlag {rk.MONATE[fe.start.month - 1]} {fe.start.year} übernehmen? Belegungsstopp ab "
                       f"{fe.stopp_ab:%d.%m.%Y}" + (" – Monat gleichwertig zu anderen, frei wählbar" if fe.gleichwertig else "")
                       + (f" – für {len(fe.ohne_ausweich)} Person(en) fehlt ein Ausweichzimmer" if fe.ohne_ausweich else "")
                       + (" – Achtung: auch der beste Monat liegt an der Warnschwelle" if fe.engpass else ""))
        else:
            erg.append(f"{v.flur.text}: in {d['jahr']} ist kein Monat möglich (gesperrt oder Vorlauf zu kurz).")
    p = d["p"]
    gew = next((v for v in d["varianten"] if v.schluessel == d["wahl"]), None)
    if p.get("modus") == "budget" and gew:
        for name, schl, wert in (("Bau", "budget_bau", gew.kosten.instandhaltung), ("Möbel", "budget_moebel",
                                                                                      gew.kosten.investition)):
            if p.get(schl) is not None and p[schl] - wert > 1:
                erg.append(f"Budget {name}: {rk.euro(p[schl] - wert)} bleiben übrig.")
    if d["wahl"] != d["empfehlung"] and d["empfehlung"]:
        erg.append("Gewählt ist nicht die empfohlene Variante – bewusst so?")
    luecken = sorted({l for f in d["fl"] for l in (f.kosten.luecken if f.kosten else [])})
    if luecken:
        erg.append("Kosten unvollständig: " + "; ".join(luecken) + " – Angebot einlesen oder eintragen.")
    warn = sk.warnmonate(d["li"])
    if warn:
        erg.append(f"Belegung erreicht in {len(warn)} Monat(en) die Warnschwelle (ab {rk.MONATE[warn[0].month - 1]} "
                   f"{warn[0].year}) – Renovierungen dort vermeiden, Kontingente prüfen.")
    return erg


# ---- Zeichnen -------------------------------------------------------------------------------

def zeichnen(a) -> None:
    ansicht = a.ansicht_von("steuerung", "uebersicht")
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("steuerung", ansicht=v))
    d = a.daten
    if d.get("fremd"):
        with a.inhalt:
            leer("Die Steuerung rechnet für Goslar (Prognose, Renovierung Haus 2 und 6). Bitte oben Standort Goslar wählen.")
        return
    with a.leiste:
        segmente({j: str(j) for j in (a.heute.year, a.heute.year + 1, a.heute.year + 2)}, d["jahr"],
                 lambda j: a.setzen(st_jahr=j, nur_seite=True), sofort=True)
        knopf("Entscheidungsvorlage (PDF)", lambda: _bericht(a), "", "print").style("margin-left:auto")
    {"uebersicht": _uebersicht, "prognose": _prognose_seite, "renovierung": _renovierung, "szenarien": _szenarien,
     "kennzahlen": _kennzahlen}[ansicht](a)


def _bericht(a) -> None:
    d = dict(a.daten)
    if "strategien" not in d:
        d["strategien"] = rk.szenarien_mehrjahr(d["fl"], d["p"], d["jahr"], 5)
    html = sk.bericht_html({**d, "standort": "Goslar", "heute": a.heute, "empfehlung": d["wahl"], "empfohlen": d["empfehlung"]})
    seiten.html_drucken(a, html, f"Entscheidungsvorlage_Renovierung_{d['jahr']}")


def _kpi(titel: str, wert: str, unter: str = "", stufe: str = "", tipp: str = "") -> None:
    k = ui.element("div").classes("m-kpikarte")
    if tipp:
        attr(k, title=tipp)
    with k:
        ui.label(titel).classes("m-zweite")
        ui.label(wert).classes("m-kpiwert" + (f" m-{stufe}" if stufe in ("krit", "warn") else ""))
        if unter:
            ui.label(unter).classes("m-zweite")


def _chart(a, li: sk.Linie, hoehe: str = "300px") -> None:
    from . import seite_auswertung as sa

    if not li.monate:
        leer("Keine Prognosedaten – Pivot unter „Daten & Import“ wählen.")
        return
    T = sa._T()
    opt = sa._chart_basis()
    opt["xAxis"]["data"] = [f"{rk.MONATE[m.month - 1]} {str(m.year)[2:]}" for m in li.monate]
    opt["series"] = [
        {"name": "80-%-Spanne unten", "type": "line", "data": li.lo80, "stack": "band", "lineStyle": {"opacity": 0},
         "symbol": "none", "tooltip": {"show": False}},
        {"name": "80-%-Spanne", "type": "line", "stack": "band", "symbol": "none", "lineStyle": {"opacity": 0},
         "data": [None if h is None or lo is None else round(h - lo, 1) for h, lo in zip(li.hi80, li.lo80)],
         "areaStyle": {"color": T["akzent"], "opacity": .15}},
        {"name": "Vorjahr", "type": "line", "data": li.vorjahr, "symbol": "none",
         "lineStyle": {"color": T["text3"], "width": 1.2, "type": "dotted"}},
        {"name": "Ist", "type": "line", "data": li.ist, "symbol": "none", "lineStyle": {"color": T["text"], "width": 2}},
        {"name": "Prognose", "type": "line", "data": li.prognose, "symbol": "none",
         "lineStyle": {"color": T["akzent"], "width": 2, "type": "dashed"}},
        {"name": "Kapazität (minus Baustellen)", "type": "line", "data": li.kapazitaet, "symbol": "none", "step": "middle",
         "lineStyle": {"color": T.get("rot", "#c0392b"), "width": 1.5}},
    ]
    if li.warnschwelle:
        opt["series"][-1]["markLine"] = {"symbol": "none", "silent": True, "label": {"formatter": "Warnschwelle", "position": "insideEndTop",
                                                                                     "color": T["text3"]},
                                         "lineStyle": {"type": "dashed", "color": T.get("orange", "#d68910")},
                                         "data": [{"yAxis": li.warnschwelle}]}
    opt["yAxis"]["name"] = "Plätze"
    opt["legend"]["data"] = [s["name"] for s in opt["series"] if not s["name"].endswith("unten")]
    opt["grid"]["top"] = 40
    sa._chart(opt)
    ui.query(".m-chart").style(f"height:{hoehe}")


def _uebersicht(a) -> None:
    d, li, g = a.daten, a.daten["li"], a.daten["guete"]
    jahr, p = d["jahr"], d["p"]
    warn = sk.warnmonate(li)
    progs = [h for h in li.hi80 if h is not None]
    spitze = max(progs) if progs else None
    geplant = sum(z.zimmer for z in d["zeilen"])
    kosten = sum(z.kosten.summe for z in d["zeilen"])
    ziel = int(p.get("ziel_zimmer") or 0)
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            if d["fehler"]:
                ui.label(d["fehler"]).classes("m-pille warn").style("white-space:normal")
            with ui.element("div").classes("m-kpis"):
                _kpi("Höchste Belegung (obere Spanne, 12 M.)",
                     f"{round(100 * spitze / li.kap_voll)} %" if spitze and li.kap_voll else "–",
                     f"{spitze:.0f} von {li.kap_voll} Plätzen" if spitze else "", "krit" if warn else "",
                     "Obere Grenze der 80-%-Spanne – kein Erwartungswert")
                _kpi("Monate an der Warnschwelle", f"{len(warn)}", "von 12 · Kapazität ohne Baustellen",
                     "warn" if warn else "")
                bau = sum(z.kosten.instandhaltung for z in d["zeilen"])
                mob = sum(z.kosten.investition for z in d["zeilen"])
                if p.get("modus") == "budget":
                    bb, bm = p.get("budget_bau"), p.get("budget_moebel")
                    _kpi(f"Renovierung {jahr}", f"{geplant} Zimmer", "geplant (vorgemerkt + Vorschläge) nach Budget")
                    _kpi(f"Kosten {jahr}", rk.euro(kosten),
                         f"Bau {rk.euro(bau)}" + (f" von {rk.euro(bb)}" if bb is not None else "") +
                         f" · Möbel {rk.euro(mob)}" + (f" von {rk.euro(bm)}" if bm is not None else ""),
                         "warn" if (bb is not None and bau > bb + .5) or (bm is not None and mob > bm + .5) else "",
                         "Zwei getrennte Budgets: Bau (Maler/Boden, Nebenkosten) und Möbel (Möbel + Aufbau)")
                else:
                    _kpi(f"Renovierung {jahr}", f"{geplant} / {ziel} Zimmer", "geplant (vorgemerkt + Vorschläge) / Ziel",
                         "warn" if geplant < ziel else "")
                    _kpi(f"Kosten {jahr}", rk.euro(kosten), f"Bau {rk.euro(bau)} · Möbel {rk.euro(mob)}", "",
                         "inkl. Puffer und nicht abziehbarer Umsatzsteuer (Vorsteuerquote)")
            with ui.element("section").classes("m-block m-breit"):
                ui.label("Belegung: Ist, Prognose, Vorjahr – und was die Baustellen an Kapazität kosten").classes("m-btitel")
                _chart(a, li, "280px")
                ui.label(f"{g.satz} Ab Monat 13 nur fortgeschrieben.").classes("m-zweite").style("white-space:normal")
            with ui.element("div").classes("m-zwei"):
                with ui.element("section").classes("m-block"):
                    ui.label(f"Renovierung {jahr}").classes("m-btitel")
                    _gantt(a, d["zeilen"], jahr, kompakt=True)
                    knopf("Zur Planung", lambda: a.oeffnen("steuerung", ansicht="renovierung"), "leise", "arrow_forward")
                with ui.element("section").classes("m-block"):
                    ui.label("Szenarien über 5 Jahre").classes("m-btitel")
                    _strategie_tabelle(d["strategien"], kompakt=True)
                    knopf("Alle Szenarien", lambda: a.oeffnen("steuerung", ansicht="szenarien"), "leise", "arrow_forward")
            with ui.element("section").classes("m-block m-breit"):
                ui.label("Zu entscheiden").classes("m-btitel")
                if not d["entscheidungen"]:
                    ui.label("Nichts offen.").classes("m-pille ok")
                for t in d["entscheidungen"]:
                    with ui.element("div").classes("m-liste-zeile"):
                        ui.icon("help_outline").classes("m-zweite")
                        ui.label(t).style("white-space:normal")


def _prognose_seite(a) -> None:
    d, li, g = a.daten, a.daten["li"], a.daten["guete"]
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            if d["fehler"]:
                ui.label(d["fehler"]).classes("m-pille warn").style("white-space:normal")
            with ui.element("section").classes("m-block m-breit"):
                ui.label("Goslar: 12 Monate Ist, 24 Monate Prognose").classes("m-btitel")
                _chart(a, li, "340px")
                ui.label("Gepunktet: derselbe Monat ein Jahr früher (Ist). Rote Stufenlinie: Kapazität minus Betten in "
                         "Renovierung (vorgemerkt und Vorschläge). Ab Monat 13 ist die Prognose nur fortgeschrieben.").classes(
                    "m-zweite").style("white-space:normal")
            with ui.element("div").classes("m-zwei"):
                with ui.element("section").classes("m-block"):
                    ui.label("Wie gut war die Prognose?").classes("m-btitel")
                    ui.label(g.satz).classes("m-ptext")
                    if g.hinweis:
                        ui.label(g.hinweis).classes("m-zweite").style("white-space:normal")
                    ui.label("Die Spanne im Diagramm stammt aus denselben Rückblick-Fehlern; ihre „Trefferquote“ ist "
                             "deshalb kein Test. Die Prüfung oben trennt alte und jüngste Monate.").classes(
                        "m-xk-hinweis")
                with ui.element("section").classes("m-block"):
                    ui.label("Buchungsstände (für ein späteres Pickup-Modell)").classes("m-btitel")
                    st = d.get("staende") or {}
                    ui.label(f"{len(st)} Monatsstand/-stände gesammelt" + (f" (seit {min(st)})" if st else "") +
                             ". Je Monat wird festgehalten, was für die kommenden Monate schon gebucht ist. Nach etwa "
                             "12 Ständen lässt sich ablesen, wie viel erfahrungsgemäß noch dazukommt.").classes(
                        "m-zweite").style("white-space:normal")
                    knopf("Ausführliche Prognose (Auswertung)", lambda: a.oeffnen("auswertung", ansicht="prognose"),
                          "leise", "insights")


def _strategie_tabelle(strategien, kompakt: bool = False) -> None:
    sp = "minmax(170px, 2fr) 60px 64px 110px 90px 64px" + ("" if kompakt else " 80px")
    with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
        for t in ("Strategie", "Zimmer", "Bestand", "Kosten 5 J.", "je Zimmer", "Zyklus") + (() if kompakt else ("Sperr-Zi.-M.",)):
            ui.label(t)
    for s in strategien:
        z = ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}")
        attr(z, title=s.deutung)
        with z:
            ui.label(s.titel).classes("m-name")
            ui.label(str(s.zimmer)).classes("m-mono")
            ui.label(f"{s.anteil:.0f} %").classes("m-mono")
            ui.label(rk.euro(s.summe("summe"))).classes("m-mono")
            ui.label(rk.euro(s.summe("summe") / s.zimmer) if s.zimmer else "–").classes("m-mono")
            ui.label("–" if s.zyklus is None else f"{s.zyklus:g} J.").classes("m-mono")
            if not kompakt:
                ui.label(f"{s.summe('sperr'):g}").classes("m-mono")


def _szenarien(a) -> None:
    from . import seite_auswertung as sa

    d = a.daten
    st = d["strategien"]
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            ui.label("Was bringt welches Tempo – über fünf Jahre? Jede Strategie wird Jahr für Jahr durchgerechnet: jede Etage "
                     "bzw. jedes Zimmer höchstens einmal, Preise mit Steigerung, Reihenfolge nach Bedarf. Bestand = Anteil "
                     "der Zimmer in Haus 2 und 6, die in dieser Zeit erneuert werden.").classes("m-ptext")
            with ui.element("section").classes("m-block m-breit"):
                ui.label(f"Vergleich {d['jahr']}–{d['jahr'] + 4}").classes("m-btitel")
                _strategie_tabelle(st)
            if st and any(s.jahre for s in st):
                T = sa._T()
                farben = [T["akzent"], T.get("blau", "#5b8def"), T.get("orange", "#d68910"), T.get("gruen", "#3aa76d"),
                          T["text3"]]
                jahre = [str(j["jahr"]) for j in st[0].jahre]
                with ui.element("div").classes("m-zwei"):
                    for titel, feld, einheit in (("Kosten kumuliert", "summe", "€"), ("Zimmer erneuert kumuliert", "zimmer", "Zimmer")):
                        with ui.element("section").classes("m-block"):
                            ui.label(titel).classes("m-btitel")
                            opt = sa._chart_basis()
                            opt["xAxis"]["data"] = jahre
                            opt["yAxis"]["name"] = einheit
                            opt["grid"]["top"] = 50
                            opt["legend"]["type"] = "scroll"
                            reihen = []
                            for i, s in enumerate(st):
                                summe, werte = 0.0, []
                                for j in s.jahre:
                                    summe += j[feld]
                                    werte.append(round(summe))
                                reihen.append({"name": s.titel.split(":")[0], "type": "line", "data": werte,
                                               "lineStyle": {"color": farben[i % len(farben)], "width": 2}, "symbol": "circle"})
                            opt["series"] = reihen
                            sa._chart(opt)
            for s in st:
                with ui.element("section").classes("m-block m-breit"):
                    ui.label(s.titel).classes("m-btitel")
                    ui.label(s.erklaerung).classes("m-zweite").style("white-space:normal")
                    ui.label(s.deutung).classes("m-ptext").style("white-space:normal")
                    sp = "60px minmax(220px, 3fr) 60px 100px 100px 100px 70px"
                    with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
                        for t in ("Jahr", "Maßnahmen", "Zimmer", "Bau", "Möbel", "Gesamt", "Sperr"):
                            ui.label(t)
                    for j in s.jahre:
                        with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                            ui.label(str(j["jahr"])).classes("m-mono")
                            attr(ui.label(j["text"]).classes("m-zweite"), title=j["text"])
                            ui.label(str(j["zimmer"])).classes("m-mono")
                            ui.label(rk.euro(j["bau"])).classes("m-mono")
                            ui.label(rk.euro(j["moebel"])).classes("m-mono")
                            ui.label(rk.euro(j["summe"])).classes("m-mono")
                            ui.label(f"{j['sperr']:g}").classes("m-mono")


def _kennzahlen(a) -> None:
    d = a.daten
    with a.leiste:
        knopf("Werte eingeben …", lambda: _werte_panel(a), "", "edit_note")
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            with ui.element("div").classes("m-kpis"):
                for k in d["kz"]:
                    _kpi(k.titel, k.wert, k.unter, k.stufe, f"Quelle: {k.quelle}" if k.quelle else "")
            if d["luecken"]:
                with ui.element("section").classes("m-block m-breit"):
                    ui.label("Was noch fehlt – und wo man es einträgt").classes("m-btitel")
                    for titel, bedarf in d["luecken"]:
                        with ui.element("div").classes("m-liste-zeile"):
                            ui.label(titel).classes("m-name")
                            ui.label(f"braucht: {bedarf}").classes("m-zweite")
            ui.label("Zum Ausprobieren gehen auch erfundene Zahlen – sie lassen sich jederzeit ändern oder mit Rückgängig "
                     "zurücknehmen. Engpässe je Haus und Zimmertyp stehen im Tagesbetrieb unter Auswertung → Zimmer & "
                     "Engpässe.").classes("m-xk-hinweis")
            knopf("Zu den Engpässen", lambda: a.oeffnen("auswertung", ansicht="zimmer"), "leise", "insights")


def _werte_panel(a) -> None:
    w, noten, fl = sk.werte(), rk.zustandsnoten(), a.daten["fl"]

    def bauen():
        ui.label("Tagessätze je Gruppe (€ je Belegtag) – für Erlös und Leerstandskosten. Leer = unbekannt.").classes("m-ktitel")
        saetze = {}
        with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(4, 1fr)"):
            for g in sk.GRUPPEN:
                saetze[g] = ui.number(g, value=w["tagessaetze"].get(g), min=0, step=5, format="%.2f").classes(
                    "m-feld").props("dense outlined dark clearable")
        ui.label("Abweisungen „kein Zimmer frei“ je Monat").classes("m-ktitel")
        monate = [date(a.heute.year, a.heute.month, 1) - __import__("datetime").timedelta(days=31 * i) for i in range(12)]
        monate = [date(m.year, m.month, 1) for m in monate]
        ab = {}
        with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(6, 1fr)"):
            for m in reversed(monate):
                k = f"{m:%Y-%m}"
                ab[k] = ui.number(f"{rk.MONATE[m.month - 1]} {str(m.year)[2:]}", value=w["abweisungen"].get(k), min=0, step=1,
                                  format="%d").classes("m-feld").props("dense outlined dark")
        ui.label("Zustandsnote je Etage (1 sehr gut … 5 sehr schlecht) – fließt in den Bedarf ein").classes("m-ktitel")
        nf = {}
        with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(4, 1fr)"):
            for f in sorted(fl, key=lambda x: (x.haus, rk.zp._etage_sort(x.etage))):
                nf[f.schluessel] = ui.select({0: "–", 1: "1", 2: "2", 3: "3", 4: "4", 5: "5"}, value=noten.get(f.schluessel, 0),
                                             label=f.text).classes("m-feld").props('dense outlined dark popup-content-class="m-popup"')

        async def speichern():
            ok1 = await a.aendern(sk.werte_schritt, {"tagessaetze": {g: f.value for g, f in saetze.items() if f.value},
                                                     "abweisungen": {k: f.value for k, f in ab.items() if f.value}})
            neu = {k: int(f.value or 0) for k, f in nf.items() if f.value}
            ok2 = True if neu == noten else await a.aendern(rk.zustand_schritt, neu)
            if ok1 and ok2:
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Werte für die Kennzahlen", bauen, breit=True)


# ---- Renovierung ------------------------------------------------------------------------------

def _buendeln(teile: list) -> list[tuple]:
    """Einzelzimmer, deren Termine sich überschneiden, als ein Balken: (von, bis, „2-401, 2-402 …“)."""
    erg: list[list] = []
    for _zid, kurz, von, bis, _b in sorted(teile, key=lambda t: t[2]):
        if erg and von <= erg[-1][1]:
            erg[-1][1] = max(erg[-1][1], bis)
            erg[-1][2].append(kurz)
        else:
            erg.append([von, bis, [kurz]])
    return [(v, b, ", ".join(k)) for v, b, k in erg]


def _gantt(a, zeilen: list, jahr: int, kompakt: bool = False) -> None:
    """Zeilen = Maßnahmen. Schraffiert = Belegungsstopp (Vorlauf), Balken = Bauzeit; Einzelzimmer als kurze Balken je
    Zimmer. Vorschläge gestrichelt."""
    j0, j1 = date(jahr, 1, 1), date(jahr, 12, 31)
    tage = (j1 - j0).days + 1
    pos = lambda d_: max(0.0, min(100.0, 100 * ((d_ - j0).days) / tage))
    with ui.element("div").classes("m-gantt" + (" kompakt" if kompakt else "")):
        with ui.element("div").classes("m-gantt-zeile m-gantt-kopf"):
            ui.label("Maßnahme")
            with ui.element("div").classes("m-gantt-spur"):
                for m in range(12):
                    ui.label(rk.MONATE[m]).classes("m-gantt-monat").style(f"left:{100 * m / 12:.2f}%")
        if not zeilen:
            ui.label("Noch nichts geplant und kein Vorschlag – Ziel oder Budget setzen.").classes("m-zweite")
        for z in zeilen:
            k = z.kosten
            with ui.element("div").classes("m-gantt-zeile"):
                t = ui.element("div").classes("m-gantt-titel")
                with t:
                    ui.label(z.text if z.art == "etage" else f"{z.text} · {z.zimmer} Zi.").classes("m-name")
                    ui.label(("" if z.art == "etage" else rk.ARTEN[z.art] + " · ") + f"{rk.euro(k.summe)}"
                             + (f" (Bau {rk.euro(k.instandhaltung)} · Möbel {rk.euro(k.investition)})" if not kompakt else "")).classes(
                        "m-zweite")
                attr(t, title="\n".join(f"{x}: {rk.euro(b)}" for x, b in k.herleitung if b) + f"\n= {rk.euro(k.summe)}")
                spur = ui.element("div").classes("m-gantt-spur")
                with spur:
                    if a.heute.year == jahr:
                        ui.element("div").classes("m-gantt-heute").style(f"left:{pos(a.heute):.2f}%")
                    teile = _buendeln(z.teile) if z.teile else [(z.start, z.ende, "")]
                    if z.art == "etage" and z.stopp_ab <= j1 and z.start >= j0:
                        attr(ui.element("div").classes("m-gantt-vorlauf").style(
                            f"left:{pos(z.stopp_ab):.2f}%; width:{pos(z.start) - pos(z.stopp_ab):.2f}%"),
                            title=f"Belegungsstopp ab {z.stopp_ab:%d.%m.%Y}")
                    for von, bis, kurz in teile:
                        b = ui.element("button").classes(f"m-gantt-bau {z.status}" + (" eng" if z.ohne_ausweich or z.engpass else "")
                                                         + ("" if z.art == "etage" else " klein")).style(
                            f"left:{pos(von):.2f}%; width:{max(.8, pos(bis) - pos(von)):.2f}%")
                        attr(b, title=f"{kurz or z.text}: {von:%d.%m.} – {bis:%d.%m.%Y} · "
                                      f"{'vorgemerkt' if z.status == 'vorgemerkt' else 'Vorschlag'}"
                                      + (" · Monat gleichwertig" if z.gleichwertig else ""))
                        with b:
                            ui.label(f"{von:%d.%m.}" if z.art == "etage" else str(kurz.count(",") + 1) if kurz else "")
                        b.on("click", lambda z=z: _zeile_panel(a, z))
    with ui.element("div").classes("m-gantt-legende"):
        ui.label("▬ Bauzeit (vorgemerkt)")
        ui.label("┅ Vorschlag").classes("vorschlag")
        ui.label("░ Belegungsstopp").classes("vorlauf")
        ui.label("▪ Einzelzimmer").classes("vorlauf")
        ui.label("orange = Ausweich fehlt oder Warnschwelle").classes("eng")


def _zeile_panel(a, z: rk.PlanZeile) -> None:
    k = z.kosten

    def bauen():
        ui.label(z.titel).classes("m-name")
        if z.art == "etage":
            ui.label(f"Bau {z.start:%d.%m.} – {z.ende:%d.%m.%Y} · Belegungsstopp ab {z.stopp_ab:%d.%m.%Y} · {z.zimmer} Zimmer, "
                     f"{z.betten} Betten").classes("m-ptext")
        else:
            ui.label(f"{z.zimmer} Zimmer, je im ersten Leerstand, der lang genug ist:").classes("m-ptext")
            for _zid, kurz, von, bis, _b in z.teile:
                ui.label(f"{kurz}: {von:%d.%m.} – {bis:%d.%m.%Y}").classes("m-zweite")
        ui.label("So kommen die Kosten zustande").classes("m-ktitel")
        with ui.element("div").classes("m-kap").style("grid-template-columns: 1fr auto"):
            for text, betrag in k.herleitung:
                if betrag:
                    ui.label(text).classes("m-zweite")
                    ui.label(rk.euro(betrag)).classes("m-mono")
            ui.label("Gesamt (wie es bei uns zählt)").classes("m-name")
            ui.label(rk.euro(k.summe)).classes("m-mono m-name")
            ui.label("davon Bau + Nebenkosten · Möbel + Aufbau").classes("m-zweite")
            ui.label(f"{rk.euro(k.instandhaltung)} · {rk.euro(k.investition)}").classes("m-mono")
        ui.label("Das Maler-/Bodenangebot ist nur der erste Posten. Möbel, Aufbau, Puffer und – je nach Vorsteuerquote – "
                 "die Umsatzsteuer kommen dazu; Puffer und Vorsteuerquote stehen unter „Annahmen & Angebote“.").classes(
            "m-xk-hinweis")
        for l in k.luecken:
            ui.label(l).classes("m-pille warn")
        if z.gleichwertig:
            ui.label("Nach Buchungen und Prognose sind mehrere Monate gleich gut – der früheste ist gewählt, ein anderer "
                     "passt genauso.").classes("m-zweite").style("white-space:normal")
        if z.engpass:
            ui.label("In diesem Monat erreicht die obere Prognose die Warnschwelle der verringerten Kapazität – es war "
                     "kein besserer Monat frei.").classes("m-pille warn").style("white-space:normal")
        if z.ohne_ausweich:
            ui.label(f"Für {z.ohne_ausweich} betroffene Person(en) ist im Bauzeitraum kein passendes Zimmer frei.").classes(
                "m-pille warn")

        def eintraege():
            if z.art == "etage":
                return [(z.flur, z.start, z.ende)]
            return [(z.flur, von, bis, z.art, [zid]) for zid, _k, von, bis, _b in z.teile]

        async def merken():
            if await a.aendern(rk.vormerken_mehrere_schritt, eintraege()):
                a.panel_zu()

        async def weg():
            if z.art == "etage":
                ok = await a.aendern(rk.entfernen_schritt, z.flur, z.start.isoformat(), "etage")
            else:
                ok = await a.aendern(rk.entfernen_mehrere_schritt, [(z.flur, von.isoformat(), z.art) for _i, _k, von, _b, _x in z.teile])
            if ok:
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            if z.status == "vorschlag":
                knopf("Bestätigen und vormerken", merken, "primaer", "bookmark_add")
            else:
                knopf("Vormerkung entfernen", weg, "", "delete")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel(("Vorschlag übernehmen?" if z.status == "vorschlag" else "Vorgemerkte Renovierung"), bauen, breit=True)


def _alle_uebernehmen(a, vs) -> None:
    eintraege, texte = [], []
    for v in vs:
        if v.art == "etage" and v.fenster:
            fe = v.fenster
            eintraege.append((v.flur.schluessel, fe.start, fe.ende))
            texte.append((v.flur.text, f"Stopp ab {fe.stopp_ab:%d.%m.} · Bau {fe.start:%d.%m.} – {fe.ende:%d.%m.%Y}"
                          + (" · Ausweich fehlt" if fe.ohne_ausweich else "")))
        for z, von, bis in v.teile:
            eintraege.append((v.flur.schluessel, von, bis, v.art, [z.id]))
            texte.append((z.kurz, f"{rk.ARTEN[v.art]} · {von:%d.%m.} – {bis:%d.%m.%Y}"))

    def bauen():
        ui.label("Diese Vorschläge werden als unverbindliche Renovierung vorgemerkt:").classes("m-ptext")
        for titel, text in texte:
            with ui.element("div").classes("m-liste-zeile"):
                ui.label(titel).classes("m-name")
                ui.label(text).classes("m-zweite")

        async def ok():
            if await a.aendern(rk.vormerken_mehrere_schritt, eintraege):
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            knopf(f"Bestätigen ({len(eintraege)})", ok, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Vorschläge übernehmen?", bauen)


def _renovierung(a) -> None:
    d = a.daten
    p, fl, jahr = d["p"], d["fl"], d["jahr"]
    with a.leiste:
        knopf("Annahmen & Angebote …", lambda: _annahmen(a), "", "tune")

        async def export():
            from pathlib import Path

            try:
                pfad = Path(rk.speicher.einstellungen().get("export_ordner") or rk.speicher.pfad("Exporte")) \
                    / f"Renovierungsplan_{jahr}.xlsx"
                await run.io_bound(rk.excel, a.stand, jahr, pfad, d["zeilen"])
            except Exception as exc:             # noqa: BLE001
                a.toast(f"Nicht gespeichert: {exc}", fehler=True)
                return
            a.toast("Renovierungsplan gespeichert" if seiten._datei_oeffnen(str(pfad)) else f"Gespeichert: {pfad}", rueck=False)
        knopf("Excel", export, "", "table_view")
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            ui.label("Unverbindliche Planung: Hier wird nichts gesperrt, niemand umgezogen und keine Buchung verschoben.").classes(
                "m-ptext")
            _vorgabe_block(a, d, p, fl, jahr)
            _varianten_block(a, d, p)
            with ui.element("section").classes("m-block m-breit"):
                with ui.element("div").classes("m-zeile-flex"):
                    gew = next((v for v in d["varianten"] if v.schluessel == d["wahl"]), None)
                    ui.label(f"Jahresplan {jahr}" + (f" – {gew.titel}" if gew else "")).classes("m-btitel")
                    if [v for v in d["vs"] if v.fenster or v.teile]:
                        knopf("Alle Vorschläge übernehmen …", lambda: _alle_uebernehmen(a, d["vs"]), "primaer",
                              "bookmark_add").style("margin-left:auto")
                _gantt(a, d["zeilen"], jahr)
                ui.label("Beträge = alles zusammen: Maler/Boden, Nebenkosten, Möbel, Aufbau, Puffer und nicht abziehbare "
                         "Umsatzsteuer. Klick auf einen Balken zeigt die Herleitung Schritt für Schritt.").classes("m-xk-hinweis")
            _etagen_block(a, d, p, fl, jahr)
            if "monate" in d:
                _monate(a, *d["monate"])
            ui.label(f"Annahmen: Preisstand {p['preisstand']}, +{p['preis_pct']} % je Jahr · Nebenkosten {p['neben_pct']} % · "
                     f"Puffer {p['puffer_pct']} % · Vorsteuerquote {p['vorsteuer_pct']} % (0 % = brutto) · Einzelzimmer-Bau "
                     f"anteilig + {p.get('einzel_aufschlag_pct')} % · Belegungsstopp {p['vorlauf_tage']} Tage vorher · Bauzeit "
                     + ", ".join(f"Haus {h} {p['kosten'][h].get('dauer_tage', 30)} Tage" for h in p["haeuser"])
                     + f" · Einzelzimmer {p.get('zimmer_tage')} Tage, Möbel {p.get('moebel_tage')} Tage").classes("m-xk-hinweis")


def _vorgabe_block(a, d, p, fl, jahr) -> None:
    with ui.element("section").classes("m-block m-breit"):
        with ui.element("div").classes("m-zeile-flex"):
            ui.label("Vorgabe").classes("m-btitel")

            async def modus(v):
                a.st_var = None
                await a.aendern(rk.parameter_schritt, {**p, "modus": v})
            segmente({"ziel": "Zimmerziel", "budget": "Budget (Bau und Möbel getrennt)"}, p.get("modus") or "ziel", modus)
        with ui.element("div").classes("m-zeile-flex"):
            if p.get("modus") == "budget":
                bau = ui.number("Budget Bau (Maler/Boden, Nebenkosten) €", value=p.get("budget_bau"), min=0, step=1000,
                                format="%.0f").classes("m-feld").props("dense outlined dark clearable").style(
                    "flex:1 1 240px; max-width:340px")
                mob = ui.number("Budget Möbel (Möbel + Aufbau) €", value=p.get("budget_moebel"), min=0, step=500,
                                format="%.0f").classes("m-feld").props("dense outlined dark clearable").style(
                    "flex:1 1 240px; max-width:340px")

                async def setzen():
                    a.st_var = None
                    await a.aendern(rk.parameter_schritt, {**p, "budget_bau": None if bau.value in (None, "") else float(bau.value),
                                                           "budget_moebel": None if mob.value in (None, "") else float(mob.value)})
                knopf("Budget übernehmen", setzen, "leise", "check")
            else:
                ziel = int(p.get("ziel_zimmer") or 0)
                zahl = ui.number("Zimmer je Jahr", value=ziel, min=0, max=500, step=1, format="%d").classes("m-feld").props(
                    "dense outlined dark").style("max-width:160px")

                async def ziel_setzen():
                    if int(zahl.value or 0) != ziel:
                        a.st_var = None
                        await a.aendern(rk.parameter_schritt, {**p, "ziel_zimmer": int(zahl.value or 0)})
                knopf("Ziel übernehmen", ziel_setzen, "leise", "check")
                zy = rk.zyklus(fl, ziel)
                if zy:
                    ui.label(f"≙ jedes Zimmer etwa alle {zy:g} Jahre ({rk.bestand(fl)} Zimmer in Haus {', '.join(p['haeuser'])})").classes(
                        "m-zweite")
        ui.label("Beträge so, wie sie bei euch zählen (mit Puffer und nicht abziehbarer Umsatzsteuer). Leeres Budgetfeld = "
                 "keine Grenze." if p.get("modus") == "budget" else
                 "Ganze Etagen werden auf das Ziel gerundet; Einzelzimmer füllen bis zum Ziel auf.").classes("m-zweite")


def _varianten_block(a, d, p) -> None:
    with ui.element("section").classes("m-block m-breit"):
        ui.label("Wege im Vergleich – ★ empfohlen (meister Bedarf gedeckt, dann mehr Zimmer, dann günstiger)").classes("m-btitel")
        with ui.element("div").classes("m-rv-varianten"):
            for v in d["varianten"]:
                k = v.kosten
                leer_ = not v.massnahmen
                b = ui.element("button").classes("m-rv-monat m-rv-var" + (" bester" if v.schluessel == d["wahl"] else "")
                                                + (" gesperrt" if leer_ else ""))
                attr(b, title=v.erklaerung)
                with b:
                    ui.label(v.titel + (" ★" if v.schluessel == d["empfehlung"] else "")).classes("m-name")
                    if leer_:
                        ui.label(v.hinweis or "nichts passt").classes("m-zweite").style("white-space:normal")
                    else:
                        ui.label(f"{v.zimmer} Zimmer · Bedarf {v.punkte:g} P.").classes("m-zweite")
                        ui.label(rk.euro(k.summe)).classes("m-mono m-name")
                        ui.label(f"Bau {rk.euro(k.instandhaltung)} · Möbel {rk.euro(k.investition)}").classes("m-zweite")
                        ui.label(f"Sperr-Zimmermonate {v.sperr_zimmermonate(p):g}").classes("m-zweite")
                        if p.get("modus") == "budget":
                            rb = None if p.get("budget_bau") is None else p["budget_bau"] - k.instandhaltung
                            rm = None if p.get("budget_moebel") is None else p["budget_moebel"] - k.investition
                            ui.label("Rest: " + " · ".join(x for x in (f"Bau {rk.euro(rb)}" if rb is not None else "",
                                                                       f"Möbel {rk.euro(rm)}" if rm is not None else "") if x)
                                     or "keine Grenze").classes("m-zweite")
                if not leer_:
                    b.on("click", lambda v=v: a.setzen(st_var=v.schluessel, nur_seite=True))
        gew = next((v for v in d["varianten"] if v.schluessel == d["wahl"]), None)
        if gew:
            ui.label(gew.erklaerung + (" Einzelzimmer-Bau ist aus dem Etagenangebot geschätzt." if any(
                m.art == "zimmer" for m in gew.massnahmen) else "")).classes("m-zweite").style("white-space:normal")
        if d["billig"] and p.get("modus") == "budget" and not any(v.massnahmen for v in d["varianten"][:1]):
            f, k = d["billig"]
            ui.label(f"Günstigste ganze Etage: {f.text} – Bau {rk.euro(k.instandhaltung)}, Möbel {rk.euro(k.investition)}.").classes(
                "m-pille warn").style("white-space:normal")


def _etagen_block(a, d, p, fl, jahr) -> None:
    with ui.element("section").classes("m-block m-breit"):
        ui.label("Etagen nach Bedarf").classes("m-btitel")
        ui.label("Bedarf = Punkte je Zimmer: „Renovierung nötig“ (4), über 15 Jahre nicht renoviert (2), Zustandsnote 4/5 (+2/+4), "
                 f"offene Mängel schwächer (0,5–1,5), in den letzten {rk.FRISCH_JAHRE} Jahren renoviert (−3). Klick: Monate "
                 "dieser Etage.").classes("m-zweite").style("white-space:normal")
        if fl and max(f.bedarf for f in fl) <= 0:
            ui.label("Für diese Etagen sind weder Renovierungsdaten, Zustandsnoten noch Mängel erfasst – die Reihenfolge ist "
                     "noch keine Empfehlung.").classes("m-pille warn").style("white-space:normal")
        sp = "40px minmax(140px, 1fr) 96px 64px 60px minmax(200px, 2fr) minmax(160px, 1.2fr) 120px"
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("", "Etage", "Zimmer", "Bedarf", "Note", "Warum", "Datenlage · Besonderheiten", f"ganze Etage {jahr}"):
                ui.label(t)
        for i, f in enumerate(fl, 1):
            k = rk.kosten(p, f.haus, len(f.zimmer), jahr)
            z = ui.element("div").classes("m-raster m-zeile m-rv-zeile" + (" an" if f.schluessel == a.rv_flur else "")).style(
                f"grid-template-columns:{sp}")
            with z:
                ui.label(str(i)).classes("m-mono")
                ui.label(f.text).classes("m-name")
                ui.label(f"{len(f.zimmer)} · {f.betten} B.").classes("m-mono")
                ui.label(f"{f.bedarf:g}").classes("m-mono" + {"krit": " m-krit", "warn": " m-warn"}.get(f.ampel, ""))
                ui.label(str(f.zustand) if f.zustand else "–").classes("m-mono")
                attr(ui.label("; ".join(t for _p, t in f.gruende) or "nichts erfasst").classes("m-zweite"),
                     title="\n".join(f"{p_:+g} P. – {t}" for p_, t in f.gruende))
                attr(ui.label(" · ".join(f.luecken + f.sonder) or "–").classes("m-zweite"), title="\n".join(f.luecken + f.sonder))
                attr(ui.label(rk.euro(k.summe)).classes("m-mono"),
                     title="\n".join(f"{x}: {rk.euro(b)}" for x, b in k.herleitung if b) + "\n" + "\n".join(k.luecken))
            z.on("click", lambda f=f: a.setzen(rv_flur=f.schluessel, nur_seite=True))


def _monate(a, f, fs, best) -> None:
    jahr = fs[0].start.year if fs else a.heute.year
    with ui.element("section").classes("m-block m-breit"):
        ui.label(f"{f.text}: Monate {jahr}").classes("m-btitel")
        ui.label("Betroffen = wohnt im Bauzeitraum oder reist darin an (bekannte Buchungen). „Ausweich“ = für jede betroffene "
                 "Person ein passendes freies Zimmer in allen Häusern (Gruppe, nur Männer, Gäste/EMR/Doppelzimmer). "
                 "„gleichwertig“ = der Unterschied ist kleiner als die Unsicherheit der Prognose.").classes(
            "m-zweite").style("white-space:normal")
        with ui.element("div").classes("m-rv-jahr"):
            for fe in fs:
                k = ui.element("button").classes(f"m-rv-monat {fe.stufe}" + (" bester" if best is fe else ""))
                with k:
                    ui.label(rk.MONATE[fe.start.month - 1] + (" ★" if best is fe else "")
                             + (" ≈" if fe.gleichwertig else "") + (" · Engpass" if fe.engpass else "")).classes(
                        "m-zweite" + (" m-warn" if fe.engpass else ""))
                    ui.label({"gesperrt": "gesperrt", "frei": "frei"}.get(fe.stufe, f"{fe.betroffen} betroffen")).classes(
                        "m-name")
                    ui.label(f"Stopp ab {fe.stopp_ab:%d.%m.}" + (f" · {fe.mieter} Mieter" if fe.mieter else "")).classes(
                        "m-zweite")
                    ui.label((f"{len(fe.ohne_ausweich)} ohne Ausweich" if fe.ohne_ausweich else f"{fe.frei_gesamt} frei gesamt")
                             + (f" · Progn. {fe.prognose[0]:.0f}" if fe.prognose else "")).classes("m-zweite")
                k.on("click", lambda fe=fe, f=f: _fenster(a, f, fe))


def _fenster(a, f, fe) -> None:
    def bauen():
        ui.label(f"{f.text} · {fe.start:%d.%m.} – {fe.ende:%d.%m.%Y}").classes("m-name")
        ui.label(f"Belegungsstopp ab {fe.stopp_ab:%d.%m.%Y}. Im ganzen Bauzeitraum frei: {fe.frei_im_haus} Zimmer im selben "
                 f"Haus, {fe.frei_gesamt} in allen Häusern.").classes("m-ptext")
        if fe.ausweich:
            ui.label("Ausweich: " + ", ".join(f"Haus {h}: {n}" for h, n in sorted(fe.ausweich.items()))).classes("m-pille ok")
        if fe.gesperrt:
            ui.label("Dieser Monat ist in den Annahmen gesperrt.").classes("m-pille warn")
        for titel, liste, spalte in (("Wohnt im Bauzeitraum – Umzug nötig", fe.umzug, "bis"),
                                     ("Reist im Bauzeitraum an – umleiten", fe.umleiten, "ab"),
                                     ("Zwischen Stopp und Baubeginn neu – besser woanders hin", fe.nach_stopp, "ab")):
            if not liste:
                continue
            ui.label(f"{titel} ({len(liste)})").classes("m-ktitel")
            for name, zimmer, tag, gruppe in liste:
                with ui.element("div").classes("m-liste-zeile"):
                    ui.label(name).classes("m-name")
                    ui.label(f"{zimmer} · {gruppe or '–'} · {spalte} {tag:%d.%m.%Y}").classes("m-zweite")
        if fe.ohne_ausweich:
            ui.label(f"Kein passendes Ausweichzimmer ({len(fe.ohne_ausweich)})").classes("m-ktitel")
            for name, gruppe, grund in fe.ohne_ausweich:
                with ui.element("div").classes("m-liste-zeile"):
                    ui.label(name).classes("m-name")
                    ui.label(f"{gruppe} · {grund}").classes("m-zweite")
        if not (fe.umzug or fe.umleiten or fe.nach_stopp):
            ui.label("Nach den bekannten Buchungen ist niemand betroffen.").classes("m-pille ok")
        if fe.mieter:
            ui.label(f"{fe.mieter} Mietverhältnis(se) betroffen – Umzug ist eine Frage des Vertrags.").classes("m-pille warn")
        ui.label("Vormerken speichert nur diesen Plan-Eintrag (unverbindlich).").classes("m-zweite")

        async def merken():
            if await a.aendern(rk.vormerken_schritt, f.schluessel, fe.start, fe.ende):
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            knopf("Bestätigen und vormerken", merken, "primaer", "bookmark_add")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel(f"Renovierung {rk.MONATE[fe.start.month - 1]} {fe.start.year}", bauen, breit=True)


def _annahmen(a) -> None:
    from .seite_daten import _hochladen

    p = rk.parameter()

    def feld(titel, wert, schritt=1, mx=None):
        return ui.number(titel, value=wert, min=0, max=mx, step=schritt, format="%g").classes("m-feld").props(
            "dense outlined dark")

    def bauen():
        ui.label("Alle Beträge netto (wie im Angebot). Die Umsatzsteuer kommt über die Vorsteuerquote dazu.").classes("m-ptext")
        felder = {}
        with ui.element("div").classes("m-kap").style("grid-template-columns: 70px repeat(4, 1fr)"):
            for t in ("Haus", "Bau je Etage (€)", "Möbel je Zimmer (€)", "Aufbau je Zimmer (€)", "Bauzeit (Tage)"):
                ui.label(t).classes("m-zweite")
            for h in p["haeuser"]:
                k = p["kosten"][h]
                ui.label(f"Haus {h}").classes("m-name")
                for s, schritt in (("bau_etage", 1000), ("moebel_zimmer", 50), ("aufbau_zimmer", 50), ("dauer_tage", 1)):
                    felder[(h, s)] = feld("", k.get(s, 0), schritt)
        with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(3, 1fr)"):
            ziel = feld("Zimmer je Jahr (Ziel)", p["ziel_zimmer"])
            neben = feld("Nebenkosten % vom Bau", p["neben_pct"], 1, 100)
            puffer = feld("Puffer %", p["puffer_pct"], 1, 100)
            vq = feld("Vorsteuerquote % (0 = brutto)", p["vorsteuer_pct"], 5, 100)
            preis = feld("Preissteigerung % je Jahr", p["preis_pct"], .5, 50)
            stand = feld("Preisstand (Jahr)", p["preisstand"], 1)
            vorlauf = feld("Belegungsstopp vorher (Tage)", p["vorlauf_tage"], 7, 365)
        gesperrt = ui.select({i + 1: m for i, m in enumerate(rk.MONATE)}, value=list(p.get("gesperrt") or []), multiple=True,
                             label="Gesperrte Monate (keine Renovierung)").classes("m-feld").props(
            'dense outlined dark use-chips popup-content-class="m-popup"')
        if p.get("angebote"):
            ui.label("Eingelesene Angebote").classes("m-ktitel")
            for an in p["angebote"]:
                ui.label(f"Haus {an.get('haus')} · {'Möbel' if an.get('art') == 'moebel' else 'Bau'} · {rk.euro(float(an.get('netto') or 0))} "
                         f"netto" + (f" für {an.get('zimmer')} Zimmer" if an.get("art") == "moebel" else "")
                         + (f" · {an.get('datei')}" if an.get("datei") else "")).classes("m-zweite")

        async def speichern():
            neu = {**p, "ziel_zimmer": int(ziel.value or 0), "neben_pct": float(neben.value or 0),
                   "puffer_pct": float(puffer.value or 0), "vorsteuer_pct": float(vq.value or 0),
                   "preis_pct": float(preis.value or 0), "preisstand": int(stand.value or a.heute.year),
                   "vorlauf_tage": int(vorlauf.value or 0), "gesperrt": sorted(gesperrt.value or []),
                   "kosten": {h: {s: float(felder[(h, s)].value or 0) for s in ("bau_etage", "moebel_zimmer", "aufbau_zimmer",
                                                                                "dauer_tage")} for h in p["haeuser"]}}
            for h in p["haeuser"]:
                neu["kosten"][h]["dauer_tage"] = int(neu["kosten"][h]["dauer_tage"] or 30)
            if await a.aendern(rk.parameter_schritt, neu):
                a.panel_zu()

        async def angebot(dateien):
            for pfad, name in dateien[:1]:
                try:
                    ang = await run.io_bound(rk.angebot_lesen, pfad)
                except Exception as exc:         # noqa: BLE001
                    a.toast(f"Angebot nicht lesbar: {exc}", fehler=True)
                    return
                ang["datei"] = name
                _angebot_pruefen(a, ang)
        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            _hochladen(a, "Angebot einlesen (PDF)", ".pdf", angebot)
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Renovierung – Annahmen & Angebote", bauen, breit=True)


def _angebot_pruefen(a, ang: dict) -> None:
    """Erkanntes vor dem Speichern zeigen – Haus, Art und Zimmerzahl korrigierbar."""
    p = rk.parameter()

    def bauen():
        ui.label(f"Aus „{ang.get('datei', '')}“ erkannt – bitte prüfen. Gespeichert wird nur der Betrag in den Annahmen, "
                 "die Datei selbst nicht.").classes("m-ptext")
        haus = ui.select({h: f"Haus {h}" for h in p["haeuser"]}, value=ang["haus"] if ang["haus"] in p["haeuser"] else None,
                         label="Haus").classes("m-feld").props('dense outlined dark popup-content-class="m-popup"')
        art = ui.select({"bau": "Bau (Maler/Boden) je Etage", "moebel": "Möbel"}, value=ang["art"], label="Art").classes(
            "m-feld").props('dense outlined dark popup-content-class="m-popup"')
        netto = ui.number("Nettosumme (€)", value=ang["netto"], min=0, step=100, format="%.2f").classes("m-feld").props(
            "dense outlined dark")
        zimmer = ui.number("Für wie viele Zimmer (nur Möbel)", value=ang.get("zimmer") or 0, min=0, step=1,
                           format="%d").classes("m-feld").props("dense outlined dark")
        datum = ui.input("Angebotsdatum (JJJJ-MM-TT, optional)", value=str(a.heute)).classes("m-feld").props(
            "dense outlined dark")

        async def ok():
            try:
                neu = rk.angebot_uebernehmen(p, {"haus": haus.value, "art": art.value, "netto": float(netto.value or 0),
                                                 "zimmer": int(zimmer.value or 0), "datum": (datum.value or "")[:10],
                                                 "datei": ang.get("datei", "")})
            except ValueError as exc:
                a.toast(str(exc), fehler=True)
                return
            if await a.aendern(rk.parameter_schritt, neu):
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            knopf("Übernehmen", ok, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Angebot prüfen", bauen)
