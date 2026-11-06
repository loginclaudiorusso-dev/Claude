"""Seite „Anreisen“ – Zusätze zum Zuteilen (das baut ``oberflaeche``): Ansichten Abreisen und Firmenprogramm,
Menü „Mehr“ (Drucken, Person hinzufügen, Planung zurücknehmen, Optimieren, UWT) und die Personenangaben im Panel."""

from __future__ import annotations

import json
from datetime import date

from nicegui import run, ui

from . import anreisen_kern as ank
from . import seiten
from .ui_bausteine import attr, badge, badge_neu, kennzahlen, knopf, leer, segmente

ANSICHTEN = {"zuteilen": "Zuteilen", "personen": "Personen", "abreisen": "Abreisen", "eintragen": "Firmenprogramm"}


def daten(a) -> None:
    """Daten der Ansichten Abreisen/Firmenprogramm (Zuteilen lädt ``oberflaeche`` selbst)."""
    ansicht = a.ansicht_von("anreisen", "zuteilen")
    if ansicht == "abreisen":
        von, bis = ank.zeitraum(a.ab_zeitraum, a.heute)
        a.daten = {"zeilen": ank.abreisen(a.stand, von, bis), "von": von, "bis": bis}
    elif ansicht == "eintragen":
        a.daten = {"zeilen": ank.eintragen_liste(a.stand, a.heute, a.ein_tage)}
    elif ansicht == "personen":
        a.daten = {"zeilen": ank.personen_liste(a.stand, a.heute, a.neu)}


def werkzeuge(a) -> None:
    ansicht = a.ansicht_von("anreisen", "zuteilen")
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("anreisen", ansicht=v), ansicht=True)


def mehr_menue(a) -> None:
    """„Mehr“ im Kopf der Ansicht Zuteilen – seltene Aktionen gebündelt statt vieler Knöpfe."""
    with a.werkzeuge:
        with knopf("Mehr", None, "leise m-kz-mehr", "more_horiz"):
            with ui.menu().props('dark class="m-menue"'):
                ui.menu_item("Anreiseliste drucken", lambda: _drucken(a, "anreise"))
                ui.menu_item("Schlüsselliste drucken", lambda: _drucken(a, "schluessel"))
                ui.menu_item("Zimmerschilder drucken", lambda: _drucken(a, "schilder"))
                ui.menu_item("Zimmerliste als Excel …", lambda: _excel(a))
                ui.separator()
                ui.menu_item("Vergangene Anreisen ausblenden" if a.zu_vergangene else "Auch vergangene Anreisen zeigen (12 Monate)",
                             lambda: a.setzen(zu_vergangene=not a.zu_vergangene))
                ui.menu_item("Archiv: frühere Anreisen suchen …", lambda: archiv_panel(a))
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
        segmente({False: "Abgehakte ausblenden", True: "Alle zeigen"}, a.ein_alle, lambda x: a.setzen(ein_alle=x, laden=False))
        if offen:
            knopf("Abtipp-Modus" if not a.ein_abtipp else "Abtipp-Modus beenden",
                  lambda: _abtipp_umschalten(a, not a.ein_abtipp), "primaer" if not a.ein_abtipp else "",
                  "view_sidebar", "Einen Eintrag nach dem anderen – je Feld ein Kopierknopf, danach „Eingetragen – nächster“")
            knopf("Offene kopieren", lambda: _kopieren(a), "gruen", "content_copy")
            knopf("Alle als eingetragen markieren", lambda: a.aendern(ank.eintragen_setzen, [z.schluessel for z in offen],
                                                                       True, a.heute, a.ein_tage), "", "done_all")
    if a.ein_abtipp and offen:
        _abtipp(a, offen)
        return
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
        for z in (zs if a.ein_alle else offen):
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


# ---- 0.55: Abtipp-Modus ------------------------------------------------------------------
# Ins Belegungssystem des Trägers muss jede Planung von Hand übertragen werden. Statt zwischen zwei großen Fenstern die
# Zeile zu suchen: ein Eintrag groß, je Feld ein Kopierknopf, „Eingetragen – nächster“. Im eigenen Fenster lässt sich
# INNternat dafür zu einem schmalen Streifen am rechten Rand machen, der im Vordergrund bleibt.

SCHMAL_BREITE = 380


async def _abtipp_umschalten(a, an: bool) -> None:
    if not an:
        await _schmal(a, False)
    await a.setzen(ein_abtipp=an, ein_pos=0, laden=False)


def _abtipp(a, offen: list) -> None:
    pos = min(max(0, a.ein_pos), len(offen) - 1)
    z = offen[pos]
    with a.inhalt, ui.element("section").classes("m-abtipp"):
        with ui.element("div").classes("m-abtipp-kopf"):
            ui.label(f"Eintrag {pos + 1} von {len(offen)}").classes("m-btitel")
            knopf("", lambda: _schmal(a, not getattr(a, "ein_schmal", False)), "leise",
                  "close_fullscreen" if not getattr(a, "ein_schmal", False) else "open_in_full",
                  "Schmal am rechten Rand und im Vordergrund (nur im eigenen Fenster)" if not getattr(a, "ein_schmal", False)
                  else "Wieder normale Fenstergröße")
        nr = 0
        for titel, wert in z.felder():
            nr += bool(wert)
            with ui.element("div").classes("m-abtipp-feld"):
                ui.label(f"{nr} · {titel}" if wert else titel).classes("m-zweite")
                ui.label(wert or "–").classes("m-abtipp-wert")
                if wert:
                    knopf("", lambda w=wert, t=titel: _feld_kopieren(a, t, w), "leise", "content_copy", f"{titel} kopieren")
        with ui.element("div").classes("m-abtipp-knoepfe"):
            knopf("", lambda: a.setzen(ein_pos=max(0, pos - 1), laden=False), "leise", "chevron_left", "Vorheriger (←)")
            knopf("Überspringen", lambda: a.setzen(ein_pos=(pos + 1) % len(offen), laden=False), "leise", "skip_next",
                  "Überspringen (N oder →)")
            knopf("Eingetragen – nächster", lambda: _eingetragen(a, z, pos), "primaer", "done", "Eingetragen (E)")
        # 0.58: Ein-Tasten-Kürzel – E eingetragen, N/→ überspringen, ← zurück, 1–6 Feld kopieren
        felder = [(t, w) for t, w in z.felder() if w]
        tasten = {"e": lambda: _eingetragen(a, z, pos), "n": lambda: a.setzen(ein_pos=(pos + 1) % len(offen), laden=False),
                  "arrowright": lambda: a.setzen(ein_pos=(pos + 1) % len(offen), laden=False),
                  "arrowleft": lambda: a.setzen(ein_pos=max(0, pos - 1), laden=False)}
        for i, (t, w) in enumerate(felder[:9], 1):
            tasten[str(i)] = lambda t=t, w=w: _feld_kopieren(a, t, w)
        a.tasten = (lambda: a.seite == "anreisen" and a.ein_abtipp, tasten)
        ui.label("Tasten: 1–" + str(min(9, len(felder))) + " Feld kopieren · E eingetragen · N oder → überspringen · "
                 "← zurück").classes("m-tasten-hinweis")
        ui.label("Tipp: Felder nacheinander kopieren und im Belegungssystem einfügen. „Eingetragen“ hakt den Eintrag ab "
                 "(Rückgängig wie immer).").classes("m-zweite").style("white-space: normal")


async def _feld_kopieren(a, titel: str, wert: str) -> None:
    ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(wert)})")
    a.toast(f"{titel} kopiert: {wert}", rueck=False, dauer=2)


async def _eingetragen(a, z, pos: int) -> None:
    if await a.aendern(ank.eintragen_setzen, [z.schluessel], True, a.heute, a.ein_tage):
        a.ein_pos = pos                        # die Liste rückt nach – an derselben Stelle steht der nächste
        a.zeichnen()


async def _schmal(a, an: bool) -> None:
    """Eigenes Fenster (pywebview): schmaler Streifen rechts, im Vordergrund – und zurück. Im Browser nur die Ansicht."""
    from nicegui import app

    fenster = getattr(app.native, "main_window", None)
    a.ein_schmal = an
    a.body.classes(add="abtipp-schmal") if an else a.body.classes(remove="abtipp-schmal")
    if fenster is not None:
        try:
            if an:
                a.ein_fenster_vorher = (await fenster.get_size(), await fenster.get_position())
                breite = int(await ui.run_javascript("screen.availWidth", timeout=3) or 1366)
                hoehe = int(await ui.run_javascript("screen.availHeight", timeout=3) or 800)
                fenster.resize(SCHMAL_BREITE, hoehe)
                fenster.move(max(0, breite - SCHMAL_BREITE), 0)
                fenster.set_always_on_top(True)
            elif getattr(a, "ein_fenster_vorher", None):
                (w, h), (x, y) = a.ein_fenster_vorher
                fenster.set_always_on_top(False)
                fenster.resize(w, h)
                fenster.move(x, y)
        except Exception:                      # noqa: BLE001 – ohne Fensterfunktionen bleibt es bei der Ansicht
            pass
    a.zeichnen()


async def _kopieren(a) -> None:
    text = await run.io_bound(ank.eintragen_text, a.stand, a.heute, a.ein_tage)
    ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(text)})")
    a.toast(f"{text.count(chr(10)) + 1 if text else 0} Zeilen kopiert", rueck=False)


# ---- Personen im Panel ------------------------------------------------------------------

def _zimmer_pruefen(a, schluessel: str) -> None:
    """Bestimmtes Zimmer prüfen: warum steht es nicht in der Auswahl – und von Hand trotzdem zuweisen, wenn es geht."""
    from . import kern

    ui.label("Bestimmtes Zimmer prüfen").classes("m-ktitel")
    with ui.element("div").classes("m-schalter"):
        ein = ui.input(f"Zimmer, z. B. {kern._beispiel()}").classes("m-feld").props("dense outlined dark")
        knopf_pruefen = knopf("Prüfen", None, "", "search")
    ergebnis = ui.element("div")

    async def pruefen():
        r = await run.io_bound(kern.zimmer_pruefen, a.stand, schluessel, ein.value or "")
        ergebnis.clear()
        with ergebnis:
            ui.label(r.text).classes("m-ptext " + {"passt": "", "ausnahme": "m-warn", "nein": "m-krit"}[r.art])
            for g in r.gruende:
                ui.label(f"• {g}").classes("m-zweite").style("white-space:normal")
            if r.art in ("passt", "ausnahme") and r.zimmer:
                async def zuweisen(zid=r.zimmer):
                    if await a.aendern(kern.zuweisen, schluessel, zid):
                        a.panel_zu()
                with ui.element("div").classes("m-paktionen"):
                    knopf("Zuweisen" if r.art == "passt" else "Trotzdem zuweisen (Ausnahme)", zuweisen,
                          "primaer" if r.art == "passt" else "", "check")
    knopf_pruefen.on("click", pruefen)
    ein.on("keydown.enter", pruefen)


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
        gr_vorher = ank.gruppe_auswahl(p.gruppe)
        gr = ui.select(ank.GRUPPEN, value=gr_vorher, label="Gruppe").classes(
            "m-feld").props('dense outlined dark popup-content-class="m-popup"')
        attr(gr, title="Bestimmt Zeitraum und erlaubte Zimmer (z. B. EMR nur Haus 2, Etage 1–2). Details zur Maßnahme "
                       "gehören in die Bemerkung.")

        async def angaben():
            ok = await a.aendern(ank.angaben_setzen, p.schluessel, g.value or "", bool(tier.value))
            if ok and gr.value and gr.value != gr_vorher:      # nur wenn wirklich umgestellt (RVL bleibt RVL)
                ok = await a.aendern(ank.gruppe_setzen, p.schluessel, gr.value)
            if ok:
                await person_panel(a, schluessel)

        with ui.element("div").classes("m-paktionen"):
            knopf("Angaben speichern", angaben, "primaer", "check")
        _zimmer_pruefen(a, schluessel)
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
            ui.label("Erinnerung an die Abreise").classes("m-ktitel")
            kan = ank.kanaele()
            er_an = ui.switch("erinnern", value=p.erinnerung_tage is not None).props("dense color=indigo-4")
            with ui.element("div").classes("m-zweispaltig"):
                er_tage = ui.number("Tage vorher (0 = am Abreisetag)", value=p.erinnerung_tage if p.erinnerung_tage is not None else 2,
                                    min=0, max=60, step=1, format="%d").classes("m-feld").props("dense outlined dark")
                er_kanal = ui.select(kan, value=p.erinnerung_kanal if p.erinnerung_kanal in kan else "app", label="Wie").classes(
                    "m-feld").props('dense outlined dark popup-content-class="m-popup"')

            async def erinnern():
                await a.aendern(ank.erinnerung_setzen, p.schluessel, bool(er_an.value), int(er_tage.value or 0),
                                er_kanal.value or "app")

            knopf("Erinnerung speichern", erinnern, "", "notifications")
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


# =======================================================================================
# Personen: alle kommenden Anreisen auf einer Liste – Filter „neu (7 Tage)“, „ohne Zimmer“
# =======================================================================================

PS_FILTER = {"alle": "alle Personen", "neu": "neu (7 Tage)", "ohne": "ohne Zimmer", "mit": "mit Zimmer"}


def _ps_passt(z, f: str) -> bool:
    return (f == "alle" or (f == "neu" and z.neu_seit is not None) or (f == "ohne" and not z.zimmer)
            or (f == "mit" and bool(z.zimmer)))


def personen_zeichnen(a) -> None:
    zs = a.daten["zeilen"]
    f = a.ps_filter
    with a.leiste:
        kennzahlen([(k, sum(1 for z in zs if _ps_passt(z, k)), t, {"alle": "neutral", "neu": "blau", "ohne": "akzent",
                                                                   "mit": "ok"}[k]) for k, t in PS_FILTER.items()],
                   f, lambda k: a.setzen(ps_filter="alle" if k == f else k),
                   {"neu": "Erstmals in den letzten 7 Tagen in den Listen (Anreiseliste, UWT, von Hand)"})
        suche = ui.input(placeholder="Name, Gruppe, Zimmer …", value=a.ps_text).classes("m-feld m-sucheingabe").props(
            "dense outlined dark clearable")
        suche.on("keydown.enter", lambda: a.setzen(ps_text=suche.value or ""))
        from .ui_bausteine import live_suche

        live_suche(suche, lambda t: a.setzen(ps_text=t), "personen")
        suche.on("clear", lambda: a.setzen(ps_text=""))
        knopf("Person hinzufügen", lambda: person_neu_panel(a), "primaer", "person_add").style("margin-left:auto")
    text = (a.ps_text or "").lower()
    sichtbar = [z for z in zs if _ps_passt(z, f) and (not text or text in f"{z.name} {z.gruppe} {z.zimmer}".lower())]
    if f == "neu":
        sichtbar.sort(key=lambda z: (z.neu_seit, z.anreise), reverse=True)
    sp = "minmax(200px, 1.4fr) 110px 150px 120px 120px minmax(120px, 1fr)"
    with a.inhalt:
        if not sichtbar:
            leer("Keine neuen Personen in den letzten 7 Tagen." if f == "neu" else "Keine Personen in diesem Filter.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("Name", "Gruppe", "Zeitraum", "Zimmer", "In den Listen", ""):
                ui.label(t)
        for z in sichtbar:
            with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                with ui.element("div").classes("m-namezeile"):
                    n = ui.label(z.name).classes("m-name m-link")
                    n.on("click", lambda z=z: person_panel(a, z.schluessel))
                    if z.neu_seit:
                        badge_neu(z.neu_seit)
                ui.label(z.gruppe).classes("m-mono")
                ui.label(z.zeitraum).classes("m-mono")
                with ui.element("div"):
                    if z.zimmer:
                        st = {"ok": "belegt", "maengel": "maengel"}.get(z.status, "pruefen")
                        badge(st, z.zimmer)
                    else:
                        badge("ohne")
                ui.label(f"seit {z.neu_seit:%d.%m.}" if z.neu_seit else "länger").classes("m-zweite")
                knopf("Zuteilen", lambda z=z: a.oeffnen("anreisen", ansicht="zuteilen", kennung=z.kennung), "leise",
                      "meeting_room", "Zur Anreise – Zimmer wählen")


async def _excel(a) -> None:
    titel = next((x.titel for x in a.anreisen if x.kennung == a.kennung), "")
    try:
        text, pfad = await run.io_bound(ank.anreise_excel, a.stand, a.kennung, titel)
    except PermissionError:
        a.toast("Die Datei ist noch geöffnet – bitte in Excel schließen und erneut versuchen.", fehler=True)
        return
    except ValueError as exc:
        a.toast(str(exc), fehler=True)
        return
    a.toast(text if seiten._datei_oeffnen(pfad) else f"{text} – {pfad}", rueck=False)



def archiv_panel(a) -> None:
    """Frühere Anreisen über jeden Zeitraum – mit Zimmer (Planung, Gebäudeplan oder Historie), Drucken und Excel."""
    from datetime import date, timedelta

    from . import seiten
    from .ui_bausteine import tabelle

    z = {"von": (a.heute - timedelta(days=90)).isoformat(), "bis": a.heute.isoformat(), "text": ""}

    def bauen():
        ui.label("Alle eingelesenen Anreisen bleiben gespeichert – hier über jeden Zeitraum. Zimmer laut eigener Planung, "
                 "sonst laut Gebäudeplan oder Zimmerhistorie.").classes("m-ptext")
        with ui.element("div").classes("m-kap").style("grid-template-columns: 1fr 1fr 2fr"):
            ui.input("Anreise von", value=z["von"], on_change=lambda e: (z.__setitem__("von", e.value), liste.refresh())).classes(
                "m-feld").props("dense outlined dark type=date")
            ui.input("bis", value=z["bis"], on_change=lambda e: (z.__setitem__("bis", e.value), liste.refresh())).classes(
                "m-feld").props("dense outlined dark type=date")
            ui.input("Name, Maßnahme, Gruppe oder Zimmer", value="", on_change=lambda e: (z.__setitem__("text", e.value or ""),
                                                                                       liste.refresh())).classes(
                "m-feld").props("dense outlined dark clearable")

        def zeitraum():
            try:
                von, bis = date.fromisoformat(z["von"]), date.fromisoformat(z["bis"])
            except (TypeError, ValueError):
                return None
            return (von, bis) if von <= bis else (bis, von)

        @ui.refreshable
        def liste():
            zr = zeitraum()
            if zr is None:
                ui.label("Bitte zwei gültige Daten wählen.").classes("m-zweite")
                return
            zs = ank.archiv(a.stand, *zr, z["text"])
            ohne = sum(1 for x in zs if not x.zimmer)
            ui.label(f"{len(zs)} Personen an {len({x.anreise for x in zs})} Anreisetagen"
                     + (f" · {ohne} ohne bekanntes Zimmer" if ohne else "")).classes("m-ktitel")
            if not zs:
                ui.label("Keine Anreisen in diesem Zeitraum. Es gibt nur Anreisen, deren Liste in INNternat eingelesen "
                         "wurde.").classes("m-zweite").style("white-space:normal")
                return
            with tabelle("auto minmax(160px, 1.6fr) auto minmax(90px, 1fr) auto auto auto"):
                with ui.element("div").classes("m-raster m-tkopf"):
                    for t in ("Anreise", "Name", "Gruppe", "Maßnahme", "Zeitraum", "Zimmer", "laut"):
                        ui.label(t)
                for x in zs[:500]:
                    with ui.element("div").classes("m-raster m-zeile"):
                        ui.label(f"{x.anreise:%d.%m.%Y}").classes("m-mono")
                        ui.label(x.name).classes("m-name")
                        ui.label(x.gruppe).classes("m-zweite")
                        ui.label(x.massnahme or "–").classes("m-zweite")
                        ui.label(f"{x.von:%d.%m.%y} – {x.bis:%d.%m.%y}").classes("m-mono")
                        ui.label(x.zimmer or "–").classes("m-mono")
                        ui.label(x.quelle).classes("m-zweite")
            if len(zs) > 500:
                ui.label(f"Angezeigt: 500 von {len(zs)} – Drucken und Excel enthalten alle.").classes("m-zweite")
        liste()

        def drucken():
            if (zr := zeitraum()) is not None:
                seiten.html_drucken(a, ank.archiv_html(ank.archiv(a.stand, *zr, z["text"]), *zr), f"Anreisen_{zr[0]}_{zr[1]}")

        async def excel():
            if (zr := zeitraum()) is None:
                return
            try:
                text, pfad = await run.io_bound(ank.archiv_speichern, a.stand, *zr, z["text"])
            except PermissionError:
                a.toast("Die Datei ist noch geöffnet – bitte in Excel schließen und erneut versuchen.", fehler=True)
                return
            except Exception as exc:          # noqa: BLE001
                a.toast(f"Nicht gespeichert: {exc}", fehler=True)
                return
            a.toast(text if seiten._datei_oeffnen(str(pfad)) else f"{text} – {pfad}", rueck=False)

        with ui.element("div").classes("m-paktionen"):
            knopf("Drucken", drucken, "", "print")
            knopf("Excel", excel, "", "table_view")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel("Archiv: frühere Anreisen", bauen, breit=True)
