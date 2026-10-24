"""Seite „Anreisen“ – Zusätze zum Zuteilen (das baut ``oberflaeche``): Ansichten Abreisen und Firmenprogramm,
Menü „Mehr“ (Drucken, Person hinzufügen, Planung zurücknehmen, Optimieren, UWT) und die Personenangaben im Panel."""

from __future__ import annotations

import json
from datetime import date

from nicegui import run, ui

from . import anreisen_kern as ank
from . import seiten
from .ui_bausteine import attr, knopf, leer, segmente

ANSICHTEN = {"zuteilen": "Zuteilen", "abreisen": "Abreisen", "eintragen": "Firmenprogramm"}


def daten(a) -> None:
    """Daten der Ansichten Abreisen/Firmenprogramm (Zuteilen lädt ``oberflaeche`` selbst)."""
    ansicht = a.ansicht_von("anreisen", "zuteilen")
    if ansicht == "abreisen":
        von, bis = ank.zeitraum(a.ab_zeitraum, a.heute)
        a.daten = {"zeilen": ank.abreisen(a.stand, von, bis), "von": von, "bis": bis}
    elif ansicht == "eintragen":
        a.daten = {"zeilen": ank.eintragen_liste(a.stand, a.heute, a.ein_tage)}


def werkzeuge(a) -> None:
    ansicht = a.ansicht_von("anreisen", "zuteilen")
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("anreisen", ansicht=v))


def mehr_menue(a) -> None:
    """„Mehr“ im Kopf der Ansicht Zuteilen – seltene Aktionen gebündelt statt vieler Knöpfe."""
    with a.werkzeuge:
        with knopf("Mehr", None, "leise", "more_horiz"):
            with ui.menu().props('dark class="m-menue"'):
                ui.menu_item("Anreiseliste drucken", lambda: _drucken(a, "anreise"))
                ui.menu_item("Schlüsselliste drucken", lambda: _drucken(a, "schluessel"))
                ui.menu_item("Zimmerschilder drucken", lambda: _drucken(a, "schilder"))
                ui.separator()
                ui.menu_item("Person hinzufügen …", lambda: person_neu_panel(a))
                ui.menu_item("Planung dieser Anreise zurücknehmen", lambda: a.aendern(ank.anreise_zuruecknehmen, a.kennung))
                ui.separator()
                ui.menu_item("Belegung optimieren …", lambda: optimieren_panel(a))
                ui.menu_item("Kommende UWT automatisch zuteilen", lambda: a.aendern(ank.uwt_zuteilen, a.heute))
                ui.menu_item("Kommende UWT-Planungen zurücknehmen", lambda: a.aendern(ank.uwt_zuruecknehmen, a.heute))


async def _drucken(a, art: str) -> None:
    if not a.kennung:
        return
    titel = next((x.titel for x in a.anreisen if x.kennung == a.kennung), "")
    try:
        text = await run.io_bound(ank.anreise_druck, a.stand, a.kennung, art, titel)
    except ValueError as exc:
        a.toast(str(exc), fehler=True)
        return
    seiten.html_drucken(a, text, f"{art}_{a.kennung}")


# ---- Abreisen ---------------------------------------------------------------------------

def abreisen_zeichnen(a) -> None:
    zs = a.daten["zeilen"]
    with a.leiste:
        segmente(ank.ZEITRAEUME, a.ab_zeitraum, lambda w: a.setzen(ab_zeitraum=w))
        ui.label(f"{len(zs)} Abreisen").classes("m-kpi")
        knopf("Abreiseliste drucken", lambda: _ab_drucken(a), "", "print")
    sp = "28px 110px minmax(160px, 1.4fr) minmax(120px, 1fr) 90px 120px"
    with a.inhalt:
        if not zs:
            leer("Keine Abreisen in diesem Zeitraum.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("", "Abreise", "Name", "Maßnahme", "Zimmer", "Nächste Anreise"):
                ui.label(t)
        for z in zs:
            r = ui.element("div").classes("m-raster m-zeile m-klick").style(f"grid-template-columns:{sp}")
            with r:
                with ui.element("div"):
                    ui.element("div").classes("m-ampel " + ("akzent" if z.art == "geplant" else "ok"))
                ui.label(z.tag).classes("m-mono")
                ui.label(z.name).classes("m-name")
                ui.label(z.massnahme).classes("m-zweite")
                ui.label(z.zimmer).classes("m-mono")
                ui.label(z.naechste).classes("m-mono")
            from . import seite_zimmer

            r.on("click", lambda z=z: seite_zimmer.karte_oeffnen(a, z.zimmer_id))


async def _ab_drucken(a) -> None:
    text = await run.io_bound(ank.abreisen_druck, a.stand, a.daten["von"], a.daten["bis"])
    seiten.html_drucken(a, text, f"Abreiseliste_{a.daten['von']:%Y-%m-%d}")


# ---- Firmenprogramm (Eintragen) ---------------------------------------------------------

def eintragen_zeichnen(a) -> None:
    zs = a.daten["zeilen"]
    offen = [z for z in zs if not z.haken]
    with a.leiste:
        ui.html(f'<span class="m-kpi"><b>{len(offen)}</b> noch eintragen<span class="m-punktt">·</span>'
                f'<b>{len(zs) - len(offen)}</b> erledigt<span class="m-punktt">·</span>Anreisen der nächsten '
                f'{a.ein_tage} Tage</span>', sanitize=False)
        segmente({14: "14 Tage", 30: "30 Tage", 90: "90 Tage"}, a.ein_tage, lambda t: a.setzen(ein_tage=t))
        if offen:
            knopf("Offene kopieren", lambda: _kopieren(a), "gruen", "content_copy")
            knopf("Alle als eingetragen markieren", lambda: a.aendern(ank.eintragen_setzen, [z.schluessel for z in offen],
                                                                       True, a.heute, a.ein_tage), "", "done_all")
    sp = "36px 110px minmax(160px, 1.4fr) minmax(140px, 1.2fr) 90px 190px"
    with a.inhalt:
        ui.label("Im Programm geplant, aber noch nicht im Belegungssystem gebucht. „Kopieren“ legt die Zeilen "
                 "(Zimmer, Name, Maßnahme, von, bis) tabulatorgetrennt in die Zwischenablage – zum Einfügen oder "
                 "Abtippen. Danach abhaken.").classes("m-ptext").style("padding: 14px 20px 4px")
        if not zs:
            leer("Nichts einzutragen.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("", "Anreise", "Name", "Maßnahme", "Zimmer", "Zeitraum"):
                ui.label(t)
        for z in zs:
            with ui.element("div").classes("m-raster m-zeile" + (" fertig" if z.haken else "")).style(f"grid-template-columns:{sp}"):
                with ui.element("div"):
                    b = ui.element("button").classes("m-haken" + (" an" if z.haken else ""))
                    attr(b, title="Im Belegungssystem eingetragen", aria_pressed=str(z.haken).lower())
                    with b:
                        ui.icon("check")
                    b.on("click", lambda z=z: a.aendern(ank.eintragen_setzen, [z.schluessel], not z.haken, a.heute, a.ein_tage))
                ui.label(f"{z.von:%d.%m.%Y}").classes("m-mono")
                ui.label(z.name).classes("m-name")
                ui.label(z.massnahme).classes("m-zweite")
                ui.label(z.zimmer).classes("m-mono")
                ui.label(f"{z.von:%d.%m.%Y} – {z.bis:%d.%m.%Y}").classes("m-mono")


async def _kopieren(a) -> None:
    text = await run.io_bound(ank.eintragen_text, a.stand, a.heute, a.ein_tage)
    ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(text)})")
    a.toast(f"{text.count(chr(10)) + 1 if text else 0} Zeilen kopiert", rueck=False)


# ---- Personen im Panel ------------------------------------------------------------------

async def person_panel(a, schluessel: str) -> None:
    try:
        p = await run.io_bound(ank.person, a.stand, schluessel)
    except ValueError as exc:
        a.toast(str(exc), fehler=True)
        return

    def bauen():
        ui.label(f"{p.massnahme} · Anreise {p.anreise:%d.%m.%Y}" + (f" · TN-ID {p.tn_id}" if p.tn_id else "")).classes("m-ptext")
        ui.label("Für die Zuteilung").classes("m-ktitel")
        g = ui.select({"": "unbekannt", "w": "weiblich", "m": "männlich", "d": "divers"}, value=p.geschlecht,
                      label="Geschlecht" + (" (aus dem Vornamen geschätzt)" if p.geschlecht_geschaetzt else "")).classes(
            "m-feld").props('dense outlined dark options-dense popup-content-class="m-popup"')
        tier = ui.switch("kommt mit Tier", value=p.tier).props("dense color=indigo-4")

        async def angaben():
            if await a.aendern(ank.angaben_setzen, p.schluessel, g.value or "", bool(tier.value)):
                await person_panel(a, schluessel)

        with ui.element("div").classes("m-paktionen"):
            knopf("Angaben speichern", angaben, "primaer", "check")
        if p.aus_liste:
            ui.label("Aufenthalt").classes("m-ktitel")
            ab = ui.input("Abreise (leer = offen)", value=p.abreise.isoformat() if p.abreise else "").classes("m-feld").props(
                "dense outlined dark type=date")
            bem = ui.input("Bemerkung", value=p.bemerkung).classes("m-feld").props("dense outlined dark")

            async def aufenthalt():
                d = date.fromisoformat(ab.value) if ab.value else None
                if await a.aendern(ank.person_aendern, p.schluessel, d, bem.value or ""):
                    a.panel_zu()

            with ui.element("div").classes("m-paktionen"):
                knopf("Speichern", aufenthalt, "", "check")
                knopf("Person entfernen", lambda: _entfernen(a, p), "leise", "delete")
        else:
            ui.label("Aus UWT-Liste bzw. Gebäudeplan – Zeitraum dort ändern.").classes("m-ptext")

    a.panel(p.name, bauen)


async def _entfernen(a, p) -> None:
    if await a.aendern(ank.person_entfernen, p.schluessel):
        a.panel_zu()


def person_neu_panel(a) -> None:
    def bauen():
        ui.label("Person von Hand zur Anreiseliste hinzufügen (z. B. Nachmeldung). Sie erscheint unter ihrem "
                 "Anreisetag zum Zuteilen.").classes("m-ptext")
        name = ui.input("Name (Nachname, Vorname)").classes("m-feld").props("dense outlined dark")
        mn = ui.select(ank.massnahmen(), label="Maßnahme", new_value_mode="add-unique", with_input=True).classes(
            "m-feld").props('dense outlined dark options-dense popup-content-class="m-popup"')
        an = ui.input("Anreise", value=a.kennung or a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
        ab = ui.input("Abreise (optional)").classes("m-feld").props("dense outlined dark type=date")
        tn = ui.input("TN-ID (optional)").classes("m-feld").props("dense outlined dark")

        async def speichern():
            try:
                von = date.fromisoformat(an.value)
            except (TypeError, ValueError):
                a.toast("Bitte die Anreise wählen.", fehler=True)
                return
            bis = date.fromisoformat(ab.value) if ab.value else None
            if await a.aendern(ank.person_anlegen, name.value or "", mn.value or "", von, bis, tn.value or ""):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Hinzufügen", speichern, "primaer", "person_add")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Person hinzufügen", bauen)


def optimieren_panel(a) -> None:
    async def bauen_async(liste_box):
        vs = await run.io_bound(ank.optimieren_vorschlaege, a.heute)
        liste_box.clear()
        gewaehlt = {i for i, v in enumerate(vs) if v.vorauswahl and v.umsetzbar}
        with liste_box:
            if not vs:
                ui.label("Keine Verbesserungen gefunden – die Belegung passt.").classes("m-ptext")
                return
            for i, v in enumerate(vs):
                with ui.element("div").classes("m-plan-u"):
                    cb = ui.checkbox(v.text, value=i in gewaehlt).props("dense dark color=indigo-4")
                    cb.on_value_change(lambda e, i=i: gewaehlt.add(i) if e.value else gewaehlt.discard(i))
                    ui.label(f"{v.zeitraum} · " + "; ".join(v.gruende[:3])).classes("m-zweite")
                    if not v.umsetzbar:
                        ui.label("Nur als Aufgabe: Buchung im Belegungssystem ändern").classes("m-zweite").style("color:var(--orange)")

            async def los():
                auswahl = [vs[i] for i in sorted(gewaehlt)]
                if not auswahl:
                    a.toast("Nichts ausgewählt.", fehler=True)
                    return
                if await a.aendern(ank.optimieren_umsetzen, auswahl, a.heute):
                    a.panel_zu()

            with ui.element("div").classes("m-paktionen"):
                knopf(f"Ausgewählte übernehmen", los, "primaer", "check")
                knopf("Abbrechen", a.panel_zu, "leise")

    def bauen():
        ui.label("Vorschläge, wie Kurse auf einem Flur zusammenkommen und Zimmer besser passen – mit Begründung. "
                 "Nichts wird ohne „Übernehmen“ geändert; danach ist Rückgängig möglich.").classes("m-ptext")
        box = ui.element("div").classes("m-plan-liste")
        with box:
            ui.label("Rechnet …").classes("m-ptext")
        ui.timer(0.05, lambda: bauen_async(box), once=True)

    a.panel("Belegung optimieren", bauen, breit=True)
