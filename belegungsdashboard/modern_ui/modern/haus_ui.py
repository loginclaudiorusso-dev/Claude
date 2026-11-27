"""1.63: „Aktuell im Haus“ (Bildschirmliste), Abwesenheiten und Schlüsselausgaben – als Panels, erreichbar unter
Übersicht → Im Haus und aus jeder Zeile von „Aktuell im Haus“."""

from __future__ import annotations

from datetime import date, timedelta

from nicegui import run, ui

from . import haus_kern as hk
from .ui_bausteine import attr, knopf, leer, segmente

ARTEN = {"": "Alle", "im_haus": "Im Haus", "abwesend": "Abwesend", "geplant": "Nur geplant"}
SPALTEN = "78px minmax(150px, 1fr) auto auto"


def _daten(a):
    from . import notfall_kern as nk

    ids = {z.kurz: z.id for z in a.stand.zimmer}
    zs = nk.zeilen(a.stand, a.heute)
    return hk.im_haus(zs, hk.abw_laden(), hk.schl_laden(), a.heute, lambda k: ids.get(k, k))


async def im_haus_panel(a, art: str = "", text: str = "") -> None:
    if a.stand is None:
        a.toast("Erst Daten laden.", fehler=True)
        return
    alle = await run.io_bound(_daten, a)
    zustand = {"art": art, "text": text}

    def bauen():
        n = hk.zaehlen(alle)
        ui.label(f"Stand {a.heute:%d.%m.%Y} laut Gebäude- und Zimmerplan · {n['im_haus']} im Haus · {n['abwesend']} abwesend"
                 + (f" · {n['geplant']} nur geplant" if n["geplant"] else "")
                 + " – Gäste, Besucher und Personal kennt das Programm nicht.").classes("m-ptext")
        with ui.element("div").classes("m-paktionen").style("align-items:center;flex-wrap:wrap"):
            segmente(ARTEN, zustand["art"], lambda v: neu("art", v))
            such = ui.input(placeholder="Name, Zimmer, Gruppe …", value=zustand["text"]).props(
                "dense outlined clearable").classes("m-feld").style("min-width:220px")
            such.on_value_change(lambda e: neu("text", e.value or ""))
            knopf("Notfallliste drucken", lambda: _notfall(a), "leise", "print")
        box = ui.element("div")

        def zeichnen():
            box.clear()
            zs = hk.filtern(alle, zustand["art"], zustand["text"])
            with box:
                if not zs:
                    leer("Niemand passt zu dieser Auswahl.")
                    return
                haus = None
                for z in zs[:600]:
                    if z.haus != haus:                       # je Haus eine Überschrift
                        haus = z.haus
                        hz = hk.zaehlen([x for x in zs if x.haus == haus])
                        ui.label(f"Haus {haus} · {hz['im_haus']} im Haus" + (f" · {hz['abwesend']} abwesend" if hz["abwesend"]
                                                                            else "")
                                 + (f" · {hz['geplant']} nur geplant" if hz["geplant"] else "")).classes("m-abschnitt")
                    with ui.element("div").classes("m-raster m-zeile" + (" fertig" if z.art == "abwesend" else "")).style(
                            f"grid-template-columns:{SPALTEN};align-items:center"):
                        ui.label(z.zimmer).classes("m-mono")
                        with ui.element("div"):
                            ui.label(z.name).classes("m-name")
                            ui.label(" · ".join(t for t in (z.gruppe, f"bis {z.bis:%d.%m.%Y}" if z.bis else "") if t)
                                     ).classes("m-zweite")
                        with ui.element("div").classes("m-paktionen").style("padding:0;gap:4px"):
                            if z.art == "abwesend":
                                ui.label(z.abwesend).classes("m-pille warn")
                            elif z.art == "geplant":
                                ui.label("nur geplant").classes("m-pille neutral")
                            if z.schluessel:
                                ui.label(f"{z.schluessel} Schlüssel").classes("m-pille ok")
                        with ui.element("div").classes("m-paktionen").style("padding:0;flex-wrap:nowrap"):
                            if z.art == "abwesend":
                                knopf("", lambda z=z: _wieder_da(a, z), "leise", "home",
                                      "Wieder da – Abwesenheit beenden")
                            else:
                                knopf("", lambda z=z: abwesend_panel(a, z.name, z.zimmer_id), "leise", "luggage",
                                      "Abwesend eintragen (Heimfahrt, Urlaub …)")
                            knopf("", lambda z=z: schluessel_panel(a, z.name, z.zimmer_id, z.bis), "leise", "key",
                                  "Schlüssel ausgeben oder zurücknehmen")
                if len(zs) > 600:
                    ui.label(f"… und {len(zs) - 600} weitere – bitte suchen").classes("m-zweite")

        def neu(k, v):
            zustand[k] = v
            zeichnen()
        zeichnen()
        with ui.element("div").classes("m-paktionen"):
            knopf("Alle Abwesenheiten", lambda: abwesenheiten_panel(a), "leise", "list")
            knopf("Alle Schlüssel", lambda: schluessel_liste_panel(a), "leise", "key")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel("Aktuell im Haus", bauen, breit=True)


async def _notfall(a) -> None:
    from .seite_zimmer import notfall_drucken

    await notfall_drucken(a)


async def _wieder_da(a, z) -> None:
    """Abwesenheit endet gestern – heute ist die Person wieder da."""
    def tun():
        alle = hk.abw_laden()
        x = next((y for y in alle if y.id == z.abw_id), None)
        if x is None:
            raise ValueError("Diese Abwesenheit gibt es nicht mehr.")
        if x.von_d >= a.heute:
            return hk.abw_entfernen(x.id)
        from .kern import _schritt

        def schreiben():
            liste = hk.abw_laden()
            for y in liste:
                if y.id == x.id:
                    y.bis = (a.heute - timedelta(days=1)).isoformat()
            hk._abw_speichern(liste)
        _schritt(f"{x.name} wieder da", schreiben, [hk.ABW_DATEI])
        return f"{x.name} ist wieder da"
    if await a.aendern(tun):
        await im_haus_panel(a)


def _zimmer_optionen(a) -> dict:
    return {"": "– ohne Zimmer –", **{z.id: z.kurz for z in sorted(a.stand.zimmer, key=lambda z: z.kurz) if z.aktiv}}


def abwesend_panel(a, name: str = "", zimmer: str = "") -> None:
    def bauen():
        n = ui.input("Name", value=name).classes("m-feld w-full").props("dense outlined dark")
        zim = ui.select(_zimmer_optionen(a), value=zimmer or "", label="Zimmer", with_input=True).classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        with ui.element("div").classes("m-zweispaltig"):
            von = ui.input("Abwesend ab", value=a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
            bis = ui.input("Wieder da ab (letzter Tag weg + 1)", value=(a.heute + timedelta(days=3)).isoformat()).classes(
                "m-feld").props("dense outlined dark type=date")
        grund = ui.select(hk.GRUENDE, value="heimfahrt", label="Grund").classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        notiz = ui.input("Notiz (optional)").classes("m-feld w-full").props("dense outlined dark")
        ui.label("Abwesende stehen in „Aktuell im Haus“ und auf der Notfallliste getrennt und zählen nicht als im Haus. "
                 "Das Zimmer bleibt belegt.").classes("m-zweite")

        async def speichern():
            try:
                v, w = date.fromisoformat(von.value), date.fromisoformat(bis.value)
            except (TypeError, ValueError):
                a.toast("Bitte beide Daten wählen.", fehler=True)
                return
            if await a.aendern(hk.abw_anlegen, n.value or "", zim.value or "", v, w - timedelta(days=1), grund.value,
                               notiz.value or ""):
                await im_haus_panel(a)

        with ui.element("div").classes("m-paktionen"):
            knopf("Eintragen", speichern, "primaer", "check")
            knopf("Abbrechen", lambda: im_haus_panel(a), "leise")

    a.panel("Abwesenheit eintragen", bauen)


async def abwesenheiten_panel(a) -> None:
    alle = await run.io_bound(hk.abw_laden)
    kurz = {z.id: z.kurz for z in a.stand.zimmer} if a.stand else {}

    def bauen():
        with ui.element("div").classes("m-paktionen"):
            knopf("Neue Abwesenheit", lambda: abwesend_panel(a), "primaer", "add")
            knopf("Für ganzen Kurs …", lambda: kurs_panel(a), "", "groups",
                  "Eine Abwesenheit für alle eines Kurses (z. B. Ferienwoche, Außenpraktikum) – und Kursliste drucken")
        aktuell = [x for x in alle if x.bis_d >= a.heute - timedelta(days=30)]
        if not aktuell:
            leer("Keine Abwesenheiten eingetragen.")
        for x in sorted(aktuell, key=lambda x: x.von, reverse=True):
            with ui.element("div").classes("m-mzeile").style("grid-template-columns:1fr auto"):
                with ui.element("div"):
                    ui.label(f"{x.name}" + (f" · {kurz.get(x.zimmer, x.zimmer)}" if x.zimmer else "")).classes("m-name")
                    ui.label(f"{hk.GRUENDE.get(x.grund, x.grund)} · {x.von_d:%d.%m.} – {x.bis_d:%d.%m.%Y}"
                             + (" · heute weg" if x.am(a.heute) else "") + (f" · {x.notiz}" if x.notiz else "")).classes(
                        "m-zweite")

                async def weg(x=x):
                    if await a.aendern(hk.abw_entfernen, x.id):
                        await abwesenheiten_panel(a)
                knopf("", weg, "leise", "delete", "Abwesenheit löschen")
        knopf("Zurück", lambda: im_haus_panel(a), "leise")

    a.panel("Abwesenheiten", bauen)


async def schluessel_panel(a, name: str = "", zimmer: str = "", bis: date | None = None) -> None:
    offen_alle = hk.offen_von(await run.io_bound(hk.schl_laden), name, zimmer) if name else []

    def bauen():
        if offen_alle:
            ui.label("Noch nicht zurück").classes("m-abschnitt")
            for x in offen_alle:
                with ui.element("div").classes("m-paktionen").style("align-items:center"):
                    ui.label(f"{x.anzahl} × {x.bezeichnung or 'Schlüssel'} · seit {date.fromisoformat(x.aus):%d.%m.%Y}"
                             ).classes("m-ptext")

                    async def zurueck(x=x):
                        if await a.aendern(hk.zuruecknehmen, x.id, a.heute):
                            await im_haus_panel(a)
                    knopf("Zurück erhalten", zurueck, "primaer", "keyboard_return")
            ui.label("Weitere ausgeben").classes("m-abschnitt")
        n = ui.input("Name", value=name).classes("m-feld w-full").props("dense outlined dark")
        zim = ui.select(_zimmer_optionen(a), value=zimmer or "", label="Zimmer", with_input=True).classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        with ui.element("div").classes("m-zweispaltig"):
            anz = ui.number("Anzahl", value=1, min=1, step=1, format="%d").classes("m-feld").props("dense outlined dark")
            bez = ui.input("Bezeichnung / Nummer (optional)", placeholder="z. B. Zimmer + Haustür").classes(
                "m-feld").props("dense outlined dark")
            am = ui.input("Ausgegeben am", value=a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
            rueck = ui.input("Zurück bis (Abreise)", value=bis.isoformat() if bis else "").classes("m-feld").props(
                "dense outlined dark type=date")
        attr(rueck, title="Nach diesem Tag gilt ein nicht zurückgegebener Schlüssel als überfällig")

        async def ausgeben():
            try:
                tag = date.fromisoformat(am.value)
            except (TypeError, ValueError):
                tag = a.heute
            try:
                b = date.fromisoformat(rueck.value) if rueck.value else None
            except ValueError:
                b = None
            if await a.aendern(hk.ausgeben, n.value or "", zim.value or "", int(anz.value or 1), bez.value or "", tag, b):
                await im_haus_panel(a)

        with ui.element("div").classes("m-paktionen"):
            knopf("Ausgeben", ausgeben, "primaer", "key")
            knopf("Alle Schlüssel", lambda: schluessel_liste_panel(a), "leise", "list")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Schlüssel", bauen)


async def schluessel_liste_panel(a, nur_offen: bool = True) -> None:
    alle = await run.io_bound(hk.schl_laden)
    kurz = {z.id: z.kurz for z in a.stand.zimmer} if a.stand else {}
    zustand = {"offen": nur_offen}

    def bauen():
        offen = [x for x in alle if x.offen]
        ueber = [x for x in offen if x.ueberfaellig(a.heute)]
        ui.label(f"{sum(x.anzahl for x in offen)} Schlüssel draußen · {len(ueber)} überfällig (Abreise vorbei)").classes(
            "m-zweite")
        sw = ui.switch("nur offene", value=zustand["offen"]).props("dense")
        box = ui.element("div")

        def zeichnen():
            box.clear()
            zs = [x for x in alle if x.offen] if zustand["offen"] else alle
            zs = sorted(zs, key=lambda x: (not x.ueberfaellig(a.heute), x.aus), reverse=False)
            with box:
                if not zs:
                    leer("Keine Schlüssel draußen.")
                for x in zs:
                    with ui.element("div").classes("m-mzeile").style("grid-template-columns:1fr auto"):
                        with ui.element("div"):
                            ui.label(f"{x.name}" + (f" · {kurz.get(x.zimmer, x.zimmer)}" if x.zimmer else "")).classes(
                                "m-name")
                            ui.label(f"{x.anzahl} × {x.bezeichnung or 'Schlüssel'} · aus {date.fromisoformat(x.aus):%d.%m.%Y}"
                                     + (f" · zurück {date.fromisoformat(x.zurueck):%d.%m.%Y}" if x.zurueck else "")
                                     + (" · ÜBERFÄLLIG" if x.ueberfaellig(a.heute) else "")).classes(
                                "m-zweite" + (" m-warn" if x.ueberfaellig(a.heute) else ""))
                        if x.offen:
                            async def zurueck(x=x):
                                if await a.aendern(hk.zuruecknehmen, x.id, a.heute):
                                    await schluessel_liste_panel(a, zustand["offen"])
                            knopf("Zurück", zurueck, "leise", "keyboard_return")

        sw.on_value_change(lambda e: (zustand.__setitem__("offen", bool(e.value)), zeichnen()))
        zeichnen()
        with ui.element("div").classes("m-paktionen"):
            knopf("Schlüssel ausgeben", lambda: schluessel_panel(a), "primaer", "key")
            knopf("Aktuell im Haus", lambda: im_haus_panel(a), "leise", "groups")

    a.panel("Schlüssel", bauen)


def kurs_panel(a, kurs: str = "", von: date | None = None, bis: date | None = None) -> None:
    """1.75: Abwesenheit für einen ganzen Kurs (Ferien, Außenpraktikum, Brückentag) und Kursliste drucken."""
    von = von or a.heute
    bis = bis or von + timedelta(days=6)
    kurse = hk.kurse(a.stand.lage, von, bis) if a.stand else {}
    kurz = {z.id: z.kurz for z in a.stand.zimmer} if a.stand else {}

    def bauen():
        with ui.element("div").classes("m-zweispaltig"):
            f_von = ui.input("Abwesend ab", value=von.isoformat()).classes("m-feld").props("dense outlined dark type=date")
            f_bis = ui.input("bis einschließlich", value=bis.isoformat()).classes("m-feld").props(
                "dense outlined dark type=date")
        if not kurse:
            leer("Im Zeitraum wohnt niemand mit einer Maßnahme im Haus.")
            knopf("Zurück", lambda: abwesenheiten_panel(a), "leise")
            return
        k = kurs if kurs in kurse else next(iter(kurse))
        wahl = ui.select({n: f"{n} ({len(p)})" for n, p in kurse.items()}, value=k, label="Kurs / Maßnahme",
                         with_input=True).classes("m-feld w-full").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        ui.label("Wer ist betroffen? (alle angehakt – einzelne abwählen)").classes("m-abschnitt")
        haken = {}
        for name, zid in kurse[k]:
            haken[(name, zid)] = ui.checkbox(f"{name} · {kurz.get(zid, zid)}", value=True).props("dense")
        grund = ui.select(hk.GRUENDE, value="ferien", label="Grund").classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        notiz = ui.input("Notiz (optional)").classes("m-feld w-full").props("dense outlined dark")
        ui.label("Die Zimmer bleiben belegt. Wer im Zeitraum schon abwesend eingetragen ist, wird nicht doppelt "
                 "eingetragen. Ein Klick auf „Rückgängig“ nimmt alle wieder heraus.").classes("m-zweite")

        def zeitraum():
            try:
                return date.fromisoformat(f_von.value), date.fromisoformat(f_bis.value)
            except (TypeError, ValueError):
                a.toast("Bitte beide Daten wählen.", fehler=True, rueck=False)
                return None

        def neu_bauen(_e=None):
            z = zeitraum()
            if z:
                kurs_panel(a, wahl.value, *z)
        wahl.on_value_change(neu_bauen)
        f_von.on("change", neu_bauen)
        f_bis.on("change", neu_bauen)

        async def eintragen():
            z = zeitraum()
            if not z:
                return
            wer = [p for p, h in haken.items() if h.value]
            if await a.aendern(hk.abw_sammel_anlegen, wer, z[0], z[1], grund.value, notiz.value or "", wahl.value):
                await abwesenheiten_panel(a)

        def drucken():
            from .seiten import html_drucken

            z = zeitraum() or (von, bis)
            wer = [(n, kurz.get(zid, zid)) for (n, zid), h in haken.items() if h.value]
            html_drucken(a, hk.kursliste_html(wahl.value, wer, "Kursliste",
                                              f"{z[0]:%d.%m.} – {z[1]:%d.%m.%Y} · {len(wer)} Personen"), "Kursliste")

        with ui.element("div").classes("m-paktionen"):
            knopf("Abwesenheit eintragen", eintragen, "primaer", "check")
            knopf("Kursliste drucken", drucken, "", "print", "Name, Zimmer und eine Spalte zum Unterschreiben")
            knopf("Zurück", lambda: abwesenheiten_panel(a), "leise")

    a.panel("Abwesenheit für einen ganzen Kurs", bauen)
