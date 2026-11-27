"""1.74: Panel „Checkliste“ je Mietvertrag – abhaken, was zum Einzug/Auszug erledigt ist; eigene Punkte."""

from __future__ import annotations

from datetime import datetime

from nicegui import run, ui

from . import mieter_checkliste as mc
from .ui_bausteine import knopf


async def panel(a, mv) -> None:
    from . import kuendigung_kern as kk

    gekuendigt = mv.nr in (await run.io_bound(kk.laden))
    ps = await run.io_bound(mc.punkte, mv, a.heute, None, gekuendigt)

    def bauen():
        fertig = sum(p.erledigt for p in ps)
        ui.label(f"Mietvertrag {mv.nr} · {mv.name} · {fertig} von {len(ps)} erledigt").classes("m-ptext")
        for abschnitt in ("Einzug", "Auszug", "Eigene"):
            teil = [p for p in ps if p.abschnitt == abschnitt]
            if not teil:
                continue
            ui.label({"Eigene": "Eigene Punkte"}.get(abschnitt, abschnitt)).classes("m-ktitel")
            for p in teil:
                with ui.element("div").classes("m-mzeile").style("grid-template-columns:minmax(0,1fr) auto;gap:8px"):
                    with ui.element("div").style("min-width:0"):
                        cb = ui.checkbox(p.text, value=p.erledigt).props("dense color=primary")
                        cb.on_value_change(lambda e, p=p: haken(p, e.value))
                        if p.erledigt:
                            am = datetime.fromisoformat(p.am)
                            ui.label(f"am {am:%d.%m.%Y %H:%M}" + (f" · {p.wer}" if p.wer else "")).classes(
                                "m-zweite").style("margin-left:30px")
                    if p.eigen:
                        knopf("", lambda p=p: weg(p), "leise", "delete", "Eigenen Punkt entfernen")
                    else:
                        ui.label("")
        with ui.element("div").classes("m-zeile-flex").style("gap:8px;margin-top:10px;align-items:center"):
            neu = ui.input("Eigener Punkt", placeholder="z. B. Kopie Ausweis").classes("m-feld").props(
                "dense outlined dark").style("flex:1")
            knopf("Hinzufügen", lambda: hinzu(neu.value), "", "add")

    async def haken(p, an: bool):
        if await a.aendern_leicht(mc.setzen, mv.nr, p.id, an):
            await panel(a, mv)

    async def weg(p):
        if await a.aendern_leicht(mc.eigenen_entfernen, mv.nr, p.id):
            await panel(a, mv)

    async def hinzu(text: str):
        if await a.aendern_leicht(mc.eigener_punkt, mv.nr, text or ""):
            await panel(a, mv)

    a.panel(f"Checkliste MV {mv.nr}", bauen, breit=True)
