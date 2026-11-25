"""1.60: FM-Tickets anzeigen – ein Ticket (aus der Suche, aus „Defekte Zimmer“) und die Liste aller Tickets."""

from __future__ import annotations

from datetime import datetime

from nicegui import run, ui

from . import fm_ticket_kern as tk
from .ui_bausteine import knopf


def _offene() -> set[tuple[str, str]]:
    from belegung import maengel as mg

    return {(m.zimmer, m.art) for m in mg.offen()}


def _wann(iso: str) -> str:
    try:
        return f"{datetime.fromisoformat(iso):%d.%m.%Y %H:%M}"
    except ValueError:
        return iso


async def ticket_panel(a, nr: str) -> None:
    alle = await run.io_bound(tk.laden)
    t = next((x for x in alle if x.nr == nr), None)
    if t is None:
        a.toast(f"Ticket {nr} nicht gefunden.", fehler=True)
        return
    offene = await run.io_bound(_offene)
    from belegung import maengel as mg

    def bauen():
        ist_offen = tk.offen(t, offene)
        with ui.element("div").classes("m-paktionen").style("align-items:center"):
            ui.label("offen" if ist_offen else "erledigt").classes("m-pille " + ("warn" if ist_offen else "ok"))
            ui.label(f"gesendet {_wann(t.zeit)}" + (f" von {t.wer}" if t.wer else "") + (f" · an {t.an}" if t.an else "")
                     ).classes("m-zweite")
        ui.label(t.betreff).classes("m-name").style("white-space:normal")
        ui.label("Mängel").classes("m-abschnitt")
        for i, (zid, art) in enumerate(t.maengel):
            kurz = t.zimmer[i] if i < len(t.zimmer) and len(t.zimmer) == len(t.maengel) else zid.removeprefix("GS-")
            with ui.element("div").classes("m-paktionen").style("align-items:center"):
                ui.icon("check_circle" if (zid, art) not in offene else "build").style(
                    "color:" + ("var(--gruen)" if (zid, art) not in offene else "var(--orange)"))
                ui.label(f"Zimmer {kurz} – {mg.NAMEN.get(art, art)}").classes("m-ptext")
                ui.label("behoben" if (zid, art) not in offene else "offen").classes("m-zweite")

                async def karte(zid=zid):
                    from .seite_zimmer import karte_oeffnen

                    await karte_oeffnen(a, zid)
                knopf("", karte, "leise", "open_in_new", "Zimmerkarte öffnen")
        if t.erledigt_von_hand:
            ui.label(f"Von Hand als erledigt markiert am {_wann(t.erledigt_von_hand)}.").classes("m-zweite")
        with ui.element("div").classes("m-paktionen"):
            if ist_offen:
                async def erinnern():
                    from .seite_heute import fm_mail

                    text = (f"Hallo,\n\nzu unserem Auftrag {t.nr} vom {_wann(t.zeit)[:10]} ist noch nicht alles erledigt:\n\n"
                            + "\n".join(f"- Zimmer {t.zimmer[i] if i < len(t.zimmer) else z} – {mg.NAMEN.get(ar, ar)}"
                                        for i, (z, ar) in enumerate(t.maengel) if (z, ar) in offene)
                            + "\n\nBitte um kurze Rückmeldung, bis wann es erledigt wird.\n\nVielen Dank!\n")
                    fm_mail(a, vorlage=(f"[{t.nr}] Erinnerung: {t.betreff.split('] ', 1)[-1]}", text))
                knopf("Erinnerung an FM", erinnern, "primaer", "mail", "Nachfassen – mit derselben Ticketnummer")

                async def erledigt():
                    await run.io_bound(tk.erledigen, t.nr, True)
                    a.toast(f"{t.nr} als erledigt markiert", rueck=False)
                    await ticket_panel(a, t.nr)
                knopf("Als erledigt markieren", erledigt, "leise", "check")
            elif t.erledigt_von_hand:
                async def wieder():
                    await run.io_bound(tk.erledigen, t.nr, False)
                    await ticket_panel(a, t.nr)
                knopf("Wieder öffnen", wieder, "leise", "undo")
            knopf("Alle Tickets", lambda: liste_panel(a), "leise", "list")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel(f"FM-Ticket {t.nr}", bauen)


async def liste_panel(a, nur_offen: bool = True) -> None:
    alle = sorted(await run.io_bound(tk.laden), key=lambda t: t.zeit, reverse=True)
    offene = await run.io_bound(_offene)
    zustand = {"offen": nur_offen, "suche": ""}

    def bauen():
        with ui.element("div").classes("m-paktionen").style("align-items:center;flex-wrap:wrap"):
            suche = ui.input(placeholder="Suchen: FM-42, Zimmer 2-108, Heizung …").props("dense outlined clearable").classes(
                "m-feld").style("min-width:260px")
            sw = ui.switch("nur offene", value=nur_offen).props("dense")
        box = ui.element("div").classes("m-vp-liste")

        def zeichnen():
            q = (zustand["suche"] or "").lower().strip()
            treffer = tk.finden(q, alle) if tk.suchbegriff(q) else [
                t for t in alle if not q or q in (t.betreff + " " + " ".join(t.zimmer) + " " + t.an).lower()]
            if zustand["offen"]:
                treffer = [t for t in treffer if tk.offen(t, offene)]
            box.clear()
            with box:
                ui.label(f"{len(treffer)} von {len(alle)} Tickets").classes("m-zweite")
                for t in treffer[:300]:
                    z = ui.element("div").classes("m-vp-zeile m-klick")
                    with z:
                        ui.label(t.nr).classes("m-mono m-name")
                        with ui.element("div"):
                            ui.label(t.betreff.split("] ", 1)[-1]).classes("m-name").style("white-space:normal")
                            ui.label(f"{_wann(t.zeit)} · {'offen' if tk.offen(t, offene) else 'erledigt'}"
                                     + (f" · {t.wer}" if t.wer else "")).classes("m-zweite")
                    z.on("click", lambda t=t: ticket_panel(a, t.nr))

        def neu(k, v):
            zustand[k] = v
            zeichnen()
        suche.on_value_change(lambda e: neu("suche", e.value or ""))
        sw.on_value_change(lambda e: neu("offen", bool(e.value)))
        zeichnen()
        knopf("Schließen", a.panel_zu, "leise")

    a.panel("FM-Tickets", bauen, breit=True)
