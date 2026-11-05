"""Auswertung → Maßnahmen (0.53): Maßnahmen im Vergleich – Teilnehmende je Maßnahmenart, jede als eigene Kurve
(Ist und Prognose = gebuchter Bestand + erwartete neue Kurse). Keine Betten und keine Summe – die Internatsbelegung
steht in der allgemeinen Prognose. Darstellung: ein gemeinsames Diagramm oder je Maßnahme ein kleines Diagramm.
Rechnet in ``massnahmen_kern``."""

from __future__ import annotations

from nicegui import ui

from . import massnahmen_kern as mk
from .ui_bausteine import knopf, leer, segmente, tabelle

MON = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
KURZ = {"lang": "Haupt", "vorbereitung": "Vorb.", "ibtz": "IBTZ", "uebrige": "übrige", "ohne": "ohne Zimmer"}
FARBEN_EXTRA = ["#9b6bd6", "#c2a14a", "#4fb3bf", "#d67fa6", "#7a8f3a", "#b5654a", "#5c7fb8", "#8c8c8c"]
EIN_DIAGRAMM_BIS = 5


def _z(x: float | None, nk: int = 0) -> str:
    return "–" if x is None else f"{x:,.{nk}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def daten(a) -> None:
    vor = int(getattr(a, "mn_vor", 24) or 24)
    roh = mk._roh()
    liste = mk.familien_liste(roh, a.heute)
    gr = {f: g for f, g, _t in liste}
    auswahl = [f for f in (getattr(a, "mn_auswahl", None) or []) if f in gr]
    # leer = alle Arten mit Teilnehmenden in den letzten 12 Monaten (ohne „ohne Zimmer“), größte zuerst
    arten = auswahl or [f for f, g, t in liste if g != "ohne" and t > 0]
    darstellung = getattr(a, "mn_darstellung", None) or ("ein" if len(arten) <= EIN_DIAGRAMM_BIS else "je")
    d = {"stand": mk.stand(), "vor": vor, "liste": liste, "auswahl": auswahl, "arten": arten, "darstellung": darstellung,
         "skala": getattr(a, "mn_skala", "gleich"), "je": {}, "vergleich": [], "tests": [], "tests_ohne": [], "neu": [],
         "quelle": "", "verbleib": 0}
    if arten:
        vl = mk.vorlauf_messen()
        d["je"] = mk.je_familie(roh, a.heute, arten, 12, vor, False, vl)
        d["vergleich"] = mk.vergleich(roh, a.heute, arten, False, vl)
        d["tests"] = mk.rueckwaertstest(roh)
        d["tests_ohne"] = mk.rueckwaertstest(roh, verbleib=False)
        p0 = next(iter(d["je"].values()), None)
        d["quelle"] = p0.nachbuchung_quelle if p0 else mk.pickup_kurve(vl).quelle
        d["verbleib"] = sum(p.mit_verbleib for p in d["je"].values())
        d["neu"] = sorted((e for p in d["je"].values() for e in p.neu), key=lambda e: (e.start, e.familie))
    a.daten = d


def zeichnen(a) -> None:
    d = a.daten
    with a.leiste:
        optionen = {f: f"{f} · {KURZ.get(g, g)}" for f, g, _t in d["liste"]}
        ui.select(optionen, value=d["auswahl"], multiple=True, with_input=True, label="Maßnahmen (leer = alle)",
                  on_change=lambda e: a.setzen(mn_auswahl=list(e.value or []), mn_darstellung=None, nur_seite=True)).classes(
            "m-feld").props('dense outlined dark use-chips clearable options-dense popup-content-class="m-popup"').style(
            "min-width:320px;max-width:620px")
        haupt = [f for f, g, _t in d["liste"] if g == "lang"]
        if haupt and d["auswahl"] != haupt:
            knopf("Nur Hauptmaßnahmen", lambda: a.setzen(mn_auswahl=haupt, mn_darstellung=None, nur_seite=True), "leise",
                  "checklist")
        segmente({"ein": "Ein Diagramm", "je": "Je Maßnahme"}, d["darstellung"],
                 lambda v: a.setzen(mn_darstellung=v, nur_seite=True), sofort=True)
        if d["darstellung"] == "je":
            segmente({"gleich": "gleiche Skala", "eigen": "eigene Skala"}, d["skala"],
                     lambda v: a.setzen(mn_skala=v, nur_seite=True), sofort=True)
        segmente({12: "12 Monate", 24: "24 Monate", 36: "36 Monate"}, d["vor"],
                 lambda v: a.setzen(mn_vor=v, nur_seite=True), sofort=True)
        knopf("Geplante Plätze …", lambda: _plaetze_panel(a), "", "event_seat").style("margin-left:auto")
    with a.inhalt:
        if not d["stand"]["pivot"]:
            leer("Noch kein Maßnahmen-Pivot eingelesen. Unter Daten & Import → „Maßnahmen-Prognose“ hochladen.")
            knopf("Zu Daten & Import", lambda: a.oeffnen("daten"), "primaer", "upload_file")
            return
        if not d["je"]:
            leer("Für diese Auswahl gibt es keine Daten.")
            return
        with ui.element("div").classes("m-rv"):
            pv = d["stand"]["pivot"]
            ui.label(f"Teilnehmende je Maßnahmenart (alle, nicht nur Internat) · Maßnahmen-Pivot {pv['von'][:10]} – "
                     f"{pv['bis'][:10]}" + (" · überbrückt: " + ", ".join(f"{x[0][:10]}–{x[1][:10]}" for x in pv["luecken"])
                                           if pv.get("luecken") else "")).classes("m-zweite").style("white-space:normal")
            _kpis(d["vergleich"])
            with ui.element("section").classes("m-block m-breit"):
                ui.label(f"{len(d['je'])} Maßnahme(n) – Ist und Prognose, {d['vor']} Monate").classes("m-btitel")
                if d["darstellung"] == "ein":
                    _ein_diagramm(d["je"])
                else:
                    _raster(d["je"], d["skala"] == "gleich")
                ui.label("Durchgezogen = Ist · gestrichelt = Prognose (gebucht + erwartete neue Kurse aus den Vorjahren) · "
                         "hell hinterlegt = Prognosezeitraum · in der Legende lassen sich Linien aus- und einblenden.").classes(
                    "m-zweite").style("white-space:normal")
            _vergleich_tabelle(a, d)
            _neue_liste(d["neu"])
            _test(d["tests"], d["tests_ohne"], d["quelle"], d["verbleib"])


def _farben() -> list[str]:
    from . import seite_auswertung as sa

    t = sa._T()
    return [t["akzent"], t.get("blau", "#5b8def"), t.get("orange", "#d68910"), t.get("gruen", "#3aa76d"),
            t.get("rot", "#d64545")] + FARBEN_EXTRA


def _achsen(pg) -> tuple[list[str], int]:
    x = [f"{MON[z.monat.month - 1]} {z.monat.year % 100}" for z in pg.zeilen]
    h = next((i for i, z in enumerate(pg.zeilen) if z.art == "prognose"), len(x) - 1)
    return x, h


def _linien(name: str, pg, farbe: str, h: int) -> list[dict]:
    werte = [round(z.summe, 1) for z in pg.zeilen]
    return [{"name": name, "type": "line", "symbol": "none", "data": [w if k <= h else None for k, w in enumerate(werte)],
             "lineStyle": {"color": farbe, "width": 2.5}},
            {"name": name, "type": "line", "symbol": "none", "data": [w if k >= h else None for k, w in enumerate(werte)],
             "lineStyle": {"color": farbe, "width": 2.5, "type": "dashed"}}]


def _prognosebereich(t: dict, x: list, h: int) -> dict:
    return {"silent": True, "itemStyle": {"color": t["akzent"], "opacity": .05},
            "label": {"show": True, "position": "insideTopLeft", "color": t["text3"], "formatter": "Prognose"},
            "data": [[{"xAxis": x[h]}, {"xAxis": x[-1]}]]}


def _ein_diagramm(je: dict) -> None:
    from . import seite_auswertung as sa

    t = sa._T()
    farben = _farben()
    x, h = _achsen(next(iter(je.values())))
    opt = sa._chart_basis()
    opt["xAxis"]["data"] = x
    opt["xAxis"]["boundaryGap"] = False
    opt["yAxis"]["scale"] = False
    opt["yAxis"]["name"] = "Teilnehmende"
    opt["grid"]["top"] = 50
    opt["legend"]["type"] = "scroll"
    reihen = []
    for i, (fam, pg) in enumerate(je.items()):
        reihen += _linien(fam, pg, farben[i % len(farben)], h)
    reihen[0]["markArea"] = _prognosebereich(t, x, h)
    opt["series"] = reihen
    opt["legend"]["data"] = list(je)
    sa._chart(opt)


def _raster(je: dict, gleiche_skala: bool) -> None:
    """Je Maßnahme ein kleines Diagramm – gleicher Zeitraum, wahlweise gleiche Skala."""
    from . import seite_auswertung as sa

    t = sa._T()
    farben = _farben()
    hoch = max((z.summe for pg in je.values() for z in pg.zeilen), default=0) * 1.1 or None
    with ui.element("div").classes("m-mn-raster"):
        for i, (fam, pg) in enumerate(je.items()):
            x, h = _achsen(pg)
            jetzt = pg.zeilen[h].summe
            in12 = pg.zeilen[min(len(pg.zeilen) - 1, h + 12)].summe
            with ui.element("div").classes("m-mn-kachel"):
                with ui.element("div").classes("m-zeile-flex"):
                    ui.label(fam).classes("m-name")
                    ui.label(f"heute {_z(jetzt)} · in 12 Mon. {_z(in12)}").classes("m-zweite").style("margin-left:auto")
                opt = sa._chart_basis()
                opt["xAxis"]["data"] = x
                opt["xAxis"]["boundaryGap"] = False
                opt["yAxis"]["scale"] = False
                if gleiche_skala and hoch:
                    opt["yAxis"]["max"] = round(hoch)
                opt["grid"] = {"left": 34, "right": 8, "top": 10, "bottom": 22}
                opt["legend"] = {"show": False}
                reihen = _linien(fam, pg, farben[i % len(farben)], h)
                reihen[0]["markArea"] = {**_prognosebereich(t, x, h), "label": {"show": False}}
                opt["series"] = reihen
                sa._chart(opt)


def _kpis(zeilen: list) -> None:
    from .seite_steuerung import _kpi

    mit_trend = [z for z in zeilen if z.trend is not None and z.tage_vorjahr >= 365]
    mit_verbleib = [z for z in zeilen if z.verbleib is not None]
    with ui.element("div").classes("m-kpis"):
        if mit_trend:
            hoch = max(mit_trend, key=lambda z: z.trend)
            tief = min(mit_trend, key=lambda z: z.trend)
            _kpi("Am stärksten gewachsen", hoch.familie, f"{_pfeil(hoch.trend)[0]} Teilnehmertage zum Vorjahr", "")
            _kpi("Am stärksten geschrumpft", tief.familie, f"{_pfeil(tief.trend)[0]} Teilnehmertage zum Vorjahr",
                 "krit" if tief.trend <= -.1 else "")
        if mit_verbleib:
            gut = max(mit_verbleib, key=lambda z: z.verbleib)
            schlecht = min(mit_verbleib, key=lambda z: z.verbleib)
            _kpi("Höchster Verbleib", gut.familie, f"{round(100 * gut.verbleib)} % bis Kursende")
            _kpi("Niedrigster Verbleib", schlecht.familie, f"{round(100 * schlecht.verbleib)} % bis Kursende",
                 "krit" if schlecht.verbleib < .6 else "")


def _vergleich_tabelle(a, d) -> None:
    zeilen = d["vergleich"]
    if not zeilen:
        return
    gr = {f: g for f, g, _t in d["liste"]}
    with ui.element("section").classes("m-block m-breit"):
        ui.label("Maßnahmen im Vergleich").classes("m-btitel")
        with ui.element("div").classes("m-tab-scroll"):
            with tabelle("minmax(110px, 1.2fr) minmax(120px, 1fr) auto auto auto auto auto auto auto auto"):
                with ui.element("div").classes("m-raster m-tkopf"):
                    for t in ("Maßnahme", "Gruppe", "TN-Tage 12 Mon.", "Trend z. Vorjahr", "Starts/Jahr", "Kursgröße (früher)",
                              "Verbleib", "heute", "in 12 Mon.", "in 24 Mon."):
                        ui.label(t)
                for z in sorted(zeilen, key=lambda z: -z.tage_12m):
                    with ui.element("div").classes("m-raster m-zeile"):
                        ui.label(z.familie).classes("m-name")
                        ui.select(mk.GRUPPEN, value=gr.get(z.familie, z.gruppe),
                                  on_change=lambda e, fam=z.familie: a.aendern(mk.zuordnung_schritt, fam, e.value)).classes(
                            "m-feld").props('dense borderless dark options-dense popup-content-class="m-popup"')
                        ui.label(_z(z.tage_12m)).classes("m-mono")
                        txt, kl = _pfeil(z.trend)
                        ui.label(txt).classes(f"m-mono {kl}")
                        ui.label(_z(z.starts_jahr, 1)).classes("m-mono")
                        ui.label(f"{_z(z.groesse)} ({_z(z.groesse_vorher)})").classes("m-mono")
                        ui.label(f"{round(100 * z.verbleib)} %" if z.verbleib is not None else "–").classes(
                            "m-mono" + (" m-krit" if z.verbleib is not None and z.verbleib < .6 else ""))
                        for w in (z.heute, z.in12, z.in24):
                            ui.label(_z(w)).classes("m-mono")
        ui.label("Teilnehmende (alle, nicht nur Internat) · Trend = Teilnehmertage der letzten 12 Monate gegen die 12 Monate "
                 "davor (grün ab +10 %, rot ab −10 %) · Kursgröße = Median der Kurse der letzten 3 Jahre, in Klammern die 3 "
                 "Jahre davor · Verbleib = am Kursende noch dabei (rot unter 60 %) · Gruppe änderbar („Hauptmaßnahmen“ = "
                 "Knopf „Nur Hauptmaßnahmen“). Ob sich eine Maßnahme wirtschaftlich lohnt, zeigt das nicht – dafür fehlen "
                 "Erlöse und Kosten.").classes("m-xk-hinweis")


def _neue_liste(neu: list) -> None:
    _neue(type("P", (), {"neu": neu})())


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
                    ui.label({"geplant": "eigene Plätze", "Nachbuchung": "erwartete Nachbuchung zum gebuchten Kurs",
                              "Sockel": "Kurzkurse: Sockel wie in den Vorjahren"}.get(e.herkunft, "wie in den Vorjahren")
                             ).classes("m-zweite")


def _test(tests: list, ohne: list | None = None, quelle: str = "", verbleib: int = 0) -> None:
    with ui.element("section").classes("m-block m-breit"):
        ui.label("Wie gut wäre die Prognose gewesen? (Rückwärtstest)").classes("m-btitel")
        if not tests:
            ui.label("Dafür braucht es mindestens drei Jahre im Maßnahmen-Pivot.").classes("m-zweite")
            return
        o = {t.jahr: t for t in ohne or []}
        with tabelle("70px auto auto minmax(180px, 1fr)"):
            with ui.element("div").classes("m-raster m-tkopf"):
                for k in ("Jahr", "Jan–Jun", "Jul–Dez", "zum Vergleich: ohne Verbleib"):
                    ui.label(k)
            for t in tests:
                x = o.get(t.jahr)
                with ui.element("div").classes("m-raster m-zeile"):
                    ui.label(str(t.jahr)).classes("m-name")
                    ui.label(_pz(t.h1)).classes("m-mono")
                    ui.label(_pz(t.h2)).classes("m-mono")
                    ui.label(f"{_pz(x.h1)} · {_pz(x.h2)}" if x else "–").classes("m-mono m-zweite")
        ui.label("Stichtag jeweils 1. Januar, nur mit dem Wissen von damals: laufende Kurse mit ihrem Bestand am Stichtag "
                 "und der damals bekannten Verbleibskurve, alle späteren Kurse geschätzt, als wäre noch keiner gebucht "
                 "(eher strenger als die Wirklichkeit). Mittlere Abweichung je Monat, Summe aller Gruppen außer „ohne "
                 "Zimmer“. Das zweite Halbjahr hängt an den neuen Kursen – eigene geplante Plätze machen es genauer."
                 ).classes("m-xk-hinweis")
        ui.label(f"So wird gerechnet: gebuchte Kurse × Verbleib früherer Kurse derselben Art ({verbleib} Arten mit Kurve) · "
                 f"teilweise gebuchte Kurse plus erwartete Nachbuchung ({quelle}) · neue Kurse mit dem Verlauf der "
                 "Vorjahre · Kurzkurse als Sockel je Monat.").classes("m-xk-hinweis")


def _pz(x: float | None) -> str:
    if x is None:
        return "–"
    return "±0 %" if round(x) == 0 else f"{round(x):+d} %".replace("-", "−")


def _pfeil(x: float | None) -> tuple[str, str]:
    if x is None:
        return "–", ""
    p = round(100 * x)
    return (f"{p:+d} %".replace("-", "−") if p else "±0 %"), ("m-krit" if p <= -10 else "m-ok" if p >= 10 else "")


def _plaetze_panel(a) -> None:
    familien = list(a.daten.get("arten") or [])
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
