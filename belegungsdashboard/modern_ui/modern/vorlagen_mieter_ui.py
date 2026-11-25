"""1.68: Panel „Vorlagen für Mietverträge“ – was da ist, was fehlt, wohin es gehört; Hochladen und Muster anlegen."""

from __future__ import annotations

import uuid
from pathlib import Path

from nicegui import run, ui

from . import vorlagen_mieter as vm
from .ui_bausteine import knopf

ENDUNG = {".vorlage": ".vorlage,.txt", ".pdf": ".pdf", ".jpg": ".jpg,.jpeg"}


def hinweis(a, im_formular: bool = False) -> None:
    """Gelber Hinweis, solange der Vertragstext fehlt bzw. noch das Muster ist (Mieter-Seite und „Neuer Mieter“)."""
    try:
        fehlt, muster = vm.vertrag_fehlt(), vm.ist_muster()
    except Exception:                              # noqa: BLE001 – nur ein Hinweis
        return
    if not fehlt and not muster:
        return
    text = ("Der Vertragstext ist noch nicht eingerichtet – ohne ihn kann kein Mietvertrag erstellt werden."
            if fehlt else "Verträge nutzen noch den MUSTER-Text – bitte durch den eigenen Vertragstext ersetzen.")
    with ui.element("div").classes("m-mzeile").style(
            "grid-template-columns:1fr auto;border-left:4px solid var(--warn, #F59E0B);padding:8px 10px;"
            "background:color-mix(in srgb, #F59E0B 10%, transparent);border-radius:var(--r)"):
        ui.label(text).classes("m-ptext")
        knopf("Vorlagen einrichten", lambda: panel(a), "primaer" if fehlt else "leise", "upload")


def _hochladen(a, datei: str, nachher):
    ordner = Path(__import__("tempfile").gettempdir()) / "belegung_uploads" / uuid.uuid4().hex[:8]

    async def fertig(e):
        f = e.file if hasattr(e, "file") else e.files[0]
        ordner.mkdir(parents=True, exist_ok=True)
        ziel = ordner / Path(f.name).name
        await f.save(ziel)
        up.reset()
        if await a.aendern(vm.einrichten, datei, ziel.read_bytes()):
            await nachher()

    endung = next((v for k, v in ENDUNG.items() if datei.endswith(k)), "*")
    up = ui.upload(auto_upload=True, on_upload=fertig).props(f'accept="{endung}"').classes("hidden")
    return up


async def panel(a) -> None:
    st = await run.io_bound(vm.status)
    ziel = await run.io_bound(vm.zielordner)
    muster = await run.io_bound(vm.ist_muster)

    def bauen():
        ui.label("Für einen Mietvertrag braucht das Programm den Vertragstext (Mietvertrag.vorlage). Die Vordrucke "
                 "(Wohnungsgeberbestätigung, SEPA, Mietschuldenfreiheit) und das Logo hängt es an, wenn sie da sind. "
                 "Die Vorlagen liegen im gemeinsamen Datenordner – sie bleiben bei Updates erhalten und gelten für alle "
                 "Standorte.").classes("m-ptext")
        ui.label(f"Ordner: {ziel}").classes("m-zweite m-mono").style(
            "white-space:normal;word-break:break-all;overflow:visible;text-overflow:clip;max-height:none;height:auto")
        for s in st:
            up = _hochladen(a, s.datei, lambda: panel(a))
            with ui.element("div").classes("m-mzeile").style(
                    "grid-template-columns:22px minmax(0,1fr) auto;align-items:center;gap:8px"):
                ui.label("✓" if s.da else ("!" if s.pflicht else "–")).style(
                    f"font-weight:700;color:{'#16A34A' if s.da else ('#DC2626' if s.pflicht else 'var(--text2, #64748B)')}")
                with ui.element("div").style("min-width:0"):
                    ui.label(s.titel).classes("m-name")
                    ui.label(s.datei).classes("m-zweite m-mono").style("white-space:normal;word-break:break-all;overflow:visible;text-overflow:clip;max-height:none;height:auto")
                    ui.label(("vorhanden" if s.da else ("fehlt – Pflicht" if s.pflicht else "fehlt"))
                             + (" · MUSTER" if s.pflicht and s.da and muster else "") + f" · {s.text}").classes(
                        "m-zweite").style("white-space:normal")
                knopf("Ersetzen" if s.da else "Hochladen", lambda up=up: up.run_method("pickFiles"),
                      "leise" if s.da else ("primaer" if s.pflicht else ""), "upload",
                      f"{s.datei} auswählen – eine vorhandene Datei bleibt als Kopie erhalten")
        if any(s.pflicht and not s.da for s in st):
            ui.label("Noch kein Vertragstext zur Hand? Das Muster enthält alle Platzhalter und einen neutralen "
                     "Rahmen; danach die Datei im Editor öffnen und den eigenen, geprüften Wortlaut eintragen "
                     "(Zeilen mit „MUSTER“ ersetzen).").classes("m-ptext")

            async def muster_():
                if await a.aendern(vm.muster_anlegen):
                    await panel(a)
            knopf("Muster-Vertragstext anlegen", muster_, "", "description")

    a.panel("Vorlagen für Mietverträge", bauen, breit=True)
