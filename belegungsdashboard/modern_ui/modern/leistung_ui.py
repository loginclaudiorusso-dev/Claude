"""1.72: Panel „Ladezeiten“ – die langsamsten Schritte auf diesem PC, zum Ansehen und Kopieren."""

from __future__ import annotations

from nicegui import ui

from . import leistung_messung as lm
from .ui_bausteine import knopf, leer


def panel(a) -> None:
    ms = lm.messungen()
    b = lm.bericht(ms)

    def bauen():
        ui.label("Wie lange das Laden auf diesem PC seit dem Start gedauert hat – je Schritt und Seite. Bei langsamen "
                 "Fenstern bitte „Kopieren“ und den Text weitergeben: Er enthält nur Seitennamen und Sekunden, keine "
                 "Namen oder Inhalte.").classes("m-ptext")
        if not ms:
            leer("Noch keine Messungen – einfach ein paar Seiten öffnen.")
            return
        ui.label(f"{len(ms)} Messungen · {b['langsam']} davon langsamer als {lm.LANGSAM:g} s").classes("m-zweite")
        ui.label("Langsamste Schritte").classes("m-ktitel")
        for m in b["langsamste"]:
            with ui.element("div").classes("m-mzeile").style("grid-template-columns:70px 1fr auto"):
                ui.label(f"{m.dauer:.1f} s").classes("m-name").style(
                    f"color:{'#DC2626' if m.dauer >= lm.LANGSAM else 'inherit'}")
                ui.label(f"{m.stufe} · {m.seite}").classes("m-zweite")
                ui.label(m.zeit).classes("m-zweite")
        ui.label("Je Seite (Anzahl · Mittel · Max)").classes("m-ktitel")
        for s, n, mi, mx in b["je_seite"][:15]:
            ui.label(f"{s}: {n} × · {mi:.1f} s · max {mx:.1f} s").classes("m-zweite")

        async def kopieren():
            ui.clipboard.write(lm.text(ms))
            a.toast("Ladezeiten in die Zwischenablage kopiert", rueck=False)
        with ui.element("div").classes("m-paktionen"):
            knopf("Kopieren", kopieren, "primaer", "content_copy")

    a.panel("Ladezeiten", bauen, breit=True)
