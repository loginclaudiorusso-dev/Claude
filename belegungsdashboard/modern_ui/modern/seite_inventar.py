"""Seite „Inventar“: Gegenstände (Bestand, verteilt, im Lager) und ihre Verteilung auf die Zimmer – hinzufügen,
entfernen, Ausstattung kopieren, Inventarliste drucken. Daten: ``belegung.inventar``."""

from __future__ import annotations

from nicegui import run, ui

from belegung import inventar as iv
from belegung import zimmerplan as zp

from . import seiten
from .kern import _schritt
from .ui_bausteine import attr, knopf, leer, segmente

ANSICHTEN = {"gegenstaende": "Gegenstände", "zimmer": "Zimmer"}


def daten(a) -> None:
    inv = iv.laden()
    zimmer = [z for z in a.stand.zimmer if z.aktiv]
    a.daten = {"inv": inv, "zimmer": zimmer}


def _aendern(titel: str, aktion) -> str:
    def los():
        inv = iv.laden()
        erg = aktion(inv)
        iv.speichern(inv)
        return erg
    _schritt(titel, los, [iv.DATEI])
    return titel


def gegenstand_speichern(gid: str | None, name: str, kategorie: str, bestand: int | None, notiz: str) -> str:
    def aktion(inv):
        g = inv.gegenstand(gid) if gid else None
        neu = iv.Gegenstand(name, kategorie, bestand, notiz, g.id) if g else iv.Gegenstand(name, kategorie, bestand, notiz)
        inv.gegenstand_speichern(neu)
    return _aendern(f"„{name.strip()}“ gespeichert", aktion)


def gegenstand_loeschen(gid: str) -> str:
    return _aendern("Gegenstand gelöscht", lambda inv: inv.gegenstand_loeschen(gid))


def verteilen(gid: str, zimmer: list[tuple[str, int]], anzahl: int, je_bett: bool) -> str:
    if not zimmer:
        raise ValueError("Bitte Zimmer wählen.")
    _aendern("Verteilt", lambda inv: inv.hinzufuegen(zimmer, gid, anzahl, je_bett))
    return f"In {len(zimmer)} Zimmer verteilt"


def wegnehmen(gid: str, zids: list[str]) -> str:
    _aendern("Entfernt", lambda inv: inv.entfernen(zids, gid))
    return f"Aus {len(zids)} Zimmern entfernt"


def setzen(zid: str, gid: str, anzahl: int) -> str:
    _aendern("Anzahl geändert", lambda inv: inv.setzen(zid, gid, anzahl))
    return "Gespeichert"


def kopieren(von: str, nach: list[str]) -> str:
    _aendern("Ausstattung kopiert", lambda inv: inv.kopieren(von, nach))
    return f"Ausstattung von {von.removeprefix('GS-')} in {len(nach)} Zimmer übernommen"


def zeichnen(a) -> None:
    ansicht = a.ansicht_von("inventar", "gegenstaende")
    inv: iv.Inventar = a.daten["inv"]
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("inventar", ansicht=v))
        knopf("Neuer Gegenstand", lambda: _gegenstand_panel(a, None), "primaer", "add")
        knopf("Inventarliste drucken", lambda: seiten.html_drucken(a, iv.druck_html(inv, a.daten["zimmer"]), "Inventarliste"),
              "", "print")
    if ansicht == "gegenstaende":
        _gegenstaende(a, inv)
    else:
        _zimmer(a, inv)


def _gegenstaende(a, inv: iv.Inventar) -> None:
    sp = "minmax(180px, 1.4fr) 130px 90px 90px 90px minmax(140px, 1fr) 90px"
    with a.inhalt:
        if not inv.gegenstaende:
            leer("Noch keine Gegenstände – „Neuer Gegenstand“ legt einen an.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("Gegenstand", "Kategorie", "Bestand", "Verteilt", "Im Lager", "Notiz", ""):
                ui.label(t)
        for g in inv.gegenstaende:
            frei = inv.frei(g.id)
            with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                n = ui.label(g.name).classes("m-name m-link")
                n.on("click", lambda g=g: _gegenstand_panel(a, g))
                ui.label(g.kategorie).classes("m-zweite")
                ui.label("–" if g.bestand is None else str(g.bestand)).classes("m-mono")
                ui.label(str(inv.verteilt(g.id))).classes("m-mono")
                ui.label("–" if frei is None else str(frei)).classes("m-mono" + (" m-krit" if frei is not None and frei < 0 else ""))
                attr(ui.label(g.notiz).classes("m-zweite"), title=g.notiz)
                knopf("Verteilen", lambda g=g: _verteilen_panel(a, g), "leise", "call_split")


def _zimmer(a, inv: iv.Inventar) -> None:
    sp = "90px minmax(120px, .8fr) minmax(240px, 2fr) 90px"
    with a.inhalt:
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("Zimmer", "Lage", "Ausstattung", ""):
                ui.label(t)
        for z in sorted(a.daten["zimmer"], key=lambda z: (zp._haus_sort(z.haus), zp._etage_sort(z.etage), z.nummer)):
            text = inv.kurztext(z.id)
            with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                ui.label(z.kurz).classes("m-name")
                ui.label(zp.flur_text(z)).classes("m-zweite")
                attr(ui.label(text or "–").classes("m-zweite"), title=text)
                knopf("Ändern", lambda z=z: _zimmer_panel(a, z), "leise", "edit")


def _gegenstand_panel(a, g) -> None:
    def bauen():
        name = ui.input("Name", value=g.name if g else "").classes("m-feld").props("dense outlined dark")
        kat = ui.select(iv.KATEGORIEN, value=g.kategorie if g else "Sonstiges", label="Kategorie").classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        bestand = ui.number("Bestand insgesamt (leer = nicht gezählt)", value=g.bestand if g else None, min=0, step=1,
                            format="%d").classes("m-feld").props("dense outlined dark")
        notiz = ui.input("Notiz", value=g.notiz if g else "").classes("m-feld").props("dense outlined dark")

        async def speichern():
            b = None if bestand.value in (None, "") else int(bestand.value)
            if await a.aendern(gegenstand_speichern, g.id if g else None, name.value or "", kat.value, b, notiz.value or ""):
                a.panel_zu()

        async def loeschen():
            if await a.aendern(gegenstand_loeschen, g.id):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            if g:
                knopf("Löschen", loeschen, "leise", "delete")
            knopf("Abbrechen", a.panel_zu, "leise")
        if g:
            wo = a.daten["inv"].wo(g.id)
            ui.label(f"In {len(wo)} Zimmern").classes("m-ktitel")
            ui.label(", ".join(f"{zid.removeprefix('GS-')} ({n})" for zid, n in wo[:60]) or "–").classes("m-zweite").style(
                "white-space:normal")

    a.panel(g.name if g else "Neuer Gegenstand", bauen)


def _verteilen_panel(a, g) -> None:
    zimmer = {z.id: z for z in a.daten["zimmer"]}

    def bauen():
        ui.label(f"„{g.name}“ in Zimmer verteilen oder herausnehmen. Mehrere Zimmer wählen oder ein ganzes Haus.").classes("m-ptext")
        haus = ui.select({"": "–", **{h: f"ganzes Haus {h}" for h in sorted({z.haus for z in zimmer.values()}, key=zp._haus_sort)}},
                         value="", label="Haus (optional)").classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        wahl = ui.select({zid: z.kurz for zid, z in sorted(zimmer.items(), key=lambda x: (zp._haus_sort(x[1].haus), x[1].nummer))},
                         multiple=True, label="Zimmer", with_input=True).classes("m-feld").props(
            'dense outlined dark options-dense use-chips popup-content-class="m-popup"')
        haus.on_value_change(lambda e: setattr(wahl, "value", [zid for zid, z in zimmer.items() if z.haus == e.value]) if e.value else None)
        anzahl = ui.number("Anzahl je Zimmer", value=1, min=1, step=1, format="%d").classes("m-feld").props("dense outlined dark")
        je_bett = ui.switch("je Bett (Doppelzimmer doppelt)").props("dense color=indigo-4")

        async def rein():
            if await a.aendern(verteilen, g.id, [(zid, zimmer[zid].betten) for zid in (wahl.value or [])],
                               int(anzahl.value or 1), bool(je_bett.value)):
                a.panel_zu()

        async def raus():
            if await a.aendern(wegnehmen, g.id, list(wahl.value or [])):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Hinzufügen", rein, "primaer", "add")
            knopf("Aus diesen Zimmern entfernen", raus, "leise", "remove")

    a.panel(f"Verteilen · {g.name}", bauen)


def _zimmer_panel(a, z) -> None:
    inv: iv.Inventar = a.daten["inv"]

    def bauen():
        felder = {}
        for g in inv.gegenstaende:
            with ui.element("div").classes("m-einst"):
                ui.label(g.name).classes("m-ptext")
                felder[g.id] = ui.number(value=inv.anzahl(z.id, g.id), min=0, step=1, format="%d").classes("m-feld klein").props(
                    "dense outlined dark")

        async def speichern():
            for gid, f in felder.items():
                if int(f.value or 0) != inv.anzahl(z.id, gid):
                    await a.aendern(setzen, z.id, gid, int(f.value or 0))
            a.panel_zu()

        ui.label("Ausstattung kopieren in …").classes("m-ktitel")
        ziel = ui.select({x.id: x.kurz for x in a.daten["zimmer"] if x.id != z.id}, multiple=True, with_input=True,
                         label="andere Zimmer").classes("m-feld").props(
            'dense outlined dark options-dense use-chips popup-content-class="m-popup"')

        async def kop():
            if ziel.value and await a.aendern(kopieren, z.id, list(ziel.value)):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            knopf("Kopieren", kop, "", "content_copy")

    a.panel(f"Ausstattung · {z.kurz}", bauen)
