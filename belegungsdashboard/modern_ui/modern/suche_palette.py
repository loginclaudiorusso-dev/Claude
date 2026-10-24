"""Strg+K: Suchen und Springen – Seiten, Personen (Anreiselisten, UWT, Gebäudeplan, Zimmerplan) und Zimmer."""

from __future__ import annotations

from datetime import date

from nicegui import run, ui

from .kern import kurz
from .ui_bausteine import attr


def treffer(text: str, stand, heute: date) -> list[tuple[str, str, str, dict]]:
    """(Titel, Zusatz, Seite, Zustand) – Seiten zuerst, dann Personen/Zimmer aus der Suche des Hauptprogramms."""
    from belegung import suche

    from .register import NAV

    q = text.strip().lower()
    erg = []
    for key, titel, _icon, _g in NAV:
        if q and q in titel.lower():
            erg.append((titel, "Seite", key, {}))
    if stand is not None and len(q) >= 2:
        for t in suche.suchen(text, stand, heute=heute)[:40]:
            zusatz = " · ".join(x for x in (t.zimmer_text, t.massnahme, f"{t.von:%d.%m.%y}–{t.bis:%d.%m.%y}"
                                             if t.bis else f"ab {t.von:%d.%m.%y}", t.status(heute)) if x)
            if t.zimmer_id:
                erg.append((t.name, zusatz, "zimmer", {"karte": t.zimmer_id}))
            else:
                erg.append((t.name, zusatz, "anreisen", {"kennung": t.von.isoformat()}))
    return erg


def oeffnen(a) -> None:
    with ui.dialog().props("position=top") as dlg, ui.element("div").classes("m-palette"):
        eingabe = ui.input(placeholder="Person, Zimmer (z. B. 2-408) oder Seite …").classes("m-palette-ein").props(
            "dense borderless dark autofocus")
        liste = ui.element("div").classes("m-palette-liste")
        auswahl = {"i": 0, "erg": []}

        def zeichnen():
            liste.clear()
            with liste:
                if not auswahl["erg"]:
                    ui.label("Tippen zum Suchen – Enter öffnet, ↑ ↓ wählt, Esc schließt.").classes("m-zweite").style(
                        "padding:10px 12px")
                for i, (titel, zusatz, seite, zustand) in enumerate(auswahl["erg"]):
                    b = ui.element("button").classes("m-palette-z" + (" an" if i == auswahl["i"] else ""))
                    with b:
                        attr(ui.label(titel).classes("m-name"), title=titel)
                        ui.label(zusatz).classes("m-zweite")
                    b.on("click", lambda i=i: los(i))

        async def suchen():
            auswahl["erg"] = await run.io_bound(treffer, eingabe.value or "", a.stand, a.heute)
            auswahl["i"] = 0
            zeichnen()

        async def los(i: int | None = None):
            i = auswahl["i"] if i is None else i
            if 0 <= i < len(auswahl["erg"]):
                _t, _z, seite, zustand = auswahl["erg"][i]
                dlg.close()
                await a.oeffnen(seite, **zustand)

        def taste(e):
            k = e.args.get("key")
            if k == "ArrowDown":
                auswahl["i"] = min(auswahl["i"] + 1, len(auswahl["erg"]) - 1)
                zeichnen()
            elif k == "ArrowUp":
                auswahl["i"] = max(auswahl["i"] - 1, 0)
                zeichnen()
            elif k == "Enter":
                return los()

        eingabe.on("update:model-value", suchen, throttle=0.25, leading_events=False)
        eingabe.on("keydown", taste, args=["key"])
        zeichnen()
    dlg.open()
