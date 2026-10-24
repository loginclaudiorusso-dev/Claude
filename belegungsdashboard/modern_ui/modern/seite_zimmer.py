"""Seite „Zimmer“: Ansichten Zeitstrahl und Liste. Klick auf ein Zimmer (oder eine Belegung) öffnet rechts die
Zimmerkarte mit Bewohnern, Mängeln, Hinweis, Notizen und Umzug."""

from __future__ import annotations

from datetime import date, timedelta

from nicegui import run, ui

from . import seiten, zimmer_kern as zk
from .ui_bausteine import attr, badge, kennzahlen, knopf, leer, segmente

ANSICHTEN = {"uebersicht": "Übersicht", "zeitstrahl": "Zeitstrahl", "liste": "Liste", "maengel": "Defekte Zimmer"}


def daten(a) -> None:
    ansicht = a.ansicht_von("zimmer", "uebersicht")
    if ansicht == "uebersicht":
        a.daten = {"haeuser": zk.uebersicht(a.stand, a.zu_tag), "np": None}
        return
    if ansicht == "maengel":
        a.daten = zk.maengel_liste(a.stand, a.heute)
        return
    if ansicht == "zeitstrahl":
        seiten.zs_daten(a)
    else:
        f = zk.filter_bauen(a.zl_haus, a.zl_status, a.zl_schnell, a.zl_text)
        a.daten = zk.liste(a.stand, f, a.heute)


def zeichnen(a) -> None:
    ansicht = a.ansicht_von("zimmer", "uebersicht")
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("zimmer", ansicht=v))
    if ansicht == "uebersicht":
        _uebersicht(a)
    elif ansicht == "maengel":
        _maengel(a)
    elif ansicht == "zeitstrahl":
        seiten.zs_zeichnen(a)
        _klickbar(a)
    else:
        _liste(a)


def _klickbar(a) -> None:
    """Klick auf Zimmer oder Belegung im Zeitstrahl öffnet die Zimmerkarte."""
    for el in a.inhalt.default_slot.children:
        el.on("click", lambda e: karte_oeffnen(a, e.args) if e.args else None,
              js_handler="(e) => { const t = e.target.closest('[data-z]'); emit(t ? t.dataset.z : null); }")


def _liste(a) -> None:
    from .kern import WT  # noqa: F401

    with a.werkzeuge:
        segmente({"": "Alle Häuser", **{h: f"Haus {h}" for h in ("2", "3.1", "3.2", "3.3", "6")}}, a.zl_haus,
                 lambda h: a.setzen(zl_haus=h))
    zs = a.daten
    with a.leiste:
        suche = ui.input(placeholder="Zimmer, Name, Hinweis …", value=a.zl_text).classes("m-feld m-sucheingabe").props(
            "dense outlined dark clearable")
        suche.on("keydown.enter", lambda: a.setzen(zl_text=suche.value or ""))
        suche.on("clear", lambda: a.setzen(zl_text=""))
        segmente(zk.STATUS, a.zl_status, lambda s: a.setzen(zl_status=s))
        with ui.element("div").classes("m-segm").props('role="group"'):
            for k, text in zk.MERKMALE.items():
                an = k in a.zl_schnell
                b = ui.element("button").classes("an" if an else "")
                attr(b, aria_pressed=str(an).lower())
                with b:
                    ui.label(text)
                b.on("click", lambda k=k: a.setzen(zl_schnell=a.zl_schnell ^ {k}))
        ui.label(f"{len(zs)} Zimmer").classes("m-kpi")
        knopf("Liste drucken", lambda: _drucken(a, "liste"), "", "print")
        knopf("FM-Mängelbericht", lambda: _drucken(a, "fm"), "", "build")
    spalten = "104px 76px minmax(110px, .9fr) 90px minmax(80px, .6fr) minmax(90px, .7fr) minmax(160px, 1.6fr) minmax(120px, 1.2fr)"
    with a.inhalt:
        if not zs:
            leer("Keine Zimmer mit diesen Filtern.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{spalten}"):
            for t in ("Zustand", "Zimmer", "Lage", "Merkmale", "Renoviert", "Boden", "Heute", "Mängel / Hinweis"):
                ui.label(t)
        for r in zs:
            stufe = {0: "", 1: "warn", 2: "warn", 3: "krit"}[r.stufe]
            z = ui.element("div").classes("m-raster m-zeile m-klick").style(f"grid-template-columns:{spalten}")
            with z:
                with ui.element("div"):
                    badge(r.status)
                ui.label(r.kurz).classes("m-name m-mono")
                ui.label(r.lage).classes("m-zweite")
                ui.label(r.merkmale or "–").classes("m-zweite")
                ui.label(r.reno or "–").classes("m-zweite")
                ui.label(r.boden or "–").classes("m-zweite")
                attr(ui.label(r.heute).classes("m-zweite"), title=r.heute)
                text = r.maengel or r.notiz
                attr(ui.label(text).classes(f"m-zweite {'m-' + stufe if stufe else ''}"), title=text)
            z.on("click", lambda r=r: karte_oeffnen(a, r.zimmer))


async def _drucken(a, art: str) -> None:
    if art == "fm":
        text = await run.io_bound(zk.fm_bericht)
        name = "Maengelbericht"
    else:
        f = zk.filter_bauen(a.zl_haus, a.zl_status, a.zl_schnell, a.zl_text)
        text = await run.io_bound(zk.liste_druck, a.stand, f, a.heute)
        name = "Zimmerliste"
    seiten.html_drucken(a, text, name)


# =======================================================================================
# Zimmerkarte im Panel
# =======================================================================================

async def karte_oeffnen(a, zimmer_id: str) -> None:
    try:
        k = await run.io_bound(zk.karte, a.stand, zimmer_id, a.heute)
    except ValueError as exc:
        a.toast(str(exc), fehler=True)
        return
    a.panel(f"Zimmer {k.kurz}", lambda: _karte(a, k), breit=True)


async def _nach(a, aktion, *args, zimmer: str) -> None:
    """Ändern und die Karte mit frischen Daten neu öffnen."""
    if await a.aendern(aktion, *args):
        await karte_oeffnen(a, zimmer)


def _karte(a, k: zk.Karte) -> None:
    ui.label(f"{k.lage} · {k.betten} Bett{'en' if k.betten > 1 else ''}" + (f" · {k.merkmale}" if k.merkmale else "")
             ).classes("m-ptext")
    if k.unbewohnbar:
        badge("unbewohnbar", f"unbewohnbar: {k.unbewohnbar}")
    # Bewohner
    ui.label("Bewohner").classes("m-ktitel")
    if not k.personen:
        ui.label("Frei – niemand wohnt hier oder kommt.").classes("m-ptext")
    for p in k.personen:
        with ui.element("div").classes("m-plan-u"):
            ui.label(p.name).classes("m-name")
            ui.label(f"{p.gruppe} · {p.von:%d.%m.%Y} – {p.bis:%d.%m.%Y} · {p.quelle}" + (" · kommt" if p.kommt else "")
                     ).classes("m-zweite")
            if p.umzug is not None:
                u = p.umzug
                ui.label(f"Umzug: {u.text} · {u.status_text}").classes("m-zweite").style("color:var(--orange)")
            with ui.element("div").classes("m-paktionen"):
                if p.zimmer_waehlbar:
                    s = ui.select(p.zimmer_waehlbar, value=p.zimmer_jetzt, label="Zimmer").classes("m-feld").props(
                        'dense outlined dark options-dense popup-content-class="m-popup"').style("max-width:220px")
                    s.on_value_change(lambda e, p=p: _nach(a, zk.zimmer_setzen, p.schluessel, e.value, zimmer=e.value)
                                      if e.value and e.value != p.zimmer_jetzt else None)
                if p.fest_umschaltbar:
                    knopf("Wieder auf geplant" if p.fest else "Steht fest", lambda p=p: _nach(
                        a, zk.fest_setzen, p.schluessel, not p.fest, zimmer=k.zimmer), "", "check" if not p.fest else "")
                if p.umzug is not None:
                    knopf("Umzug zurücknehmen", lambda p=p: _nach(a, zk.umzug_entfernen, p.umzug.id, zimmer=k.zimmer), "leise")
                    knopf("Umzug steht fest" if not p.umzug.belegt else "Umzug wieder geplant", lambda p=p: _nach(
                        a, zk.umzug_fest, p.umzug.id, not p.umzug.belegt, zimmer=k.zimmer), "leise")
                elif p.umzug_moeglich:
                    knopf("Umzug planen …", lambda p=p: _umzug(a, k, p), "", "swap_horiz")
                knopf("Notiz", lambda p=p: _notiz(a, k, p.schluessel, p.name), "leise", "edit_note")
            for n in p.notizen[:3]:
                _notiz_zeile(a, k, n)
    # Mängel
    ui.label("Mängel").classes("m-ktitel")
    from belegung import maengel as mg

    offen = {m[0]: m for m in k.maengel}
    for art, name, stufe, unbew, seit in k.maengel:
        with ui.element("div").classes("m-mangel"):
            ui.label(f"{'!' * stufe} {name}").classes("m-name " + ("m-krit" if stufe == 3 else "m-warn"))
            ui.label(f"seit {seit:%d.%m.%Y}").classes("m-zweite")
            sw = ui.switch("unbewohnbar", value=unbew).props("dense color=red-4")
            sw.on_value_change(lambda e, art=art: _nach(a, zk.unbewohnbar_setzen, k.zimmer, art, e.value, zimmer=k.zimmer))
            knopf("behoben", lambda art=art: _nach(a, zk.mangel_setzen, k.zimmer, art, False, zimmer=k.zimmer), "leise", "check")
    neu = ui.select({art: name for art, name in mg.KATALOG if art not in offen}, label="Mangel melden …").classes(
        "m-feld").props('dense outlined dark options-dense popup-content-class="m-popup"')
    neu.on_value_change(lambda e: _nach(a, zk.mangel_setzen, k.zimmer, e.value, True, zimmer=k.zimmer) if e.value else None)
    # Hinweis + Notizen zum Zimmer
    ui.label("Hinweis zum Zimmer (dauerhaft)").classes("m-ktitel")
    h = ui.input(value=k.hinweis, placeholder="z. B. Rollo klemmt").classes("m-feld").props("dense outlined dark")
    h.on("blur", lambda: _nach(a, zk.hinweis_setzen, k.zimmer, h.value or "", zimmer=k.zimmer)
         if (h.value or "") != k.hinweis else None)
    from belegung import zimmerplan as zp

    with ui.element("div").classes("m-paktionen"):
        knopf("Notiz zum Zimmer", lambda: _notiz(a, k, zp.zimmer_schluessel(k.zimmer), f"Zimmer {k.kurz}"), "leise", "edit_note")
        knopf("Zur Reinigung", lambda: _reinigung(a, k), "leise", "cleaning_services")
    for n in k.notizen[:5]:
        _notiz_zeile(a, k, n)
    # Belegungen
    if k.belegungen:
        ui.label("Belegungen ab heute").classes("m-ktitel")
        for zeit, text, art in k.belegungen[:12]:
            with ui.element("div").classes("m-liste-zeile"):
                ui.element("div").classes(f"m-zs-punkt {art}")
                ui.label(text).classes("m-name")
                ui.label(zeit).classes("m-mono")


def _notiz_zeile(a, k: zk.Karte, n) -> None:
    with ui.element("div").classes("m-notiz"):
        ui.label(n.text).classes("m-ptext").style("color:var(--text)")
        ui.label(f"{n.erstellt:%d.%m.%Y}" + (f" · Wiedervorlage {n.wiedervorlage:%d.%m.%Y}" if n.wiedervorlage else "")
                 ).classes("m-zweite")
        knopf("", lambda: _nach(a, zk.notiz_loeschen, n.id, zimmer=k.zimmer), "leise", "close", "Notiz löschen")


def _notiz(a, k: zk.Karte, person: str, name: str) -> None:
    def bauen():
        ui.label(f"Notiz für {name}. Mit Wiedervorlage erscheint sie an dem Tag unter Heute.").classes("m-ptext")
        text = ui.textarea("Notiz").classes("m-feld").props("outlined dark autogrow")
        wv = ui.input("Wiedervorlage (optional)").classes("m-feld").props("dense outlined dark type=date")

        async def speichern():
            d = date.fromisoformat(wv.value) if wv.value else None
            if await a.aendern(zk.notiz_hinzu, person, name, text.value or "", d):
                await karte_oeffnen(a, k.zimmer)

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            knopf("Zurück", lambda: karte_oeffnen(a, k.zimmer), "leise")

    a.panel(f"Notiz · {name}", bauen)


def _umzug(a, k: zk.Karte, p: zk.Person) -> None:
    def bauen():
        ui.label(f"{p.name} zieht ab einem Tag aus {k.kurz} in ein anderes Zimmer. Angeboten werden nur Zimmer, die "
                 "ab dem Tag frei sind; Ausnahmen mit Grund.").classes("m-ptext")
        ab = ui.input("Umzug ab", value=max(a.heute, p.von).isoformat()).classes("m-feld").props("dense outlined dark type=date")
        ziel = ui.select({}, label="Neues Zimmer", with_input=True).classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        grund = ui.input("Grund (optional)").classes("m-feld").props("dense outlined dark")

        async def ziele():
            try:
                d = date.fromisoformat(ab.value)
            except (TypeError, ValueError):
                return
            ziel.set_options(await run.io_bound(zk.umzug_ziele, k.zimmer, p.schluessel, p.name, d), value=None)

        ab.on_value_change(ziele)

        async def speichern():
            if not ziel.value:
                a.toast("Bitte ein Zimmer wählen.", fehler=True)
                return
            if await a.aendern(zk.umzug_speichern, k.zimmer, p.schluessel, p.name, ziel.value,
                               date.fromisoformat(ab.value), grund.value or ""):
                await karte_oeffnen(a, k.zimmer)

        with ui.element("div").classes("m-paktionen"):
            knopf("Umzug speichern", speichern, "primaer", "swap_horiz")
            knopf("Zurück", lambda: karte_oeffnen(a, k.zimmer), "leise")
        ui.timer(0.05, ziele, once=True)

    a.panel(f"Umzug · {p.name}", bauen)


def _reinigung(a, k: zk.Karte) -> None:
    from belegung import zimmerplan as zp

    from . import seiten_kern as sk

    def bauen():
        tag = ui.input("Tag", value=a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
        grund = ui.select(zp.REINIGUNG_GRUENDE, value=zp.REINIGUNG_GRUENDE[0], label="Grund", new_value_mode="add-unique",
                          with_input=True).classes("m-feld").props('dense outlined dark options-dense popup-content-class="m-popup"')

        async def speichern():
            if await a.aendern(sk.reinigung_hinzu, k.kurz, date.fromisoformat(tag.value), grund.value or ""):
                await karte_oeffnen(a, k.zimmer)

        with ui.element("div").classes("m-paktionen"):
            knopf("Auf die Reinigungsliste", speichern, "primaer", "add")
            knopf("Zurück", lambda: karte_oeffnen(a, k.zimmer), "leise")

    a.panel(f"Reinigung · Zimmer {k.kurz}", bauen)


# =======================================================================================
# Übersicht (Kacheln) und defekte Zimmer
# =======================================================================================

def _uebersicht(a) -> None:
    from datetime import timedelta

    haeuser = a.daten["haeuser"]
    alle = [k for et in haeuser.values() for ks in et.values() for k in ks]
    n = {s: sum(1 for k in alle if k.status == s) for s in ("frei", "teilweise", "belegt", "geplant", "gesperrt")}
    defekt = sum(1 for k in alle if k.stufe)
    f = a.zu_filter
    with a.leiste:
        kennzahlen([("frei", n["frei"] + n["teilweise"], "frei", "ok"), ("belegt", n["belegt"], "belegt", "blau"),
                    ("geplant", n["geplant"], "geplant", "akzent"), ("gesperrt", n["gesperrt"], "gesperrt", "neutral"),
                    ("maengel", defekt, "mit Mängeln", "warn")], f,
                   lambda k: a.setzen(zu_filter=None if k == a.zu_filter else k, laden=False))
        ui.label(f"am {a.zu_tag:%d.%m.%Y}").classes("m-kpi")
        knopf("", lambda: a.setzen(zu_tag=a.zu_tag - timedelta(days=1)), "leise", "chevron_left", "Tag zurück")
        knopf("Heute", lambda: a.setzen(zu_tag=a.heute), "leise")
        knopf("", lambda: a.setzen(zu_tag=a.zu_tag + timedelta(days=1)), "leise", "chevron_right", "Tag weiter")
        tag = ui.input(value=a.zu_tag.isoformat()).classes("m-feld").props("dense outlined dark type=date").style("width:160px")
        tag.on_value_change(lambda e: a.setzen(zu_tag=date.fromisoformat(e.value)) if e.value else None)
        with ui.element("span").classes("m-legende").style("margin-left:auto"):
            for z_ in ("frei", "teilweise", "belegt", "geplant", "gesperrt", "maengel", "unbewohnbar"):
                badge(z_)
    with a.inhalt:
        with ui.element("div").classes("m-haeuser"):
            for haus, etagen in haeuser.items():
                with ui.element("section").classes("m-block m-haus"):
                    ui.label(f"Haus {haus}").classes("m-btitel")
                    for etage, ks in etagen.items():
                        with ui.element("div").classes("m-etage"):
                            ui.label(etage).classes("m-zweite m-etage-titel")
                            with ui.element("div").classes("m-kacheln"):
                                for k in ks:
                                    passt = (f is None or (f == "maengel" and k.stufe) or k.status == f
                                             or (f == "frei" and k.status == "teilweise"))
                                    kl = f"m-kachel {k.status}" + (" unbew" if k.unbewohnbar else "") + ("" if passt else " aus")
                                    b = ui.element("button").classes(kl)
                                    attr(b, title=k.titel)
                                    with b:
                                        ui.label(k.nr)
                                        if k.stufe:
                                            ui.label("!" * k.stufe).classes("m-kachel-m")
                                    b.on("click", lambda k=k: karte_oeffnen(a, k.zimmer))


def _maengel(a) -> None:
    zs: list[zk.MZeile] = a.daten
    with a.leiste:
        n = {st: sum(1 for z in zs if z.stufe == st) for st in (3, 2, 1)}
        kennzahlen([(3, n[3], "nicht bewohnbar", "krit"), (2, n[2], "dringend", "warn"), (1, n[1], "leicht", "neutral")],
                   a.dz_filter, lambda k: a.setzen(dz_filter=None if k == a.dz_filter else k, laden=False))
        ui.label(f"{sum(len(z.maengel) for z in zs)} offene Mängel").classes("m-kpi")
        knopf("FM-Bericht drucken", lambda: _fm(a, "druck"), "", "print").style("margin-left:auto")
        knopf("FM-Liste (Excel)", lambda: _fm(a, "excel"), "", "table_view")
        knopf("Für Mail kopieren", lambda: _fm(a, "mail"), "leise", "content_copy")
        from .seite_daten import _hochladen

        _hochladen(a, "Erledigte aus FM-Liste", ".xlsx", lambda f: _fm_zurueck(a, f), art="leise")
    sp = "116px 80px minmax(110px, .7fr) minmax(260px, 2.2fr) 120px 110px 40px"
    with a.inhalt:
        if not zs:
            leer("Keine offenen Mängel – alle Zimmer in Ordnung.")
            return
        for st, titel in zk.STUFEN.items():
            gruppe = [z for z in zs if z.stufe == st and (a.dz_filter is None or a.dz_filter == st)]
            if not gruppe:
                continue
            ui.label(f"{titel} ({len(gruppe)})").classes("m-abschnitt")
            with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
                for t in ("", "Zimmer", "Lage", "Mängel", "Heute", "Nächste Anreise", ""):
                    ui.label(t)
            for z in gruppe:
                with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                    with ui.element("div"):
                        badge("unbewohnbar" if z.stufe == 3 else "maengel", {3: "unbewohnbar", 2: "Mängel", 1: "Hinweis"}[z.stufe])
                    n_ = ui.label(z.kurz).classes("m-name m-link")
                    n_.on("click", lambda z=z: karte_oeffnen(a, z.zimmer))
                    ui.label(z.lage).classes("m-zweite")
                    with ui.element("div").classes("m-mliste"):
                        for art, name, stufe, unbew, seit, notiz in z.maengel:
                            with ui.element("div").classes("m-mzeile"):
                                attr(ui.label(f"{'!' * stufe} {name}").classes("m-ptext " + ("m-krit" if unbew else "m-warn" if stufe == 2 else "")),
                                     title=notiz or name)
                                ui.label(f"seit {seit:%d.%m.}").classes("m-zweite")
                                knopf("", lambda z=z, art=art: a.aendern(zk.mangel_setzen, z.zimmer, art, False), "leise", "check",
                                      "Behoben")
                    ui.label(z.heute).classes("m-zweite")
                    ui.label(f"{z.naechste:%d.%m.%Y}" if z.naechste else "–").classes("m-mono" + (" m-warn" if z.naechste and
                                                                                                  (z.naechste - a.heute).days <= 7 else ""))
                    knopf("", lambda z=z: karte_oeffnen(a, z.zimmer), "leise", "open_in_new", "Zimmerkarte")


async def _fm(a, art: str) -> None:
    import json

    if art == "druck":
        seiten.html_drucken(a, await run.io_bound(zk.fm_bericht_html, a.stand, a.heute), "Maengelbericht_FM")
    elif art == "mail":
        text = await run.io_bound(zk.fm_mailtext, a.stand)
        ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(text)})")
        a.toast("Mängelliste für die Mail kopiert", rueck=False)
    else:
        try:
            text, pfad = await run.io_bound(zk.fm_excel, a.stand, a.heute)
        except Exception as exc:             # noqa: BLE001
            a.toast(f"Nicht gespeichert: {exc}", fehler=True)
            return
        if not seiten._datei_oeffnen(str(pfad)):
            a.toast(f"{text}: {pfad}", rueck=False)
        else:
            a.toast(text, rueck=False)


async def _fm_zurueck(a, dateien) -> None:
    eintraege, fehler = await run.io_bound(zk.fm_erledigte_lesen, dateien[0][0])

    def bauen():
        if fehler:
            for f in fehler[:10]:
                ui.label(f).classes("m-zweite").style("color:var(--orange)")
        if not eintraege:
            ui.label("In der Liste ist nichts als erledigt eingetragen (Spalte „erledigt am“).").classes("m-ptext")
            return
        ui.label(f"{len(eintraege)} offene Mängel sind laut FM erledigt:").classes("m-ptext")
        for zid, art, tag, bem in eintraege[:60]:
            from belegung import maengel as mg

            ui.label(f"{zid.removeprefix('GS-')}: {mg.NAMEN.get(art, art)} – erledigt {tag:%d.%m.%Y}" + (f" ({bem})" if bem else "")
                     ).classes("m-zweite")

        async def los():
            if await a.aendern(zk.fm_erledigte_uebernehmen, eintraege):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Als behoben übernehmen", los, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Erledigte aus der FM-Liste", bauen)
