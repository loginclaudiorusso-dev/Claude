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
    internat = bool(getattr(a, "mn_internat", False))
    vor = int(getattr(a, "mn_vor", 24) or 24)
    roh = mk._roh()
    pg = mk.prognose(roh, a.heute, 12, vor, internat)
    d = {"pg": pg, "stand": mk.stand(), "internat": internat, "vor": vor}
    if pg is not None:
        d["tests"] = mk.rueckwaertstest(roh)
        d["abgleich"] = _abgleich(roh, a.heute)
    a.daten = d


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
        segmente({False: "Teilnehmende", True: "Internat (Betten)"}, d["internat"],
                 lambda v: a.setzen(mn_internat=v, nur_seite=True), sofort=True)
        segmente({12: "12 Monate", 24: "24 Monate"}, d["vor"], lambda v: a.setzen(mn_vor=v, nur_seite=True), sofort=True)
        knopf("Geplante Plätze …", lambda: _plaetze_panel(a), "", "event_seat").style("margin-left:auto")
    pg = d["pg"]
    with a.inhalt:
        if pg is None:
            leer("Noch kein Maßnahmen-Pivot eingelesen. Unter Daten & Import → „Maßnahmen-Prognose“ hochladen.")
            knopf("Zu Daten & Import", lambda: a.oeffnen("daten"), "primaer", "upload_file")
            return
        with ui.element("div").classes("m-rv"):
            _kopf(a, d, pg)
            _kpis(pg)
            with ui.element("section").classes("m-block m-breit"):
                ui.label(("Internat (Betten)" if pg.internat else "Teilnehmende") + " je Maßnahmengruppe – Ist, gebucht und "
                         "erwartet").classes("m-btitel")
                _chart(pg)
                ui.label("Fläche = Ist bzw. gebucht + erwartete neue Kurse je Gruppe · gestrichelt: Spanne der neuen Kurse "
                         "(kleineres/größeres der beiden Vorjahre) · senkrechte Linie = heute.").classes("m-zweite").style(
                    "white-space:normal")
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


def _kpis(pg) -> None:
    jetzt = next((z for z in pg.zeilen if z.art == "prognose"), pg.zeilen[-1])
    idx = pg.zeilen.index(jetzt)

    def in_(n):
        z = pg.zeilen[min(len(pg.zeilen) - 1, idx + n)]
        return z, f"{_z(z.summe - z.erwartet + z.klein)}–{_z(z.summe - z.erwartet + z.gross)}"
    einheit = "Betten" if pg.internat else "Teilnehmende"
    from .seite_steuerung import _kpi

    with ui.element("div").classes("m-kpis"):
        _kpi(f"{einheit} {MON[jetzt.monat.month - 1]} {jetzt.monat.year}", _z(jetzt.summe),
             f"davon Hauptmaßnahmen {_z(jetzt.je_gruppe.get('lang', 0))}")
        for n in (6, 12):
            z, sp = in_(n)
            _kpi(f"in {n} Monaten ({MON[z.monat.month - 1]} {z.monat.year})", _z(z.summe),
                 f"gebucht {_z(z.gebucht)} + erwartet {_z(z.erwartet)} · Spanne {sp}")
        geplant = sum(1 for e in pg.neu if e.herkunft == "geplant")
        _kpi("Erwartete neue Kurse", str(len(pg.neu)), f"davon {geplant} mit eigenen Plätzen" if geplant else
             "aus dem Rhythmus der Vorjahre")


def _chart(pg) -> None:
    from . import seite_auswertung as sa

    t = sa._T()
    farben = {"lang": t["akzent"], "vorbereitung": t.get("blau", "#5b8def"), "ibtz": t.get("orange", "#d68910"),
              "uebrige": t["text3"]}
    opt = sa._chart_basis()
    x = [f"{MON[z.monat.month - 1]} {z.monat.year % 100}" for z in pg.zeilen]
    opt["xAxis"]["data"] = x
    opt["xAxis"]["boundaryGap"] = False
    opt["yAxis"]["scale"] = False
    opt["grid"]["top"] = 44
    opt["legend"]["type"] = "scroll"
    reihen = []
    for g in REIHEN:
        if not any(z.je_gruppe.get(g) for z in pg.zeilen):
            continue
        reihen.append({"name": mk.GRUPPEN[g], "type": "line", "stack": "summe", "symbol": "none",
                       "data": [round(z.je_gruppe.get(g, 0.0), 1) for z in pg.zeilen],
                       "lineStyle": {"color": farben[g], "width": 1}, "areaStyle": {"color": farben[g], "opacity": .35}})
    for name, feld in (("Spanne unten", "klein"), ("Spanne oben", "gross")):
        reihen.append({"name": name, "type": "line", "symbol": "none",
                       "data": [None if z.art == "ist" else round(z.summe - z.erwartet + getattr(z, feld), 1) for z in pg.zeilen],
                       "lineStyle": {"color": t["text2"], "width": 1, "type": "dashed"}})
    heute = next((i for i, z in enumerate(pg.zeilen) if z.art == "prognose"), None)
    if heute is not None and reihen:
        reihen[0]["markLine"] = {"silent": True, "symbol": "none", "lineStyle": {"color": t["text3"], "type": "solid"},
                                 "label": {"formatter": "heute", "color": t["text3"]}, "data": [{"xAxis": x[heute]}]}
    opt["series"] = reihen
    sa._chart(opt)


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
