"""Auswertung → Maßnahmen (0.50): Teilnehmende bzw. Internat je Maßnahmengruppe, gebuchter Bestand + erwartete neue
Kurse, Tabelle je Hauptmaßnahme, Rückwärtstest, Abgleich mit dem Standort-Pivot. Rechnet in ``massnahmen_kern``."""

from __future__ import annotations

from datetime import date

from nicegui import ui

from . import massnahmen_kern as mk
from . import standort_kern
from .ui_bausteine import attr, knopf, leer, segmente, tabelle

MON = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
REIHEN = ["lang", "vorbereitung", "ibtz", "uebrige"]


def _z(x: float | None, nk: int = 0) -> str:
    return "–" if x is None else f"{x:,.{nk}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def daten(a) -> None:
    internat = bool(getattr(a, "mn_internat", True))      # Standard: Belegung im Internat (Betten)
    vor = int(getattr(a, "mn_vor", 24) or 24)
    roh = mk._roh()
    liste = mk.familien_liste(roh, a.heute)
    bekannt = {f for f, _g, _t in liste}
    auswahl = [f for f in (getattr(a, "mn_auswahl", None) or []) if f in bekannt]
    modus = getattr(a, "mn_modus", "summe") if len(auswahl) >= 2 else "summe"
    pg = mk.prognose(roh, a.heute, 12, vor, internat, set(auswahl) or None)
    d = {"pg": pg, "stand": mk.stand(), "internat": internat, "vor": vor, "kap": None, "liste": liste, "auswahl": auswahl,
         "modus": modus}
    if pg is not None:
        vergleich_arten = auswahl or [f for f, g, _t in liste if g in ("lang", "vorbereitung", "ibtz")]
        d["vergleich"] = mk.vergleich(roh, a.heute, vergleich_arten, internat)
        if modus == "vergleich":
            d["je"] = mk.je_familie(roh, a.heute, auswahl, 12, vor, internat)
        d["tests"] = mk.rueckwaertstest(roh)
        d["abgleich"] = _abgleich(roh, a.heute)
        d["kap"] = _kapazitaet() if internat and not auswahl else None
    a.daten = d


def _kapazitaet() -> int | None:
    from . import auswertung_kern as ak

    ds, _f = ak.datenstand()
    try:
        k = ds.kapazitaet(f"BFW {standort_kern.aktiv().kurz}") if ds is not None else 0
    except Exception:                          # noqa: BLE001
        return None
    return int(k) or None


def _abgleich(roh: dict, heute: date) -> list:
    """Standort-Pivot (Reha-Belegung des aktiven Standorts) gegen alle Teilnehmenden laut Maßnahmen-Pivot."""
    from . import auswertung_kern as ak

    ds, _f = ak.datenstand()
    if ds is None:
        return []
    schluessel = f"BFW {standort_kern.aktiv().kurz}"
    try:
        reihe = ds.reha(schluessel)
    except Exception:                          # noqa: BLE001 – Standort fehlt im Pivot
        return []
    werte = {t.date(): float(v) for t, v in reihe.items()}
    return mk.abgleich(roh, lambda t: werte.get(t), 18, min(heute, ds.stichtag))


def zeichnen(a) -> None:
    d = a.daten
    with a.leiste:
        segmente({True: "Internat (Betten)", False: "alle Teilnehmenden"}, d["internat"],
                 lambda v: a.setzen(mn_internat=v, nur_seite=True), sofort=True)
        segmente({12: "12 Monate", 24: "24 Monate", 36: "36 Monate"}, d["vor"],
                 lambda v: a.setzen(mn_vor=v, nur_seite=True), sofort=True)
        knopf("Geplante Plätze …", lambda: _plaetze_panel(a), "", "event_seat").style("margin-left:auto")
    with a.leiste:
        _auswahl(a, d)
    pg = d["pg"]
    with a.inhalt:
        if pg is None:
            leer("Noch kein Maßnahmen-Pivot eingelesen. Unter Daten & Import → „Maßnahmen-Prognose“ hochladen.")
            knopf("Zu Daten & Import", lambda: a.oeffnen("daten"), "primaer", "upload_file")
            return
        with ui.element("div").classes("m-rv"):
            _kopf(a, d, pg)
            _kpis(pg, d["kap"])
            with ui.element("section").classes("m-block m-breit"):
                titel = ("Belegungsprognose Internat (Betten)" if pg.internat else "Prognose aller Teilnehmenden")
                if d["auswahl"]:
                    titel += (" – Vergleich: " if d["modus"] == "vergleich" else " – ") + ", ".join(d["auswahl"][:6]) + (
                        " …" if len(d["auswahl"]) > 6 else "")
                ui.label(titel + f" – {d['vor']} Monate").classes("m-btitel")
                if d["modus"] == "vergleich":
                    _vergleich_chart(d["je"])
                else:
                    _chart(pg, d["kap"])
                ui.label("Je Maßnahme eine Farbe: durchgezogen = Ist, gestrichelt = Prognose (gebucht + erwartete neue Kurse) · "
                         "hell hinterlegt = Prognosezeitraum · Kennzahlen oben = Summe der Auswahl." if d["modus"] == "vergleich" else
                         "Durchgezogen = Ist · gestrichelt = Prognose (gebucht + erwartete neue Kurse) · Band = Spanne der "
                         "neuen Kurse aus den Vorjahren · gepunktet = nur sicher gebucht (laut Pivot) · rot = Kapazität (bei "
                         "Auswahl ausgeblendet) · hell hinterlegt = Prognosezeitraum.").classes("m-zweite").style("white-space:normal")
            with ui.expansion("Aufteilung nach Maßnahmengruppen").classes("m-block m-breit m-rv-exp"):
                _gruppen_chart(pg)
            _vergleich_tabelle(d)
            _tabelle(a, pg)
            _neue(pg)
            _test(d["tests"])
            _abgleich_block(d["abgleich"])


def _kopf(a, d, pg) -> None:
    pv, li = d["stand"]["pivot"], d["stand"]["listen"]
    teile = [f"Maßnahmen-Pivot {pv['von'][:10]} – {pv['bis'][:10]}, {pv['kurse']} Kurse"]
    if pv.get("luecken"):
        teile.append("überbrückt: " + ", ".join(f"{x[0][:10]}–{x[1][:10]}" for x in pv["luecken"]))
    teile.append(f"Anreiselisten: {li['kurse']} Kurse" if li else "keine Anreiselisten")
    if pg.internat:
        teile.append(f"Internatsanteil {pg.anteil_quelle}")
    ui.label(" · ".join(teile)).classes("m-zweite").style("white-space:normal")


def _kpis(pg, kap: int | None) -> None:
    jetzt = next((z for z in pg.zeilen if z.art == "prognose"), pg.zeilen[-1])
    idx = pg.zeilen.index(jetzt)
    einheit = "im Internat" if pg.internat else "Teilnehmende"
    from .seite_steuerung import _kpi

    def ausl(w: float) -> str:
        return f" · {round(100 * w / kap)} % der Kapazität" if kap else ""
    with ui.element("div").classes("m-kpis"):
        _kpi(f"Heute {einheit}", _z(jetzt.summe), f"{MON[jetzt.monat.month - 1]} {jetzt.monat.year}{ausl(jetzt.summe)}")
        for n in (6, 12, len(pg.zeilen) - 1 - idx):
            z = pg.zeilen[min(len(pg.zeilen) - 1, idx + n)]
            unten, oben = z.summe - z.erwartet + z.klein, z.summe - z.erwartet + z.gross
            _kpi(f"Prognose {MON[z.monat.month - 1]} {z.monat.year}", _z(z.summe),
                 f"Spanne {_z(unten)}–{_z(oben)} · sicher gebucht {_z(z.gebucht)}{ausl(z.summe)}",
                 "krit" if kap and oben >= kap else "warn" if kap and oben >= .9 * kap else "")


def _chart(pg, kap: int | None) -> None:
    """Eine Linie: Ist bis heute, danach Prognose mit Band; dazu „nur gebucht“ und die Kapazität."""
    from . import seite_auswertung as sa

    t = sa._T()
    opt = sa._chart_basis()
    x = [f"{MON[z.monat.month - 1]} {z.monat.year % 100}" for z in pg.zeilen]
    h = next((i for i, z in enumerate(pg.zeilen) if z.art == "prognose"), len(pg.zeilen) - 1)
    r = lambda v: round(v, 1)
    unten = [None if i < h else r(z.summe - z.erwartet + z.klein) for i, z in enumerate(pg.zeilen)]
    breite = [None if i < h else r(z.gross - z.klein) for i, z in enumerate(pg.zeilen)]
    opt["xAxis"]["data"] = x
    opt["xAxis"]["boundaryGap"] = False
    opt["yAxis"]["scale"] = False
    opt["grid"]["top"] = 44
    opt["series"] = [
        {"name": "Spanne", "type": "line", "stack": "band", "symbol": "none", "data": unten, "lineStyle": {"opacity": 0},
         "tooltip": {"show": False}, "silent": True},
        {"name": "Spanne (neue Kurse)", "type": "line", "stack": "band", "symbol": "none", "data": breite,
         "lineStyle": {"opacity": 0}, "areaStyle": {"color": t["akzent"], "opacity": .16}, "silent": True},
        {"name": "Ist", "type": "line", "symbol": "none", "data": [r(z.summe) if i <= h else None for i, z in enumerate(pg.zeilen)],
         "lineStyle": {"color": t["text"], "width": 3}},
        {"name": "Prognose", "type": "line", "symbol": "circle", "symbolSize": 5,
         "data": [r(z.summe) if i >= h else None for i, z in enumerate(pg.zeilen)],
         "lineStyle": {"color": t["akzent"], "width": 3, "type": "dashed"}, "itemStyle": {"color": t["akzent"]},
         "markArea": {"silent": True, "itemStyle": {"color": t["akzent"], "opacity": .05},
                      "label": {"show": True, "position": "insideTopLeft", "color": t["text3"], "formatter": "Prognose"},
                      "data": [[{"xAxis": x[h]}, {"xAxis": x[-1]}]]}},
        {"name": "sicher gebucht", "type": "line", "symbol": "none",
         "data": [r(z.gebucht) if i >= h else None for i, z in enumerate(pg.zeilen)],
         "lineStyle": {"color": t["text3"], "width": 2, "type": "dotted"}},
    ]
    if kap:
        opt["series"].append({"name": "Kapazität", "type": "line", "symbol": "none", "data": [kap] * len(x),
                              "lineStyle": {"color": t.get("rot", "#d64545"), "width": 1.5}})
    opt["legend"]["data"] = ["Ist", "Prognose", "Spanne (neue Kurse)", "sicher gebucht"] + (["Kapazität"] if kap else [])
    sa._chart(opt)


def _gruppen_chart(pg) -> None:
    from . import seite_auswertung as sa

    t = sa._T()
    farben = {"lang": t["akzent"], "vorbereitung": t.get("blau", "#5b8def"), "ibtz": t.get("orange", "#d68910"),
              "uebrige": t["text3"]}
    opt = sa._chart_basis()
    opt["xAxis"]["data"] = [f"{MON[z.monat.month - 1]} {z.monat.year % 100}" for z in pg.zeilen]
    opt["yAxis"]["scale"] = False
    opt["grid"]["top"] = 44
    opt["series"] = [{"name": mk.GRUPPEN[g], "type": "bar", "stack": "g", "barMaxWidth": 18,
                      "data": [round(z.je_gruppe.get(g, 0.0), 1) for z in pg.zeilen],
                      "itemStyle": {"color": farben[g], "opacity": .85}, "areaStyle": {"color": farben[g]}}
                     for g in REIHEN if any(z.je_gruppe.get(g) for z in pg.zeilen)]
    sa._chart(opt)
    ui.label("Je Monat: Ist bzw. Prognose (gebucht + erwartet), aufgeteilt nach Gruppen.").classes("m-zweite")


def _tabelle(a, pg) -> None:
    einheit = "Betten" if pg.internat else "TN"
    with ui.element("section").classes("m-block m-breit"):
        ui.label("Hauptmaßnahmen, Vorbereitung und IBTZ").classes("m-btitel")
        anteile, gesamt = mk.internat_anteile()
        with tabelle("minmax(110px, 1.2fr) minmax(150px, 1.2fr) auto auto auto auto auto auto auto"):
            with ui.element("div").classes("m-raster m-tkopf"):
                for t in ("Art", "Gruppe", f"heute ({einheit})", "in 6 Mon.", "in 12 Mon.", "nächster Start", "Kursgröße",
                          "Verbleib", "Internat"):
                    ui.label(t)
            for f in pg.familien:
                with ui.element("div").classes("m-raster m-zeile"):
                    ui.label(f.familie).classes("m-name")
                    ui.select({k: v for k, v in mk.GRUPPEN.items()}, value=f.gruppe,
                              on_change=lambda e, fam=f.familie: a.aendern(mk.zuordnung_schritt, fam, e.value)).classes(
                        "m-feld").props('dense borderless dark options-dense popup-content-class="m-popup"')
                    for w in (f.heute, f.in6, f.in12):
                        ui.label(_z(w)).classes("m-mono")
                    attr(ui.label(f"{f.naechster:%m/%Y} · {f.naechster_wie}" if f.naechster else "–").classes("m-mono"),
                         title="gebucht = steht schon im Pivot · erwartet = aus dem Rhythmus der Vorjahre · geplant = eigene Plätze")
                    ui.label(_z(f.kursgroesse)).classes("m-mono")
                    ui.label(f"{round(100 * f.verbleib)} %" if f.verbleib is not None else "–").classes("m-mono")
                    q = anteile.get(f.familie)
                    ui.label(f"{round(100 * q)} %" if q is not None else (f"≈{round(100 * gesamt)} %" if gesamt is not None else "–")
                             ).classes("m-mono")
        ui.label("Kursgröße = höchste Teilnehmerzahl je Kurs (Median der letzten 3 Jahre) · Verbleib = Teilnehmende am "
                 "Kursende ÷ zu Beginn · Internat = 1 − Pendler-Anteil laut Anreiselisten (≈ = Anteil über alle Kurse). "
                 "Gruppe änderbar: „ohne Zimmer“ nimmt eine Art aus der Prognose.").classes("m-xk-hinweis")


def _neue(pg) -> None:
    with ui.expansion(f"Erwartete neue Kurse ({len(pg.neu)})").classes("m-block m-breit m-rv-exp"):
        if not pg.neu:
            ui.label("Keine – alle Starts im Zeitraum sind schon gebucht.").classes("m-zweite")
            return
        with tabelle("auto minmax(140px, 1fr) auto auto"):
            with ui.element("div").classes("m-raster m-tkopf"):
                for t in ("Start", "Art", "Größe (Spanne)", "Grundlage"):
                    ui.label(t)
            for e in pg.neu:
                with ui.element("div").classes("m-raster m-zeile"):
                    ui.label(f"{e.start:%d.%m.%Y}").classes("m-mono")
                    ui.label(e.familie).classes("m-name")
                    ui.label(f"{_z(e.spitze)} ({_z(max(e.klein) if e.klein else 0)}–{_z(max(e.gross) if e.gross else 0)})").classes("m-mono")
                    ui.label("eigene Plätze" if e.herkunft == "geplant" else "wie in den Vorjahren").classes("m-zweite")


def _test(tests: list) -> None:
    with ui.element("section").classes("m-block m-breit"):
        ui.label("Wie gut wäre die Prognose gewesen? (Rückwärtstest)").classes("m-btitel")
        if not tests:
            ui.label("Dafür braucht es mindestens drei Jahre im Maßnahmen-Pivot.").classes("m-zweite")
            return
        for t in tests:
            with ui.element("div").classes("m-liste-zeile"):
                ui.label(str(t.jahr)).classes("m-name")
                ui.label(f"Jan–Jun: {_pz(t.h1)}").classes("m-mono")
                ui.label(f"Jul–Dez: {_pz(t.h2)}").classes("m-mono")
        ui.label("Stichtag jeweils 1. Januar, Summe aller Gruppen außer „ohne Zimmer“, mittlere Abweichung je Monat. Laufende "
                 "Kurse sind mit ihrem tatsächlichen Verlauf gerechnet (damals war nur der gebuchte Stand bekannt) – der "
                 "Test ist dadurch etwas zu günstig. Das zweite Halbjahr hängt an den neuen Kursen: eigene geplante Plätze "
                 "machen es genauer.").classes("m-xk-hinweis")


def _pz(x: float | None) -> str:
    if x is None:
        return "–"
    return "±0 %" if round(x) == 0 else f"{round(x):+d} %".replace("-", "−")


def _abgleich_block(zeilen: list) -> None:
    with ui.expansion("Abgleich mit dem Standort-Pivot").classes("m-block m-breit m-rv-exp"):
        if not zeilen:
            ui.label("Der Standort-Pivot (Belegung) ist nicht geladen oder enthält diesen Standort nicht.").classes("m-zweite")
            return
        with tabelle("auto auto auto auto"):
            with ui.element("div").classes("m-raster m-tkopf"):
                for t in ("Monat", "Teilnehmende (Maßnahmen-Pivot)", "Standort-Pivot", "Verhältnis"):
                    ui.label(t)
            for m, tn, st in zeilen:
                with ui.element("div").classes("m-raster m-zeile"):
                    ui.label(f"{MON[m.month - 1]} {m.year}").classes("m-mono")
                    ui.label(_z(tn)).classes("m-mono")
                    ui.label(_z(st)).classes("m-mono")
                    ui.label(f"{round(100 * st / tn)} %" if tn else "–").classes("m-mono")
        q = [st / tn for _m, tn, st in zeilen if tn and st]
        if q:
            mittel = sum(q) / len(q)
            ui.label(f"Im Mittel {round(100 * mittel)} %. Nahe 100 %: der Standort-Pivot zählt alle Teilnehmenden. Deutlich "
                     "darunter (etwa beim Internatsanteil): er zählt nur das Internat. Große Sprünge in einzelnen Monaten "
                     "deuten auf fehlende oder doppelte Daten hin.").classes("m-xk-hinweis")


def _plaetze_panel(a) -> None:
    pg = a.daten.get("pg")
    familien = [f.familie for f in pg.familien] if pg else []
    eintraege = mk.stand()["plaetze"]
    wahl = {"familie": familien[0] if familien else "", "monat": f"{a.heute.year + 1}-06", "plaetze": 20}

    def bauen():
        ui.label("Geplante Plätze ersetzen die Schätzung für diesen Start (gleiche Art, ±6 Wochen). Gibt es dort noch "
                 "keinen erwarteten Kurs, wird einer mit dem üblichen Verlauf der Art angelegt.").classes("m-ptext")
        for p in eintraege:
            with ui.element("div").classes("m-liste-zeile"):
                ui.label(f"{p['familie']} · {p['monat']}").classes("m-name")
                ui.label(f"{p['plaetze']} Plätze").classes("m-mono")
                knopf("", lambda p=p: a.aendern(mk.plaetze_schritt, p["familie"], p["monat"], None), "leise", "delete",
                      "Eintrag entfernen")
        with ui.element("div").classes("m-kap").style("grid-template-columns: 2fr 1fr 1fr"):
            ui.select(familien, value=wahl["familie"] or None, label="Art",
                      on_change=lambda e: wahl.__setitem__("familie", e.value)).classes("m-feld").props(
                'dense outlined dark popup-content-class="m-popup"')
            ui.input("Startmonat (JJJJ-MM)", value=wahl["monat"], on_change=lambda e: wahl.__setitem__("monat", e.value)).classes(
                "m-feld").props("dense outlined dark")
            ui.number("Plätze", value=wahl["plaetze"], min=1, step=1, format="%d",
                      on_change=lambda e: wahl.__setitem__("plaetze", e.value)).classes("m-feld").props("dense outlined dark")

        async def speichern():
            if not wahl["familie"] or len(str(wahl["monat"])) != 7:
                a.toast("Bitte Art und Startmonat (z. B. 2027-06) angeben.", fehler=True)
                return
            if await a.aendern(mk.plaetze_schritt, wahl["familie"], wahl["monat"], int(wahl["plaetze"] or 0)):
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            knopf("Hinzufügen", speichern, "primaer", "add")
            knopf("Schließen", a.panel_zu, "leise")
    a.panel("Geplante Plätze", bauen)


# ---- Auswahl und Vergleich (0.52) -----------------------------------------------------------------------

KURZ = {"lang": "Haupt", "vorbereitung": "Vorb.", "ibtz": "IBTZ", "uebrige": "übrige", "ohne": "ohne Zimmer"}


def _auswahl(a, d) -> None:
    optionen = {f: f"{f} · {KURZ.get(g, g)}" for f, g, _t in d["liste"]}
    ui.select(optionen, value=d["auswahl"], multiple=True, with_input=True, label="Maßnahmen (leer = alle)",
              on_change=lambda e: a.setzen(mn_auswahl=list(e.value or []), nur_seite=True)).classes("m-feld").props(
        'dense outlined dark use-chips clearable options-dense popup-content-class="m-popup"').style("min-width:340px;max-width:620px")
    if len(d["auswahl"]) >= 2:
        segmente({"summe": "Summe", "vergleich": "Vergleich"}, d["modus"], lambda v: a.setzen(mn_modus=v, nur_seite=True),
                 sofort=True)
    hauptarten = [f for f, g, _t in d["liste"] if g == "lang"]
    if hauptarten and d["auswahl"] != hauptarten:
        knopf("Alle Hauptmaßnahmen", lambda: a.setzen(mn_auswahl=hauptarten, nur_seite=True), "leise", "checklist")


def _vergleich_chart(je: dict) -> None:
    from . import seite_auswertung as sa

    t = sa._T()
    farben = [t["akzent"], t.get("blau", "#5b8def"), t.get("orange", "#d68910"), t.get("gruen", "#3aa76d"),
              t.get("rot", "#d64545"), "#9b6bd6", "#c2a14a", "#4fb3bf", t["text2"], "#d67fa6"]
    if not je:
        ui.label("Keine Daten für die Auswahl.").classes("m-zweite")
        return
    erste = next(iter(je.values()))
    x = [f"{MON[z.monat.month - 1]} {z.monat.year % 100}" for z in erste.zeilen]
    h = next((i for i, z in enumerate(erste.zeilen) if z.art == "prognose"), len(x) - 1)
    opt = sa._chart_basis()
    opt["xAxis"]["data"] = x
    opt["xAxis"]["boundaryGap"] = False
    opt["yAxis"]["scale"] = False
    opt["grid"]["top"] = 44
    opt["legend"]["type"] = "scroll"
    reihen = []
    for i, (fam, pg) in enumerate(je.items()):
        f = farben[i % len(farben)]
        werte = [round(z.summe, 1) for z in pg.zeilen]
        reihen.append({"name": fam, "type": "line", "symbol": "none", "data": [w if k <= h else None for k, w in enumerate(werte)],
                       "lineStyle": {"color": f, "width": 2.5}})
        reihen.append({"name": fam, "type": "line", "symbol": "none", "data": [w if k >= h else None for k, w in enumerate(werte)],
                       "lineStyle": {"color": f, "width": 2.5, "type": "dashed"}})
    reihen[0]["markArea"] = {"silent": True, "itemStyle": {"color": t["akzent"], "opacity": .05},
                             "label": {"show": True, "position": "insideTopLeft", "color": t["text3"], "formatter": "Prognose"},
                             "data": [[{"xAxis": x[h]}, {"xAxis": x[-1]}]]}
    opt["series"] = reihen
    opt["legend"]["data"] = list(je)
    sa._chart(opt)


def _pfeil(x: float | None) -> tuple[str, str]:
    if x is None:
        return "–", ""
    p = round(100 * x)
    return (f"{p:+d} %".replace("-", "−") if p else "±0 %"), ("m-krit" if p <= -10 else "m-ok" if p >= 10 else "")


def _vergleich_tabelle(d) -> None:
    zeilen = d.get("vergleich") or []
    if not zeilen:
        return
    einheit = "Betten" if d["internat"] else "TN"
    with ui.element("section").classes("m-block m-breit"):
        ui.label("Maßnahmen im Vergleich" + ("" if d["auswahl"] else " – alle Hauptmaßnahmen, Vorbereitung und IBTZ")).classes(
            "m-btitel")
        with ui.element("div").classes("m-tab-scroll"):
            with tabelle("minmax(110px, 1.2fr) auto auto auto auto auto auto auto auto auto auto"):
                with ui.element("div").classes("m-raster m-tkopf"):
                    for t in ("Art", "Gruppe", "TN-Tage 12 Mon.", "Trend z. Vorjahr", "Starts/Jahr", "Kursgröße (früher)",
                              "Verbleib", "Internat", f"heute ({einheit})", "in 12 Mon.", "in 24 Mon."):
                        ui.label(t)
                for z in sorted(zeilen, key=lambda z: -z.tage_12m):
                    with ui.element("div").classes("m-raster m-zeile"):
                        ui.label(z.familie).classes("m-name")
                        ui.label(KURZ.get(z.gruppe, z.gruppe)).classes("m-zweite")
                        ui.label(_z(z.tage_12m)).classes("m-mono")
                        txt, kl = _pfeil(z.trend)
                        ui.label(txt).classes(f"m-mono {kl}")
                        ui.label(_z(z.starts_jahr, 1)).classes("m-mono")
                        g, gv = _z(z.groesse), _z(z.groesse_vorher)
                        ui.label(f"{g} ({gv})").classes("m-mono")
                        ui.label(f"{round(100 * z.verbleib)} %" if z.verbleib is not None else "–").classes(
                            "m-mono" + (" m-krit" if z.verbleib is not None and z.verbleib < .6 else ""))
                        ui.label(f"{round(100 * z.internat)} %" if z.internat is not None else "–").classes("m-mono")
                        for w in (z.heute, z.in12, z.in24):
                            ui.label(_z(w)).classes("m-mono")
        ui.label("Lesart für die Leitung: Trend = Teilnehmertage der letzten 12 Monate gegen die 12 Monate davor · Kursgröße "
                 "= Median der Kurse der letzten 3 Jahre (in Klammern die 3 Jahre davor) · Verbleib = am Kursende noch dabei "
                 "(rot unter 60 %) · Internat = Anteil ohne P laut Anreiselisten. Ob sich eine Maßnahme lohnt, lässt sich "
                 "daraus nur zur Nachfrage sagen – für Wirtschaftlichkeit fehlen Erlöse und Kosten je Maßnahme.").classes(
            "m-xk-hinweis")
