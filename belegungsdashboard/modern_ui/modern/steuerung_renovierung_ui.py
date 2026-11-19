"""1.29: Steuerung – Oberfläche der Renovierung: Etagen wählen, Empfehlung, Varianten, Vorgaben, Gantt/Jahresplan,
Zeitfenster und Annahmen (inkl. Angebot prüfen).

Aus seite_steuerung.py ausgelagert (nur verschoben, keine Funktionsänderung); dort weiter erreichbar."""

from __future__ import annotations

from datetime import date
from nicegui import run, ui
from . import renovierung_kern as rk
from . import seiten
from .ui_bausteine import attr, knopf, segmente, tabelle


HK_KLASSE = {"angebot": "ok", "eingabe": "neutral", "schaetzung": "warn", "platzhalter": "krit"}


def _hk(herkunft: str) -> None:
    ui.label(rk.HERKUNFT_TEXT.get(herkunft, herkunft)).classes(f"m-pille m-hk {HK_KLASSE.get(herkunft, 'neutral')}")


def _platzhalter_banner(a, d) -> None:
    if not d["platzhalter"]:
        return
    with ui.element("section").classes("m-block m-breit m-rv-banner"):
        ui.label("Achtung: Diese Beträge sind noch keine Angebotspreise").classes("m-btitel")
        for t in d["platzhalter"]:
            ui.label(t).classes("m-ptext")
        ui.label("Solange kein Angebot eingelesen ist, sind alle Summen dieser Häuser nur Richtwerte.").classes("m-zweite")
        knopf("Angebot einlesen …", lambda: _annahmen(a), "primaer", "upload")


def _zone(nr: str, titel: str, frage: str) -> None:
    """Sichtbare Trennung der Arbeitsseite: Eingabe | Ergebnis | Entscheidung."""
    with ui.element("div").classes("m-zone"):
        ui.label(nr).classes("m-zone-nr")
        ui.label(titel).classes("m-zone-t")
        ui.label(frage).classes("m-zweite")


# ---- Renovierung ------------------------------------------------------------------------------

def _etage_waehlen(a, d, p, fl, jahr) -> None:
    """Eine bestimmte ganze Etage selbst planen – unabhängig vom Vorschlag."""
    schon = {e["flur"] for e in rk.plan() if e["start"][:4] == str(jahr) and e["art"] == "etage"}
    optionen = {}
    for f in sorted(fl, key=lambda x: (x.haus, rk.zp._etage_sort(x.etage))):
        k = rk.kosten(p, f.haus, len(f.zimmer), jahr)
        optionen[f.schluessel] = (f"{f.text} – {len(f.zimmer)} Zimmer – Bau {rk.tsd(k.basis_brutto)} laut Angebot"
                                  + (" – schon vorgemerkt" if f.schluessel in schon else ""))
    with ui.element("section").classes("m-block m-breit"):
        with ui.element("div").classes("m-zeile-flex"):
            ui.label("Ganze Etage selbst planen").classes("m-btitel")
            wahl = ui.select(optionen, value=getattr(a, "st_etage", None) if getattr(a, "st_etage", None) in optionen else None,
                             label="Etage wählen").classes("m-feld").props(
                'dense outlined dark popup-content-class="m-popup"').style("min-width:360px; flex:1 1 360px; max-width:560px")

            def planen():
                f = next((x for x in fl if x.schluessel == wahl.value), None)
                if f is None:
                    a.toast("Bitte zuerst eine Etage wählen.", fehler=True)
                    return
                a.st_etage = f.schluessel
                _etage_panel(a, d, f)
            knopf("Monat wählen und vormerken …", planen, "primaer", "event")
        ui.label("Für eine Etage, die Sie auf jeden Fall machen wollen – egal ob INNternat sie vorschlägt. Vorgemerktes wird vom "
                 "Baubudget abgezogen; der Vorschlag darunter verteilt nur noch den Rest.").classes("m-zweite").style(
            "white-space:normal")


def _etage_panel(a, d, f) -> None:
    p, jahr = d["p"], d["jahr"]
    k = rk.kosten(p, f.haus, len(f.zimmer), jahr)
    fs = rk.monatsfenster(a.stand, f, jahr, p, d.get("prog"))
    rk.engpass_markieren(fs, f, d.get("kap"), rk.jahresplan(a.stand, jahr, None, p),
                         defekt=rk.defekte_betten(a.stand, {z.id for z in f.zimmer}))
    best = rk.bester_monat(fs, a.heute)

    def bauen():
        ui.label(f"{f.text} · {len(f.zimmer)} Zimmer, {f.betten} Betten · {f.klassen_text}").classes("m-name")
        with ui.element("div").classes("m-kap").style("grid-template-columns: 1fr auto"):
            for text, wert in ((f"Bau laut Angebot ({rk.HERKUNFT_TEXT[k.herkunft_bau]})", k.basis_brutto),
                               (f"Bau {jahr} (mit Preissteigerung, Puffer)", k.instandhaltung), (f"Möbel {jahr}", k.investition)):
                ui.label(text).classes("m-zweite")
                ui.label(rk.euro(wert)).classes("m-mono")
        bb = d["p_rest"].get("budget_bau")
        if bb is not None and k.instandhaltung > bb + .5:
            ui.label(f"Mehr als das noch freie Baubudget ({rk.tsd(bb)}) – vormerken geht trotzdem, das Budget wird dann "
                     "überschritten.").classes("m-pille warn").style("white-space:normal")
        if best:
            ui.label(f"Bester Monat: {rk.MONATE[best.start.month - 1]} {jahr} (Belegungsstopp ab {best.stopp_ab:%d.%m.%Y})"
                     + (" – gleichwertig mit anderen" if best.gleichwertig else "")).classes("m-ptext")

            async def merken():
                if await a.aendern(rk.vormerken_schritt, f.schluessel, best.start, best.ende):
                    a.panel_zu()
            knopf(f"Im besten Monat vormerken ({rk.MONATE[best.start.month - 1]})", merken, "primaer", "bookmark_add")
        else:
            ui.label(f"In {jahr} ist kein Monat möglich (gesperrt oder Vorlauf zu kurz).").classes("m-pille warn")
        ui.label("Oder einen anderen Monat wählen:").classes("m-ktitel")
        _monate(a, f, fs, best)

    a.panel(f"Ganze Etage planen: {f.text}", bauen, breit=True)


def _empfehlung_karte(a, d, kompakt: bool = False) -> None:
    v, p, ant = d["gewaehlt"], d["p_rest"], d["antrag"]
    if not v:
        return
    k = v.kosten
    bau_von, bau_bis = k.spanne_von("bau")
    with ui.element("section").classes("m-block m-breit m-rv-empf"):
        titel = ("Rechnerisch beste Variante unter den Annahmen: " if v.schluessel == d["empfehlung"] else "Gewählt: ") + v.titel
        ui.label(titel + (" – für das, was nach den Vormerkungen übrig ist" if d["bereits"]["anzahl"] else "")).classes("m-btitel")
        ui.label("; ".join(m.text for m in v.massnahmen) or "keine Maßnahme").classes("m-ptext").style("white-space:normal")
        with ui.element("div").classes("m-zeile-flex"):
            ui.label(f"deckt {v.a_zimmer} von {rk.a_zimmer(d['fl'])} Klasse-A-Zimmern · {v.zimmer} Zimmer").classes("m-name")
            ui.label(f"Bau ≈ {rk.spanne_text(bau_von, bau_bis)}").classes("m-mono")
            ui.label(f"Möbel-Antrag ≈ {rk.spanne_text(ant['von'], ant['bis'])}").classes("m-mono")
            if p.get("modus") != "ziel" and p.get("budget_bau") is not None and v.rest_bau is not None:
                ui.label(f"Rest Bau ≈ {rk.tsd(v.rest_bau)}").classes("m-mono" + (" m-warn" if v.rest_bau > 500 else ""))
        hinweise = []
        if d["bereits"]["anzahl"]:
            hinweise.append(f"Schon vorgemerkt: {d['bereits']['anzahl']} Maßnahme(n), Bau {rk.tsd(d['bereits']['bau'])} – "
                            "im Möbelantrag enthalten, vom Baubudget abgezogen")
        if k.geschaetzt > .2:
            hinweise.append(f"⚠ {100 * k.geschaetzt:.0f} % der Summe sind Schätzung/Platzhalter")
        if d["robust"]:
            hinweise.append(d["robust"])
        if hinweise:
            ui.label(" · ".join(hinweise)).classes("m-zweite").style("white-space:normal")
        if not kompakt:
            with ui.element("div").classes("m-zeile-flex"):
                if [x for x in d["vs"] if x.fenster or x.teile]:
                    knopf("Alle Vorschläge übernehmen …", lambda: _alle_uebernehmen(a, d["vs"]), "primaer", "bookmark_add")


def _renovierung(a) -> None:
    d = a.daten
    p, fl, jahr = d["p"], d["fl"], d["jahr"]
    with a.leiste:
        knopf("Annahmen & Angebote …", lambda: _annahmen(a), "", "request_quote")

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
        knopf("Excel", export, "", "grid_on")
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            _platzhalter_banner(a, d)
            ui.label("Werkzeug: Renovierung planen").classes("m-btitel").style("font-size:17px")
            _zone("1", "Eingabe", "Was soll passieren? Budget oder Ziel, Planjahr, eigene Etagen")
            _vorgabe_block(a, d, p, fl, jahr)
            _etage_waehlen(a, d, p, fl, jahr)
            _zone("2", "Ergebnis", "Was schlägt INNternat vor, was kostet es, wann geht es?")
            _empfehlung_karte(a, d)
            with ui.expansion(f"Varianten {jahr} vergleichen").classes("m-block m-breit m-rv-exp"):
                _varianten_block(a, d, p)
            with ui.element("section").classes("m-block m-breit"):
                ui.label(f"Zeitplan {jahr}" + (f" – {d['gewaehlt'].titel}" if d["gewaehlt"] else "")).classes("m-btitel")
                _gantt(a, d["zeilen"], jahr)
            with ui.expansion("Bedarf und Kosten je Etage").classes("m-block m-breit m-rv-exp"):
                _etagen_block(a, d, p, fl, jahr)
            if "monate" in d:
                with ui.expansion(f"Monate {d['monate'][0].text}").classes("m-block m-breit m-rv-exp"):
                    _monate(a, *d["monate"])
            _zone("3", "Entscheidung", "Was wird übernommen? Erst dann ändert sich der Plan")
            with ui.element("section").classes("m-block m-breit"):
                es = d["entscheidungen"]
                if not es:
                    ui.label("Nichts offen.").classes("m-pille ok")
                for t in es:
                    with ui.element("div").classes("m-liste-zeile"):
                        ui.icon("help_outline").classes("m-zweite")
                        ui.label(t).style("white-space:normal")
                with ui.element("div").classes("m-zeile-flex"):
                    if [x for x in d["vs"] if x.fenster or x.teile]:
                        knopf("Alle Vorschläge übernehmen …", lambda: _alle_uebernehmen(a, d["vs"]), "primaer", "bookmark_add")
                    knopf("Annahmen ansehen (Grundlagen)", lambda: a.oeffnen("steuerung", ansicht="grundlagen"), "leise",
                          "arrow_forward")


def _annahmen_liste(p: dict, fl: list | None = None) -> list[tuple[str, str]]:
    erg = []
    for h in p["haeuser"]:
        k = p["kosten"][h]
        groessen = sorted(len(f.zimmer) for f in fl or [] if f.haus == h)
        n = groessen[len(groessen) // 2] if groessen else 9            # typische Etage des Hauses
        erg.append((f"Haus {h}: Bau je Etage {rk.euro(k.get('bau_etage') or 0)} netto", rk.herkunft(p, h, "bau_etage")))
        erg.append((f"Haus {h}: Möbel je Zimmer {rk.euro(k.get('moebel_zimmer') or 0)} netto, Aufbau "
                    f"{rk.euro(k.get('aufbau_zimmer') or 0)}", rk.herkunft(p, h, "moebel_zimmer")))
        je, hk, wie = rk.bau_je_einzelzimmer(p, h, n)
        erg.append((f"Haus {h}: Einzelzimmer-Bau {rk.euro(je)} je Zimmer ({wie})", hk))
        erg.append((f"Haus {h}: Bauzeit einer Etage {k.get('dauer_tage', 30)} Tage", ""))
    erg += [(f"Puffer Bau {p.get('puffer_bau_pct')} %, Möbel {p.get('puffer_moebel_pct')} %", ""),
            (f"Preissteigerung Bau {p.get('preis_pct')} %, Möbel {p.get('preis_moebel_pct')} % je Jahr ab {p.get('preisstand')}", ""),
            (f"Nebenkosten {p.get('neben_pct')} % vom Bau · Vorsteuerquote {p.get('vorsteuer_pct')} % (0 % = brutto)", ""),
            (f"Belegungsstopp {p.get('vorlauf_tage')} Tage vor Baubeginn · Möbel-Lieferzeit {p.get('lieferzeit_tage')} Tage", ""),
            (f"Leerstand nötig: Einzelzimmer {p.get('zimmer_tage')} Tage, Möbeltausch {p.get('moebel_tage')} Tage", ""),
            (f"Kernbestand: Puffer {p.get('kern_puffer_pct')} %, Typen-Reserve {p.get('typ_reserve_pct')} %", "")]
    return erg


def _vorgabe_block(a, d, p, fl, jahr) -> None:
    kern = d["kern"]
    with ui.element("section").classes("m-block m-breit"):
        with ui.element("div").classes("m-zeile-flex"):
            ui.label("Vorgabe").classes("m-btitel")

            async def modus(v):
                a.st_var = None
                await a.aendern(rk.parameter_schritt, {**p, "modus": v})
            segmente({"budget": "Baubudget (fest)", "ziel": "Zimmerziel"}, "ziel" if p.get("modus") == "ziel" else "budget", modus)
        with ui.element("div").classes("m-zeile-flex"):
            if p.get("modus") != "ziel":
                bau = ui.number("Baubudget € (feste Grenze, verfällt)", value=p.get("budget_bau"), min=0, step=1000,
                                format="%.0f").classes("m-feld").props("dense outlined dark clearable").style(
                    "flex:1 1 240px; max-width:320px")
                mob = ui.number("Möbel: realistische Obergrenze € (optional)", value=p.get("moebel_obergrenze"), min=0, step=500,
                                format="%.0f").classes("m-feld").props("dense outlined dark clearable").style(
                    "flex:1 1 240px; max-width:320px")

                async def setzen():
                    a.st_var = None
                    await a.aendern(rk.parameter_schritt, {**p, "budget_bau": None if bau.value in (None, "") else float(bau.value),
                                                           "moebel_obergrenze": None if mob.value in (None, "") else float(mob.value)})
                knopf("Übernehmen", setzen, "leise", "check")
            else:
                ziel = int(p.get("ziel_zimmer") or 0)
                zahl = ui.number("Zimmer je Jahr", value=ziel, min=0, max=500, step=1, format="%d").classes("m-feld").props(
                    "dense outlined dark").style("max-width:160px")

                async def ziel_setzen():
                    if int(zahl.value or 0) != ziel:
                        a.st_var = None
                        await a.aendern(rk.parameter_schritt, {**p, "ziel_zimmer": int(zahl.value or 0)})
                knopf("Übernehmen", ziel_setzen, "leise", "check")
            vorrang = ui.select({"": "kein Haus-Vorrang", **{h: f"Haus {h} zuerst" for h in p["haeuser"]}},
                                value=p.get("haus_vorrang") or "", label="Reihenfolge").classes("m-feld").props(
                'dense outlined dark popup-content-class="m-popup"').style("min-width:200px; max-width:260px; flex:0 0 auto")

            async def vorrang_setzen(e):
                a.st_var = None
                await a.aendern(rk.parameter_schritt, {**p, "haus_vorrang": e.value or ""})
            vorrang.on_value_change(vorrang_setzen)
        if p.get("modus") != "ziel":
            ui.label("Das Baubudget soll möglichst voll in gedeckten Bedarf gehen. Den Möbelbedarf rechnet INNternat aus – das "
                     "ist der Antrag; eine Obergrenze ist nur nötig, wenn klar ist, dass nicht mehr genehmigt wird.").classes(
                "m-zweite").style("white-space:normal")
        if kern.gesamt:
            with ui.element("div").classes("m-zeile-flex"):
                cb = ui.checkbox("Reserve-Etagen nicht renovieren (Kernbestand)", value=bool(p.get("kernbestand")))

                async def kern_setzen(e):
                    a.st_var = None
                    await a.aendern(rk.parameter_schritt, {**p, "kernbestand": bool(e.value)})
                cb.on_value_change(kern_setzen)
                ui.label(kern.text + (" Vorschlag Reserve: " + ", ".join(f.text for f in kern.etagen) + "." if kern.etagen
                                      else "")).classes("m-zweite").style("white-space:normal")


def _varianten_block(a, d, p) -> None:
    ui.label("Vorgeschlagen werden nur Etagen mit erfasstem Bedarf. Eine bestimmte Etage können Sie oben unter „Ganze Etage "
             "selbst planen“ wählen.").classes("m-xk-hinweis")
    ui.label("★ = rechnerisch beste Variante unter den Annahmen (meister Bedarf: erst A, dann B, dann C; dann mehr Zimmer; "
             "dann mehr genutztes Baubudget). Klick wählt eine andere.").classes("m-zweite").style("white-space:normal")
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
                    ui.label(f"{v.zimmer} Zimmer · davon {v.a_zimmer} Klasse A").classes("m-zweite")
                    ui.label(f"Bau {rk.spanne_text(*k.spanne_von('bau'))}").classes("m-mono")
                    ui.label(f"Möbel {rk.spanne_text(*k.spanne_von('moebel'))}").classes("m-zweite")
                    ui.label(f"Sperr-Zimmermonate {v.sperr_zimmermonate(p):g}").classes("m-zweite")
                    if p.get("modus") != "ziel" and p.get("budget_bau") is not None and v.rest_bau is not None:
                        ui.label(f"Rest Bau {rk.tsd(v.rest_bau)}").classes("m-zweite")
            if not leer_:
                b.on("click", lambda v=v: a.setzen(st_var=v.schluessel, nur_seite=True))


def _etagen_block(a, d, p, fl, jahr) -> None:
    ui.label("Klassen je Zimmer, getrennt für Bau und Möbel: A = jetzt, B = in 1–3 Jahren, C = später. „Bau laut Angebot“ = "
             f"der Preis, wie er im Angebot steht (inkl. nicht abziehbarer Steuer); „Bau {jahr}“ = mit Preissteigerung und "
             "Puffer. Klick: diese Etage planen.").classes("m-zweite").style("white-space:normal")
    if fl and not any(f.wert for f in fl):
        ui.label("Für diese Etagen ist kein Bedarf erfasst (Renovierungsdaten, Zustandsnoten, Mängel) – die Reihenfolge ist "
                 "noch keine Empfehlung.").classes("m-pille warn").style("white-space:normal")
    sp = "minmax(140px, 1fr) auto minmax(160px, 1.2fr) auto minmax(180px, 1.8fr) auto auto auto"
    with tabelle(sp):
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("Etage", "Zimmer", "Klassen", "Note", "Datenlage · Besonderheiten", "Bau laut Angebot", f"Bau {jahr}",
                      f"Möbel {jahr}"):
                ui.label(t)
        reserve = {f.schluessel for f in d["kern"].etagen}
        for f in fl:
            k = rk.kosten(p, f.haus, len(f.zimmer), jahr)
            z = ui.element("div").classes("m-raster m-zeile m-rv-zeile" + (" an" if f.schluessel == a.rv_flur else "")).style(
                f"grid-template-columns:{sp}")
            with z:
                ui.label(f.text + (" · Reserve" if f.schluessel in reserve else "")
                         + ("" if f.schluessel in d["machbar"] else " · kein Monat machbar")).classes("m-name")
                ui.label(f"{len(f.zimmer)} · {f.betten} B.").classes("m-mono")
                attr(ui.label(f.klassen_text).classes("m-mono" + {"krit": " m-krit", "warn": " m-warn"}.get(f.ampel, "")),
                     title="\n".join(t for _w, t in f.gruende))
                ui.label(str(f.zustand) if f.zustand else "–").classes("m-mono")
                attr(ui.label(" · ".join(f.luecken + f.sonder) or "–").classes("m-zweite"), title="\n".join(f.luecken + f.sonder))
                with ui.element("div").classes("m-zeile-flex").style("gap:4px; flex-wrap:nowrap"):
                    ui.label(rk.euro(k.basis_brutto)).classes("m-mono")
                    _hk(k.herkunft_bau)
                attr(ui.label(rk.euro(k.instandhaltung)).classes("m-mono"),
                     title="\n".join(f"{x}: {rk.euro(b)}" for x, b in k.herleitung if b))
                ui.label(rk.euro(k.investition)).classes("m-mono")
            z.on("click", lambda f=f: _etage_panel(a, d, f))


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


def gantt_text(von: date, bis: date, kurz: str, art: str) -> str:
    """1.12: Beschriftung eines Balkens – Zeitraum und bei Einzelzimmern die Zahl der Zimmer, z. B. „10.06.–24.06. · 3 Zi.“."""
    zeit = f"{von:%d.%m.}–{bis:%d.%m.}"
    if art == "etage":
        return zeit
    n = kurz.count(",") + 1 if kurz else 0
    return f"{zeit} · {n} Zi." if n else zeit


def gantt_kosten(bau: float, moebel: float, summe: float, kompakt: bool = False) -> str:
    """1.12: Kostenzeile ohne „Bau 0 T€“ – nur die Teile, die etwas kosten."""
    if kompakt:
        return rk.tsd(summe)
    teile = [f"{t} {rk.tsd(x)}" for t, x in (("Bau", bau), ("Möbel", moebel)) if round(x / 1000)]
    if len(teile) == 2:
        return " · ".join(teile) + f" = {rk.tsd(summe)}"
    return teile[0] if teile else f"Kosten {rk.tsd(summe)}"


def _gantt(a, zeilen: list, jahr: int, kompakt: bool = False) -> None:
    """Zeilen = Maßnahmen, zeitlich sortiert. Schraffiert = Belegungsstopp, Balken = Bauzeit, gestrichelt = Vorschlag;
    ⚑ = Ausweich fehlt, ▲ = Warnschwelle, grau = nicht prüfbar (hinter den Buchungen).
    1.12: Jeder Balken trägt Zeitraum und Zimmerzahl (im Balken, wenn er breit genug ist, sonst daneben);
    Titel und Kosten werden nicht mehr abgeschnitten."""
    j0, j1 = date(jahr, 1, 1), date(jahr, 12, 31)
    tage = (j1 - j0).days + 1
    pos = lambda d_: max(0.0, min(100.0, 100 * ((d_ - j0).days) / tage))
    zeilen = sorted(zeilen, key=lambda z: (z.start, z.text))
    with ui.element("div").classes("m-gantt" + (" kompakt" if kompakt else "")):
        with ui.element("div").classes("m-gantt-zeile m-gantt-kopf"):
            ui.label("Maßnahme")
            with ui.element("div").classes("m-gantt-spur"):
                for m in range(12):
                    ui.label(rk.MONATE[m]).classes("m-gantt-monat" + (" q" if m % 3 == 0 else "")).style(
                        f"left:{100 * m / 12:.2f}%")
        if not zeilen:
            ui.label("Noch nichts geplant und kein Vorschlag – Baubudget oder Ziel setzen.").classes("m-zweite")
        for z in zeilen:
            k = z.kosten
            with ui.element("div").classes("m-gantt-zeile" + (" vorschlag" if z.status != "vorgemerkt" else "")):
                t = ui.element("div").classes("m-gantt-titel")
                with t:
                    ui.label(z.text).classes("m-name")
                    ui.label((f"{z.zimmer} Zimmer · {z.betten} Betten" if z.art == "etage"
                              else f"{z.zimmer} Zimmer · {rk.ARTEN[z.art]}")).classes("m-zweite")
                    ui.label(gantt_kosten(k.instandhaltung, k.investition, k.summe, kompakt)).classes("m-zweite m-gantt-kosten")
                attr(t, title="\n".join(f"{x}: {rk.euro(b)}" for x, b in k.herleitung if b) + f"\n= {rk.euro(k.summe)}")
                with ui.element("div").classes("m-gantt-spur"):
                    if a.heute.year == jahr:
                        ui.element("div").classes("m-gantt-heute").style(f"left:{pos(a.heute):.2f}%")
                    teile = _buendeln(z.teile) if z.teile else [(z.start, z.ende, "")]
                    if z.art == "etage" and z.stopp_ab <= j1 and z.start >= j0:
                        attr(ui.element("div").classes("m-gantt-vorlauf").style(
                            f"left:{pos(z.stopp_ab):.2f}%; width:{pos(z.start) - pos(z.stopp_ab):.2f}%"),
                            title=f"Belegungsstopp ab {z.stopp_ab:%d.%m.%Y}")
                    zeichen = ("⚑" if z.ohne_ausweich else "") + ("▲" if z.engpass else "")
                    for von, bis, kurz in teile:
                        links, breite = pos(von), max(1.2, pos(bis) - pos(von))
                        text = gantt_text(von, bis, kurz, z.art) + (f" {zeichen}" if zeichen else "")
                        innen = breite >= (9 if not kompakt else 12)
                        b = ui.element("button").classes(
                            f"m-gantt-bau {z.status}" + (" aus" if z.ohne_ausweich else "") + (" warn" if z.engpass else "")
                            + ("" if z.pruefbar else " offen")).style(f"left:{links:.2f}%; width:{breite:.2f}%")
                        attr(b, title=f"{kurz or z.text}: {von:%d.%m.} – {bis:%d.%m.%Y} · "
                                      f"{'vorgemerkt' if z.status == 'vorgemerkt' else 'Vorschlag'}"
                                      + (" · ⚑ Ausweich fehlt" if z.ohne_ausweich else "")
                                      + (" · ▲ Warnschwelle" if z.engpass else "")
                                      + ("" if z.pruefbar else " · nicht prüfbar (hinter den Buchungen)")
                                      + (" · Monat gleichwertig" if z.gleichwertig else ""))
                        with b:
                            if innen:
                                ui.label(text)
                        b.on("click", lambda z=z: _zeile_panel(a, z))
                        if not innen:                       # Beschriftung neben dem Balken – rechts, am Jahresende links
                            rechts = links + breite <= 78
                            ui.label(text).classes("m-gantt-text" + (" eng" if zeichen else "")).style(
                                f"left:calc({links + breite:.2f}% + 6px)" if rechts else f"right:calc({100 - links:.2f}% + 6px)")
    with ui.element("div").classes("m-gantt-legende"):
        for kl, txt in (("fest", "vorgemerkt (fest)"), ("vorschlag", "Vorschlag"), ("vorlauf", "Belegungsstopp vor dem Bau"),
                        ("offen", "nicht prüfbar (hinter den Buchungen)")):
            with ui.element("span").classes("m-gantt-lg"):
                ui.element("i").classes(kl)
                ui.label(txt)
        ui.label("⚑ Ausweich fehlt").classes("eng")
        ui.label("▲ Warnschwelle").classes("eng")
        ui.label("Klick auf einen Balken zeigt Zimmer und Termine").classes("hinweis")


def _zeile_panel(a, z: rk.PlanZeile) -> None:
    k = z.kosten

    def bauen():
        ui.label(z.titel).classes("m-name")
        if z.art == "etage":
            ui.label(f"Bau {z.start:%d.%m.} – {z.ende:%d.%m.%Y} · Belegungsstopp ab {z.stopp_ab:%d.%m.%Y} · {z.zimmer} Zimmer, "
                     f"{z.betten} Betten").classes("m-ptext")
        else:
            ui.label(f"{z.zimmer} Zimmer, gebündelt in Kampagnen (frühestens nach der Möbel-Lieferzeit):").classes("m-ptext")
            for _zid, kurz, von, bis, _b in z.teile:
                ui.label(f"{kurz}: {von:%d.%m.} – {bis:%d.%m.%Y}").classes("m-zweite")
        if z.art != "moebel" and k.basis_bau:
            ui.label(f"Bau laut Angebot/Annahme: {rk.euro(k.basis_bau)} netto = {rk.euro(k.basis_brutto)} inkl. nicht "
                     "abziehbarer Steuer.").classes("m-ptext")
        ui.label("So kommen die Kosten zustande").classes("m-ktitel")
        with ui.element("div").classes("m-kap").style("grid-template-columns: 1fr auto"):
            for text, betrag in k.herleitung:
                if betrag:
                    ui.label(text).classes("m-zweite")
                    ui.label(rk.euro(betrag)).classes("m-mono")
            ui.label("Bau-Budget (Maler/Boden, Nebenkosten, Steuer)").classes("m-name")
            ui.label(rk.euro(k.instandhaltung)).classes("m-mono m-name")
            ui.label("Möbel (Möbel, Aufbau, Steuer)").classes("m-name")
            ui.label(rk.euro(k.investition)).classes("m-mono m-name")
            ui.label("Spanne gesamt").classes("m-zweite")
            ui.label(rk.spanne_text(*k.spanne)).classes("m-mono")
        for l in k.luecken:
            ui.label(l).classes("m-pille warn")
        if z.gleichwertig:
            ui.label("Mehrere Monate sind gleich gut – der früheste ist gewählt, ein anderer passt genauso.").classes(
                "m-zweite").style("white-space:normal")
        if z.engpass:
            ui.label("▲ In diesem Monat erreicht die obere Prognose die Warnschwelle der verringerten Kapazität – es war kein "
                     "besserer Monat frei.").classes("m-pille warn").style("white-space:normal")
        if z.ohne_ausweich:
            ui.label(f"⚑ Für {z.ohne_ausweich} betroffene Person(en) ist im Bauzeitraum kein passendes Zimmer frei.").classes(
                "m-pille warn")
        if not z.pruefbar:
            ui.label("Dieser Monat liegt hinter den bekannten Buchungen – der Ausweich ist nicht prüfbar, es zählt nur die "
                     "Prognose.").classes("m-pille neutral").style("white-space:normal")

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
                          + (" · ⚑ Ausweich fehlt" if fe.ohne_ausweich else "")))
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


def _monate(a, f, fs, best) -> None:
    ui.label("Betroffen = wohnt im Bauzeitraum oder reist darin an (bekannte Buchungen). ⚑ = für jemanden fehlt ein passendes "
             "freies Zimmer in allen Häusern. ▲ = Warnschwelle. „offen“ = hinter den bekannten Buchungen, nicht prüfbar. "
             "≈ = gleichwertig.").classes("m-zweite").style("white-space:normal")
    with ui.element("div").classes("m-rv-jahr"):
        for fe in fs:
            k = ui.element("button").classes(f"m-rv-monat {fe.stufe}" + (" bester" if best is fe else ""))
            with k:
                ui.label(rk.MONATE[fe.start.month - 1] + (" ★" if best is fe else "") + (" ≈" if fe.gleichwertig else "")
                         + (" ▲" if fe.engpass else "") + (" ⚑" if fe.ohne_ausweich else "")).classes(
                    "m-zweite" + (" m-warn" if fe.engpass else ""))
                ui.label({"gesperrt": "gesperrt", "frei": "frei", "offen": "offen"}.get(
                    fe.stufe, f"{fe.betroffen} betroffen")).classes("m-name")
                ui.label(f"Stopp ab {fe.stopp_ab:%d.%m.}" + (f" · {fe.mieter} Mieter" if fe.mieter else "")).classes("m-zweite")
                ui.label((f"{len(fe.ohne_ausweich)} ohne Ausweich" if fe.ohne_ausweich else f"{fe.frei_gesamt} frei gesamt")
                         + (f" · Progn. {fe.prognose[0]:.0f}" if fe.prognose else "")).classes("m-zweite")
            k.on("click", lambda fe=fe, f=f: _fenster(a, f, fe))


def _fenster(a, f, fe) -> None:
    def bauen():
        ui.label(f"{f.text} · {fe.start:%d.%m.} – {fe.ende:%d.%m.%Y}").classes("m-name")
        ui.label(f"Belegungsstopp ab {fe.stopp_ab:%d.%m.%Y}. Im ganzen Bauzeitraum frei: {fe.frei_im_haus} Zimmer im selben "
                 f"Haus, {fe.frei_gesamt} in allen Häusern.").classes("m-ptext")
        if not fe.pruefbar:
            ui.label("Hinter den bekannten Buchungen – Ausweich nicht prüfbar, nur Prognose.").classes("m-pille neutral")
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
            ui.label(f"⚑ Kein passendes Ausweichzimmer ({len(fe.ohne_ausweich)})").classes("m-ktitel")
            for name, gruppe, grund in fe.ohne_ausweich:
                with ui.element("div").classes("m-liste-zeile"):
                    ui.label(name).classes("m-name")
                    ui.label(f"{gruppe} · {grund}").classes("m-zweite")
        if not (fe.umzug or fe.umleiten or fe.nach_stopp) and fe.pruefbar:
            ui.label("Nach den bekannten Buchungen ist niemand betroffen.").classes("m-pille ok")
        if fe.mieter:
            ui.label(f"{fe.mieter} Mietverhältnis(se) betroffen – Umzug ist eine Frage des Vertrags.").classes("m-pille warn")

        async def merken():
            if await a.aendern(rk.vormerken_schritt, f.schluessel, fe.start, fe.ende):
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            knopf("Bestätigen und vormerken", merken, "primaer", "bookmark_add")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel(f"Renovierung {rk.MONATE[fe.start.month - 1]} {fe.start.year}", bauen, breit=True)


# ---- Annahmen und Angebote ------------------------------------------------------------------------

HAUS_FELDER = (("bau_etage", "Bau je Etage €", 1000), ("moebel_zimmer", "Möbel je Zimmer €", 50),
               ("aufbau_zimmer", "Aufbau je Zimmer €", 50), ("dauer_tage", "Bauzeit Etage (Tage)", 1),
               ("einheit_boden", "€/m² Boden", 1), ("einheit_wand", "€/m² Wand+Decke", 1), ("einheit_tuer", "€ je Tür", 10),
               ("zimmer_boden_m2", "Zimmer: m² Boden", 1), ("zimmer_wand_m2", "Zimmer: m² Wand+Decke", 1),
               ("zimmer_tueren", "Zimmer: Türen", 1), ("bau_zimmer", "Einzelzimmer-Bau fest € (optional)", 100))
GANZZAHL = ("preisstand", "vorlauf_tage", "lieferzeit_tage", "zimmer_tage", "moebel_tage")


def _annahmen(a) -> None:
    from .seite_daten import _hochladen

    p = rk.parameter()

    def feld(titel, wert, schritt=1, mx=None):
        return ui.number(titel, value=wert, min=0, max=mx, step=schritt, format="%g").classes("m-feld").props(
            "dense outlined dark")

    def bauen():
        ui.label("Beträge netto wie im Angebot. Bau je Etage und Einheitspreise kommen beim Einlesen eines Bau-Angebots mit; "
                 "Zimmerflächen bitte eintragen – dann rechnen Einzelzimmer mit echten Preisen statt mit einer Schätzung.").classes(
            "m-ptext").style("white-space:normal")
        felder = {}
        for h in p["haeuser"]:
            k = p["kosten"][h]
            with ui.element("div").classes("m-zeile-flex"):
                ui.label(f"Haus {h}").classes("m-ktitel")
                _hk(rk.herkunft(p, h, "bau_etage"))
            with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(4, 1fr)"):
                for schl, titel, schritt in HAUS_FELDER:
                    felder[(h, schl)] = feld(titel, k.get(schl, 0), schritt)
        ui.label("Allgemein").classes("m-ktitel")
        with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(4, 1fr)"):
            allg = {s: feld(t, p.get(s), st, mx) for s, t, st, mx in (
                ("puffer_bau_pct", "Puffer Bau %", 1, 100), ("puffer_moebel_pct", "Puffer Möbel %", 1, 100),
                ("preis_pct", "Preissteigerung Bau %/J.", .5, 50), ("preis_moebel_pct", "Preissteigerung Möbel %/J.", .5, 50),
                ("preisstand", "Preisstand (Jahr)", 1, None), ("neben_pct", "Nebenkosten % vom Bau", 1, 100),
                ("vorsteuer_pct", "Vorsteuerquote % (0 = brutto)", 5, 100), ("vorlauf_tage", "Belegungsstopp vorher (Tage)", 7, 365),
                ("lieferzeit_tage", "Möbel-Lieferzeit (Tage)", 7, 365), ("zimmer_tage", "Einzelzimmer: Tage leer", 1, 90),
                ("moebel_tage", "Möbeltausch: Tage leer", 1, 30), ("einzel_aufschlag_pct", "Einzelzimmer ohne Preise: Aufschlag %", 5, 200),
                ("kern_puffer_pct", "Kernbestand: Puffer %", 1, 50), ("typ_reserve_pct", "Kernbestand: Typen-Reserve %", 1, 50))}
        gesperrt = ui.select({i + 1: m for i, m in enumerate(rk.MONATE)}, value=list(p.get("gesperrt") or []), multiple=True,
                             label="Gesperrte Monate (keine Renovierung)").classes("m-feld").props(
            'dense outlined dark use-chips popup-content-class="m-popup"')
        if p.get("angebote"):
            ui.label("Eingelesene Angebote").classes("m-ktitel")
            for an in p["angebote"]:
                ui.label(f"Haus {an.get('haus')} · {'Möbel' if an.get('art') == 'moebel' else 'Bau'} · "
                         f"{rk.euro(float(an.get('netto') or 0))} netto" + (f" für {an.get('zimmer')} Zimmer" if an.get("art") == "moebel" else "")
                         + (f" · {an.get('datum')}" if an.get("datum") else "") + (f" · {an.get('datei')}" if an.get("datei") else "")).classes("m-zweite")

        async def speichern():
            neu = {**p, "gesperrt": sorted(gesperrt.value or []),
                   "kosten": {h: {**p["kosten"][h], **{s: float(felder[(h, s)].value or 0) for s, _t, _x in HAUS_FELDER}}
                              for h in p["haeuser"]}}
            for s, f in allg.items():
                neu[s] = int(f.value or 0) if s in GANZZAHL else float(f.value or 0)
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
    """Erkanntes vor dem Speichern zeigen – Haus, Art, Summe, Zimmerzahl und Einheitspreise korrigierbar."""
    p = rk.parameter()

    def bauen():
        ui.label(f"Aus „{ang.get('datei', '')}“ erkannt – bitte prüfen. Gespeichert werden nur die Beträge in den Annahmen, "
                 "die Datei selbst nicht.").classes("m-ptext")
        haus = ui.select({**{h: f"Haus {h}" for h in p["haeuser"]}, "alle": "für alle Häuser"},
                         value=ang["haus"] if ang["haus"] in p["haeuser"] else ("alle" if ang["art"] == "moebel" else None),
                         label="Haus").classes("m-feld").props('dense outlined dark popup-content-class="m-popup"')
        art = ui.select({"bau": "Bau (Maler/Boden) je Etage", "moebel": "Möbel"}, value=ang["art"], label="Art").classes(
            "m-feld").props('dense outlined dark popup-content-class="m-popup"')
        netto = ui.number("Nettosumme (€)", value=ang["netto"], min=0, step=100, format="%.2f").classes("m-feld").props(
            "dense outlined dark")
        if not ang["netto"]:
            ui.label("Die Nettosumme wurde im PDF nicht gefunden – bitte eintragen.").classes("m-pille warn")
        zimmer = ui.number("Für wie viele Zimmer (nur Möbel)", value=ang.get("zimmer") or 0, min=0, step=1,
                           format="%d").classes("m-feld").props("dense outlined dark")
        ein = {}
        if ang["art"] == "bau":
            ui.label(f"Einheitspreise aus den Positionen (Boden {ang.get('boden_m2', 0):g} m², Wand/Decke "
                     f"{ang.get('wand_m2', 0):g} m²; Nebenarbeiten der Gruppe eingerechnet):").classes("m-zweite")
            with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(3, 1fr)"):
                for s, t in (("einheit_boden", "€/m² Boden"), ("einheit_wand", "€/m² Wand+Decke"), ("einheit_tuer", "€ je Tür")):
                    ein[s] = ui.number(t, value=ang.get(s) or 0, min=0, step=.5, format="%.2f").classes("m-feld").props(
                        "dense outlined dark")
        datum = ui.input("Angebotsdatum (JJJJ-MM-TT)", value=str(a.heute)).classes("m-feld").props("dense outlined dark")
        gueltig = ui.input("Gültig bis (Festpreis; leer = 31.12. des Angebotsjahres)", value=ang.get("gueltig_bis") or "").classes(
            "m-feld").props("dense outlined dark type=date")
        ui.label("Solange das Angebot gilt, rechnet INNternat keine Preissteigerung darauf.").classes("m-zweite")

        async def ok():
            try:
                neu = rk.angebot_uebernehmen(p, {"haus": haus.value, "art": art.value, "netto": float(netto.value or 0),
                                                 "zimmer": int(zimmer.value or 0), "datum": (datum.value or "")[:10],
                                                 "datei": ang.get("datei", ""), "gueltig_bis": (gueltig.value or "")[:10],
                                                 **{s: float(f.value or 0) for s, f in ein.items()}})
            except ValueError as exc:
                a.toast(str(exc), fehler=True)
                return
            if await a.aendern(rk.parameter_schritt, neu):
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            knopf("Übernehmen", ok, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Angebot prüfen", bauen)
