"""Netzwerkordner (0.54): Daten aus dem bisherigen Ordner übernehmen – beim ersten Start im neuen Ordner gefragt und
jederzeit unter Einstellungen → Datensicherung erreichbar. Logik in ``netz_kern``."""

from __future__ import annotations

from nicegui import run, ui

from . import netz_kern
from .ui_bausteine import attr, knopf


async def uebernahme_dialog(a, beim_start: bool = False) -> bool:
    """Fenster: bisherigen Ordner angeben → prüfen (was wird kopiert) → übernehmen. True = übernommen."""
    zustand = {"u": None}
    with ui.dialog().props("persistent" if beim_start else "") as dlg, ui.element("div").classes("m-frage m-netz"):
        attr(dlg, role="dialog", aria_label="Daten übernehmen")
        ui.label("Neuer Datenordner – Daten übernehmen?" if beim_start else "Daten aus dem bisherigen Ordner übernehmen"
                 ).classes("m-titel")
        ui.label(f"Datenordner: {netz_kern.basis()}").classes("m-zweite m-netz-pfad")
        ui.label("Hier liegen noch keine Daten. Geben Sie den Ordner an, in dem INNternat bisher lag (dort, wo "
                 "„Start.bat“ liegt). Kopiert werden nur die Daten – Planung, Listen, Gebäudeplan, Vorlagen, Sicherungen, "
                 "alle Standorte. Der bisherige Ordner bleibt unverändert.").classes("m-ptext")
        ein = ui.input("Bisheriger Ordner", placeholder=r"z. B. C:\Belegung oder \\server\freigabe\Belegung"
                       ).props("outlined dense clearable").classes("w-full")
        ui.label("Tipp: im Explorer den Ordner öffnen, oben in die Adresszeile klicken, kopieren und hier einfügen."
                 ).classes("m-zweite")
        ergebnis = ui.element("div").classes("m-netz-erg")
        with ui.element("div").classes("m-netz-knoepfe"):
            knopf("Ohne Daten beginnen" if beim_start else "Abbrechen", lambda: dlg.submit(False))
            pruefen_k = knopf("Prüfen", None, "", "search")
            los = knopf("Übernehmen", None, "primaer", "drive_file_move")
            los.props("disabled")

        async def pruefen() -> None:
            u = await run.io_bound(netz_kern.uebernahme_pruefen, ein.value or "")
            zustand["u"] = u
            ergebnis.clear()
            with ergebnis:
                if u.probleme:
                    for p in u.probleme:
                        ui.label(p).classes("m-warn-text")
                else:
                    ui.label(f"Gefunden: {u.text}").classes("m-ok")
                    for rel in u.dateien[:6]:
                        ui.label(f"• {rel}").classes("m-zweite")
                    if len(u.dateien) > 6:
                        ui.label(f"• … und {len(u.dateien) - 6} weitere").classes("m-zweite")
            if u.ok:
                los.props(remove="disabled")
            else:
                los.props("disabled")

        async def uebernehmen() -> None:
            u = zustand["u"]
            if u is None or not u.ok:
                return
            los.props("disabled")
            try:
                text = await run.io_bound(netz_kern.uebernehmen, u.quelle)
            except (ValueError, OSError) as exc:
                ergebnis.clear()
                with ergebnis:
                    ui.label(f"Nicht übernommen: {exc}").classes("m-warn-text")
                return
            ergebnis.clear()
            with ergebnis:
                ui.label(text).classes("m-ok")
            a.toast(text, rueck=False, dauer=20)
            dlg.submit(True)

        pruefen_k.on("click", pruefen)
        ein.on("keydown.enter", pruefen)
        los.on("click", uebernehmen)
    dlg.open()
    return bool(await dlg)


def neustart_hinweis() -> None:
    with ui.dialog().props("persistent") as dlg, ui.element("div").classes("m-frage"):
        ui.label("Daten übernommen").classes("m-titel")
        ui.label("Bitte INNternat jetzt einmal schließen und über „INNternat starten“ neu öffnen – dann ist alles "
                 "frisch geladen.").classes("m-ptext")
        with ui.element("div").classes("m-netz-knoepfe"):
            knopf("Verstanden", dlg.close, "primaer")
    dlg.open()
