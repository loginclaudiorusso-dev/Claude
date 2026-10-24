"""Seite „Zimmer“: Ansichten Zeitstrahl und Liste. Klick auf ein Zimmer (oder eine Belegung) öffnet rechts die
Zimmerkarte mit Bewohnern, Mängeln, Hinweis, Notizen und Umzug."""

from __future__ import annotations

from datetime import date, timedelta

from nicegui import run, ui

from . import seiten, zimmer_kern as zk
from .ui_bausteine import attr, knopf, leer, segmente

ANSICHTEN = {"zeitstrahl": "Zeitstrahl", "liste": "Liste"}


def daten(a) -> None:
    ansicht = a.ansicht_von("zimmer", "zeitstrahl")
    if ansicht == "zeitstrahl":
        seiten.zs_daten(a)
    else:
        f = zk.filter_bauen(a.zl_haus, a.zl_status, a.zl_schnell, a.zl_text)
        a.daten = zk.liste(a.stand, f, a.heute)


def zeichnen(a) -> None:
    ansicht = a.ansicht_von("zimmer", "zeitstrahl")
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("zimmer", ansicht=v))
    if ansicht == "zeitstrahl":
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
    spalten = "28px 76px minmax(110px, .9fr) 90px minmax(80px, .6fr) minmax(90px, .7fr) minmax(160px, 1.6fr) minmax(120px, 1.2fr)"
    with a.inhalt:
        if not zs:
            leer("Keine Zimmer mit diesen Filtern.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{spalten}"):
            for t in ("", "Zimmer", "Lage", "Merkmale", "Renoviert", "Boden", "Heute", "Mängel / Hinweis"):
                ui.label(t)
        for r in zs:
            stufe = {0: "", 1: "warn", 2: "warn", 3: "krit"}[r.stufe]
            punkt = {"frei": "ok", "teilweise": "ok", "gesperrt": "neutral"}.get(r.status, "akzent")
            z = ui.element("div").classes("m-raster m-zeile m-klick").style(f"grid-template-columns:{spalten}")
            with z:
                with ui.element("div"):
                    ui.element("div").classes(f"m-ampel {punkt}")
                ui.label(r.kurz).classes("m-name")
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
        ui.label(f"Unbewohnbar: {k.unbewohnbar}").classes("m-pille krit")
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
