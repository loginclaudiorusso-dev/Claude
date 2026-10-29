"""Seite „Zimmer“: Ansichten Zeitstrahl und Liste. Klick auf ein Zimmer (oder eine Belegung) öffnet rechts die
Zimmerkarte mit Bewohnern, Mängeln, Hinweis, Notizen und Umzug."""

from __future__ import annotations

from datetime import date, timedelta

from nicegui import run, ui

from . import seiten, zimmer_kern as zk
from .ui_bausteine import attr, badge, kennzahlen, knopf, leer, segmente

ANSICHTEN = {"uebersicht": "Übersicht", "karten": "Karten", "zeitstrahl": "Zeitstrahl", "liste": "Liste",
             "maengel": "Defekte Zimmer"}


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
        return
    f = zk.filter_bauen(a.zl_haus, a.zl_status, a.zl_schnell, a.zl_text, a.zl_mehr)
    tag = a.zu_tag
    a.daten = {"n": zk.zaehler(a.stand, a.zl_haus, tag, bool(a.zl_mehr.get("alle"))),
               "kpi": zk.kennzahl_text(zk._sortiert(a.stand, f, tag))}
    if ansicht == "karten":
        a.daten["haeuser"], a.daten["hinweis"] = zk.karten(a.stand, f, tag)
    else:
        a.daten["zeilen"] = zk.liste(a.stand, f, tag)


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
    elif ansicht == "karten":
        _karten(a)
    else:
        _liste(a)


_ZIEL_WEG = "document.querySelectorAll('.m-zs-zeile.ziel').forEach(x => x.classList.remove('ziel'))"


def _klickbar(a) -> None:
    """Klick auf Zimmer oder Belegung im Zeitstrahl öffnet die Zimmerkarte. Geplante Personen lassen sich per Ziehen
    in eine andere Zimmerzeile verschieben (Prüfung und Bestätigung wie im Hauptprogramm)."""
    for el in a.inhalt.default_slot.children:
        el.on("click", lambda e: karte_oeffnen(a, e.args) if e.args else None,
              js_handler="(e) => { const t = e.target.closest('[data-z]'); emit(t ? t.dataset.z : null); }")
        el.on("dragstart", js_handler="(e) => { const b = e.target.closest('[data-p]'); if (!b) return; "
              "e.dataTransfer.setData('text/plain', b.dataset.p + '|' + b.dataset.z); e.dataTransfer.effectAllowed = 'move'; "
              "document.body.classList.add('m-zieht'); }")
        el.on("dragover", js_handler="(e) => { if (!document.body.classList.contains('m-zieht')) return; "
              "const z = e.target.closest('[data-zd]'); if (!z) return; e.preventDefault(); "
              f"if (!z.classList.contains('ziel')) {{ {_ZIEL_WEG}; z.classList.add('ziel'); }} }}")
        el.on("dragend", js_handler=f"(e) => {{ document.body.classList.remove('m-zieht'); {_ZIEL_WEG}; }}")
        el.on("drop", lambda e: _gezogen(a, e.args), js_handler="(e) => { const z = e.target.closest('[data-zd]'); "
              "const d = (e.dataTransfer.getData('text/plain') || '').split('|'); e.preventDefault(); "
              f"document.body.classList.remove('m-zieht'); {_ZIEL_WEG}; "
              "if (z && d[0] && d[1] !== z.dataset.zd) emit({p: d[0], z: z.dataset.zd}); }")


async def _gezogen(a, args) -> None:
    if not isinstance(args, dict) or not args.get("p") or not args.get("z"):
        return
    w = await run.io_bound(zk.wechsel_pruefen, args["p"], args["z"])
    if w.fehler:
        a.toast(f"Zimmerwechsel nicht möglich: {w.fehler}", fehler=True, rueck=False)
        return

    def bauen():
        ui.label(f"{w.name} ({w.zeitraum})").classes("m-name")
        with ui.element("div").classes("m-wechsel"):
            ui.label(w.vorher).classes("m-pille neutral")
            ui.icon("arrow_forward")
            ui.label(w.nach_kurz).classes("m-pille ok")
        ui.label(f"{w.vorher} wird dafür frei.").classes("m-ptext")
        if w.war_fest:
            ui.label("Die Planung war „fest“ – im neuen Zimmer gilt sie wieder als geplant.").classes("m-ptext")
        if w.hinweis:
            ui.label(f"Achtung – Ausnahme: {w.hinweis}").classes("m-ptext").style("color:var(--orange)")
        if w.partner:
            ui.label(f"DZ-Partner laut Liste: {', '.join(n for _, n in w.partner)}."
                     + ("" if w.partner_passt else " Für beide ist dort kein Platz.")).classes("m-ptext")
        ui.label("Danach im Belegungssystem umbuchen (steht unter Anreisen → Firmenprogramm).").classes("m-zweite")

        async def los(mit: bool):
            if await a.aendern(zk.wechseln, w.person, w.nach, mit):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            if w.partner and w.partner_passt:
                knopf("Beide wechseln", lambda: los(True), "primaer", "check")
                knopf(f"Nur {w.name.split(',')[0]}", lambda: los(False), "", "person")
            else:
                knopf("Zimmer wechseln", lambda: los(False), "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Zimmer wechseln", bauen)


def _filterleiste(a, ansicht: str) -> None:
    """Gemeinsame Such- und Filterleiste für Karten und Liste (wie „Zimmer finden“ im bisherigen Programm)."""
    with a.werkzeuge:
        segmente({"": "Alle Häuser", **{h: f"Haus {h}" for h in ("2", "3.1", "3.2", "3.3", "6")}}, a.zl_haus,
                 lambda h: a.setzen(zl_haus=h))
    n = a.daten["n"]
    with a.leiste:
        suche = ui.input(placeholder="Zimmer, Name, Hinweis …", value=a.zl_text).classes("m-feld m-sucheingabe").props(
            "dense outlined dark clearable")
        suche.on("keydown.enter", lambda: a.setzen(zl_text=suche.value or ""))
        suche.on("clear", lambda: a.setzen(zl_text=""))
        segmente({s: (t if not s else f"{t} {n.get(s, 0)}") for s, t in zk.STATUS.items()}, a.zl_status,
                 lambda s: a.setzen(zl_status=s))
        with ui.element("div").classes("m-segm").props('role="group"'):
            for k, text in zk.MERKMALE.items():
                an = k in a.zl_schnell
                b = ui.element("button").classes("an" if an else "")
                attr(b, aria_pressed=str(an).lower())
                with b:
                    ui.label(text)
                b.on("click", lambda k=k: a.setzen(zl_schnell=a.zl_schnell ^ {k}))
        _filter_menue(a)
        if a.zl_schnell or a.zl_status or a.zl_text or zk.mehr_aktiv(a.zl_mehr):
            knopf("Zurücksetzen", lambda: a.setzen(zl_schnell=set(), zl_status="", zl_text="", zl_mehr={}), "leise", "close")
    with a.leiste:
        tag = ui.input(value=a.zu_tag.isoformat()).classes("m-feld").props("dense outlined dark type=date").style("width:160px")
        attr(tag, title="Stichtag – Status und Bewohner an diesem Tag")
        tag.on_value_change(lambda e: a.setzen(zu_tag=date.fromisoformat(e.value)) if e.value else None)
        if a.zu_tag != a.heute:
            knopf("Heute", lambda: a.setzen(zu_tag=a.heute), "leise")
        ui.label(a.daten["kpi"]).classes("m-kpi m-mono")
        with knopf("Drucken & Export", None, "", "print").style("margin-left:auto"):
            with ui.menu().props('dark class="m-menue"'):
                ui.menu_item("Zimmerliste drucken (mit Bewohnern)", lambda: _drucken(a, "liste"))
                ui.menu_item("Zimmerliste drucken (ohne Namen)", lambda: _drucken(a, "liste_ohne"))
                ui.menu_item("Als Excel – diese Auswahl mit „frei bis“", lambda: _auswahl_excel(a, True))
                ui.menu_item("Als Excel – ohne Namen", lambda: _auswahl_excel(a, False))
                ui.separator()
                ui.menu_item("Kopieren (für Excel)", lambda: _kopieren(a))
                ui.menu_item("Belegung am Tag als Excel …", lambda: _excel(a))
                ui.separator()
                ui.menu_item("FM-Mängelbericht drucken", lambda: _drucken(a, "fm"))
        if ansicht == "liste":
            with knopf("Bearbeiten", None, "", "edit"):
                with ui.menu().props('dark class="m-menue"'):
                    ui.menu_item("Eigenschaften der markierten Zimmer …", lambda: _eigenschaften_panel(a))
                    ui.menu_item("Renovierungsliste einfügen …", lambda: _renovierungen_panel(a))


def _filter_menue(a) -> None:
    """Seltenere Filter – Boden, Mangel, Renovierung, Gäste/Bad über Flur, Personengruppe, außer Betrieb."""
    m = {**zk.MEHR_LEER, **a.zl_mehr}
    opt = zk.filter_optionen(a.heute)
    n = zk.mehr_aktiv(a.zl_mehr)

    def umschalten(art: str, wert: str):
        return a.setzen(zl_mehr={**m, art: sorted(set(m[art]) ^ {wert})})

    def setzen(art: str, wert):
        return a.setzen(zl_mehr={**m, art: wert})

    def eintrag(text: str, an: bool, fn):
        with ui.menu_item(on_click=fn, auto_close=False).classes("m-mpunkt"):
            ui.icon("check_box" if an else "check_box_outline_blank").classes("m-mhaken" + (" an" if an else ""))
            ui.label(text)

    with knopf(f"Filter · {n}" if n else "Filter", None, "akzent" if n else "", "filter_list"):
        with ui.menu().props('dark class="m-menue"').style("max-height:70vh"):
            ui.label("Boden").classes("m-mgruppe")
            for k, t in opt["boeden"].items():
                eintrag(t, k in m["boeden"], lambda k=k: umschalten("boeden", k))
            ui.label("Mangel").classes("m-mgruppe")
            for k, t in opt["maengel"].items():
                eintrag(t, k in m["maengel"], lambda k=k: umschalten("maengel", k))
            ui.label("Renovierung").classes("m-mgruppe")
            for k, t in opt["renoviert"].items():
                eintrag(t, m["renoviert"] == k, lambda k=k: setzen("renoviert", k))
            ui.label("Merkmale").classes("m-mgruppe")
            for k, t in opt["merkmale"].items():
                eintrag(t, k in m["merkmale"], lambda k=k: umschalten("merkmale", k))
            ui.label("Personengruppe").classes("m-mgruppe")
            for k, t in opt["modus"].items():
                eintrag(t, m["modus"] == k, lambda k=k: setzen("modus", k))
            for k, t in opt["gruppen"].items():
                eintrag(t, k in m["gruppen"], lambda k=k: umschalten("gruppen", k))
            ui.separator()
            eintrag("Auch Zimmer außer Betrieb (Lager, Jugendhilfe …)", bool(m["alle"]), lambda: setzen("alle", not m["alle"]))


def _mangel_menue(a) -> None:
    """Filter nach Mangelart/-stufe. Derselbe Zustand wie „Filter → Mangel“ in Karten und Liste – die Auswahl gilt also
    in allen Zimmer-Ansichten."""
    gewaehlt = list(a.zl_mehr.get("maengel") or [])
    opt = zk.filter_optionen(a.heute)["maengel"]

    def umschalten(k: str):
        return a.setzen(zl_mehr={**a.zl_mehr, "maengel": sorted(set(gewaehlt) ^ {k})}, laden=False)

    titel = "Mangelart" + (f" · {len(gewaehlt)}" if gewaehlt else "")
    with knopf(titel, None, "akzent" if gewaehlt else "", "construction"):
        with ui.menu().props('dark class="m-menue"').style("max-height:70vh"):
            ui.label("Stufe").classes("m-mgruppe")
            for k, t in opt.items():
                if k == next((x for x in opt if not x.startswith("stufe:")), None):
                    ui.label("Mangelart").classes("m-mgruppe")
                an = k in gewaehlt
                with ui.menu_item(on_click=lambda k=k: umschalten(k), auto_close=False).classes("m-mpunkt"):
                    ui.icon("check_box" if an else "check_box_outline_blank").classes("m-mhaken" + (" an" if an else ""))
                    ui.label(t)
            if gewaehlt:
                ui.separator()
                ui.menu_item("Mangelart-Filter aufheben", lambda: a.setzen(zl_mehr={**a.zl_mehr, "maengel": []}, laden=False))


def _liste(a) -> None:
    _filterleiste(a, "liste")
    zs = a.daten["zeilen"]
    sichtbar = {z.zimmer for z in zs}
    a.zk_auswahl &= sichtbar
    spalten = ("34px 104px 76px minmax(110px, .9fr) 90px minmax(80px, .6fr) minmax(90px, .7fr) minmax(160px, 1.6fr) "
               "minmax(120px, 1.2fr)")
    with a.inhalt:
        if not zs:
            leer("Keine Zimmer mit diesen Filtern – Filter lockern oder „Zurücksetzen“.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{spalten}"):
            alle = ui.checkbox(value=bool(zs) and a.zk_auswahl == sichtbar).props("dense dark size=xs")
            attr(alle, title="Alle markieren (für „Bearbeiten“)")
            for t in ("Zustand", "Zimmer", "Lage", "Merkmale", "Renoviert", "Boden", "Am Tag", "Mängel / Hinweis"):
                ui.label(t)
        boxen = []
        for r in zs:
            stufe = {0: "", 1: "warn", 2: "warn", 3: "krit"}[r.stufe]
            z = ui.element("div").classes("m-raster m-zeile m-klick").style(f"grid-template-columns:{spalten}")
            with z:
                cb = ui.checkbox(value=r.zimmer in a.zk_auswahl).props("dense dark size=xs")
                cb.on_value_change(lambda e, zid=r.zimmer: a.zk_auswahl.add(zid) if e.value else a.zk_auswahl.discard(zid))
                boxen.append(cb)
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
            z.on("click", lambda e, r=r: karte_oeffnen(a, r.zimmer),
                 js_handler="(e) => { if (!e.target.closest('.q-checkbox')) emit(); }")

        def alle_umschalten(e):
            a.zk_auswahl.clear()
            if e.value:
                a.zk_auswahl.update(sichtbar)
            for cb in boxen:
                cb.set_value(e.value)
        alle.on_value_change(alle_umschalten)


def _karten(a) -> None:
    """Je Haus und Etage eine Spalte, je Zimmer eine Karte mit Zustand, Merkmalen, Mängeln und Bewohnern."""
    _filterleiste(a, "karten")
    haeuser = a.daten["haeuser"]
    with a.inhalt:
        if a.daten["hinweis"]:
            ui.label(a.daten["hinweis"]).classes("m-hinweisbox")
        if not haeuser:
            leer("Keine Zimmer mit diesen Filtern – Filter lockern oder „Zurücksetzen“.")
            return
        for h in haeuser:
            with ui.element("section").classes("m-khaus"):
                with ui.element("div").classes("m-khaus-kopf"):
                    ui.icon("apartment")
                    ui.label(f"Haus {h.haus}").classes("m-btitel")
                    ui.label(h.unter).classes("m-kpi m-mono")
                with ui.element("div").classes("m-ketagen"):
                    for e in h.etagen:
                        with ui.element("div").classes("m-ketage"):
                            with ui.element("div").classes("m-ketage-kopf"):
                                ui.label(e.titel).classes("m-name")
                                ui.label(e.unter).classes("m-zweite")
                            for k in e.karten:
                                _zkarte(a, k)


def _zkarte(a, k) -> None:
    kl = "m-zkarte" + (" unbew" if k.unbewohnbar else "")
    el = ui.element("button").classes(kl)
    attr(el, title=f"Zimmer {k.kurz} – Klick: Zimmerkarte")
    with el:
        with ui.element("div").classes("m-zk-kopf"):
            ui.label(k.kurz).classes("m-zk-nr m-mono")
            ui.label(f"{k.betten} Bett{'en' if k.betten > 1 else ''}").classes("m-zweite")
            with ui.element("span").style("margin-left:auto"):
                badge(k.status)
        if k.merkmale:
            ui.label(k.merkmale).classes("m-zweite")
        if k.maengel:
            with ui.element("div").classes("m-zk-mangel " + ("krit" if k.stufe == 3 else "warn" if k.stufe == 2 else "")):
                ui.icon("priority_high")
                ui.label(k.maengel)
        for b in k.belegungen:
            with ui.element("div").classes(f"m-zk-bel {b.art}"):
                ui.icon({"gesperrt": "block", "geplant": "schedule"}.get(b.art, "person"))
                with ui.element("div"):
                    ui.label(b.titel).classes("m-zk-name")
                    ui.label(b.zeit + (" · geplant" if b.art == "geplant" else "")).classes("m-zweite m-mono")
        if k.frei_bis:
            ui.label(k.frei_bis).classes("m-zweite").style("color:var(--gruen)")
    el.on("click", lambda k=k: karte_oeffnen(a, k.zimmer))


async def _kopieren(a) -> None:
    import json

    f = zk.filter_bauen(a.zl_haus, a.zl_status, a.zl_schnell, a.zl_text, a.zl_mehr)
    text, n = await run.io_bound(zk.liste_tsv, a.stand, f, a.zu_tag)
    ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(text)})")
    a.toast(f"{n} Zimmer kopiert – in Excel einfügen (Strg+V)", rueck=False)


async def _excel(a) -> None:
    try:
        text, pfad = await run.io_bound(zk.belegung_excel, a.stand, a.zu_tag)
    except PermissionError:
        a.toast("Die Datei ist noch geöffnet – bitte in Excel schließen und erneut versuchen.", fehler=True)
        return
    except Exception as exc:                # noqa: BLE001
        a.toast(f"Nicht gespeichert: {exc}", fehler=True)
        return
    a.toast(text if seiten._datei_oeffnen(str(pfad)) else f"{text} – {pfad}", rueck=False)


def _eigenschaften_panel(a) -> None:
    from .kern import kurz

    gewaehlt = sorted(a.zk_auswahl)
    if not gewaehlt:
        a.toast("Bitte zuerst in der Liste Zimmer markieren (Kästchen links).", fehler=True)
        return
    namen = ", ".join(kurz(z) for z in gewaehlt[:12])

    def bauen():
        ui.label(f"{len(gewaehlt)} Zimmer: {namen}" + (" …" if len(gewaehlt) > 12 else "")).classes("m-ptext")
        reno = ui.select({"gleich": "Renovierung: nicht ändern", "datum": "renoviert am …", "entfernen": "Renovierung entfernen"},
                         value="gleich").classes("m-feld").props('dense outlined dark popup-content-class="m-popup"')
        datum = ui.input("Renoviert am", value=a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
        datum.bind_visibility_from(reno, "value", value="datum")
        boden = ui.select({"-": "Boden: nicht ändern", **{b: b for b in zk.boeden()}, "": "Boden entfernen (unbekannt)"},
                          value="-").classes("m-feld").props('dense outlined dark popup-content-class="m-popup"')
        vermutet = ui.checkbox("nur vermutet („ziemlich sicher“)").props("dark dense")

        async def speichern():
            d = date.fromisoformat(datum.value) if reno.value == "datum" and datum.value else None
            if await a.aendern(zk.eigenschaften_setzen, gewaehlt, reno.value, d,
                               None if boden.value == "-" else boden.value, vermutet.value):
                a.zk_auswahl.clear()
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Eigenschaften setzen", bauen)


def _renovierungen_panel(a) -> None:
    def bauen():
        ui.label("In Excel die Spalten Haus, Zimmer, (Notiz,) Datum markieren, kopieren (Strg+C) und hier einfügen "
                 "(Strg+V). Es gilt das neuere Datum; ein sicher eingetragener Boden bleibt.").classes("m-ptext")
        text = ui.textarea(placeholder="3.1\tE20\t\t27.09.2019\n2\t402\tfertigstellung\t07.01.2026").classes(
            "m-feld").props("outlined dark autogrow").style("min-height:180px")
        info = ui.label("").classes("m-zweite")
        boden = ui.select({"": "Boden nicht setzen", **{b: f"Boden: {b}" for b in zk.boeden()}}, value=zk.boeden()[0]
                          ).classes("m-feld").props('dense outlined dark popup-content-class="m-popup"')
        vermutet = ui.checkbox("nur vermutet („ziemlich sicher“)", value=True).props("dark dense")

        async def pruefen():
            n, fehler = await run.io_bound(zk.renovierungen_pruefen, a.stand, text.value or "")
            info.text = f"{n} Zimmer erkannt" + (f" · nicht zugeordnet: {', '.join(fehler[:6])}" if fehler else "")
        text.on("blur", pruefen)

        async def uebernehmen():
            if await a.aendern(zk.renovierungen_uebernehmen, text.value or "", boden.value, vermutet.value):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Übernehmen", uebernehmen, "primaer", "check")
            knopf("Prüfen", pruefen, "leise", "fact_check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Renovierungsliste einfügen", bauen, breit=True)


async def _drucken(a, art: str) -> None:
    if art == "fm":
        text = await run.io_bound(zk.fm_bericht)
        name = "Maengelbericht"
    else:
        f, kachel, mf = _auswahl(a, art.startswith("kachel"))
        namen = not art.endswith("_ohne")
        zeilen = await run.io_bound(zk.druck_zeilen, a.stand, a.zu_tag, f, kachel, namen, mf)
        text = zk.druck_html(zeilen, a.zu_tag, f, kachel, namen, mf)
        name = "Zimmerliste"
    seiten.html_drucken(a, text, name)


def _auswahl(a, kachel: bool):
    """(Filter, Kacheln, Mangelart) der sichtbaren Auswahl – Übersicht: die angeklickten Kacheln und die Mangelart,
    Liste/Karten: die Filterleiste (dort steckt die Mangelart schon im Filter)."""
    if kachel:
        return None, zk.kacheln(a.zu_filter), list(a.zl_mehr.get("maengel") or [])
    return zk.filter_bauen(a.zl_haus, a.zl_status, a.zl_schnell, a.zl_text, a.zl_mehr), None, None


async def _auswahl_excel(a, namen: bool, kachel: bool = False) -> None:
    f, k, mf = _auswahl(a, kachel)
    try:
        zeilen = await run.io_bound(zk.druck_zeilen, a.stand, a.zu_tag, f, k, namen, mf)
        text, pfad = await run.io_bound(zk.druck_excel, zeilen, a.zu_tag, f, k, namen, mf)
    except PermissionError:
        a.toast("Die Datei ist noch geöffnet – bitte in Excel schließen und erneut versuchen.", fehler=True)
        return
    except Exception as exc:                # noqa: BLE001
        a.toast(f"Nicht gespeichert: {exc}", fehler=True)
        return
    a.toast(text if seiten._datei_oeffnen(str(pfad)) else f"{text} – {pfad}", rueck=False)


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
    with ui.element("div").classes("m-ktitelzeile"):
        ui.label("Bewohner").classes("m-ktitel")
        knopf("Person hinzufügen", lambda: person_hinzu_panel(a, k), "primaer", "person_add")
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
    f = zk.kacheln(a.zu_filter)
    mf = a.zl_mehr.get("maengel") or []
    with a.leiste:
        unbew = sum(1 for k in alle if k.unbewohnbar)
        unfertig = sum(1 for k in alle if k.nicht_fertig)
        # Die Kacheln sind zugleich die Legende: gleiche Symbole und Farben wie die Zimmer darunter
        kennzahlen([("frei", n["frei"] + n["teilweise"], "frei" + (f" · davon {n['teilweise']} mit 1 Bett" if n["teilweise"] else ""), "ok"),
                    ("unfertig", unfertig, "nicht bezugsfertig", "warn"),
                    ("belegt", n["belegt"], "belegt", "blau"), ("geplant", n["geplant"], "geplant", "akzent"),
                    ("gesperrt", n["gesperrt"], "gesperrt", "neutral"), ("maengel", defekt, "mit Mängeln", "warn"),
                    ("unbewohnbar", unbew, "unbewohnbar", "krit")], f,
                   lambda k: a.setzen(zu_filter=f ^ {k}, laden=False),
                   {k: t + " – Klick: dazunehmen/wegnehmen (mehrere möglich)" for k, t in {
                       "frei": f"Mindestens ein Bett frei: {n['frei']} ganz leer, {n['teilweise']} Doppelzimmer mit einem freien "
                               "Bett (grün umrandet)",
                       "belegt": "Alle Betten belegt (blau)", "geplant": "Nur geplant, noch nicht eingezogen (violett)",
                       "gesperrt": "Gesperrt (gestreift)", "maengel": "Offene Mängel (Marke „!“ an der Kachel)",
                       "unbewohnbar": "Wegen eines Mangels nicht bewohnbar (roter Rahmen)",
                       "unfertig": "Frei, aber noch nicht bezugsfertig: Reinigung bis zu diesem Tag offen oder dringender "
                                   "Mangel (Besen an der Kachel)"}.items()})
        _mangel_menue(a)
        if f or mf:
            knopf("Zurücksetzen", lambda: a.setzen(zu_filter=frozenset(), zl_mehr={**a.zl_mehr, "maengel": []}, laden=False),
                  "leise", "close")
        ui.label(f"am {a.zu_tag:%d.%m.%Y}").classes("m-kpi")
        knopf("", lambda: a.setzen(zu_tag=a.zu_tag - timedelta(days=1)), "leise", "chevron_left", "Tag zurück")
        knopf("Heute", lambda: a.setzen(zu_tag=a.heute), "leise")
        knopf("", lambda: a.setzen(zu_tag=a.zu_tag + timedelta(days=1)), "leise", "chevron_right", "Tag weiter")
        tag = ui.input(value=a.zu_tag.isoformat()).classes("m-feld").props("dense outlined dark type=date").style("width:160px")
        tag.on_value_change(lambda e: a.setzen(zu_tag=date.fromisoformat(e.value)) if e.value else None)
        with knopf("Drucken & Export", None, "", "print").style("margin-left:auto"):
            with ui.menu().props('dark class="m-menue"'):
                was = f"nur „{zk.kachel_text(f, mf)}“" if f or mf else "alle Zimmer"
                ui.menu_item(f"Drucken – {was} (mit Bewohnern)", lambda: _drucken(a, "kachel"))
                ui.menu_item(f"Drucken – {was} (ohne Namen)", lambda: _drucken(a, "kachel_ohne"))
                ui.menu_item(f"Als Excel – {was} mit „frei bis“", lambda: _auswahl_excel(a, True, kachel=True))
                ui.menu_item("Als Excel – ohne Namen", lambda: _auswahl_excel(a, False, kachel=True))
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
                                    passt = zk.kachel_passt(k.status, k.stufe, k.unbewohnbar, k.arten, f, mf, bool(k.nicht_fertig))
                                    kl = f"m-kachel {k.status}" + (" unbew" if k.unbewohnbar else "") + ("" if passt else " aus")
                                    b = ui.element("button").classes(kl)
                                    attr(b, title=k.titel)
                                    with b:
                                        ui.label(k.nr)
                                        if k.stufe:
                                            ui.label("!" * k.stufe).classes("m-kachel-m")
                                        if k.nicht_fertig:
                                            ui.icon("cleaning_services").classes("m-kachel-u")
                                    b.on("click", lambda k=k: karte_oeffnen(a, k.zimmer))


def _maengel(a) -> None:
    zs: list[zk.MZeile] = a.daten
    mf = a.zl_mehr.get("maengel") or []
    with a.leiste:
        n = {st: sum(1 for z in zs if z.stufe == st) for st in (3, 2, 1)}
        kennzahlen([(3, n[3], "nicht bewohnbar", "krit"), (2, n[2], "dringend", "warn"), (1, n[1], "leicht", "neutral")],
                   a.dz_filter, lambda k: a.setzen(dz_filter=None if k == a.dz_filter else k, laden=False))
        ui.label(f"{sum(len(z.maengel) for z in zs)} offene Mängel").classes("m-kpi")
        _mangel_menue(a)
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
        if mf and not any(zk.mangel_passt(z.stufe, {m[0] for m in z.maengel}, mf) for z in zs):
            leer("Kein Zimmer mit dieser Mangelart – Auswahl unter „Mangelart“ ändern.")
        for st, titel in zk.STUFEN.items():
            gruppe = [z for z in zs if z.stufe == st and (a.dz_filter is None or a.dz_filter == st)
                      and zk.mangel_passt(z.stufe, {m[0] for m in z.maengel}, mf)]
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


# =======================================================================================
# Person in dieses Zimmer: aus den Anreisen ohne Zimmer wählen oder neu anlegen
# =======================================================================================

GESCHLECHT = {"": "unbekannt", "m": "männlich", "w": "weiblich", "d": "divers"}


async def person_hinzu_panel(a, k: zk.Karte) -> None:
    kandidaten = await run.io_bound(zk.kandidaten, a.stand, k.zimmer, a.heute)

    def bauen():
        knopf("Zurück zur Zimmerkarte", lambda: karte_oeffnen(a, k.zimmer), "leise", "arrow_back")
        if kandidaten:
            ui.label("Aus den Anreisen – noch ohne Zimmer").classes("m-ktitel")
            ui.label("Diese Personen dürfen hier wohnen und das Zimmer ist in ihrem Zeitraum frei.").classes("m-ptext")
            for c in kandidaten[:12]:
                with ui.element("div").classes("m-kandidat"):
                    with ui.element("div"):
                        with ui.element("div").classes("m-namezeile"):
                            ui.label(c.name).classes("m-name")
                            if c.schluessel in a.neu:
                                from .ui_bausteine import badge_neu

                                badge_neu(a.neu[c.schluessel])
                        ui.label(f"{c.zweite} · {c.zeit}" + (" · passt am besten" if c.vorschlag else "")).classes("m-zweite")
                    knopf("Hier einziehen", lambda c=c: _nach(a, _zuweisen, c.schluessel, k.zimmer, zimmer=k.zimmer),
                          "gruen" if c.vorschlag else "", "login")
            if len(kandidaten) > 12:
                ui.label(f"… und {len(kandidaten) - 12} weitere – unter Anreisen → Zuteilen.").classes("m-zweite")
        ui.label("Neue Person anlegen").classes("m-ktitel")
        ui.label("Für Nachmeldungen, Gäste oder Mieter: die Person wird angelegt und gleich in dieses Zimmer geplant "
                 "(Rückgängig nimmt beides zurück).").classes("m-ptext")
        name = ui.input("Name (Nachname, Vorname)").classes("m-feld").props("dense outlined dark autofocus")
        gr = ui.select(zk.GRUPPEN_NEU, value="Reha", label="Gruppe").classes("m-feld").props(
            'dense outlined dark popup-content-class="m-popup"')
        attr(gr, title="Bestimmt, welche Zimmer erlaubt sind (z. B. Gast nur Gästezimmer, Mieter nur Haus 6)")
        with ui.element("div").classes("m-zweispaltig"):
            von = ui.input("Anreise", value=a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
            bis = ui.input("Abreise", value=(a.heute + timedelta(days=28)).isoformat()).classes("m-feld").props(
                "dense outlined dark type=date")
        with ui.element("div").classes("m-zweispaltig"):
            ge = ui.select(GESCHLECHT, value="", label="Geschlecht").classes("m-feld").props(
                'dense outlined dark popup-content-class="m-popup"')
            tier = ui.checkbox("kommt mit Tier").props("dark dense")
        bem = ui.input("Bemerkung (optional)", placeholder="z. B. Maßnahme FIAE, Hospitation, barrierefrei").classes(
            "m-feld").props("dense outlined dark")
        tn = ui.input("TN-ID (optional)").classes("m-feld").props("dense outlined dark")

        async def speichern():
            try:
                d_von, d_bis = date.fromisoformat(von.value), date.fromisoformat(bis.value)
            except (TypeError, ValueError):
                a.toast("Bitte An- und Abreise wählen.", fehler=True)
                return
            if await a.aendern(zk.person_ins_zimmer, k.zimmer, name.value or "", "", gr.value or "",
                               d_von, d_bis, ge.value or "", bool(tier.value), bem.value or "", tn.value or ""):
                await karte_oeffnen(a, k.zimmer)

        with ui.element("div").classes("m-paktionen"):
            knopf(f"Anlegen und in {k.kurz} einplanen", speichern, "primaer", "person_add")
            knopf("Abbrechen", lambda: karte_oeffnen(a, k.zimmer), "leise")

    a.panel(f"Person in Zimmer {k.kurz}", bauen, breit=True)


def _zuweisen(schluessel: str, zimmer: str) -> str:
    from . import kern

    return kern.zuweisen(schluessel, zimmer)

