"""Seite „Daten & Import“: je Quelle eine Karte mit Stand und „Hochladen“. Gelesen wird erst als Vorschau im Panel
rechts; übernommen wird nach Bestätigung (Rückgängig möglich). Dazu Gebäudeplan prüfen, ZKL-Abgleich, Pivot und
Kapazitäten, Statistik-Listen und manuelle Einträge."""

from __future__ import annotations

import tempfile
import uuid
from datetime import date
from pathlib import Path

from fastapi import Request
from nicegui import app, run, ui

from belegung import importe, konfig

from . import daten_kern as dk
from . import seiten
from .ui_bausteine import knopf, leer

UPLOAD = Path(tempfile.gettempdir()) / "belegung_uploads"
EINGEFUEGT: dict[str, dict] = {}          # Kennung → {"text", "html"} (eingefügter Gebäudeplan, kurz zwischengelagert)


@app.post("/einfuegen")
async def _einfuegen_empfangen(request: Request) -> dict:
    """Eingefügter Inhalt kommt per POST (kann größer sein als eine Socket-Nachricht); nur vom eigenen Rechner."""
    if request.client is None or request.client.host not in ("127.0.0.1", "::1", "localhost"):
        return {"id": ""}
    daten = await request.json()
    kennung = uuid.uuid4().hex
    EINGEFUEGT.clear()
    EINGEFUEGT[kennung] = {"text": str(daten.get("text") or ""), "html": str(daten.get("html") or "")}
    return {"id": kennung}


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
                   "Erinnerungen bleiben bei einem neuen Upload erhalten. Neue Dateien in den Ordnern „Listen“ und „UWT“ "
                   "werden beim Start automatisch eingelesen.",
                   lambda: knopf("Ordner jetzt einlesen", lambda: _ordner(a), "leise", "folder_open",
                                 " · ".join(f"{k}: {v}" for k, v in dk.eingangsordner().items())))
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
                    knopf("Aus Zwischenablage einfügen …", lambda: _plan_einfuegen(a), "leise", "content_paste",
                          "Gebäudeansicht im Belegungssystem markieren (Strg+A), kopieren (Strg+C) und hier einfügen")
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
                    knopf("Pivot-Struktur …", lambda: _pivot_struktur(a), "leise", "table_chart",
                          "Nur nötig, wenn eine Datei anders aufgebaut ist als üblich")
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


async def _ordner(a) -> None:
    meldungen = await run.io_bound(dk.ordner_importieren)
    if not meldungen:
        a.toast("Keine neuen Dateien in den Ordnern „Listen“ und „UWT“.", rueck=False)
        return
    await a.laden()
    a.toast("Eingelesen – " + " · ".join(meldungen[:3]) + (f" (+{len(meldungen) - 3})" if len(meldungen) > 3 else ""))


# ---- Anreiselisten ----------------------------------------------------------------------

async def _anreisen_vorschau(a, dateien) -> None:
    v = await run.io_bound(dk.anreisen_lesen, [p for p, _ in dateien], [n for _, n in dateien])
    try:
        aenderungen = await run.io_bound(dk.anreisen_aenderungen, v) if v.listen else []
    except Exception:                          # noqa: BLE001 – der Bericht ist Zusatz, der Import geht trotzdem
        aenderungen = []

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
        _aenderungen_zeigen(aenderungen)

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


def _aenderungen_zeigen(aenderungen: list) -> None:
    """Änderungsbericht vor dem Import: geänderte An-/Abreisen (mit betroffener Zimmerplanung), entfallene, neue."""
    if not aenderungen:
        ui.label("Gegenüber dem jetzigen Stand ändert sich an bekannten Personen nichts.").classes("m-zweite")
        return
    n = {art: sum(1 for x in aenderungen if x.art == art) for art in ("geaendert", "entfernt", "neu")}
    betroffen = sum(1 for x in aenderungen if x.zimmer)
    ui.label("Was sich gegenüber dem jetzigen Stand ändert").classes("m-ktitel")
    ui.label(f"{n['geaendert']} geändert · {n['entfernt']} nicht mehr auf der Liste · {n['neu']} neu"
             + (f" · {betroffen} geplante Zimmer betroffen – nach dem Import unter Anreisen prüfen" if betroffen else "")
             ).classes("m-ptext")
    titel = {"geaendert": "Geändert", "entfernt": "Nicht mehr auf der Liste", "neu": "Neu"}
    for art in ("geaendert", "entfernt", "neu"):
        liste = [x for x in aenderungen if x.art == art]
        if not liste:
            continue
        ui.label(titel[art]).classes("m-mgruppe")
        for x in liste[:25]:
            with ui.element("div").classes("m-aenderung" + (" betroffen" if x.zimmer else "")):
                ui.label(x.name).classes("m-name")
                ui.label(x.text + (f" · Zimmer {x.zimmer} geplant" if x.zimmer else "")).classes("m-zweite").style(
                    "white-space:normal")
        if len(liste) > 25:
            ui.label(f"+{len(liste) - 25} weitere").classes("m-zweite")


# ---- UWT --------------------------------------------------------------------------------

async def _uwt_vorschau(a, dateien) -> None:
    pfad, name = dateien[0]
    try:
        art, daten_ = await run.io_bound(dk.uwt_lesen, pfad)
    except Exception as exc:                  # noqa: BLE001
        a.toast(f"„{name}“ konnte nicht gelesen werden: {exc}", fehler=True)
        return

    # Blockplan ohne Personenliste: die Anzahl je Klasse kommt aus den Klassenstärken – hier vor dem Import einstellbar
    staerken = dk.klassen_der_liste(daten_) if art == "bloecke" and not daten_.personen else {}

    @ui.refreshable
    def bloecke_zeigen():
        if staerken:
            dk.klassen_anwenden(daten_, staerken)
        zaehlen = [b for b in daten_.bloecke if b.anzahl > 0]
        ui.label(f"{len(zaehlen)} Blöcke zählen · {sum(b.anzahl for b in zaehlen)} Plätze"
                 + (f" · {len(daten_.bloecke) - len(zaehlen)} ohne Internat" if len(zaehlen) < len(daten_.bloecke) else "")
                 ).classes("m-name")
        for b in daten_.bloecke[:30]:
            ui.label(f"{b.klasse} · {b.anzahl} · {b.anreise:%d.%m.%Y} – {b.abreise:%d.%m.%Y} ({(b.abreise - b.anreise).days} Nächte)"
                     ).classes("m-zweite" + (" fertig" if b.anzahl <= 0 else ""))
        if len(daten_.bloecke) > 30:
            ui.label(f"+{len(daten_.bloecke) - 30} weitere").classes("m-zweite")

    def bauen():
        if art == "klassen":
            klassen, hinweise = daten_
            ui.label(f"Klassenübersicht: {len(klassen)} Klassen").classes("m-ptext")
            for k, ps in sorted(klassen.items()):
                ui.label(f"{k}: {len(ps)} Teilnehmende, {sum(1 for p in ps if p.partner)} mit DZ-Partner").classes("m-zweite")
        else:
            ui.label(f"{len(daten_.bloecke)} Blöcke" + (f", {len(daten_.personen)} Personen" if daten_.personen else "")).classes("m-ptext")
            if staerken:
                ui.label("Klassenstärken im Internat").classes("m-abschnitt")
                ui.label("Wie viele Schüler/-innen je Klasse im Internat wohnen – 0 = Klasse zählt nicht (z. B. Chemikanten). "
                         "Wird für die nächsten Importe gespeichert.").classes("m-zweite")
                with ui.element("div").classes("m-klassen"):
                    for k in staerken:
                        n = ui.number(k, value=staerken[k], min=0, max=60, step=1, format="%d").classes("m-feld").props(
                            "dense outlined dark")
                        n.on_value_change(lambda e, k=k: (staerken.__setitem__(k, int(e.value or 0)), bloecke_zeigen.refresh()))
            bloecke_zeigen()
            hinweise = daten_.hinweise
        for h in hinweise[:10]:
            ui.label(h).classes("m-zweite").style("color:var(--orange); white-space:normal")

        async def los():
            if await a.aendern(dk.uwt_uebernehmen, art, daten_, name, staerken or None):
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
    knopf("Klassenstärken …", lambda: _klassen_panel(a), "leise", "groups")


def _klassen_panel(a) -> None:
    werte = dk.klassenstaerken()

    def bauen():
        ui.label("Wie viele Schüler/-innen je Klasse im Internat wohnen. Gilt beim nächsten Import eines Blockplans "
                 "(PDF ohne Personenliste); 0 = Klasse zählt nicht.").classes("m-ptext")
        with ui.element("div").classes("m-klassen"):
            for k in werte:
                n = ui.number(k, value=werte[k], min=0, max=60, step=1, format="%d").classes("m-feld").props("dense outlined dark")
                n.on_value_change(lambda e, k=k: werte.__setitem__(k, int(e.value or 0)))

        async def speichern():
            if await a.aendern(dk.klassenstaerken_setzen, dict(werte)):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Klassenstärken im Internat", bauen)


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


def _plan_einfuegen(a) -> None:
    """Gebäudeplan aus der Zwischenablage: Feld anklicken, Strg+V – der Browser liest Text und HTML."""
    def bauen():
        ui.label("Im Belegungssystem die Gebäudeansicht öffnen, alles markieren (Strg+A) und kopieren (Strg+C). "
                 "Dann hier in das Feld klicken und Strg+V drücken. Danach wird wie beim Hochladen mit dem Zimmerplan "
                 "verglichen.").classes("m-ptext")
        feld = ui.element("div").classes("m-einfuegen").props('tabindex="0" contenteditable="true"')
        with feld:
            ui.label("Hier klicken und Strg+V").classes("m-zweite")
        feld.on("paste", lambda e: _plan_eingefuegt(a, e.args), js_handler=(
            "async (e) => { e.preventDefault(); const t = e.clipboardData.getData('text/plain'); "
            "const h = e.clipboardData.getData('text/html'); e.target.closest('.m-einfuegen').classList.add('liest'); "
            "const r = await fetch('/einfuegen', {method: 'POST', headers: {'Content-Type': 'application/json'}, "
            "body: JSON.stringify({text: t, html: h})}); emit((await r.json()).id); }"))
        with ui.element("div").classes("m-paktionen"):
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Gebäudeplan einfügen", bauen)


async def _plan_eingefuegt(a, kennung) -> None:
    daten = EINGEFUEGT.pop(kennung, None) if isinstance(kennung, str) else None
    if not daten or not (daten["text"].strip() or daten["html"].strip()):
        a.toast("Die Zwischenablage war leer – bitte erst im Belegungssystem kopieren.", fehler=True, rueck=False)
        return
    try:
        plan, unterschiede, quelle = await run.io_bound(dk.gebaeudeplan_aus_zwischenablage, daten["text"], daten["html"])
    except ValueError as exc:
        a.toast(str(exc), fehler=True, rueck=False)
        return
    a.panel_zu()
    if not unterschiede:
        await a.aendern(seiten.sk.plan_uebernehmen, plan, [], quelle)
        return
    seiten._plan_panel(a, plan, quelle, unterschiede)


async def _einfach(a, aktion, dateien, zkl: bool = False) -> None:
    if await a.aendern(aktion, dateien[0][0]) and zkl:
        _zkl_panel(a)


async def _pivot(a, dateien) -> None:
    from . import auswertung_kern as ak

    if await a.aendern(dk.pivot_setzen, dateien[0][0], dateien[0][1]):
        await run.io_bound(ak.datenstand, True)


async def _pivot_struktur(a) -> None:
    """Aufbau der Pivot-Datei festlegen – mit Vorschau, die sofort zeigt, ob die Einstellungen passen."""
    try:
        st = await run.io_bound(dk.pivot_struktur)
    except ValueError as exc:
        a.toast(str(exc), fehler=True, rueck=False)
        return
    felder = dict(st["profil"])
    pfad = st["pfad"]
    zustand = {"ok": False, "text": "Datei wird gelesen …"}

    @ui.refreshable
    def ergebnis():
        ui.label(zustand["text"]).classes("m-ptext").style(
            "white-space:normal;" + ("" if zustand["ok"] else "color:var(--orange)"))

    async def pruefen():
        zustand["ok"], zustand["text"] = await run.io_bound(dk.pivot_vorschau, pfad, dict(felder))
        ergebnis.refresh()

    def setzen(k, v):
        felder[k] = v
        return pruefen()

    def bauen():
        ui.label(f"{pfad.name} – nur nötig, wenn eine Datei anders aufgebaut ist als üblich. Die Vorschau zeigt sofort, "
                 "ob die Einstellungen passen.").classes("m-ptext")
        props = 'dense outlined dark options-dense popup-content-class="m-popup"'
        ui.input("Profilname", value=felder["name"]).classes("m-feld").props("dense outlined dark").on_value_change(
            lambda e: felder.__setitem__("name", e.value))
        ui.select(dk.PIVOT_MODUS, value=felder["sheet_modus"], label="Tabellenblatt").classes("m-feld").props(
            props).on_value_change(lambda e: setzen("sheet_modus", e.value))
        if st["blaetter"]:
            ui.select(st["blaetter"], value=felder["sheet_name"] if felder["sheet_name"] in st["blaetter"] else None,
                      label="Blattname (bei festem Tabellenblatt)").classes("m-feld").props(props).on_value_change(
                lambda e: setzen("sheet_name", e.value))
        ui.select(dk.PIVOT_AUSRICHTUNG, value=felder["ausrichtung"], label="Ausrichtung").classes("m-feld").props(
            props).on_value_change(lambda e: setzen("ausrichtung", e.value))
        ui.select(dk.PIVOT_EBENEN, value=int(felder["hierarchie_ebenen"]), label="Ebenen").classes("m-feld").props(
            props).on_value_change(lambda e: setzen("hierarchie_ebenen", e.value))
        for k, t in (("kopfzeilen_marker", "Kopfzeilen-Text"), ("zwischensummen_suffix", "Zwischensummen-Endung"),
                     ("datumsformat", "Datumsformat")):
            i = ui.input(t, value=felder[k]).classes("m-feld").props("dense outlined dark")
            i.on("blur", lambda e, k=k, i=i: setzen(k, i.value))
            i.on("keydown.enter", lambda e, k=k, i=i: setzen(k, i.value))
        ui.label("Vorschau").classes("m-ktitel")
        ergebnis()

        async def speichern():
            from . import auswertung_kern as ak

            if await a.aendern(dk.pivot_struktur_speichern, pfad, dict(felder)):
                await run.io_bound(ak.datenstand, True)
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern und anwenden", speichern, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Pivot-Struktur", bauen)
    await pruefen()


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
