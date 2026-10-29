"""Bausteine mehrerer Seiten: Zeitstrahl (in „Zimmer“), Reinigung mit Facility-Checks, Mieter, Zimmer & Engpässe
(in „Auswertung“), Gebäudeplan prüfen (in „Daten & Import“) und Drucken. Daten laden im Hintergrund (``*_daten``),
Formulare öffnen sich im Panel rechts."""

from __future__ import annotations

import html
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

from nicegui import run, ui

from . import seiten_kern as sk
from .kern import kurz
from .ui_bausteine import attr, kennzahlen, knopf, leer, segmente

E = html.escape


def _datei_oeffnen(ziel: str) -> bool:
    """Datei/Link mit dem Standardprogramm öffnen (Windows). False = bitte über den Browser."""
    if sys.platform == "win32":
        try:
            os.startfile(ziel)          # noqa: S606 – nur eigene Dateien bzw. mailto
            return True
        except OSError:
            return False
    return False


# =======================================================================================
# Zeitstrahl
# =======================================================================================

def zs_daten(a) -> None:
    hs = sk.haeuser(a.stand)
    if a.zs_haus not in hs:
        a.zs_haus = hs[0] if hs else ""
    a.zs_haeuser = hs
    if a.zs_modus == "flure":
        from . import flur_kern as fk

        a.daten = fk.raster(a.stand, a.zs_start, a.fl_wochen)
        return
    if a.zs_flur and not a.zs_flur.startswith(f"{a.zs_haus}|"):
        a.zs_flur = ""
    a.daten = sk.zeitstrahl(a.stand, a.zs_haus, a.zs_start, a.zs_tage, a.heute, a.zs_flur) if a.zs_haus else []


ZS_MODUS = {"zimmer": "Zimmer", "flure": "Flure"}


def zs_zeichnen(a) -> None:
    if a.zs_modus == "flure":
        _flure_zeichnen(a)
        return
    with a.werkzeuge:
        segmente({h: f"Haus {h}" for h in a.zs_haeuser}, a.zs_haus, lambda h: a.setzen(zs_haus=h, zs_flur=""))
        knopf("", lambda: a.setzen(zs_start=a.zs_start - timedelta(days=7)), "leise", "chevron_left", "Eine Woche zurück")
        knopf("Heute", lambda: a.setzen(zs_start=a.heute - timedelta(days=a.heute.weekday())), "leise")
        knopf("", lambda: a.setzen(zs_start=a.zs_start + timedelta(days=7)), "leise", "chevron_right", "Eine Woche weiter")
    ende = a.zs_start + timedelta(days=a.zs_tage - 1)
    with a.leiste:
        segmente(ZS_MODUS, a.zs_modus, lambda m: a.setzen(nur_seite=True, zs_modus=m))
        if a.zs_flur:
            _h, etage, flur = a.zs_flur.split("|")
            knopf(f"nur {zp_etage(etage)} {flur}".strip(), lambda: a.setzen(nur_seite=True, zs_flur=""), "", "close",
                  "Filter auf den Flur aufheben – wieder alle Zimmer des Hauses")
        n_bel = sum(1 for z in a.daten for b in z.balken if b.art in ("belegt", "geplant", "konflikt"))
        ui.html(f'<span class="m-kpi"><b>{len(a.daten)}</b> Zimmer<span class="m-punktt">·</span>'
                f'{a.zs_start:%d.%m.} – {ende:%d.%m.%Y}<span class="m-punktt">·</span><b>{n_bel}</b> Belegungen</span>',
                sanitize=False)
        ui.html('<span class="m-legende"><i class="belegt"></i>belegt<i class="geplant"></i>im Programm geplant'
                '<i class="gesperrt"></i>gesperrt<i class="konflikt"></i>Konflikt</span>', sanitize=False).style(
            "margin-left: auto")
        segmente({14: "2 Wochen", 28: "4 Wochen", 56: "8 Wochen"}, a.zs_tage, lambda t: a.setzen(zs_tage=t))
    with a.inhalt:
        if not a.daten:
            leer("Keine Zimmer in diesem Haus.")
            return
        ui.html(_zs_html(a), sanitize=False).classes("m-zs-wrap")


def zp_etage(etage: str) -> str:
    from belegung import zimmerplan as zp

    return zp.etage_text(etage)


FL_STUFE = {"ok": "1 Welle", "warn": "2 Wellen", "krit": "3+ Wellen", "leer": "keine gewerteten"}


def _flure_zeichnen(a) -> None:
    """Flur-Raster: je Flur und Woche die Zahl paralleler Abreisewellen (grün 1 · gelb 2 · rot 3+)."""
    from . import flur_kern as fk

    with a.werkzeuge:
        knopf("", lambda: a.setzen(nur_seite=True, zs_start=a.zs_start - timedelta(days=7)), "leise", "chevron_left", "Eine Woche zurück")
        knopf("Heute", lambda: a.setzen(nur_seite=True, zs_start=a.heute - timedelta(days=a.heute.weekday())), "leise")
        knopf("", lambda: a.setzen(nur_seite=True, zs_start=a.zs_start + timedelta(days=7)), "leise", "chevron_right", "Eine Woche weiter")
    flure = a.daten or []
    with a.leiste:
        segmente(ZS_MODUS, a.zs_modus, lambda m: a.setzen(nur_seite=True, zs_modus=m))
        zs = fk.zusammenfassung(flure)
        ui.html(f'<span class="m-kpi"><b>{len(flure)}</b> Flure<span class="m-punktt">·</span>diese Woche: '
                f'<b>{zs["ok"]}</b> mit 1 Welle, <b>{zs["warn"]}</b> mit 2, <b>{zs["krit"]}</b> mit 3+</span>', sanitize=False)
        ui.html('<span class="m-legende" title="Abreisewelle: Auszüge im selben Reinigungsfenster (Wochenende zählt zum '
                'Montag, höchstens zwei Werktage). Gewertet werden lange Aufenthalte; kurze (EMR, UWT …) und Mieter '
                'stehen klein daneben."><i class="fl-ok"></i>1 Welle<i class="fl-warn"></i>2<i class="fl-krit"></i>3+'
                '</span>', sanitize=False).style("margin-left: auto")
        segmente({4: "4 Wochen", 8: "8 Wochen", 12: "12 Wochen"}, a.fl_wochen, lambda w: a.setzen(nur_seite=True, fl_wochen=w))
    with a.inhalt:
        if not flure:
            leer("Keine Zimmer im Gebäudeplan.")
            return
        ui.label("Je Flur und Woche: zu wie vielen Abreisewellen die belegten Zimmer gehören – wenige Wellen heißt "
                 "wenige Reinigungsanlässe. Klick auf ein Feld zeigt die Wellen mit Zimmern.").classes("m-ptext").style(
            "margin: 12px 20px 0")
        raster = ui.html(_flure_html(a, flure), sanitize=False).classes("m-fl-wrap")
        raster.on("click", lambda e: _flur_panel(a, e.args) if e.args else None,
                  js_handler="(e) => { const t = e.target.closest('[data-fl]'); emit(t ? t.dataset.fl : null); }")


def _flure_html(a, flure) -> str:
    n = a.fl_wochen
    teile = [f'<div class="m-fl" style="--wochen:{n}"><div class="m-fl-kopf"></div>']
    for z in flure[0].zellen:
        kl = " heute" if z.woche <= a.heute <= z.woche + timedelta(days=6) else ""
        teile.append(f'<div class="m-fl-kopf{kl}">KW {z.woche.isocalendar()[1]}<br><span>{z.woche:%d.%m.}</span></div>')
    haus = None
    for f in flure:
        if f.haus != haus:
            haus = f.haus
            teile.append(f'<div class="m-fl-haus">Haus {E(haus)}</div>')
        teile.append(f'<div class="m-fl-lab" title="{len(f.zimmer)} Zimmer"><b>{E(f.text)}</b><span>{len(f.zimmer)} Zi.</span></div>')
        for z in f.zellen:
            neben = []
            if z.kurz:
                neben.append(f"{z.kurz} kurz")
            if z.mieter:
                neben.append(f"{z.mieter} M")
            titel = (f"{f.text} (Haus {f.haus}) · KW {z.woche.isocalendar()[1]}\n{FL_STUFE[z.stufe]} · {z.belegt} von "
                     f"{len(f.zimmer)} Zimmern lang belegt" + (f" · {z.kurz} mit kurzem Aufenthalt" if z.kurz else "")
                     + (f" · {z.mieter} Mieter" if z.mieter else ""))
            teile.append(f'<button class="m-fl-z {z.stufe}" data-fl="{E(f.schluessel)}#{z.woche.isoformat()}" title="{E(titel)}">'
                         f'<b>{z.n or "–"}</b><span>{z.belegt}/{len(f.zimmer)}</span>'
                         f'<i>{E(" · ".join(neben))}</i></button>')
    teile.append("</div>")
    return "".join(teile)


async def _flur_panel(a, arg: str) -> None:
    from . import flur_kern as fk

    schluessel, _, woche = str(arg).partition("#")
    f = next((x for x in (a.daten or []) if x.schluessel == schluessel), None)
    if f is None or not woche:
        return
    mo = date.fromisoformat(woche)
    d = fk.detail(f, mo)

    def zeile(x):
        with ui.element("div").classes("m-fl-p"):
            ui.label(x.kurz).classes("m-mono")
            ui.label(x.name).classes("m-name")
            ui.label(f"{x.von:%d.%m.} – {x.bis:%d.%m.%Y}").classes("m-zweite")

    def bauen():
        z = d["zelle"]
        ui.label(f"KW {mo.isocalendar()[1]} ({mo:%d.%m.} – {mo + timedelta(days=6):%d.%m.}) · {FL_STUFE[z.stufe]} · "
                 f"{z.belegt} von {len(f.zimmer)} Zimmern lang belegt").classes("m-ptext")
        for w, leute in d["wellen"]:
            ui.label(f"Welle {w.text}: {len(set(w.zimmer))} Zimmer " + ("wird" if len(set(w.zimmer)) == 1 else "werden")
                     + " frei").classes("m-btitel").style("margin-top:10px")
            for x in leute:
                zeile(x)
        for titel, schl in (("Kurze Aufenthalte (nicht gewertet)", "kurz"), ("Mieter (nicht gewertet)", "mieter")):
            if d[schl]:
                ui.label(titel).classes("m-btitel").style("margin-top:10px")
                for x in d[schl]:
                    zeile(x)
        with ui.element("div").classes("m-paktionen"):
            knopf("Zimmer im Zeitstrahl zeigen", lambda: a.oeffnen("zimmer", "zeitstrahl", zs_modus="zimmer",
                  zs_haus=f.haus, zs_flur=f.schluessel, zs_start=mo), "primaer", "view_timeline")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel(f"Haus {f.haus} · {f.text}", bauen)


def _zs_html(a) -> str:
    t = a.zs_tage
    tage = [a.zs_start + timedelta(days=i) for i in range(t)]
    teile = ['<div class="m-zs" style="--tage:%d">' % t, '<div class="m-zs-kopf"><div class="m-zs-lab"></div><div class="m-zs-spur">']
    for i, d in enumerate(tage):
        kl = "we" if d.weekday() >= 5 else ""
        kl += " heute" if d == a.heute else ""
        text = f"{sk.WT[d.weekday()][0]}<br>{d.day}" if t <= 28 else (f"{d:%d.%m.}" if d.weekday() == 0 else "")
        teile.append(f'<div class="m-zs-tag {kl}" style="left:calc({i} * 100% / var(--tage))">{text}</div>')
    teile.append("</div></div>")
    hintergrund = "".join(f'<div class="m-zs-we" style="left:calc({i} * 100% / var(--tage))"></div>'
                          for i, d in enumerate(tage) if d.weekday() >= 5)
    if a.zs_start <= a.heute < a.zs_start + timedelta(days=t):
        hintergrund += f'<div class="m-zs-jetzt" style="left:calc({(a.heute - a.zs_start).days + .5} * 100% / var(--tage))"></div>'
    for z in a.daten:
        hinweis = f'<span class="m-zs-h" title="{E(z.hinweis)}">●</span>' if z.hinweis else ""
        teile.append(f'<div class="m-zs-zeile" data-zd="{E(z.zimmer)}"><div class="m-zs-lab" data-z="{E(z.zimmer)}" title="{E(z.lage)} – Klick öffnet die Zimmerkarte">'
                     f'<b>{E(z.kurz)}</b>{" · DZ" if z.betten > 1 else ""}{hinweis}</div><div class="m-zs-spur">{hintergrund}')
        for b in z.balken:
            kl = f"m-zs-b {b.art}" + (" ol" if b.offen_links else "") + (" or" if b.offen_rechts else "") + (" zieh" if b.person else "")
            zieh = f' draggable="true" data-p="{E(b.person)}"' if b.person else ""
            teile.append(f'<div class="{kl}" data-z="{E(z.zimmer)}"{zieh} title="{E(b.titel)}" style="left:calc({b.start} * 100% / var(--tage));'
                         f'width:calc({b.tage} * 100% / var(--tage) - 2px)"><span>{E(b.text)}</span></div>')
        teile.append("</div></div>")
    teile.append("</div>")
    return "".join(teile)


# =======================================================================================
# Reinigung
# =======================================================================================

def rg_daten(a) -> None:
    if a.ansicht_von("reinigung", "liste") == "facility":
        from belegung import eintragen

        a.daten = eintragen.facility_checks(a.stand.lage, a.heute - timedelta(days=14), a.heute + timedelta(days=45))
        return
    if a.ansicht_von("reinigung", "liste") == "last":
        a.daten = sk.reinigung_last(a.stand, a.heute)
        return
    von, bis = sk.zeitraum(a.rg_zeitraum, a.heute)
    a.daten = sk.reinigung(a.stand, von, bis, a.heute)
    a.rg_von, a.rg_bis = von, bis


RG_SPALTEN = "36px 70px minmax(80px, .8fr) minmax(90px, 1fr) minmax(100px, .9fr) minmax(120px, 1.5fr) minmax(100px, 1.2fr) 140px 36px"


def facility_setzen(schluessel: str, an: bool) -> str:
    from belegung import eintragen
    from belegung import zimmerplan as zp

    from .kern import _schritt

    heute = date.today()
    c = next((x for x in eintragen.facility_checks(zp.laden().lage, heute - timedelta(days=60), heute + timedelta(days=90))
              if x.schluessel == schluessel), None)
    if c is None:
        raise ValueError("Den Facility-Check gibt es nicht mehr.")
    _schritt("Facility-Check", lambda: eintragen.facility_setzen(c, an), [eintragen.FACILITY_DATEI])
    return f"Zimmer {c.zimmer.removeprefix('GS-')}: Facility-Check " + ("erledigt" if an else "wieder offen")


def _facility(a) -> None:
    from belegung import eintragen

    cs = a.daten
    with a.leiste:
        ui.html(f'<span class="m-kpi"><b>{sum(1 for c in cs if not c.haken)}</b> offen · Auszüge nach mindestens '
                f'{round(eintragen.facility_tage() / 30.44)} Monaten: {E(eintragen.FACILITY_AUFGABE)}</span>', sanitize=False)
    sp = "36px 110px 90px minmax(160px, 1.4fr) minmax(120px, 1fr) 110px"
    with a.inhalt:
        if not cs:
            leer("Keine Facility-Checks in den nächsten Wochen.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("", "Auszug", "Zimmer", "Bewohner", "Maßnahme", "Aufenthalt"):
                ui.label(t)
        for c in cs:
            with ui.element("div").classes("m-raster m-zeile" + (" fertig" if c.haken else "")).style(f"grid-template-columns:{sp}"):
                with ui.element("div"):
                    b = ui.element("button").classes("m-haken" + (" an" if c.haken else ""))
                    attr(b, title="Erledigt", aria_pressed=str(c.haken).lower())
                    with b:
                        ui.icon("check")
                    b.on("click", lambda c=c: a.aendern(facility_setzen, c.schluessel, not c.haken))
                ui.label(f"{c.bis:%d.%m.%Y}").classes("m-mono")
                ui.label(c.zimmer.removeprefix("GS-")).classes("m-mono")
                ui.label(c.name).classes("m-name")
                ui.label(c.massnahme).classes("m-zweite")
                ui.label(f"{c.monate} Monate").classes("m-mono")


def rg_zeichnen(a) -> None:
    ansicht = a.ansicht_von("reinigung", "liste")
    with a.werkzeuge:
        segmente({"liste": "Reinigungsliste", "last": "Vorschau 6 Wochen", "facility": "Facility-Checks"}, ansicht,
                 lambda v: a.oeffnen("reinigung", ansicht=v))
    if ansicht == "facility":
        return _facility(a)
    if ansicht == "last":
        return _rg_last(a)
    with a.werkzeuge:
        segmente(sk.ZEITRAUM, a.rg_zeitraum, lambda w: a.setzen(rg_zeitraum=w))
        knopf("Zimmer hinzufügen", lambda: _rg_hinzu_panel(a), "", "add")
        with knopf("Drucken", None, "", "print"):
            with ui.menu().props('dark class="m-menue"'):
                ui.menu_item("Reinigungsliste (gewählter Zeitraum)", lambda: _rg_drucken(a))
                ui.menu_item("Wochenblatt zum Aushängen …", lambda: _wochenblatt_panel(a))
    n = sk.reinigung_zaehlen(a.daten)
    eilig = [z for z in a.daten if not z.erledigt and z.prio <= 1]
    with a.leiste:
        kennzahlen([("offen", n["offen"], "offen", "akzent"), ("eilig", n["eilig"], "eilig (Anreise bald)", "krit" if n["eilig"] else "ok"),
                    ("erledigt", n["erledigt"], "erledigt", "ok"), ("alle", len(a.daten), "alle", "neutral")],
                   a.rg_filter, lambda f: a.setzen(rg_filter=f, laden=False))
        ui.label(f"{a.rg_von:%d.%m.} – {a.rg_bis:%d.%m.}").classes("m-kpi")
        if eilig:
            knopf(f"Alle {len(eilig)} eiligen als gereinigt markieren" if len(eilig) > 1 else "Eilige als gereinigt markieren",
                  lambda: a.aendern(sk.reinigung_setzen, [z.schluessel for z in eilig], True, a.rg_von, a.rg_bis),
                  "gruen", "done_all")
    zs = [z for z in a.daten if a.rg_filter == "alle" or (a.rg_filter == "erledigt" and z.erledigt)
          or (a.rg_filter == "offen" and not z.erledigt) or (a.rg_filter == "eilig" and not z.erledigt and z.prio <= 1)]
    with a.leiste:
        _mehrere_menue(a, [z for z in zs if not z.erledigt])
    with a.inhalt:
        if not zs:
            leer("Keine offenen Reinigungen in diesem Zeitraum." if a.daten else "Keine Reinigungen in diesem Zeitraum.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{RG_SPALTEN}"):
            for t in ("", "Zimmer", "Lage", "Art", "Auszug", "Danach", "Sauber bis", "Priorität", ""):
                ui.label(t)
        for z in zs:
            with ui.element("div").classes("m-raster m-zeile" + (" fertig" if z.erledigt else "")).style(
                    f"grid-template-columns:{RG_SPALTEN}"):
                with ui.element("div"):
                    b = ui.element("button").classes("m-haken" + (" an" if z.erledigt else ""))
                    attr(b, title="Als gereinigt markieren" if not z.erledigt else "Wieder offen", aria_pressed=str(z.erledigt).lower())
                    with b:
                        ui.icon("check")
                    b.on("click", lambda z=z: a.aendern(sk.reinigung_setzen, [z.schluessel], not z.erledigt, a.rg_von, a.rg_bis))
                attr(ui.label(z.zimmer).classes("m-name"), title=z.details)
                ui.label(z.lage).classes("m-zweite")
                attr(ui.label(z.art + (f" · {z.notiz}" if z.notiz and z.notiz != z.art else "")).classes("m-zweite"),
                     title=z.notiz or z.art)
                ui.label(z.auszug).classes("m-mono")
                attr(ui.label(z.danach).classes("m-zweite"), title=z.details)
                ui.label(z.frist).classes("m-mono")
                with ui.element("div"):
                    ui.label(z.prio_text).classes(f"m-pille {z.stufe}")
                with ui.element("div"):
                    if z.manuell_id:
                        knopf("", lambda z=z: a.aendern(sk.reinigung_entfernen, z.manuell_id), "leise", "close",
                              "Von Hand hinzugefügte Reinigung entfernen")


def _mehrere_menue(a, offen: list) -> None:
    """Mehrere auf einmal abhaken: alle sichtbaren, je Haus oder je Flur (z. B. nach einer Gruppenabreise)."""
    if len(offen) < 2:
        return
    haeuser: dict[str, list] = {}
    flure: dict[str, list] = {}
    for z in offen:
        haeuser.setdefault(z.zimmer.rsplit("-", 1)[0], []).append(z)
        flure.setdefault(z.lage, []).append(z)

    def setzen(liste):
        return a.aendern(sk.reinigung_setzen, [z.schluessel for z in liste], True, a.rg_von, a.rg_bis)

    with knopf("Mehrere abhaken", None, "", "playlist_add_check").style("margin-left:auto"):
        with ui.menu().props('dark class="m-menue"').style("max-height:70vh"):
            ui.menu_item(f"Alle sichtbaren offenen ({len(offen)})", lambda: setzen(offen))
            if len(haeuser) > 1:
                ui.separator()
                ui.label("Je Haus").classes("m-mgruppe")
                for h, liste in sorted(haeuser.items()):
                    ui.menu_item(f"Haus {h} ({len(liste)})", lambda liste=liste: setzen(liste))
            mehrfach = {f: liste for f, liste in flure.items() if len(liste) > 1}
            if mehrfach:
                ui.separator()
                ui.label("Je Flur").classes("m-mgruppe")
                for f, liste in sorted(mehrfach.items()):
                    ui.menu_item(f"{f} ({len(liste)})", lambda liste=liste: setzen(liste))


def _rg_last(a) -> None:
    """Wie viele Zimmer in den nächsten 6 Wochen je Tag gereinigt werden müssen – Spitzentage markiert."""
    tage, je_haus, schnitt = a.daten
    gesamt = sum(t.n for t in tage)
    spitzen = [t for t in tage if t.spitze]
    with a.leiste:
        ui.html(f'<span class="m-kpi"><b>{gesamt}</b> Reinigungen in 6 Wochen<span class="m-punktt">·</span>'
                f'Ø <b>{schnitt:.1f}</b> je Werktag<span class="m-punktt">·</span><b>{len(spitzen)}</b> Spitzentage</span>',
                sanitize=False)
        ui.label(" · ".join(f"Haus {h}: {n}" for h, n in je_haus.items())).classes("m-zweite").style("margin-left:auto")
    with a.inhalt:
        ui.label("Gezählt werden Zimmer (Auszug, Vorbereiten, von Hand) – nicht die Arbeitszeit. Spitzentag = mindestens "
                 "1,5-mal so viele wie an einem üblichen Werktag. Klick auf einen Tag: Reinigungsliste dieser Woche."
                 ).classes("m-ptext").style("margin:12px 20px 0")
        with ui.element("div").classes("m-last"):
            for w in ("KW", "Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"):
                ui.label(w).classes("m-last-kopf")
            hoechst = max((t.n for t in tage), default=0) or 1
            for i in range(0, len(tage), 7):
                woche = tage[i:i + 7]
                ui.label(f"KW {woche[0].tag.isocalendar()[1]}").classes("m-last-kw")
                for t in woche:
                    kl = "m-last-tag" + (" spitze" if t.spitze else "") + (" heute" if t.tag == a.heute else "") + \
                         (" we" if t.tag.weekday() >= 5 else "") + (" vorbei" if t.tag < a.heute else "")
                    zelle = ui.element("button").classes(kl).style(f"--anteil:{t.n / hoechst:.2f}")
                    attr(zelle, title=f"{sk.WT[t.tag.weekday()]} {t.tag:%d.%m.}: {t.n} Zimmer"
                         + ("".join(f"\nHaus {h}: {n}" for h, n in t.je_haus.items()) if t.je_haus else "")
                         + ("\nSpitzentag" if t.spitze else ""))
                    with zelle:
                        ui.label(f"{t.tag:%d.%m.}").classes("m-last-datum")
                        ui.label(str(t.n) if t.n else "–").classes("m-last-zahl")
                        if t.je_haus:
                            ui.label(" · ".join(f"{h}: {n}" for h, n in t.je_haus.items())).classes("m-last-haus")
                    zelle.on("click", lambda t=t: a.oeffnen("reinigung", ansicht="liste",
                                                            rg_zeitraum="woche" if t.tag < a.heute + timedelta(days=7 - a.heute.weekday())
                                                            else "naechste", rg_filter="alle"))


def _rg_hinzu_panel(a) -> None:
    def bauen():
        ui.label("Ein Zimmer zusätzlich auf die Reinigungsliste setzen, z. B. Zwischen- oder Grundreinigung.").classes("m-ptext")
        zimmer = ui.select(sk.zimmer_kurzliste(a.stand), label="Zimmer", with_input=True).classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        tag = ui.input("Tag", value=a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
        from belegung import zimmerplan as zp

        grund = ui.select(zp.REINIGUNG_GRUENDE, value=zp.REINIGUNG_GRUENDE[0], label="Grund", new_value_mode="add-unique",
                          with_input=True).classes("m-feld").props('dense outlined dark options-dense popup-content-class="m-popup"')

        async def speichern():
            if not zimmer.value:
                a.toast("Bitte ein Zimmer wählen.", fehler=True)
                return
            try:
                d = date.fromisoformat(tag.value)
            except (TypeError, ValueError):
                a.toast("Bitte einen Tag wählen.", fehler=True)
                return
            if await a.aendern(sk.reinigung_hinzu, zimmer.value, d, grund.value or ""):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Hinzufügen", speichern, "primaer", "add")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Zimmer zur Reinigung hinzufügen", bauen)


async def _rg_drucken(a) -> None:
    text = await run.io_bound(sk.reinigung_druck, a.rg_von, a.rg_bis, a.heute)
    html_drucken(a, text, f"Reinigungsliste_{a.rg_von:%Y-%m-%d}")


def html_drucken(a, text: str, name: str) -> None:
    """Druckansicht im Standardbrowser öffnen (dort drucken oder als PDF speichern)."""
    pfad = Path(tempfile.gettempdir()) / f"{name}.html"
    if "</body>" in text:
        text = text.replace("</body>", "<script>window.print()</script></body>")
    else:
        text = f"<!doctype html><meta charset='utf-8'>{text}<script>window.print()</script>"
    pfad.write_text(text, encoding="utf-8")
    if _datei_oeffnen(str(pfad)):
        a.toast("Druckansicht geöffnet – dort drucken oder als PDF speichern", rueck=False)
    else:
        ui.navigate.to(f"/druck/{pfad.name}", new_tab=True)


# =======================================================================================
# Mieter
# =======================================================================================

def mt_daten(a) -> None:
    a.daten = sk.mieter(a.heute)


MT_SPALTEN = "28px 70px minmax(160px, 1.3fr) 90px 190px minmax(120px, 1fr) minmax(170px, 1fr) 76px"


def mt_zeichnen(a) -> None:
    vertraege, weitere = a.daten
    offen = [m for m in vertraege if m.mail_offen]
    with a.leiste:
        laufend = sum(1 for m in vertraege if m.bis >= a.heute)
        kennzahlen([("laufend", laufend, "laufende Verträge", "ok"), ("mail", len(offen), "Mail zum Vertragsende offen",
                                                                       "warn" if offen else "neutral"),
                    ("weitere", len(weitere), "weitere laut Gebäudeplan", "neutral")], a.mt_filter,
                   lambda f: a.setzen(mt_filter=None if f == a.mt_filter else f, laden=False))
        knopf("Neuer Mieter", lambda: mieter_neu_panel(a), "primaer", "person_add").style("margin-left:auto")
    with a.inhalt:
        if not vertraege and not weitere:
            leer("Keine Mieter.")
            return
        if vertraege:
            with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{MT_SPALTEN}"):
                for t in ("", "Nr.", "Name", "Zimmer", "Zeitraum", "Status", "Mail zum Vertragsende", ""):
                    ui.label(t)
            for m in vertraege:
                if (a.mt_filter == "mail" and not m.mail_offen) or (a.mt_filter == "laufend" and m.bis < a.heute) \
                        or a.mt_filter == "weitere":
                    continue
                with ui.element("div").classes("m-raster m-zeile" + (" fertig" if m.bis < a.heute else "")).style(
                        f"grid-template-columns:{MT_SPALTEN}"):
                    with ui.element("div"):
                        ui.element("div").classes(f"m-ampel {m.stufe}")
                    ui.label(m.nr).classes("m-mono")
                    with ui.element("div"):
                        ui.label(m.name).classes("m-name")
                        if m.email:
                            ui.label(m.email).classes("m-zweite")
                    ui.label(m.zimmer).classes("m-mono")
                    ui.label(f"{m.von:%d.%m.%Y} – {m.bis:%d.%m.%Y}").classes("m-mono")
                    ui.label(m.status).classes("m-zweite")
                    with ui.element("div").classes("m-hinweis"):
                        if m.mail_offen:
                            knopf("Mail vorbereiten", lambda m=m: _mail_panel(a, m), "gruen", "mail")
                        elif m.mail_am:
                            ui.label(f"vorbereitet am {date.fromisoformat(m.mail_am):%d.%m.%Y}").classes("t")
                            knopf("", lambda m=m: _mail_panel(a, m), "leise", "mail", "Noch einmal vorbereiten")
                        elif m.bis >= a.heute:
                            knopf("Mail", lambda m=m: _mail_panel(a, m), "leise", "mail", "Mail zum Vertragsende vorbereiten")
                    with ui.element("div").classes("m-paktionen").style("padding:0; flex-wrap:nowrap"):
                        knopf("", lambda m=m: verlaengern_panel(a, m), "leise", "update", "Verlängern (Nebenabrede) …")
                        knopf("", lambda m=m: _unterlagen(a, m.nr), "leise", "description", "Unterlagen neu erstellen")
        if weitere and a.mt_filter in (None, "weitere"):
            ui.label("Weitere Mieter laut Gebäudeplan (ohne Vertrag in diesem Programm)").classes("m-abschnitt")
            for name, zimmer, zeit in weitere:
                with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{MT_SPALTEN}"):
                    ui.label("")
                    ui.label("–").classes("m-mono")
                    ui.label(name).classes("m-name")
                    ui.label(zimmer).classes("m-mono")
                    ui.label(zeit).classes("m-mono")
                    ui.label("")
                    ui.label("")
                    ui.label("")


async def _mit_datei(a, aktion, *args) -> bool:
    """Unterlagen erstellen und die Datei öffnen."""
    ergebnis = {}

    def los():
        text, pfad = aktion(*args)
        ergebnis["pfad"] = pfad
        return text

    if await a.aendern(los):
        if not _datei_oeffnen(str(ergebnis["pfad"])):
            a.toast(f"Gespeichert: {ergebnis['pfad']}", rueck=False)
        return True
    return False


async def _unterlagen(a, nr: str) -> None:
    from . import mieter_kern as mk

    await _mit_datei(a, mk.unterlagen_neu, nr)


def mieter_neu_panel(a) -> None:
    from belegung import mieter as mt
    from belegung import speicher

    from . import mieter_kern as mk

    def bauen():
        ui.label("Alle Unterlagen in einer PDF (Mietvertrag, Wohnungsgeberbestätigung, SEPA, Mietschuldenfreiheit) – "
                 "der Mieter wird im Zimmerplan eingetragen.").classes("m-ptext")
        with ui.element("div").classes("m-zweispaltig"):
            anrede = ui.select(mk.ANREDEN, value="Frau", label="Anrede").classes("m-feld").props(
                'dense outlined dark options-dense popup-content-class="m-popup"')
            nr = ui.input("Vertragsnummer", value=mt.naechste_nummer()).classes("m-feld").props("dense outlined dark")
            vor = ui.input("Vorname").classes("m-feld").props("dense outlined dark")
            nach = ui.input("Nachname").classes("m-feld").props("dense outlined dark")
            von = ui.input("Mietbeginn", value=a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
            bis = ui.input("Mietende", value=mt.standard_ende(a.heute).isoformat()).classes("m-feld").props(
                "dense outlined dark type=date")
            miete = ui.number("Miete (€)", value=mt.STANDARD_MIETE, min=0, step=10).classes("m-feld").props("dense outlined dark")
            flaeche = ui.number("Fläche (m²)", value=mt.STANDARD_FLAECHE, min=1, step=1, format="%d").classes("m-feld").props(
                "dense outlined dark")
            schl = ui.number("Schlüssel", value=1, min=0, step=1, format="%d").classes("m-feld").props("dense outlined dark")
            mail = ui.input("E-Mail (optional)").classes("m-feld").props("dense outlined dark")
        woher = ui.label("Vertragsnummer wird abgeglichen …").classes("m-zweite")
        with ui.expansion("Nummern mit bisherigen Verträgen abgleichen").classes("m-ptext").props("dense"):
            ui.label("Verträge, die nicht mit diesem Programm erstellt wurden, kennt die Zählung sonst nicht. Ordner mit den "
                     "bisherigen Verträgen (Dateinamen mit Nummer, z. B. „MV 26-047 …“) und/oder die zuletzt vergebene "
                     "Nummer – die nächste ist dann die höchste + 1.").classes("m-ptext")
            e = speicher.einstellungen()
            ordner = ui.input("Ordner mit bisherigen Verträgen", value=e.get(mk.EINSTELLUNG_ORDNER, ""),
                              placeholder=r"z. B. S:\Internat\Mietverträge").classes("m-feld").props("dense outlined dark")
            letzte = ui.input("Zuletzt vergebene Nummer", value=e.get(mk.EINSTELLUNG_LETZTE, ""),
                              placeholder="z. B. 26-047").classes("m-feld").props("dense outlined dark")

            async def abgleichen():
                try:
                    a.toast(await run.io_bound(mk.abgleich_einstellen, ordner.value, letzte.value), rueck=False)
                except Exception as exc:       # noqa: BLE001
                    a.toast(str(exc), fehler=True, rueck=False)
                    return
                await nummer_holen(True)
            knopf("Abgleichen", abgleichen, "", "sync")

        async def nummer_holen(setzen: bool = False):
            vorschlag, text = await run.io_bound(mk.nummern_abgleich, a.heute)
            if setzen or nr.value == erste:
                nr.value = vorschlag
            woher.text = f"Vorschlag {vorschlag} · {text}"
        erste = nr.value
        ui.timer(0.05, nummer_holen, once=True)
        zimmer = ui.select({}, label="Zimmer", with_input=True).classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        alle = ui.switch("auch Zimmer zeigen, die nicht passen").props("dense color=indigo-4")
        kaution = ui.switch("Mietsicherheit (Kaution) vereinbaren", value=False).props("dense color=indigo-4")
        flex = ui.switch("Flexibler Mietvertrag (abweichende Textstellen)", value=False).props("dense color=indigo-4")
        attr(flex, title="Nur für die Ausnahme: nimmt die Zeilen mit „?flexibel“ aus der Vorlage Mietvertrag.vorlage")

        async def zimmer_fuellen():
            try:
                v, b = date.fromisoformat(von.value), date.fromisoformat(bis.value)
            except (TypeError, ValueError):
                return
            zimmer.set_options(await run.io_bound(mk.zimmer_auswahl, v, b, anrede.value, bool(alle.value)), value=zimmer.value
                               if zimmer.value else None)

        def beginn():
            try:
                bis.value = mt.standard_ende(date.fromisoformat(von.value)).isoformat()
            except (TypeError, ValueError):
                pass

        von.on_value_change(lambda _e: (beginn(), zimmer_fuellen()))
        bis.on_value_change(lambda _e: zimmer_fuellen())
        alle.on_value_change(lambda _e: zimmer_fuellen())
        anrede.on_value_change(lambda _e: zimmer_fuellen())
        ui.timer(0.05, zimmer_fuellen, once=True)

        async def erstellen():
            try:
                v, b = date.fromisoformat(von.value), date.fromisoformat(bis.value)
            except (TypeError, ValueError):
                a.toast("Bitte Beginn und Ende wählen.", fehler=True)
                return
            werte = {"nr": nr.value or "", "anrede": anrede.value, "vorname": vor.value or "", "nachname": nach.value or "",
                     "zimmer": zimmer.value, "von": v, "bis": b, "miete": miete.value or 0, "flaeche": flaeche.value or 1,
                     "schluessel": schl.value or 0, "kaution": kaution.value, "kaution_bis": v, "email": mail.value or "",
                     "flexibel": bool(flex.value)}
            if await _mit_datei(a, mk.neuer_vertrag, werte):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Unterlagen erstellen", erstellen, "primaer", "description")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Neuer Mieter", bauen, breit=True)


def verlaengern_panel(a, m) -> None:
    from belegung import mieter as mt

    from . import mieter_kern as mk

    def bauen():
        ui.label(f"{m.name} · Zimmer {m.zimmer} · bisher bis {m.bis:%d.%m.%Y}. Erstellt die Nebenabrede (Word und PDF) "
                 "und verlängert den Eintrag im Zimmerplan.").classes("m-ptext")
        bis = ui.input("Neues Mietende", value=mt.standard_ende(m.bis + timedelta(days=1)).isoformat()).classes(
            "m-feld").props("dense outlined dark type=date")

        async def los():
            try:
                d = date.fromisoformat(bis.value)
            except (TypeError, ValueError):
                a.toast("Bitte ein Datum wählen.", fehler=True)
                return
            if await _mit_datei(a, mk.verlaengern, m.nr, d):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Nebenabrede erstellen", los, "primaer", "update")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel(f"Verlängern · MV {m.nr}", bauen)


def _mail_panel(a, m) -> None:
    from belegung import mieter as mt

    def bauen():
        ui.label(f"{m.name} · Zimmer {m.zimmer} · Vertrag bis {m.bis:%d.%m.%Y}. Die Mail öffnet sich als Entwurf in "
                 "Outlook – geprüft und abgeschickt wird von Ihnen.").classes("m-ptext")
        art = ui.select(mt.MAIL_ARTEN, value="anfrage", label="Art").classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        an = ui.input("An (E-Mail)", value=m.email).classes("m-feld").props("dense outlined dark")
        betreff = ui.input("Betreff").classes("m-feld").props("dense outlined dark")
        text = ui.textarea("Text").classes("m-feld").props("outlined dark autogrow")

        def fuellen():
            try:
                _e, b, t = sk.mieter_mail(m.nr, art.value, a.heute)
            except ValueError as exc:
                a.toast(str(exc), fehler=True)
                return
            betreff.value, text.value = b, t

        art.on_value_change(lambda _e: fuellen())
        fuellen()

        async def oeffnen():
            if not (an.value or "").strip() or "@" not in an.value:
                a.toast("Bitte eine E-Mail-Adresse eintragen.", fehler=True)
                return
            link = await run.io_bound(sk.mail_oeffnen, an.value.strip(), betreff.value, text.value)
            if link and not _datei_oeffnen(link):
                ui.navigate.to(link)
            if await a.aendern(sk.mieter_mail_vermerken, m.nr, an.value.strip()):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("In Outlook öffnen", oeffnen, "primaer", "open_in_new")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Mail zum Vertragsende", bauen)


# =======================================================================================
# Auswertung
# =======================================================================================

def aw_daten(a) -> None:
    a.daten = sk.auswertung(a.stand, a.heute, 12)


STUFE_AW = {"ok": "ok", "knapp": "warn", "kritisch": "krit"}


def aw_zeichnen(a) -> None:
    from belegung import eintragen

    aw: sk.Auswertung = a.daten
    with a.leiste:
        tief = min(aw.wochen, key=lambda w: w.frei_nach, default=None)
        ui.html(f'<span class="m-kpi"><b>{aw.offen}</b> Anreisen ohne Zimmer in 12 Wochen<span class="m-punktt">·</span>'
                f'<b>{aw.ohne_platz}</b> fänden keins<span class="m-punktt">·</span>knappste Woche nach Planung: '
                f'<b>{E(tief.kw) if tief else "–"}</b> ({tief.frei_nach if tief else 0} frei)</span>', sanitize=False)
        knopf("Grenzen ändern", lambda: a.oeffnen("einstellungen", ansicht="allgemein"), "leise", "tune").style("margin-left:auto")
    with a.inhalt:
        with ui.element("div").classes("m-zwei"):
            with ui.element("section").classes("m-block").style("grid-column: 1 / -1"):
                ui.label("Freie Zimmer je Woche – jetzt und nach Planung").classes("m-btitel")
                ui.label("„Nach Planung“: auch alle bekannten Anreisen ohne Zimmer probeweise nach den Regeln zugeteilt "
                         "(nichts wird gespeichert). EMR und Doppel gelten nach Planung. Ampel: " + eintragen.grenzen_text()
                         + ".").classes("m-ptext")
                hoechst = max([w.frei_jetzt for w in aw.wochen] + [1])
                with ui.element("div").classes("m-aw-tab breit"):
                    for t in ("Woche", "frei jetzt", "frei nach Planung", "EMR", "Doppel UWT", "Lage nach Planung"):
                        ui.label(t).classes("k")
                    for w in aw.wochen:
                        with ui.element("div").classes("m-aw-kw"):
                            ui.element("div").classes(f"m-ampel {STUFE_AW[w.stufe]}").style("margin:0 8px 0 0")
                            ui.label(w.kw)
                        ui.label(str(w.frei_jetzt)).classes("m-mono")
                        with ui.element("div").classes("m-aw-balken"):
                            with ui.element("div").classes("m-spur"):
                                ui.element("div").classes(f"m-bar {STUFE_AW[w.stufen.get('gesamt', w.stufe)]}").style(
                                    f"width:{max(2, round(100 * w.frei_nach / hoechst))}%")
                            ui.label(str(w.frei_nach)).classes("m-mono")
                        for art, wert in (("emr", w.emr), ("doppel", w.doppel)):
                            with ui.element("div"):
                                ui.label(str(wert)).classes(f"m-pille {STUFE_AW[w.stufen.get(art, 'ok')]}")
                        eng = [n for art, n in (("gesamt", "Zimmer"), ("emr", "EMR"), ("doppel", "Doppelzimmer"))
                               if w.stufen.get(art, "ok") != "ok"]
                        ui.label({"ok": "ok", "knapp": "knapp", "kritisch": "kritisch"}[w.stufe] + (" – " + ", ".join(eng) if eng else "")
                                 ).classes("m-zweite" + (" m-krit" if w.stufe == "kritisch" else " m-warn" if w.stufe == "knapp" else ""))
            with ui.element("section").classes("m-block"):
                ui.label("Was gezählt wird").classes("m-btitel")
                for art, text in eintragen.ENGPASS_ERKLAERUNG.items():
                    ui.label(f"{eintragen.ENGPASS_NAMEN[art]}: {text}").classes("m-ptext")
            with ui.element("section").classes("m-block"):
                ui.label("Belegung heute je Haus").classes("m-btitel")
                ui.label("Anteil belegter Zimmer an den nutzbaren (ohne gesperrte, ohne Gästezimmer).").classes("m-ptext")
                for h in aw.haeuser:
                    with ui.element("div").classes("m-aw-haus"):
                        ui.label(f"Haus {h.haus}").classes("m-name")
                        with ui.element("div").classes("m-aw-balken"):
                            with ui.element("div").classes("m-spur"):
                                ui.element("div").classes("m-bar akzent").style(f"width:{max(1, h.quote)}%")
                            ui.label(f"{h.quote} %").classes("m-mono")
                        ui.label(f"{h.belegt} belegt · {h.frei} frei · {h.gesperrt} gesperrt").classes("m-zweite")


# =======================================================================================
# Gebäudeplan prüfen (Panel) – genutzt von „Daten & Import“
# =======================================================================================

def _plan_panel(a, plan, kennung, unterschiede) -> None:
    def bauen():
        ui.label("Was im neuen Gebäudeplan anders ist als jetzt im Zimmerplan. Bei eigenen Einträgen wählen Sie, was "
                 "gelten soll. Alles andere kommt aus dem neuen Gebäudeplan. Rückgängig ist möglich.").classes("m-ptext")
        boxen = []
        with ui.element("div").classes("m-paktionen"):
            def alle(vorrang):
                for u, box in boxen:
                    ziel = vorrang if vorrang in u.optionen else ("entfernen" if vorrang == "plan" else "planung")
                    if ziel in u.optionen:
                        box.value = ziel
            knopf("Alles aus dem neuen Plan", lambda: alle("plan"), "")
            knopf("Alle eigenen behalten", lambda: alle("planung"), "")
        with ui.element("div").classes("m-plan-liste"):
            for u in unterschiede:
                with ui.element("div").classes("m-plan-u"):
                    ui.label(f"{u.name}").classes("m-name")
                    ui.label(u.art_text).classes("m-zweite")
                    if u.system:
                        ui.label(f"Jetzt: {u.system}").classes("m-zweite")
                    if u.plan:
                        ui.label(f"Neuer Plan: {u.plan}").classes("m-zweite")
                    if u.entscheidbar:
                        box = ui.select(u.optionen, value=u.wahl).classes("m-feld").props(
                            'dense outlined dark options-dense popup-content-class="m-popup"')
                        box.on_value_change(lambda e, u=u: setattr(u, "wahl", e.value))
                        boxen.append((u, box))
                    else:
                        ui.label(u.info or "wird übernommen").classes("m-zweite").style("color: var(--text3)")

        async def los():
            if await a.aendern(sk.plan_uebernehmen, plan, unterschiede, kennung):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Übernehmen", los, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel(f"Gebäudeplan prüfen · {len(unterschiede)} Unterschiede", bauen)


def _wochenblatt_panel(a) -> None:
    """Wochenblatt: An- und Abreisen und Reinigungen je Tag – zum Aushängen für Hausmeister und Reinigung."""
    def bauen():
        ui.label("An- und Abreisen und Reinigungen je Tag – zum Aushängen für Hausmeister und Reinigung.").classes("m-ptext")
        woche = ui.select(sk.wochen(a.heute), value=next(iter(sk.wochen(a.heute))), label="Woche").classes("m-feld").props(
            'dense outlined dark popup-content-class="m-popup"')
        namen = ui.checkbox("mit Namen", value=True).props("dark dense")

        async def drucken():
            from datetime import date as _d

            html = await run.io_bound(sk.wochenblatt, _d.fromisoformat(woche.value), bool(namen.value))
            mo = _d.fromisoformat(woche.value)
            html_drucken(a, html, f"Wochenblatt_KW{mo.isocalendar()[1]}_{mo:%Y}")

        with ui.element("div").classes("m-paktionen"):
            knopf("Drucken / PDF", drucken, "primaer", "print")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel("Wochenblatt", bauen)

