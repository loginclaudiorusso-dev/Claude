"""1.75: Planung → „Gruppe blockieren“ – Kontingente anlegen, ansehen, Zimmer freigeben, auflösen (Panel)."""

from __future__ import annotations

from datetime import date, timedelta

from nicegui import run, ui

from . import kontingent_kern as kk
from .ui_bausteine import knopf, leer

POPUP = 'dense outlined dark options-dense popup-content-class="m-popup"'


def _kurz(a) -> dict:
    return {z.id: z.kurz for z in a.stand.zimmer} if a.stand else {}


async def panel(a) -> None:
    alle = await run.io_bound(kk.laden)
    kurz = _kurz(a)

    def bauen():
        ui.label("Zimmer für eine Gruppe reservieren, auch wenn die Namen noch nicht feststehen. Die Betten zählen "
                 "überall als belegt und werden nicht anderweitig vorgeschlagen. Stehen später Namen im Zimmer "
                 "(Gebäudeplan oder Zuteilung), gibt das Kontingent diese Betten von selbst frei.").classes("m-ptext")
        knopf("Neues Kontingent …", lambda: formular(a), "primaer", "add")
        aktuell = [k for k in alle if k.bis >= a.heute - timedelta(days=7)]
        if not aktuell:
            leer("Keine Zimmer blockiert.")
        for k in aktuell:
            with ui.element("section").classes("m-block").style("margin-top:10px"):
                with ui.element("div").classes("m-paktionen").style("align-items:center"):
                    ui.label(k.titel).classes("m-name")
                    ui.label(f"{k.von:%d.%m.} – {k.bis:%d.%m.%Y} · {len(k.zimmer)} Zimmer"
                             + (" · läuft" if k.von <= a.heute <= k.bis else "")).classes("m-zweite")
                with ui.element("div").classes("m-fx-pillen"):
                    for zid in k.zimmer:
                        b = ui.element("button").classes("m-fx-pille")
                        with b:
                            ui.label(kurz.get(zid, zid) + "  ✕")
                        b.props(f'title="{kurz.get(zid, zid)} aus dem Kontingent freigeben – dann kann es zugeteilt '
                                'werden"')

                        async def frei(k=k, zid=zid):
                            if await a.aendern(kk.zimmer_freigeben, k.id, zid):
                                await panel(a)
                        b.on("click", frei)
                if k.notiz:
                    ui.label(k.notiz).classes("m-zweite")
                if k.wer or k.angelegt:
                    ui.label("angelegt " + " · ".join(t for t in (k.angelegt.replace("T", " "), k.wer) if t)).classes(
                        "m-zweite")

                async def weg(k=k):
                    if await a.aendern(kk.aufloesen, k.id):
                        await panel(a)
                with ui.element("div").classes("m-paktionen"):
                    knopf("Ändern …", lambda k=k: formular(a, k), "", "edit")
                    knopf("Auflösen", weg, "leise", "delete", "Kontingent löschen – alle Zimmer wieder frei")
        knopf("Schließen", a.panel_zu, "leise")

    a.panel("Gruppe blockieren (Kontingent)", bauen)


def formular(a, k: kk.Kontingent | None = None) -> None:
    zimmer = [z for z in (a.stand.zimmer if a.stand else []) if getattr(z, "aktiv", True)]
    optionen = {z.id: f"{z.kurz} · {z.betten} Bett{'en' if z.betten != 1 else ''}" for z in zimmer}
    haeuser = sorted({z.haus for z in zimmer})

    def bauen():
        titel = ui.input("Bezeichnung (z. B. „Kurs Elektro März“)", value=k.titel if k else "").classes(
            "m-feld w-full").props("dense outlined dark")
        with ui.element("div").classes("m-zweispaltig"):
            von = ui.input("von", value=(k.von if k else a.heute).isoformat()).classes("m-feld").props(
                "dense outlined dark type=date")
            bis = ui.input("bis (letzte Nacht)", value=(k.bis if k else a.heute + timedelta(days=27)).isoformat()) \
                .classes("m-feld").props("dense outlined dark type=date")
        auswahl = ui.select(optionen, value=list(k.zimmer) if k else [], multiple=True, with_input=True,
                            label="Zimmer").classes("m-feld w-full").props(POPUP + " use-chips")
        ui.label("Freie Zimmer automatisch wählen").classes("m-abschnitt")
        with ui.element("div").classes("m-paktionen").style("align-items:center"):
            haus = ui.select({"": "alle Häuser"} | {h: f"Haus {h}" for h in haeuser}, value="", label="Haus") \
                .classes("m-feld").props(POPUP)
            anzahl = ui.number("Anzahl Zimmer", value=6, min=1, max=200, step=1, format="%d").classes("m-feld klein") \
                .props("dense outlined dark")

            def automatisch():
                try:
                    v, b = date.fromisoformat(von.value), date.fromisoformat(bis.value)
                except (TypeError, ValueError):
                    a.toast("Bitte zuerst den Zeitraum wählen.", fehler=True, rueck=False)
                    return
                kandidaten = [z for z in zimmer if not haus.value or z.haus == haus.value]
                frei = kk.frei_im_zeitraum(a.stand.lage, v, b, kandidaten)
                schon = set(auswahl.value or [])
                neu = [z.id for z in frei if z.id not in schon][:int(anzahl.value or 0)]
                auswahl.set_value(sorted(schon | set(neu)))
                a.toast(f"{len(neu)} freie Zimmer ausgewählt" + ("" if len(neu) >= int(anzahl.value or 0)
                                                                  else " – mehr sind im Zeitraum nicht ganz frei"),
                        rueck=False)
            knopf("Auswählen", automatisch, "", "auto_awesome", "Ganz freie Zimmer im Zeitraum zur Auswahl hinzufügen")
        notiz = ui.input("Notiz (optional)", value=k.notiz if k else "").classes("m-feld w-full").props(
            "dense outlined dark")

        async def speichern():
            try:
                v, b = date.fromisoformat(von.value), date.fromisoformat(bis.value)
            except (TypeError, ValueError):
                a.toast("Bitte beide Daten wählen.", fehler=True, rueck=False)
                return
            args = (titel.value or "", v, b, list(auswahl.value or []), notiz.value or "")
            ok = await (a.aendern(kk.bearbeiten, k.id, *args) if k else a.aendern(kk.anlegen, *args))
            if ok:
                await panel(a)

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern" if k else "Blockieren", speichern, "primaer", "lock")
            knopf("Zurück", lambda: panel(a), "leise")

    a.panel("Kontingent ändern" if k else "Neues Kontingent", bauen)
