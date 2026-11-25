"""1.67: Panel „Gleiche Person?“ – Gebäudeplan-Eintrag (RIOS) und Anreise nebeneinander, Ja/Nein je Fall.

Erreichbar über die Cockpit-Karte, Anreisen → Abgleich → „Gleiche Person?“ und den Hinweis beim Zuteilen."""

from __future__ import annotations

from nicegui import run, ui

from . import gleiche_person as gp
from .ui_bausteine import knopf, leer


def _kurz(zid: str) -> str:
    from .kern import kurz

    return kurz(zid) if zid else ""


def _seite(titel: str, name: str, zeilen: list[str]) -> None:
    with ui.element("div").classes("m-gp-seite").style(
            "display:flex;flex-direction:column;gap:1px;border-left:3px solid var(--akzent);padding-left:10px"):
        ui.label(titel).classes("m-zweite")
        ui.label(name).classes("m-name")
        for z in zeilen:
            if z:
                ui.label(z).classes("m-zweite")


async def panel(a, nur_person: str = "") -> None:
    if a.stand is None:
        a.toast("Erst Daten laden.", fehler=True)
        return
    vs = await run.io_bound(gp.vorschlaege, a.stand, a.heute)
    if nur_person:
        vs = [v for v in vs if v.person == nur_person] or vs
    daten = await run.io_bound(gp.laden)

    def bauen():
        ui.label("Der Gebäudeplan aus RIOS hat keine Teilnehmernummer. Heißt eine Person dort etwas anders oder ist das "
                 "Zimmer länger gebucht (z. B. EMR ab Vortag), erkennt das Programm sie nicht sicher – sie stünde sonst "
                 "doppelt im Plan und fehlte bei den Abreisen. Bitte je Fall bestätigen. Die Entscheidung bleibt auch "
                 "nach dem nächsten Einlesen des Gebäudeplans.").classes("m-ptext")
        if not vs:
            leer("Keine offenen Fälle – alle Personen im Gebäudeplan sind zugeordnet.")
        for v in vs:
            with ui.element("div").classes("m-gp").style(
                    "display:flex;flex-direction:column;gap:10px;padding:12px 0;border-bottom:1px solid var(--rand)"):
                _seite("Gebäudeplan (RIOS)", v.gp_name,
                       [f"Zimmer {_kurz(v.zimmer)} · {v.gp_von:%d.%m.} – {v.gp_bis:%d.%m.%Y}", v.gp_massnahme])
                _seite("Anreiseliste", v.name,
                       [f"Anreise {v.von:%d.%m.} · Abreise {v.bis:%d.%m.%Y}", v.massnahme,
                        (f"eigene Planung: {_kurz(v.geplant)}" + (" – entfällt bei „Ja“" if v.geplant != v.zimmer else ""))
                        if v.geplant else "noch kein Zimmer geplant"])
                ui.label(v.grund).classes("m-zweite m-gp-grund")
                with ui.element("div").classes("m-paktionen"):
                    knopf("Ja, dieselbe Person", lambda v=v: entscheiden(gp.verbinden, v), "primaer", "check",
                          f"{v.name} wohnt in {_kurz(v.zimmer)} laut Gebäudeplan – Abreise, Suche und Zimmer passen dann")
                    knopf("Nein, andere Person", lambda v=v: entscheiden(gp.ablehnen, v), "leise", "close",
                          "Wird nicht wieder gefragt")
        if daten["verbunden"]:
            ui.label("Bestätigt").classes("m-ktitel")
            for x in sorted(daten["verbunden"], key=lambda x: x.get("von", ""), reverse=True)[:30]:
                with ui.element("div").classes("m-mzeile").style("grid-template-columns:1fr auto"):
                    ui.label(f"{x.get('name', '')} = {x.get('gp_name', '')} · {_kurz(x.get('zimmer', ''))}").classes(
                        "m-zweite")
                    knopf("", lambda x=x: entscheiden(gp.loesen, x["person"]), "leise", "undo",
                          "Verbindung lösen (falls versehentlich bestätigt)")

    async def entscheiden(fn, arg):
        if await a.aendern(fn, arg):
            await panel(a)

    a.panel("Gleiche Person? – Gebäudeplan ↔ Anreiseliste", bauen, breit=True)
