"""Hilfe- und Drucken-Dialog (0.68) im Stil von Office (Datei → Hilfe / Drucken). Inhalte: ``hilfe_kern``."""

from __future__ import annotations

from nicegui import ui

from . import __version__, hilfe_kern as hk
from .ui_bausteine import knopf

STANDARD_ANSICHT = {"anreisen": "zuteilen", "zimmer": "uebersicht", "reinigung": "liste", "inventar": "gegenstaende"}


def _ansicht(a) -> str | None:
    return a.ansicht_von(a.seite, STANDARD_ANSICHT.get(a.seite, ""))


def _rahmen(a, titel: str, unter: str):
    ablage = getattr(a, "dialog_ablage", None)
    ctx = ablage if ablage is not None else ui.element("div")
    with ctx:
        dlg = ui.dialog()
    with dlg, ui.element("div").classes("m-opt m-hilfe"):
        with ui.element("div").classes("m-opt-kopf"):
            ui.label(titel).classes("m-opt-titel")
            ui.label(unter).classes("m-opt-unter")
            ui.element("div").style("flex:1")
            knopf("", dlg.close, "leise", "close", "Schließen (Esc)")
        koerper = ui.element("div").classes("m-opt-koerper")
    dlg.on("hide", lambda: dlg.delete() if not dlg.is_deleted else None)
    return dlg, koerper


def oeffnen(a, bereich: str = "seite") -> None:
    """Hilfe – beginnt bei der gerade offenen Seite."""
    dlg, koerper = _rahmen(a, "Hilfe", "F1 öffnet diese Hilfe jederzeit – passend zur offenen Seite")
    bereiche = {"seite": ("Diese Seite", "help"), "start": ("Erste Schritte", "school"),
                "tasten": ("Tastenkürzel", "keyboard"), "info": ("Info", "info")}
    zustand = {"b": bereich if bereich in bereiche else "seite"}
    with koerper:
        links = ui.element("nav").classes("m-opt-nav")
        rechts = ui.element("section").classes("m-opt-inhalt")

    def fuellen():
        links.clear()
        rechts.clear()
        with links:
            for k, (t, icon) in bereiche.items():
                b = ui.element("button").classes("m-opt-navpunkt" + (" an" if k == zustand["b"] else ""))
                with b:
                    ui.icon(icon)
                    ui.label(t)
                b.on("click", lambda k=k: (zustand.update(b=k), fuellen()))
        with rechts:
            if zustand["b"] == "seite":
                titel, text, punkte = hk.fuer(a.seite, _ansicht(a))
                ui.label(titel).classes("m-opt-abschnitt")
                if text:
                    ui.label(text).classes("m-hilfe-text")
                with ui.element("ul").classes("m-hilfe-liste"):
                    for p in punkte:
                        with ui.element("li"):
                            ui.label(p)
                druck = hk.druckausgaben(a.seite, _ansicht(a))
                if druck:
                    ui.label("Drucken auf dieser Seite: " + ", ".join(t for t, _k in druck) + " – unter Datei → Drucken.").classes(
                        "m-opt-unter")
            elif zustand["b"] == "start":
                ui.label("Erste Schritte").classes("m-opt-abschnitt")
                for t, text in hk.ERSTE_SCHRITTE:
                    with ui.element("div").classes("m-hilfe-schritt"):
                        ui.label(t).classes("m-hilfe-st")
                        ui.label(text).classes("m-hilfe-text")
            elif zustand["b"] == "tasten":
                ui.label("Tastenkürzel").classes("m-opt-abschnitt")
                with ui.element("div").classes("m-hilfe-tasten"):
                    for t, w in hk.TASTEN:
                        ui.html(f"<kbd>{t}</kbd>", sanitize=False)
                        ui.label(w)
            else:
                from belegung import __version__ as haupt

                from . import standort_kern

                ui.label("Info").classes("m-opt-abschnitt")
                ui.label(f"INNternat – neue Oberfläche {__version__}").classes("m-hilfe-text")
                ui.label(f"Daten und Regeln: Belegung {haupt} · Standort {standort_kern.aktiv().name}").classes("m-hilfe-text")
                ui.label("Ausführliche Beschreibung: README.md und FEATURES.md im Programmordner modern_ui.").classes(
                    "m-opt-unter")

    fuellen()
    dlg.open()


async def _ausgabe(a, key: str) -> None:
    from . import seite_anreisen, seite_zimmer, seiten

    if key in ("anreise", "schluessel", "schilder"):
        await seite_anreisen._drucken(a, key)
    elif key == "abreise":
        await seite_anreisen._ab_drucken(a)
    elif key == "reinigung":
        await seiten._rg_drucken(a)
    elif key == "wochenblatt":
        seiten._wochenblatt_panel(a)
    elif key == "zimmer_liste":
        await seite_zimmer._drucken(a, "liste")
    elif key == "zimmer_ohne":
        await seite_zimmer._drucken(a, "liste_ohne")
    elif key == "fm":
        await seite_zimmer._drucken(a, "fm")


def drucken(a) -> None:
    """Drucken wie in Office: die aktuelle Ansicht oder eine fertige Druckausgabe der Seite."""
    dlg, koerper = _rahmen(a, "Drucken", "Drucken oder als PDF speichern (im Druckdialog „Als PDF speichern“ wählen)")

    async def ansicht_drucken():
        dlg.close()
        ui.run_javascript("setTimeout(() => window.print(), 350)")

    async def ausgabe(key: str):
        dlg.close()
        await _ausgabe(a, key)

    with koerper, ui.element("section").classes("m-opt-inhalt"):
        ui.label("Aktuelle Ansicht").classes("m-opt-abschnitt")
        ui.label("Druckt, was gerade im Arbeitsbereich zu sehen ist – ohne Menüband und Leisten (Strg+P).").classes(
            "m-opt-unter")
        with ui.element("div").classes("m-opt-zeile"):
            knopf("Aktuelle Ansicht drucken", ansicht_drucken, "primaer", "print")
        aus = hk.druckausgaben(a.seite, _ansicht(a))
        ui.label("Druckausgaben dieser Seite").classes("m-opt-abschnitt")
        if aus:
            ui.label("Fertig gestaltete Listen – öffnen sich als Druckansicht.").classes("m-opt-unter")
            with ui.element("div").classes("m-opt-wahl"):
                for t, k in aus:
                    b = ui.element("button").classes("m-opt-chip")
                    with b:
                        ui.icon("description")
                        ui.label(t)
                    b.on("click", lambda k=k: ausgabe(k))
        else:
            ui.label("Für diese Seite gibt es keine eigene Druckausgabe. Listen zum Drucken gibt es unter Anreisen "
                     "(Zuteilen, Abreisen), Zimmer (Übersicht, Defekte Zimmer) und Reinigung.").classes("m-opt-unter")
    dlg.open()


async def _fertig(a, key: str) -> None:
    from . import seite_anreisen, seite_inventar, seite_zimmer, seiten

    if key == "anreise_excel":
        await seite_anreisen._excel(a)
    elif key in ("kachel_excel", "kachel_excel_ohne"):
        await seite_zimmer._auswahl_excel(a, key == "kachel_excel", kachel=True)
    elif key in ("auswahl_excel", "auswahl_excel_ohne"):
        await seite_zimmer._auswahl_excel(a, key == "auswahl_excel")
    elif key == "belegung_excel":
        await seite_zimmer._excel(a)
    elif key == "fm_excel":
        await seite_zimmer._fm(a, "excel")
    elif key == "inventar_excel":
        await seite_inventar._excel(a)
    elif key == "aenderungen_excel":
        from nicegui import run

        from . import aenderungen_kern as ak
        try:
            text, pfad = await run.io_bound(ak.excel_speichern, a.ae_von, a.ae_bis, getattr(a, "ae_art", "alle"))
        except Exception as exc:             # noqa: BLE001
            a.toast(f"Nicht gespeichert: {exc}", fehler=True)
            return
        a.toast(text if seiten._datei_oeffnen(str(pfad)) else f"{text}: {pfad}", rueck=False)


async def exportieren(a) -> None:
    """0.73: Exportieren wie in Office – PDF, Tabellen dieser Ansicht als Excel oder in die Zwischenablage, fertige
    Exporte der Seite. Die Tabellen werden so gelesen, wie sie gerade angezeigt (und gefiltert) sind."""
    import json

    from nicegui import run

    from . import export_kern as ek, seiten

    try:
        roh = await ui.run_javascript(ek.LESEN_JS, timeout=5)
    except Exception:                           # noqa: BLE001 – ohne Tabellen bleiben PDF und fertige Exporte
        roh = []
    tabellen = ek.bereinigen(roh or [])
    titel = getattr(a.titel, "text", "") or "Export"
    dlg, koerper = _rahmen(a, "Exportieren", "Als PDF oder für Excel – so, wie die Ansicht gerade gefiltert ist")

    async def pdf():
        dlg.close()
        a.toast("Im Druckdialog als Ziel „Als PDF speichern“ wählen.", rueck=False)
        ui.run_javascript("setTimeout(() => window.print(), 450)")

    async def excel():
        dlg.close()
        try:
            text, pfad = await run.io_bound(ek.speichern, tabellen, titel, a.heute)
        except PermissionError:
            a.toast("Die Datei ist noch geöffnet – bitte in Excel schließen und erneut versuchen.", fehler=True)
            return
        except Exception as exc:                # noqa: BLE001
            a.toast(f"Nicht gespeichert: {exc}", fehler=True)
            return
        a.toast(text if seiten._datei_oeffnen(str(pfad)) else f"{text} – {pfad}", rueck=False)

    def kopieren():
        dlg.close()
        ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(ek.tsv(tabellen))})")
        a.toast(f"{sum(len(t['zeilen']) for t in tabellen)} Zeilen kopiert – in Excel mit Strg+V einfügen", rueck=False)

    async def fertig(key: str):
        dlg.close()
        await _fertig(a, key)

    with koerper, ui.element("section").classes("m-opt-inhalt"):
        ui.label("PDF").classes("m-opt-abschnitt")
        ui.label("Die aktuelle Ansicht ohne Menüband – im Druckdialog „Als PDF speichern“ wählen.").classes("m-opt-unter")
        with ui.element("div").classes("m-opt-zeile"):
            knopf("Als PDF speichern", pdf, "", "picture_as_pdf")
        ui.label("Tabellen dieser Ansicht").classes("m-opt-abschnitt")
        if tabellen:
            n = sum(len(t["zeilen"]) for t in tabellen)
            ui.label(f"{len(tabellen)} Tabelle{'n' if len(tabellen) != 1 else ''} erkannt, {n} Zeilen – genau wie angezeigt "
                     "und gefiltert. Je Tabelle ein Blatt, mit Filter und fester Kopfzeile.").classes("m-opt-unter")
            with ui.element("div").classes("m-opt-zeile"):
                knopf("Als Excel speichern", excel, "primaer", "table_view")
                knopf("In die Zwischenablage", kopieren, "", "content_copy")
        else:
            ui.label("Auf dieser Ansicht gibt es keine Tabelle (z. B. Kacheln oder Diagramme). Listen haben z. B. "
                     "Anreisen, Zimmer · Liste, Mieter, Termine und Inventar.").classes("m-opt-unter")
        aus = ek.fertige(a.seite, _ansicht(a))
        if aus:
            ui.label("Fertige Exporte dieser Seite").classes("m-opt-abschnitt")
            ui.label("Gestaltete Excel-Listen mit zusätzlichen Spalten (z. B. „frei bis“).").classes("m-opt-unter")
            with ui.element("div").classes("m-opt-wahl"):
                for t, k in aus:
                    b = ui.element("button").classes("m-opt-chip")
                    with b:
                        ui.icon("description")
                        ui.label(t)
                    b.on("click", lambda k=k: fertig(k))
    dlg.open()


CSS = r"""
.m-hilfe { height: min(560px, 90vh); }
.m-hilfe-text { font-size: 14px; line-height: 1.5; white-space: normal; }
.m-hilfe-liste { margin: 4px 0 12px 18px; padding: 0; display: flex; flex-direction: column; gap: 6px; font-size: 14px;
  line-height: 1.5; }
.m-hilfe-schritt { padding: 8px 0; border-bottom: 1px solid var(--ob-rand, var(--rand, #ddd)); }
.m-hilfe-st { font-weight: 600; margin-bottom: 2px; }
.m-hilfe-tasten { display: grid; grid-template-columns: max-content 1fr; gap: 8px 16px; align-items: center; font-size: 14px; }
.m-hilfe-tasten kbd { font: 12px/1 var(--ob-schrift, "Segoe UI", sans-serif); padding: 4px 7px; border-radius: 4px;
  border: 1px solid var(--ob-rand, #ccc); background: var(--ob-reiter, #f3f3f3); white-space: nowrap; justify-self: start; }
/* Drucken der aktuellen Ansicht: nur der Arbeitsbereich, ganze Höhe */
@media print {
  .m-ob, .m-nav, .m-tb, .m-topnav, .m-center, .m-schleier, .m-werkzeuge, .m-ob-status, .m-prompt-zeile, .q-notifications,
  .m-kopf .m-knopf, .m-toast { display: none !important; }
  .m-app, .m-haupt { display: block !important; height: auto !important; overflow: visible !important; }
  .m-inhalt { overflow: visible !important; zoom: 1 !important; }
  body { background: #fff !important; }
}
"""
