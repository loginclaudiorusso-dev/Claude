"""1.28: Oberfläche für Meldungen per QR-Code – Bereich „Neu per QR-Code“ in „Defekte Zimmer“ und das Fenster
„QR-Codes“ (Formular-Link, Antwortdatei, Etiketten drucken). Logik in ``qr_meldungen_kern``."""

from __future__ import annotations

from belegung import maengel as mg
from nicegui import run, ui

from . import qr_meldungen_kern as qm
from .standort_kern import kurz as zkurz
from .ui_bausteine import knopf

POPUP = 'dense outlined dark popup-content-class="m-popup"'


def daten(a) -> None:
    """Im Hintergrund (mit den übrigen Daten der Seite)."""
    try:
        a.qr_neu = qm.neue()
    except Exception:                                   # noqa: BLE001 – Zusatz, darf die Seite nie blockieren
        a.qr_neu = []


def bereich(a) -> None:
    """Neue Meldungen oben in „Defekte Zimmer“: prüfen, Art/Zimmer korrigieren, übernehmen oder verwerfen."""
    ms: list[qm.Meldung] = getattr(a, "qr_neu", None) or []
    if not ms:
        return
    arten = dict(mg.KATALOG)
    zimmer = {z.id: z.kurz for z in a.stand.zimmer if z.aktiv}
    sp = "112px 150px minmax(180px, 1.6fr) 200px 210px"
    ui.label(f"Neu per QR-Code ({len(ms)}) – bitte prüfen").classes("m-abschnitt")
    with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
        for t in ("Eingang", "Zimmer", "Meldung", "Mangelart", ""):
            ui.label(t)
    for m in ms:
        with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
            ui.label(m.zeit_text).classes("m-mono")
            wahl = {"zimmer": m.zimmer, "art": m.art}
            if m.zimmer:
                ui.label(zkurz(m.zimmer)).classes("m-name")
            else:
                s = ui.select(zimmer, value=None, with_input=True, label=f"„{m.zimmer_text or '?'}“ – Zimmer wählen") \
                    .classes("m-feld").props(POPUP)
                s.on_value_change(lambda e, w=wahl: w.update(zimmer=e.value or ""))
            with ui.element("div"):
                text = m.text or m.art_text or "(ohne Text)"
                ui.label(text).classes("m-ptext" + (" m-warn" if m.dringend else ""))
                if m.art_text and m.text:
                    ui.label(m.art_text).classes("m-zweite")
            art = ui.select(arten, value=m.art).classes("m-feld").props(POPUP)
            art.on_value_change(lambda e, w=wahl: w.update(art=e.value))
            with ui.element("div").style("display:flex;gap:6px;align-items:center"):
                knopf("Übernehmen", lambda m=m, w=wahl: a.aendern(qm.uebernehmen, m.id, w["art"], w["zimmer"]),
                      "primaer", "add_task", "Als Mangel im Zimmer anlegen (mit Rückgängig)")
                knopf("", lambda m=m: a.aendern(qm.verwerfen, m.id), "leise", "close", "Verwerfen (Spaß, doppelt, erledigt)")


def knopf_leiste(a) -> None:
    n = len(getattr(a, "qr_neu", None) or [])
    knopf(f"QR-Codes{f' · {n} neu' if n else ''}", lambda: fenster(a), "akzent" if n else "leise", "qr_code_2",
          "Meldungen per QR-Code: Formular-Link, Antwortdatei, Etiketten drucken")


def fenster(a) -> None:
    """Einrichten und Drucken – drei Schritte."""
    def bauen():
        ui.label("Gäste melden Mängel anonym per Handy: QR-Code am Zimmer → Microsoft-Forms-Formular mit "
                 "eingetragener Zimmernummer → INNternat liest die Antworten alle paar Minuten ein und zeigt sie hier "
                 "zum Prüfen. Ein Mangel entsteht erst, wenn Sie „Übernehmen“ klicken.").classes("m-ptext")

        ui.label("1 · Formular-Link (gilt für alle PCs)").classes("m-abschnitt")
        ui.label(f"In Forms: Formular öffnen → „…“ → „Vorausgefüllte URL abrufen“ → bei „Zimmer“ {qm.PLATZHALTER} "
                 "eintragen → „Vorausgefüllten Link abrufen“ → Kopieren und hier einfügen.").classes("m-ptext")
        link = ui.input(value=qm.link(), label="Vorausgefüllter Link mit ZIMMER").classes("m-feld w-full").props(
            "dense outlined dark")
        knopf("Link speichern", lambda: a.aendern(qm.link_setzen, link.value or ""), "", "link")

        ui.label("2 · Antwortdatei auf diesem PC").classes("m-abschnitt")
        ui.label("In Forms: „Antworten“ → „In Excel öffnen“. Die Datei liegt in OneDrive; im Explorer mit Umschalt + "
                 "Rechtsklick → „Als Pfad kopieren“ und hier einfügen. Es reicht ein PC.").classes("m-ptext")
        datei = ui.input(value=qm.antwortdatei(), label="Pfad der Excel-Datei (.xlsx)").classes("m-feld w-full").props(
            "dense outlined dark")

        async def datei_speichern():
            try:
                a.toast(await run.io_bound(qm.antwortdatei_setzen, datei.value or ""), rueck=False)
            except ValueError as exc:
                a.toast(str(exc), fehler=True)

        async def jetzt():
            neu, fehler = await run.io_bound(qm.einlesen, None, True)
            if fehler:
                a.toast(fehler, fehler=True)
                return
            a.toast(f"{len(neu)} neue Meldung(en) eingelesen" if neu else "Keine neuen Meldungen", rueck=False)
            if neu:
                await a.laden()

        with ui.element("div").classes("m-paktionen"):
            knopf("Pfad speichern", datei_speichern, "", "save")
            knopf("Jetzt einlesen", jetzt, "leise", "sync")

        ui.label("3 · Etiketten drucken").classes("m-abschnitt")
        haeuser = sorted({z.haus for z in a.stand.zimmer if z.aktiv})
        auswahl = {"probe": "Probe: 1 Etikett (erst mit dem Handy testen)", "": "Alle Zimmer"}
        auswahl.update({h: f"Haus {h}" for h in haeuser})
        was = ui.select(auswahl, value="probe", label="Welche Zimmer").classes("m-feld").props(POPUP)

        async def drucken():
            zs = [(z.id, z.kurz) for z in a.stand.zimmer if z.aktiv and (was.value in ("", "probe") or z.haus == was.value)]
            if was.value == "probe":
                zs = zs[:1]
            try:
                html = await run.io_bound(qm.etiketten_html, qm.link(), zs)
            except ValueError as exc:
                a.toast(str(exc), fehler=True)
                return
            from .seiten import html_drucken

            html_drucken(a, html, "QR-Etiketten")

        with ui.element("div").classes("m-paktionen"):
            knopf("Etiketten drucken", drucken, "primaer", "print")
            knopf("Schließen", a.panel_zu, "leise")
        ui.label("A4, 12 Etiketten je Seite (6 × 6 cm). Tipp: laminieren oder auf wetterfeste Etiketten drucken.") \
            .classes("m-ptext")

    a.panel("QR-Codes für Mängelmeldungen", bauen)


async def takt() -> None:
    """Alle 5 Minuten: Antwortdatei lesen (falls auf diesem PC eingetragen) und neue Meldungen als Windows-Meldung
    zeigen – auf jedem PC genau einmal (auch auf PCs ohne Antwortdatei: sie sehen, was ein anderer PC eingelesen hat)."""
    import asyncio
    import logging

    from . import melder

    log = logging.getLogger(__name__)
    await asyncio.sleep(40)
    while True:
        try:
            erg = await run.io_bound(qm.einlesen)
            if erg is None:                # 1.29.1: Programm wird gerade beendet
                return
            _, fehler = erg
            if fehler:
                log.warning("QR-Meldungen: %s", fehler)
            if await run.io_bound(melder.an):
                neu = await run.io_bound(qm.noch_nicht_gemeldet)
                if len(neu) == 1:
                    melder.windows_zeigen("Neue Meldung per QR-Code", qm.kurztext(neu[0], zkurz))
                elif neu:
                    melder.windows_zeigen(f"{len(neu)} neue Meldungen per QR-Code",
                                          "; ".join(qm.kurztext(m, zkurz) for m in neu[:3]) + (" …" if len(neu) > 3 else ""))
        except Exception:                               # noqa: BLE001 – der Takt läuft weiter
            log.exception("QR-Meldungen nicht geprüft")
        await asyncio.sleep(qm.TAKT_MINUTEN * 60)
