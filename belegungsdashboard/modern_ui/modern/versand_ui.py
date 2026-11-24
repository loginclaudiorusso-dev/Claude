"""1.59: Versandprotokoll anzeigen – Verwaltung → „Versandprotokoll“: wer wann was an wen verschickt hat."""

from __future__ import annotations

from datetime import datetime

from nicegui import run, ui

from . import versand_protokoll as vp
from .ui_bausteine import knopf


async def panel(a) -> None:
    alle = await run.io_bound(vp.laden)
    zustand = {"suche": "", "art": "", "fehler": False}

    def bauen():
        ui.label("Jede Mail, die INNternat verschickt oder in Outlook vorbereitet hat – Mail an FM, Sammelmail, "
                 "Antworten und Weiterleitungen aus dem Postfach, Mails an Mieter. Für alle PCs des Standorts gleich. "
                 "Wer was im Programm geändert hat, steht im „Änderungsverlauf“.").classes("m-ptext")
        with ui.element("div").classes("m-paktionen").style("align-items:center;flex-wrap:wrap"):
            suche = ui.input(placeholder="Suchen: Empfänger, Betreff, Zimmer …").props("dense outlined clearable").classes(
                "m-feld").style("min-width:260px")
            art = ui.select({"": "alle Arten", **vp.ARTEN}, value="").props("dense outlined options-dense").classes(
                "m-feld").style("width:170px")
            nur = ui.switch("nur Fehler").props("dense")
        liste = ui.element("div").classes("m-vp-liste")

        def zeichnen():
            treffer = vp.filtern(alle, zustand["suche"], zustand["art"], zustand["fehler"])
            liste.clear()
            with liste:
                ui.label(f"{len(treffer)} von {len(alle)} Einträgen").classes("m-zweite")
                if not treffer:
                    ui.label("Noch nichts verschickt – oder kein Treffer für diese Suche.").classes("m-zweite")
                for e in treffer[:300]:
                    with ui.element("div").classes("m-vp-zeile" + ("" if e.ok else " fehler")):
                        try:
                            wann = f"{datetime.fromisoformat(e.zeit):%d.%m.%Y %H:%M}"
                        except ValueError:
                            wann = e.zeit
                        ui.label(wann).classes("m-mono m-zweite")
                        with ui.element("div"):
                            ui.label(f"{e.art_text} · {e.betreff or '(ohne Betreff)'}").classes("m-name")
                            ui.label(f"an {e.an or '–'} · {e.weg}" + (f" · aus {e.von}" if e.von else "")
                                     + (f" · von {e.wer}" if e.wer else "")).classes("m-zweite")
                            if e.text:
                                ui.label(e.text).classes("m-zweite").style("white-space:normal")
                            if not e.ok:
                                ui.label(e.ergebnis).classes("m-zweite m-krit")

        def neu(k, v):
            zustand[k] = v or ("" if k != "fehler" else False)
            zeichnen()
        suche.on_value_change(lambda ev: neu("suche", ev.value))
        art.on_value_change(lambda ev: neu("art", ev.value))
        nur.on_value_change(lambda ev: neu("fehler", ev.value))
        zeichnen()
        with ui.element("div").classes("m-paktionen"):
            knopf("Änderungsverlauf öffnen", lambda: a.oeffnen("zimmer", "aenderungen"), "leise", "history")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel("Versandprotokoll", bauen, breit=True)


CSS = """
.m-vp-liste { display: flex; flex-direction: column; gap: 2px; margin-top: 8px; }
.m-vp-zeile { display: grid; grid-template-columns: 128px minmax(0, 1fr); gap: 10px; padding: 8px 4px;
  border-bottom: 1px solid var(--rand); }
.m-vp-zeile.fehler { background: color-mix(in srgb, var(--rot) 6%, transparent); }
"""
