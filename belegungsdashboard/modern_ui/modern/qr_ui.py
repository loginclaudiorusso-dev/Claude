"""Oberfläche für Meldungen per QR-Code. Logik in ``qr_meldungen_kern``.

1.31: eigener Unterpunkt „QR-Meldungen“ (Zimmer & Haus → Betrieb): oben die Prüfanzeige (kommt alles an?), darunter die
Meldungen (neu / übernommen / verworfen). Ein Klick auf eine Meldung öffnet rechts das Fenster mit Zimmerinfo, Zimmer-
und Artwahl, Übernehmen und Verwerfen. „Defekte Zimmer“ zeigt nur noch einen Hinweis mit Sprung dorthin. Das Fenster
„QR-Codes“ (Formular-Link, Antwortdatei, Etiketten drucken) bleibt."""

from __future__ import annotations

from belegung import maengel as mg
from nicegui import run, ui

from . import qr_meldungen_kern as qm
from .standort_kern import kurz as zkurz
from .ui_bausteine import attr, kennzahlen, knopf, leer

POPUP = 'dense outlined dark popup-content-class="m-popup"'


def daten(a) -> None:
    """Im Hintergrund (mit den übrigen Daten der Seite)."""
    try:
        a.qr_neu = qm.neue()
    except Exception:                                   # noqa: BLE001 – Zusatz, darf die Seite nie blockieren
        a.qr_neu = []


def bereich(a) -> None:
    """In „Defekte Zimmer“: nur ein Hinweis mit Sprung zum Unterpunkt QR-Meldungen."""
    ms: list[qm.Meldung] = getattr(a, "qr_neu", None) or []
    if not ms:
        return
    with ui.element("div").classes("m-ue-filter").style("cursor:pointer") as h:
        ui.icon("qr_code_2")
        ui.label(f"{len(ms)} neue Meldung{'en' if len(ms) > 1 else ''} per QR-Code – zum Prüfen öffnen")
    h.on("click", lambda: a.oeffnen("zimmer", ansicht="qr"))


def knopf_leiste(a) -> None:
    n = len(getattr(a, "qr_neu", None) or [])
    knopf(f"QR-Meldungen{f' · {n} neu' if n else ''}", lambda: a.oeffnen("zimmer", ansicht="qr"),
          "akzent" if n else "leise", "qr_code_2", "Meldungen per QR-Code prüfen und übernehmen")


# ---- 1.31: Unterpunkt „QR-Meldungen“ --------------------------------------------------------------------------------

FILTER = {"neu": "neu", "uebernommen": "übernommen", "verworfen": "verworfen"}
STUFE_SYMBOL = {"ok": ("check_circle", "m-ok"), "warn": ("warning_amber", "m-warn"), "krit": ("error", "m-krit"),
                "info": ("info", "m-zweite")}


def ansicht_daten(a) -> None:
    """Im Hintergrund: alle Meldungen und die Prüfanzeige (liest die Antwortdatei, übernimmt nichts)."""
    try:
        alle = qm.meldungen()
    except Exception:                                   # noqa: BLE001
        alle = []
    try:
        diag = qm.diagnose()
    except Exception as exc:                            # noqa: BLE001 – die Prüfung selbst darf nie die Seite blockieren
        diag = [qm.Punkt("krit", "Prüfung", f"Prüfung nicht möglich: {exc}")]
    a.qr_neu = [m for m in alle if m.status == "neu"]
    a.daten = {"alle": alle, "diag": diag}


async def _jetzt_einlesen(a) -> None:
    erg = await run.io_bound(qm.einlesen, None, True)
    if erg is None:
        return
    neu, fehler = erg
    if fehler:
        a.toast(fehler, fehler=True)
    else:
        a.toast(f"{len(neu)} neue Meldung(en) eingelesen" if neu else "Keine neuen Meldungen in der Antwortdatei",
                rueck=False)
    await a.laden()


def ansicht_zeichnen(a) -> None:
    d = a.daten or {}
    alle: list[qm.Meldung] = d.get("alle") or []
    diag: list[qm.Punkt] = d.get("diag") or []
    filt = getattr(a, "qr_filter", "neu")
    n = {k: sum(1 for m in alle if m.status == k) for k in FILTER}
    with a.leiste:
        kennzahlen([("neu", n["neu"], "neu", "warn" if n["neu"] else "neutral"),
                    ("uebernommen", n["uebernommen"], "übernommen", "ok"),
                    ("verworfen", n["verworfen"], "verworfen", "neutral")],
                   filt, lambda k: a.setzen(qr_filter=k, laden=False))
        a.status_info = f"{n['neu']} neue Meldung(en) per QR-Code"
        knopf("Einrichten & Etiketten", lambda: fenster(a), "leise", "settings",
              "Formular-Link, Antwortdatei auf diesem PC, Etiketten drucken")
        knopf("Jetzt einlesen", lambda: _jetzt_einlesen(a), "primaer", "sync", "Antwortdatei sofort lesen")
    with a.inhalt:
        _pruefanzeige(diag)
        zeigen = [m for m in alle if m.status == filt]
        ui.label(f"Meldungen – {FILTER[filt]} ({len(zeigen)})").classes("m-abschnitt")
        if not zeigen:
            leer("Keine neuen Meldungen." if filt == "neu" else f"Keine Meldungen „{FILTER[filt]}“.")
            return
        sp = "112px 110px minmax(220px, 2fr) minmax(150px, 1fr) 110px"
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("Eingang", "Zimmer", "Meldung", "Mangelart", ""):
                ui.label(t)
        for m in zeigen:
            z_ = ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp};cursor:pointer")
            attr(z_, title="Klick: Details rechts")
            with z_:
                ui.label(m.zeit_text).classes("m-mono")
                ui.label(zkurz(m.zimmer) if m.zimmer else f"„{m.zimmer_text or '?'}“").classes(
                    "m-name" + ("" if m.zimmer else " m-warn"))
                with ui.element("div"):
                    ui.label(m.text or m.art_text or "(ohne Text)").classes("m-ptext" + (" m-warn" if m.dringend else ""))
                    if m.hinweis:
                        with ui.element("div").style("display:flex;gap:4px;align-items:center"):
                            ui.icon("warning_amber").classes("m-warn")
                            ui.label(m.hinweis).classes("m-zweite m-warn").style("white-space:normal")
                ui.label(mg.NAMEN.get(m.art, m.art)).classes("m-zweite")
                ui.label({"neu": "prüfen ›", "uebernommen": "übernommen", "verworfen": "verworfen"}[m.status]).classes(
                    "m-link" if m.status == "neu" else "m-zweite")
            z_.on("click", lambda m=m: meldung_panel(a, m))


def _pruefanzeige(diag: list) -> None:
    """Kommt alles an? – jeder Punkt mit Ampel. Ist alles grün, nur eine Zeile."""
    probleme = [p for p in diag if p.stufe in ("warn", "krit")]
    kasten = ui.element("details").classes("m-qr-pruef")
    if probleme:
        kasten.props("open")                           # bei Problemen gleich aufgeklappt
    with kasten:
        with ui.element("summary").style("cursor:pointer;padding:6px 0"):
            sym, kl = STUFE_SYMBOL["krit" if any(p.stufe == "krit" for p in probleme) else "warn" if probleme else "ok"]
            ui.icon(sym).classes(kl)
            ui.label("Verbindung prüfen: " + (f"{len(probleme)} Punkt(e) beachten" if probleme else "alles in Ordnung")) \
                .classes("m-ptext").style("display:inline;margin-left:6px")
        for p in diag:
            sym, kl = STUFE_SYMBOL.get(p.stufe, STUFE_SYMBOL["info"])
            with ui.element("div").style("display:flex;gap:8px;align-items:flex-start;padding:3px 0 3px 4px"):
                ui.icon(sym).classes(kl)
                with ui.element("div"):
                    ui.label(p.titel).classes("m-name")
                    ui.label(p.text).classes("m-zweite").style("white-space:normal;word-break:break-word")


async def meldung_panel(a, m: qm.Meldung) -> None:
    """Rechts: die Meldung mit Zimmerinfo – Zimmer und Art korrigieren, übernehmen oder verwerfen."""
    from . import zimmer_kern as zk

    karte = None
    if m.zimmer:
        try:
            karte = await run.io_bound(zk.karte, a.stand, m.zimmer, a.heute)
        except ValueError:
            karte = None
    arten = dict(mg.KATALOG)
    zimmer = {z.id: z.kurz for z in a.stand.zimmer if z.aktiv}
    wahl = {"zimmer": m.zimmer, "art": m.art}

    def bauen():
        ui.label(m.text or m.art_text or "(ohne Text)").classes("m-ptext" + (" m-warn" if m.dringend else "")) \
            .style("font-size:1.05em")
        info = [f"Eingang {m.zeit_text}"] + ([f"Auswahl im Formular: {m.art_text}"] if m.art_text else []) \
            + ([f"Im Formular eingetragen: „{m.zimmer_text}“"] if m.zimmer_text else []) \
            + ([f"Prüfcode {m.code}"] if m.code else [])
        ui.label(" · ".join(info)).classes("m-zweite").style("white-space:normal")
        if m.hinweis:
            with ui.element("div").style("display:flex;gap:6px;align-items:center;margin-top:6px"):
                ui.icon("warning_amber").classes("m-warn")
                ui.label(m.hinweis).classes("m-ptext m-warn").style("white-space:normal")

        ui.label("Zimmer").classes("m-abschnitt")
        if karte is not None:
            ui.label(f"{karte.kurz} · {karte.lage} · {karte.betten} Bett{'en' if karte.betten != 1 else ''}"
                     + (f" · {karte.merkmale}" if karte.merkmale else "")).classes("m-ptext")
            heute = [p for p in karte.personen if not p.kommt]
            ui.label("Heute: " + (", ".join(f"{p.name} (bis {p.bis:%d.%m.})" for p in heute) if heute else "frei")) \
                .classes("m-zweite").style("white-space:normal")
            if karte.maengel:
                ui.label("Offene Mängel: " + ", ".join(f"{n} (seit {s_:%d.%m.})" for _a, n, _st, _u, s_, *_r in karte.maengel)) \
                    .classes("m-zweite m-warn").style("white-space:normal")
            else:
                ui.label("Keine offenen Mängel.").classes("m-zweite")
        elif m.status == "neu":
            ui.label("Das Zimmer aus dem Formular wurde nicht erkannt – bitte unten wählen.").classes("m-zweite m-warn")

        if m.status != "neu":
            ui.label({"uebernommen": f"Als Mangel übernommen am {m.erledigt}", "verworfen": f"Verworfen am {m.erledigt}"}
                     .get(m.status, m.status) + (f" – {m.hinweis}" if m.hinweis and m.status == "uebernommen" else "")) \
                .classes("m-ptext").style("margin-top:10px")
        else:
            ui.label("Übernehmen als").classes("m-abschnitt")
            s_ = ui.select(zimmer, value=m.zimmer if m.zimmer in zimmer else None, with_input=True, label="Zimmer") \
                .classes("m-feld w-full").props(POPUP)
            s_.on_value_change(lambda e: wahl.update(zimmer=e.value or ""))
            art = ui.select(arten, value=m.art, label="Mangelart").classes("m-feld w-full").props(POPUP)
            art.on_value_change(lambda e: wahl.update(art=e.value))

            async def uebernehmen():
                if await a.aendern(qm.uebernehmen, m.id, wahl["art"], wahl["zimmer"]):
                    a.panel_zu()

            async def verwerfen():
                if await a.aendern(qm.verwerfen, m.id):
                    a.panel_zu()
            with ui.element("div").classes("m-paktionen"):
                knopf("Übernehmen", uebernehmen, "primaer", "add_task", "Als Mangel im Zimmer anlegen (mit Rückgängig)")
                knopf("Verwerfen", verwerfen, "leise", "close", "Spaß, doppelt oder schon erledigt")
        with ui.element("div").classes("m-paktionen"):
            if m.zimmer:
                from .seite_zimmer import karte_oeffnen

                knopf("Zimmerkarte öffnen", lambda: karte_oeffnen(a, wahl["zimmer"] or m.zimmer), "leise", "open_in_new")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel(f"QR-Meldung · {zkurz(m.zimmer) if m.zimmer else 'Zimmer ?'}", bauen)


def fenster(a) -> None:
    """Einrichten und Drucken – drei Schritte."""
    def bauen():
        ui.label("Gäste melden Mängel anonym per Handy: QR-Code am Zimmer → Microsoft-Forms-Formular mit "
                 "eingetragener Zimmernummer → INNternat liest die Antworten alle paar Minuten ein und zeigt sie hier "
                 "zum Prüfen. Ein Mangel entsteht erst, wenn Sie „Übernehmen“ klicken.").classes("m-ptext")

        ui.label("1 · Formular-Link (gilt für alle PCs)").classes("m-abschnitt")
        ui.label(f"In Forms: Formular öffnen → „…“ → „Vorausgefüllte URL abrufen“ → bei „Zimmer“ {qm.PLATZHALTER} und bei "
                 f"„Code (bitte nicht ändern)“ {qm.CODE_PLATZHALTER} eintragen → „Vorausgefüllten Link abrufen“ → Kopieren "
                 "und hier einfügen. Der Code zeigt später, ob jemand die Zimmernummer geändert hat.").classes("m-ptext")
        if (l_ := qm.link()) and qm.CODE_PLATZHALTER not in l_:
            ui.label("Der gespeicherte Link enthält noch keinen Prüfcode (CODE).").classes("m-zweite m-warn")
        link = ui.input(value=qm.link(), label="Vorausgefüllter Link mit ZIMMER und CODE").classes("m-feld w-full").props(
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
