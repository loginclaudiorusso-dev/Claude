"""Bestandsprognose der Maßnahmen (0.79) – zwei Sichten auf dieselbe Rechnung:

* **Planung (für die Kollegen):** eine klare Ansage je Maßnahmeart – „Plane mit X · davon Y sicher“ – ohne Spannen.
* **Leitung (für die Geschäftsführung):** Verlauf mit 80 %-Spanne, drei Szenarien mit Auslöser, Frühindikator,
  Zerlegung nach Herkunft, Treffsicherheit im Rückblick und **Wenn-dann**: Klick auf einen künftigen Monat →
  „Wenn wir dann X haben – wie geht es weiter?“."""

from __future__ import annotations

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
    with a.werkzeuge:
        segmente({"planung": "Planung", "leitung": "Leitung"}, sicht, lambda v: a.setzen(mn_sicht=v, laden=False))
        ui.select({"Alle": "Alle Maßnahmen", **{x: x for x in md.arten}}, value=art,
                  on_change=lambda e: a.setzen(mn_art=e.value, laden=False)).props(
            'dense outlined dark options-dense popup-content-class="m-popup"').style("width:230px")
    if sicht == "leitung":
        with a.leiste:
            knopf("Szenarien …", lambda: _szenarien_panel(a, d["szen"]), "", "tune")
    a.status_info = (f"Stichtag {erg['letzter']:%d.%m.%Y} · {len(md.faelle)} Aufenthalte · {bp.DURCHLAEUFE} "
                     "durchgerechnete Verläufe")
    with a.inhalt, ui.element("div").classes("m-rv m-bst"):
        (_planung if sicht == "planung" else _leitung)(a, d, art)


# ---- Planung: klare Ansage -------------------------------------------------------------------------------------------

def _planung(a, d, art: str) -> None:
    e: bp.Ergebnis = d["erg"]["szenarien"]["basis"]
    z = e.zeile(art)
    k = 6
    plan = round(e.median[z, k])
    sicher = round(e.zerlegung[0, z, k] + e.zerlegung[1, z, k])
    with ui.element("section").classes("m-block m-bp-ansage"):
        ui.label(f"{'Alle Maßnahmen' if art == 'Alle' else art} · {_m(e.monate[k])}").classes("m-zweite")
        with ui.element("div").classes("m-bp-satz"):
            ui.html(f"Plane mit <b>{plan}</b> Teilnehmenden – davon <b>{sicher}</b> schon sicher, "
                    f"mit <b>{max(0, plan - sicher)}</b> weiteren rechnen wir.", sanitize=False)
        ui.label("„Sicher“ = schon in der Maßnahme (vorzeitige Abgänge schon abgezogen) oder fest angemeldet.").classes(
            "m-zweite")
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
                ui.label("Alle Maßnahmen" if zeile_art == "Alle" else zeile_art).classes("m-name")
                for s in SPALTEN:
                    p = round(e.median[zi, s])
                    si = round(e.zerlegung[0, zi, s] + e.zerlegung[1, zi, s])
                    with ui.element("div").classes("m-bp-zelle"):
                        ui.label(str(p)).classes("m-name")
                        if s:
                            ui.label(f"{si} sicher").classes("m-zweite")
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
    erg = d["erg"]
    md: bp.Modell = erg["modell"]
    e: bp.Ergebnis = erg["szenarien"]["basis"]
    z = e.zeile(art)
    _ampel(erg, d["szen"])
    with ui.element("div").classes("m-bp-kpis"):
        heute = e.median[z, 0]
        abg = e.zerlegung[0, z, 0] - e.zerlegung[0, z, 6]
        pip = e.zerlegung[2, z, 6]
        u = md.uebergaenge.get("Assessment")
        rb6 = next((r for r in erg["rueckblick"] if r.horizont == 6 and r.mae is not None), None)
        _kpi("Bestand heute", _z(heute), "Teilnehmende")
        _kpi("Erwartete Abgänge", _z(abg), f"bis {_m(e.monate[6])} (regulär + vorzeitig)")
        _kpi("Zugänge aus der Pipeline", _z(pip), f"bis {_m(e.monate[6])} aus Assessment/Vorbereitung")
        _kpi("Übergang Assessment → nächste Stufe", _p(u.quote) if u else "–",
             f"aus {mehrzahl(u.basis, 'Fall', 'Fällen')}" if u else "")
        _kpi("Treffsicherheit", f"± {_z(rb6.mae)}" if rb6 else "–",
             "6 Monate voraus, im Rückblick" if rb6 else "noch zu wenig Historie")
    with ui.element("section").classes("m-block"):
        ui.label(f"{'Alle Maßnahmen' if art == 'Alle' else art}: Verlauf, 80 %-Spanne und Szenarien").classes("m-btitel")
        chart = ui.echart(_verlauf_option(erg, d["szen"], art)).classes("m-chart m-dg")
        chart.on("m_achse", lambda ev: _wenn_dann_panel(a, erg, art, ev.args), ["index"])
        ui.label("Klick auf einen künftigen Monat: „Wenn wir dann X Teilnehmende haben – wie geht es weiter?“").classes(
            "m-zweite")
    with ui.element("section").classes("m-block"):
        ui.label("Woher die Teilnehmenden kommen (Mittel der Verläufe)").classes("m-btitel")
        ui.echart(_zerlegung_option(e, art)).classes("m-chart")
    with ui.element("div").classes("m-bst-raster"):
        _abgaenge(md)
        _rueckblick(erg["rueckblick"])
    from . import diagramm_ui

    diagramm_ui.fx_kasten([("planwert", {}, []), ("sicher", {}, []), ("abgangsquote", {}, []),
                           ("uebergangsquote", {}, []), ("rueckblick", {}, [])])
    _fx_knopf()


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
        if szen[sz].get("ausloeser"):
            text += f" Auslöser laut Szenario: {szen[sz]['ausloeser']}"
        ui.label(text).classes("m-zweite").style("white-space:normal")


def _achse(erg, art: str):
    ist = bp.ist_verlauf(erg["faelle"], erg["letzter"], art)
    e = erg["szenarien"]["basis"]
    kat = [_m(d) for d, _n in ist] + [_m(d) for d in e.monate[1:]]
    return ist, kat, len(ist)


def _verlauf_option(erg, szen, art: str) -> dict:
    from . import seite_auswertung as sa

    t = sa._T()
    ist, kat, n_ist = _achse(erg, art)
    leer_ = [None] * (n_ist - 1)
    reihen = []
    e = erg["szenarien"]["basis"]
    z = e.zeile(art)
    unten = leer_ + [round(float(x)) for x in e.p10[z]]
    breite = leer_ + [round(float(o - u)) for u, o in zip(e.p10[z], e.p90[z])]
    reihen.append({"name": "u80", "type": "line", "data": unten, "stack": "b", "symbol": "none", "lineStyle": {"opacity": 0},
                   "tooltip": {"show": False}, "silent": True})
    reihen.append({"name": "80 %-Spanne", "type": "line", "data": breite, "stack": "b", "symbol": "none",
                   "lineStyle": {"opacity": 0}, "areaStyle": {"color": t["akzent"], "opacity": .16}, "color": t["akzent"]})
    reihen.append({"name": "Ist", "type": "line", "data": [n for _d, n in ist] + [None] * (len(kat) - n_ist),
                   "color": t["text"], "lineStyle": {"color": t["text"], "width": 2.4}, "symbol": "circle", "symbolSize": 4})
    reihen.append({"name": "Planwert (normal)", "type": "line", "data": leer_ + [round(float(x)) for x in e.median[z]],
                   "color": t["akzent"], "lineStyle": {"color": t["akzent"], "width": 2.4, "type": [7, 5]}, "symbol": "none"})
    for k, farbe in (("schwach", t["orange"]), ("stark", t["blau"])):
        s = erg["szenarien"][k]
        reihen.append({"name": f"{bp.SZENARIO_NAMEN[k]} ({'+' if szen[k]['faktor'] >= 0 else '−'}{abs(round(szen[k]['faktor']))} %)",
                       "type": "line", "data": leer_ + [round(float(x)) for x in s.median[s.zeile(art)]], "color": farbe,
                       "lineStyle": {"color": farbe, "width": 1.6, "type": "dotted"}, "symbol": "none"})
    reihen[2]["markLine"] = {"silent": True, "symbol": "none", "lineStyle": {"color": t["text2"], "type": [2, 3]},
                             "label": {"formatter": "Stichtag", "color": t["text2"], "fontSize": 11},
                             "data": [{"xAxis": kat[n_ist - 1]}]}
    opt = sa._chart_basis()
    opt["xAxis"]["data"] = kat
    opt["legend"]["data"] = [r["name"] for r in reihen if r["name"] != "u80"]
    opt["series"] = reihen
    opt["grid"]["top"] = 40
    return opt


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
            besser = r.mae_vorjahr is not None and r.mae < r.mae_vorjahr
            ui.label(f"{r.horizont} Monat(e) voraus: im Schnitt ± {_z(r.mae, 1)} Teilnehmende daneben "
                     f"({_p(r.wape)}), Ist in der 80 %-Spanne: {_p(r.treffer80)} · „wie vor 12 Monaten“: "
                     f"± {_z(r.mae_vorjahr, 1)} {'→ Modell besser' if besser else '→ Modell nicht besser'}"
                     f" · {mehrzahl(r.n, 'Stichtag', 'Stichtage')}").classes("m-ptext")


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
                if w.erreichbar:
                    richtung = "mehr" if w.faktor >= 0 else "weniger"
                    ui.html(f"Damit es im {_m(w.monat)} <b>{round(w.ziel)}</b> sind, müssten die neuen Zugänge "
                            f"etwa <b>{abs(w.faktor)} % {richtung}</b> sein als üblich.", sanitize=False).classes("m-ptext")
                else:
                    ui.html(f"<b>{round(w.ziel)}</b> ist allein über die Zugänge nicht erreichbar – schon da bzw. fest "
                            f"angemeldet sind im {_m(w.monat)} rund <b>{round(w.sicher_im_monat)}</b>. Gerechnet wird mit "
                            f"dem nächstmöglichen Wert ({round(w.erreicht)}).", sanitize=False).classes("m-ptext")
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
.m-bp-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }
.m-bp-kpi { border: 1px solid var(--rand); border-radius: 8px; background: var(--fl); padding: 10px 14px; display: flex;
  flex-direction: column; gap: 2px; }
.m-bp-kpi .m-zweite { white-space: normal; }
.m-bp-wert { font-size: 24px; line-height: 32px; font-weight: 600; font-variant-numeric: tabular-nums; }
.m-bp-wd { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
"""
