"""Seite „Daten & Import“: je Quelle eine Karte mit Stand und „Hochladen“. Gelesen wird erst als Vorschau im Panel
rechts; übernommen wird nach Bestätigung (Rückgängig möglich). Dazu Gebäudeplan prüfen, ZKL-Abgleich, Pivot und
Kapazitäten, Statistik-Listen und manuelle Einträge."""

from __future__ import annotations

import tempfile
import uuid
from datetime import date
from pathlib import Path

from nicegui import run, ui

from belegung import importe, konfig

from . import daten_kern as dk
from . import seiten
from .ui_bausteine import knopf, leer

UPLOAD = Path(tempfile.gettempdir()) / "belegung_uploads"


def daten(a) -> None:
    a.daten = {"quellen": dk.uebersicht(), "plan": seiten.sk.neuer_plan(), "kap": dk.kapazitaeten(),
               "manuell": dk.manuelle(), "bloecke": dk.uwt_bloecke()}


def _hochladen(a, text: str, endungen: str, bei_dateien, mehrere: bool = False, art: str = ""):
    """Knopf, der den Dateidialog öffnet; ``bei_dateien(liste[(Pfad, Name)])`` bekommt die gespeicherten Dateien."""
    ordner = UPLOAD / uuid.uuid4().hex[:8]

    async def fertig(e):
        dateien = []
        for f in (e.files if hasattr(e, "files") else [e.file]):
            ziel = ordner / Path(f.name).name
            await f.save(ziel)
            dateien.append((ziel, Path(f.name).name))
        up.reset()
        await bei_dateien(dateien)

    up = ui.upload(multiple=mehrere, auto_upload=True, on_multi_upload=fertig if mehrere else None,
                   on_upload=None if mehrere else fertig).props(f'accept="{endungen}"').classes("hidden")
    return knopf(text, lambda: up.run_method("pickFiles"), art, "upload")


def zeichnen(a) -> None:
    d = a.daten
    q = {x.schluessel: x for x in d["quellen"]}
    with a.inhalt:
        with ui.element("div").classes("m-zwei"):
            _karte(a, q["anreisen"], lambda: _hochladen(a, "Anreiselisten hochladen", ".xlsx,.xlsm,.csv",
                                                        lambda f: _anreisen_vorschau(a, f), True, "primaer"),
                   "Je Kurs eine Liste oder die Einheitsliste. Personen werden über die TN-ID wiedererkannt – Abreisen und "
                   "Erinnerungen bleiben bei einem neuen Upload erhalten.")
            _karte(a, q["uwt"], lambda: _hochladen(a, "UWT-Plan oder Klassenliste hochladen", ".xlsx,.xlsm,.pdf",
                                                   lambda f: _uwt_vorschau(a, f)),
                   "Blockschulplan (PDF), Anreisekalender (Excel) oder Klassenübersicht mit DZ-Partnern.",
                   lambda: _uwt_bloecke(a))
            with ui.element("section").classes("m-block"):
                ui.label(q["gebaeudeplan"].titel).classes("m-btitel")
                ui.label(q["gebaeudeplan"].stand).classes("m-name")
                if q["gebaeudeplan"].hinweis:
                    ui.label(q["gebaeudeplan"].hinweis).classes("m-zweite")
                ui.label("Neuer Export aus dem Belegungssystem (Word). Er wird erst mit dem Zimmerplan verglichen; bei "
                         "Unterschieden wählen Sie, was gilt.").classes("m-ptext")
                with ui.element("div").classes("m-paktionen"):
                    _hochladen(a, "Gebäudeplan hochladen", ".docx", lambda f: _plan_lesen(a, f), art="primaer")
                    if d["plan"] is not None:
                        plan, kennung, unterschiede = d["plan"]
                        knopf(f"Neu im Ordner: {plan.datei} prüfen …", lambda: seiten._plan_panel(a, plan, kennung, unterschiede)
                              if unterschiede else a.aendern(seiten.sk.plan_uebernehmen, plan, [], kennung), "gruen")
            with ui.element("section").classes("m-block"):
                ui.label("Zimmerkontrollliste (ZKL) und Zimmer-Pivot").classes("m-btitel")
                ui.label(f"ZKL: {q['zkl'].stand}").classes("m-name")
                ui.label(f"Zimmer-Pivot: {q['zimmerpivot'].stand}").classes("m-name")
                with ui.element("div").classes("m-paktionen"):
                    _hochladen(a, "ZKL hochladen", ".xlsx,.xlsm", lambda f: _einfach(a, dk.zkl_importieren, f, zkl=True))
                    knopf("ZKL-Abgleich …", lambda: _zkl_panel(a), "leise", "compare_arrows")
                    _hochladen(a, "Zimmer-Pivot hochladen", ".xlsx,.xlsm", lambda f: _einfach(a, dk.zimmerpivot_importieren, f))
            with ui.element("section").classes("m-block"):
                ui.label(q["pivot"].titel).classes("m-btitel")
                ui.label(q["pivot"].stand).classes("m-name")
                if q["pivot"].hinweis:
                    ui.label(q["pivot"].hinweis).classes("m-zweite")
                with ui.element("div").classes("m-paktionen"):
                    _hochladen(a, "Andere Pivot-Datei …", ".xlsx,.xlsm", lambda f: _pivot(a, f))
                    knopf("Vom Server aktualisieren", lambda: a.aendern(dk.pivot_vom_server), "leise", "cloud_download")
                ui.label("Kapazitäten (Plätze)").classes("m-ktitel")
                felder = {}
                with ui.element("div").classes("m-kap"):
                    ui.label("")
                    ui.label("Netto").classes("m-zweite")
                    ui.label("Brutto").classes("m-zweite")
                    for s, w in d["kap"].items():
                        ui.label(konfig.STANDORT_LABEL[s]).classes("m-name")
                        felder[(s, "netto")] = ui.number(value=w["netto"], min=0, step=1, format="%d").classes("m-feld").props(
                            "dense outlined dark")
                        felder[(s, "brutto")] = ui.number(value=w["brutto"], min=0, step=1, format="%d").classes("m-feld").props(
                            "dense outlined dark")
                knopf("Kapazitäten speichern", lambda: a.aendern(dk.kapazitaeten_speichern, {
                    s: {"netto": int(felder[(s, "netto")].value or 0), "brutto": int(felder[(s, "brutto")].value or 0)}
                    for s in d["kap"]}), "", "check")
            for art in importe.ARTEN:
                x = q[f"import:{art}"]
                _karte(a, x, lambda art=art: _hochladen(a, "Excel hochladen", ".xlsx,.xlsm,.csv",
                                                        lambda f, art=art: _statistik(a, art, f)),
                       "Für Statistik und Prognose. Ein neuer Import ersetzt den bisherigen vollständig.",
                       (lambda art=art: knopf("Entfernen", lambda: a.aendern(dk.statistik_loeschen, art), "leise", "delete"))
                       if "noch keine" not in x.stand else None)
            _manuell(a, q["manuell"])


def _karte(a, q: dk.Quelle, knopf_bauen, text: str, extra=None) -> None:
    with ui.element("section").classes("m-block"):
        ui.label(q.titel).classes("m-btitel")
        ui.label(q.stand).classes("m-name")
        if q.hinweis:
            ui.label(q.hinweis).classes("m-zweite")
        ui.label(text).classes("m-ptext")
        with ui.element("div").classes("m-paktionen"):
            knopf_bauen()
            if extra:
                extra()


# ---- Anreiselisten ----------------------------------------------------------------------

async def _anreisen_vorschau(a, dateien) -> None:
    v = await run.io_bound(dk.anreisen_lesen, [p for p, _ in dateien], [n for _, n in dateien])

    def bauen():
        if v.fehler:
            for f in v.fehler:
                ui.label(f).classes("m-pille krit").style("white-space:normal")
        if not v.listen:
            ui.label("Keine Anreiseliste erkannt.").classes("m-ptext")
            return
        ui.label(f"{len(v.listen)} Liste(n) – das wird übernommen:").classes("m-ptext")
        for datei, tag, gruppe, n, internat in v.zeilen:
            with ui.element("div").classes("m-plan-u"):
                ui.label(f"{tag:%d.%m.%Y} · {gruppe}").classes("m-name")
                ui.label(f"{n} Personen, davon {internat} mit Internat · {datei}").classes("m-zweite")
        for h in v.hinweise[:12]:
            ui.label(h).classes("m-zweite").style("color:var(--orange); white-space:normal")

        async def los():
            if await a.aendern(dk.anreisen_uebernehmen, v):
                a.panel_zu()
                tage = sorted({z[1] for z in v.zeilen if z[1] >= a.heute})
                if tage:
                    a.toast(f"Importiert – Zimmer für {tage[0]:%d.%m.} jetzt unter Anreisen zuteilen", rueck=True)

        with ui.element("div").classes("m-paktionen"):
            knopf("Übernehmen", los, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Anreiselisten importieren", bauen, breit=True)


# ---- UWT --------------------------------------------------------------------------------

async def _uwt_vorschau(a, dateien) -> None:
    pfad, name = dateien[0]
    try:
        art, daten_ = await run.io_bound(dk.uwt_lesen, pfad)
    except Exception as exc:                  # noqa: BLE001
        a.toast(f"„{name}“ konnte nicht gelesen werden: {exc}", fehler=True)
        return

    def bauen():
        if art == "klassen":
            klassen, hinweise = daten_
            ui.label(f"Klassenübersicht: {len(klassen)} Klassen").classes("m-ptext")
            for k, ps in sorted(klassen.items()):
                ui.label(f"{k}: {len(ps)} Teilnehmende, {sum(1 for p in ps if p.partner)} mit DZ-Partner").classes("m-zweite")
        else:
            ui.label(f"{len(daten_.bloecke)} Blöcke" + (f", {len(daten_.personen)} Personen" if daten_.personen else "")).classes("m-ptext")
            for b in daten_.bloecke[:30]:
                ui.label(f"{getattr(b, 'klasse', '')}: {getattr(b, 'anreise', '')} – {getattr(b, 'abreise', '')}").classes("m-zweite")
            hinweise = daten_.hinweise
        for h in hinweise[:10]:
            ui.label(h).classes("m-zweite").style("color:var(--orange); white-space:normal")

        async def los():
            if await a.aendern(dk.uwt_uebernehmen, art, daten_, name):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Übernehmen", los, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel(f"UWT · {name}", bauen, breit=True)


def _uwt_bloecke(a) -> None:
    def zeigen():
        def bauen():
            bl = a.daten["bloecke"]
            if not bl:
                ui.label("Keine UWT-Blöcke.").classes("m-ptext")
            for b in bl:
                with ui.element("div").classes("m-notiz"):
                    ui.label(f"{b.get('klasse', '')} · {date.fromisoformat(b['anreise']):%d.%m.%Y} – "
                             f"{date.fromisoformat(b['abreise']):%d.%m.%Y}" if b.get("abreise") else b.get("klasse", "")).classes("m-name")
                    ui.label(f"{b.get('anzahl', '')} Personen · {b.get('datei', '')}").classes("m-zweite")
                    knopf("", lambda b=b: a.aendern(dk.uwt_block_loeschen, b["klasse"], b["anreise"]), "leise", "delete",
                          "Block entfernen")

        a.panel("UWT-Blöcke", bauen)

    knopf("Blöcke ansehen", zeigen, "leise", "list")


# ---- Gebäudeplan, ZKL, Pivot, Statistik --------------------------------------------------

async def _plan_lesen(a, dateien) -> None:
    pfad, name = dateien[0]
    try:
        plan, unterschiede = await run.io_bound(dk.gebaeudeplan_lesen, pfad)
        kennung = await run.io_bound(dk.gebaeudeplan_ablegen, pfad, name)
    except Exception as exc:                  # noqa: BLE001
        a.toast(f"Der Gebäudeplan konnte nicht gelesen werden: {exc}", fehler=True)
        return
    if not unterschiede:
        await a.aendern(seiten.sk.plan_uebernehmen, plan, [], kennung)
        return
    seiten._plan_panel(a, plan, kennung, unterschiede)


async def _einfach(a, aktion, dateien, zkl: bool = False) -> None:
    if await a.aendern(aktion, dateien[0][0]) and zkl:
        _zkl_panel(a)


async def _pivot(a, dateien) -> None:
    from . import auswertung_kern as ak

    if await a.aendern(dk.pivot_setzen, dateien[0][0], dateien[0][1]):
        await run.io_bound(ak.datenstand, True)


def _zkl_panel(a) -> None:
    from belegung import zkl

    async def laden_(box):
        punkte = await run.io_bound(dk.zkl_abgleich)
        box.clear()
        gewaehlt = {p.schluessel for p in punkte if p.art in zkl.VORAUSWAHL}
        with box:
            if not punkte:
                ui.label("Keine offenen Abweichungen zur ZKL.").classes("m-ptext")
                return
            for art in sorted({p.art for p in punkte}):
                ui.label(zkl.ARTEN.get(art, art)).classes("m-ktitel")
                for p in (x for x in punkte if x.art == art):
                    cb = ui.checkbox(f"{p.zimmer.removeprefix('GS-')}: {p.text}", value=p.schluessel in gewaehlt).props(
                        "dense dark color=indigo-4")
                    cb.on_value_change(lambda e, k=p.schluessel: gewaehlt.add(k) if e.value else gewaehlt.discard(k))

            async def los():
                if await a.aendern(dk.zkl_umsetzen, set(gewaehlt)):
                    a.panel_zu()

            with ui.element("div").classes("m-paktionen"):
                knopf("Gewählte übernehmen, Rest als geprüft", los, "primaer", "check")
                knopf("Abbrechen", a.panel_zu, "leise")

    def bauen():
        ui.label("Abweichungen zwischen ZKL und Zimmerplan. Angehakte werden übernommen, die übrigen als geprüft abgelegt."
                 ).classes("m-ptext")
        box = ui.element("div").classes("m-plan-liste")
        with box:
            ui.label("Wird verglichen …").classes("m-ptext")
        ui.timer(0.05, lambda: laden_(box), once=True)

    a.panel("ZKL-Abgleich", bauen, breit=True)


async def _statistik(a, art: str, dateien) -> None:
    pfad, name = dateien[0]
    try:
        zu, eintraege, hinweise, je_standort = await run.io_bound(dk.statistik_lesen, pfad, name, art)
    except Exception as exc:                  # noqa: BLE001
        a.toast(f"„{name}“ konnte nicht gelesen werden: {exc}", fehler=True)
        return

    def bauen():
        ui.label(f"{len(eintraege)} Einträge erkannt (Spalten automatisch zugeordnet).").classes("m-ptext")
        for s, n in je_standort.items():
            ui.label(f"{konfig.STANDORT_LABEL.get(s, s)}: {n}").classes("m-zweite")
        for h in hinweise[:10]:
            ui.label(h).classes("m-zweite").style("color:var(--orange); white-space:normal")
        ui.label("Passt die Zuordnung nicht, die Datei bitte im Hauptprogramm importieren (dort mit Spaltenwahl).").classes("m-zweite")

        async def los():
            if await a.aendern(dk.statistik_uebernehmen, art, pfad, name, zu, eintraege):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Übernehmen (ersetzt den bisherigen Import)", los, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel(f"{importe.ARTEN[art]} importieren", bauen)


def _manuell(a, q: dk.Quelle) -> None:
    with ui.element("section").classes("m-block"):
        ui.label(q.titel).classes("m-btitel")
        ui.label("Belegungen, die in keiner Liste stehen (z. B. Gäste, Jugendhilfe) – zählen in Statistik und Prognose."
                 ).classes("m-ptext")
        for i, e in enumerate(a.daten["manuell"]):
            with ui.element("div").classes("m-notiz"):
                ui.label(f"{e.get('typ', '')} · {konfig.STANDORT_LABEL.get(e.get('standort', ''), e.get('standort', ''))} · "
                         f"{e.get('anzahl', '')} Pers.").classes("m-name")
                ui.label(f"{date.fromisoformat(e['von']):%d.%m.%Y} – {date.fromisoformat(e['bis']):%d.%m.%Y}"
                         + (f" · {e['bezeichnung']}" if e.get("bezeichnung") else "")).classes("m-zweite")
                knopf("", lambda i=i: a.aendern(dk.manuell_loeschen, i), "leise", "delete", "Eintrag löschen")
        knopf("Eintrag hinzufügen …", lambda: _manuell_panel(a), "", "add")


def _manuell_panel(a) -> None:
    def bauen():
        typ = ui.select(konfig.MANUELLE_KATEGORIEN, value=konfig.MANUELLE_KATEGORIEN[0], label="Kategorie").classes(
            "m-feld").props('dense outlined dark options-dense popup-content-class="m-popup"')
        ort = ui.select({s: konfig.STANDORT_LABEL[s] for s in konfig.STANDORTE}, value=konfig.STANDORTE[0],
                        label="Standort").classes("m-feld").props('dense outlined dark options-dense popup-content-class="m-popup"')
        von = ui.input("Von", value=a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
        bis = ui.input("Bis", value=a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
        anz = ui.number("Anzahl Personen", value=1, min=1, step=1, format="%d").classes("m-feld").props("dense outlined dark")
        bez = ui.input("Bezeichnung (optional)").classes("m-feld").props("dense outlined dark")

        async def los():
            try:
                v, b = date.fromisoformat(von.value), date.fromisoformat(bis.value)
            except (TypeError, ValueError):
                a.toast("Bitte Von und Bis wählen.", fehler=True)
                return
            if await a.aendern(dk.manuell_hinzu, typ.value, ort.value, v, b, int(anz.value or 1), bez.value or ""):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", los, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Manueller Eintrag", bauen)
