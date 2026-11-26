"""1.72: Panel „Mieter-Akte“ – Unterlagen eines Mietvertrags: ansehen, öffnen, ablegen, entfernen."""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

from nicegui import run, ui

from . import mieter_akte as ma
from .ui_bausteine import knopf, leer


def _oeffnen(a, pfad: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(pfad))                # noqa: S606 – eigene Datei bzw. eigener Ordner
        else:
            a.toast(f"Gespeichert unter {pfad}", rueck=False)
    except OSError as exc:
        a.toast(f"Konnte nicht geöffnet werden: {exc}", fehler=True, rueck=False)


async def panel(a, mv) -> None:
    liste = await run.io_bound(ma.dateien, mv.nr)
    ordner = await run.io_bound(ma.ordner, mv.nr)

    def bauen():
        ui.label(f"Mietvertrag {mv.nr} · {mv.name} – alle Unterlagen an einem Ort. Erstellte Verträge und "
                 "Nebenabreden legt das Programm selbst ab; Kündigung, Übergabeprotokoll, Schriftverkehr hier "
                 "hochladen. Bitte nur Mietunterlagen – keine Gesundheitsdaten.").classes("m-ptext")
        up_ordner = Path(tempfile.gettempdir()) / "belegung_uploads" / uuid.uuid4().hex[:8]

        async def hochgeladen(e):
            dateien = e.files if hasattr(e, "files") else [e.file]
            up_ordner.mkdir(parents=True, exist_ok=True)
            ok = 0
            for f in dateien:
                ziel = up_ordner / Path(f.name).name
                await f.save(ziel)
                if await a.aendern(ma.ablegen, mv.nr, mv.nachname, Path(f.name).name, ziel.read_bytes()):
                    ok += 1
            up.reset()
            if ok:
                await panel(a, mv)

        up = ui.upload(multiple=True, auto_upload=True, on_multi_upload=hochgeladen).classes("hidden")
        with ui.element("div").classes("m-paktionen"):
            knopf("Dateien ablegen …", lambda: up.run_method("pickFiles"), "primaer", "upload",
                  f"Eine oder mehrere Dateien in die Akte (bis {ma.MAX_MB} MB je Datei)")
            if ordner is not None:
                knopf("Ordner öffnen", lambda: _oeffnen(a, ordner), "leise", "folder_open", str(ordner))
        if not liste:
            leer("Noch keine Unterlagen in der Akte.")
        for d in liste:
            with ui.element("div").classes("m-mzeile").style("grid-template-columns:minmax(0,1fr) auto auto;gap:8px"):
                with ui.element("div").style("min-width:0"):
                    ui.label(d.name).classes("m-name").style("white-space:normal;word-break:break-word")
                    ui.label(f"{d.geaendert:%d.%m.%Y %H:%M} · {d.groesse_text}").classes("m-zweite")
                knopf("", lambda d=d: _oeffnen(a, d.pfad), "leise", "open_in_new", "Öffnen")

                async def weg(d=d):
                    if await a.aendern(ma.entfernen, mv.nr, d.name):
                        await panel(a, mv)
                knopf("", weg, "leise", "delete", "In den Papierkorb der Akte (nicht endgültig gelöscht)")

    a.panel(f"Mieter-Akte MV {mv.nr}", bauen, breit=True)
