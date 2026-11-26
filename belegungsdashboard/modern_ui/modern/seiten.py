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
from .kern import unter_sperre
from .ui_bausteine import attr, badge, kennzahlen, knopf, leer, segmente
from .standort_kern import kurz as zkurz

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
    if a.zs_modus == "frei":                  # 1.56: freie Zimmer der nächsten Monate
        from belegung import maengel as mg

        from . import frei_kern as fr

        unbew = {m.zimmer for m in mg.offen() if m.unbewohnbar}
        a.daten = fr.raster(a.stand, a.zs_start, fr.MONATE.get(a.fr_monate, 26), a.fr_haus, unbew,
                            ab=max(a.zs_start, a.heute), mindest=7 * max(1, a.fr_min))
        return
    if a.zs_flur and not a.zs_flur.startswith(f"{a.zs_haus}|"):
        a.zs_flur = ""
    a.daten = sk.zeitstrahl(a.stand, a.zs_haus, a.zs_start, a.zs_tage, a.heute, a.zs_flur) if a.zs_haus else []


ZS_MODUS = {"zimmer": "Zimmer", "flure": "Flure", "frei": "Frei"}

_DE_LOCALE = ('{"days":["Sonntag","Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag"],'
              '"daysShort":["So","Mo","Di","Mi","Do","Fr","Sa"],"months":["Januar","Februar","März","April","Mai","Juni",'
              '"Juli","August","September","Oktober","November","Dezember"],"monthsShort":["Jan","Feb","Mär","Apr","Mai",'
              '"Jun","Jul","Aug","Sep","Okt","Nov","Dez"],"firstDayOfWeek":1}')


def _datum_waehlen(a, band: bool = False) -> None:
    """1.56: Datum direkt wählen (Kalender) – der Belegungsplan springt dorthin (Flure/Frei: auf die Woche)."""
    from . import band_ui as bu

    async def gewaehlt(e) -> None:
        if not e.value:
            return
        try:
            d = date.fromisoformat(str(e.value).replace("/", "-"))
        except ValueError:
            return
        if a.zs_modus != "zimmer":
            d -= timedelta(days=d.weekday())
        await a.setzen(nur_seite=a.zs_modus != "zimmer", zs_start=d)

    tipp = "Datum wählen – der Plan beginnt an diesem Tag"
    b = bu.klein(f"{a.zs_start:%d.%m.%Y}", "calendar_ltr", "blau", tipp=tipp, pfeil=True) if band else \
        knopf(f"{a.zs_start:%d.%m.%Y}", None, "leise", "event", tipp)
    with b:
        with ui.menu().props('class="m-menue"'):
            ui.date(value=a.zs_start.isoformat(), on_change=gewaehlt).props(
                f"mask=YYYY-MM-DD minimal today-btn :locale='{_DE_LOCALE}'")


def _zs_filter(a, art: str | None) -> None:
    """1.00: Legende als Filter – Klick schaltet die Art an/aus (mehrere = Zimmer mit einer davon); None = alle."""
    jetzt = set(getattr(a, "zs_filter", ()) or ())
    if art is None:
        jetzt = set()
    else:
        jetzt ^= {art}
    a.zs_filter = tuple(sorted(jetzt))
    a.zeichnen()


ZS_SYMBOL = {"belegt": ("person", "blau"), "geplant": ("calendar_clock", "blau"), "gesperrt": ("lock_closed", ""),
             "konflikt": ("warning", "rot")}


def _zs_band(a, ende, n_bel: int, zahl: dict) -> None:
    """1.00: Werkzeuge des Zeitstrahls als Office-Gruppen im Menüband."""
    from . import band_ui as bu

    filt = set(getattr(a, "zs_filter", ()) or ())
    with a.werkzeuge:
        with bu.gruppe("Haus"):
            with bu.gross(f"Haus {a.zs_haus}", "building_home", "blau", pfeil=True, tipp="Haus wählen"):
                with ui.menu().props('class="m-ob-menue"'):
                    for h in a.zs_haeuser:
                        ui.menu_item(f"Haus {h}", lambda h=h: a.setzen(zs_haus=h, zs_flur=""))
        with bu.gruppe("Zeitraum"):
            with bu.stapel():
                with ui.element("div").style("display:flex;gap:2px"):
                    bu.klein("", "chevron_left", "", lambda: a.setzen(zs_start=a.zs_start - timedelta(days=7)),
                             tipp="Eine Woche zurück")
                    bu.klein("", "chevron_right", "", lambda: a.setzen(zs_start=a.zs_start + timedelta(days=7)),
                             tipp="Eine Woche weiter")
                bu.klein("Heute", "calendar_today", "blau",
                         lambda: a.setzen(zs_start=a.heute - timedelta(days=a.heute.weekday())))
                _datum_waehlen(a, band=True)
            with bu.stapel():
                for t, text in ((14, "2 Wochen"), (28, "4 Wochen"), (56, "8 Wochen")):
                    bu.klein(text, "calendar_date", "blau", lambda t=t: a.setzen(zs_tage=t), an=a.zs_tage == t)
        with bu.gruppe("Zeilen"):
            bu.gross("Zimmer", "door", "teal", lambda: a.setzen(nur_seite=True, zs_modus="zimmer"), an=a.zs_modus == "zimmer")
            bu.gross("Flure", "arrow_routing", "teal", lambda: a.setzen(nur_seite=True, zs_modus="flure"),
                     an=a.zs_modus == "flure")
            bu.gross("Frei", "bed", "gruen", lambda: a.setzen(nur_seite=True, zs_modus="frei"),
                     an=a.zs_modus == "frei", tipp="Welche Zimmer sind in den nächsten Monaten frei? (Heatmap)")
        with bu.gruppe("Filter – nur Zimmer mit …"):
            for art, text in sk.ZS_ARTEN.items():
                sym, farbe = ZS_SYMBOL[art]
                bu.gross("geplant" if art == "geplant" else text, sym, farbe, lambda art=art: _zs_filter(a, art),
                         an=art in filt, zahl=zahl.get(art, 0),
                         tipp=f"Nur Zimmer mit „{text}“ zeigen (nochmal klicken: aus; mehrere kombinierbar)")
            if filt:
                with bu.stapel():
                    bu.klein("Alle zeigen", "filter", "", lambda: _zs_filter(a, None), tipp="Filter aufheben")
        with bu.gruppe("Zahlen"):
            with bu.stapel():
                n = len(sk.zeitstrahl_filtern(a.daten, filt))
                bu.info(f"<b>{n}</b> von {len(a.daten)} Zimmern" if filt else f"<b>{len(a.daten)}</b> Zimmer")
                bu.info(f"<b>{n_bel}</b> Belegungen")
                bu.info(f"{a.zs_start:%d.%m.} – {ende:%d.%m.%Y}")
                if a.zs_flur:
                    _h, etage, flur = a.zs_flur.split("|")
                    bu.klein(f"nur {zp_etage(etage)} {flur}".strip(), "filter", "",
                             lambda: a.setzen(nur_seite=True, zs_flur=""), tipp="Filter auf den Flur aufheben")


def zs_zeichnen(a) -> None:
    if a.zs_modus == "flure":
        _flure_zeichnen(a)
        return
    if a.zs_modus == "frei":
        _frei_zeichnen(a)
        return
    from . import menueband_ui

    ende_ = a.zs_start + timedelta(days=a.zs_tage - 1)
    n_bel_ = sum(1 for z in a.daten for b in z.balken if b.art in ("belegt", "geplant", "konflikt"))
    filt = set(getattr(a, "zs_filter", ()) or ())
    if menueband_ui.werkzeuge_oben(a):
        _zs_band(a, ende_, n_bel_, sk.zeitstrahl_zaehlen(a.daten))
        _zs_inhalt(a, filt)
        return
    with a.werkzeuge:
        segmente({h: f"Haus {h}" for h in a.zs_haeuser}, a.zs_haus, lambda h: a.setzen(zs_haus=h, zs_flur=""))
        knopf("", lambda: a.setzen(zs_start=a.zs_start - timedelta(days=7)), "leise", "chevron_left", "Eine Woche zurück")
        knopf("Heute", lambda: a.setzen(zs_start=a.heute - timedelta(days=a.heute.weekday())), "leise")
        knopf("", lambda: a.setzen(zs_start=a.zs_start + timedelta(days=7)), "leise", "chevron_right", "Eine Woche weiter")
        _datum_waehlen(a)
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
        with ui.element("span").classes("m-legende m-legende-filter").style("margin-left: auto"):   # 1.00: als Filter
            for art, text in sk.ZS_ARTEN.items():
                k = ui.element("button").classes("m-lf" + (" an" if art in filt else ""))
                attr(k, title=f"Nur Zimmer mit „{text}“ (nochmal klicken: aus)", aria_pressed=str(art in filt).lower())
                with k:
                    ui.html(f'<i class="{art}"></i>{text}', sanitize=False)
                k.on("click", lambda art=art: _zs_filter(a, art))
        segmente({14: "2 Wochen", 28: "4 Wochen", 56: "8 Wochen"}, a.zs_tage, lambda t: a.setzen(zs_tage=t))
    _zs_inhalt(a, filt)


def _zs_inhalt(a, filt: set) -> None:
    with a.inhalt:
        if not a.daten:
            leer("Keine Zimmer in diesem Haus.")
            return
        zeilen = sk.zeitstrahl_filtern(a.daten, filt)
        if not zeilen:
            leer("Kein Zimmer erfüllt den Filter – im Menüband „Alle zeigen“ wählen.")
            return
        voll = a.daten
        a.daten = zeilen                      # _zs_html liest a.daten – nur für das Zeichnen gefiltert
        try:
            ui.html(_zs_html(a), sanitize=False).classes("m-zs-wrap")
        finally:
            a.daten = voll


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
        _datum_waehlen(a)
    flure = a.daten or []
    with a.leiste:
        segmente(ZS_MODUS, a.zs_modus, lambda m: a.setzen(nur_seite=True, zs_modus=m))
        zs = fk.zusammenfassung(flure)
        ui.html(f'<span class="m-kpi"><b>{len(flure)}</b> Flure<span class="m-punktt">·</span>diese Woche: '
                f'<b>{zs["ok"]}</b> mit 1 Welle, <b>{zs["warn"]}</b> mit 2, <b>{zs["krit"]}</b> mit 3+</span>', sanitize=False)
        ui.element("span").style("margin-left: auto")
        segmente({4: "4 Wochen", 8: "8 Wochen", 12: "12 Wochen"}, a.fl_wochen, lambda w: a.setzen(nur_seite=True, fl_wochen=w))
    with a.inhalt:
        if not flure:
            leer("Keine Zimmer im Gebäudeplan.")
            return
        hm_legende(
            "Je Flur und Woche: zu wie vielen Abreisewellen die lang belegten Zimmer gehören. Eine Abreisewelle = Auszüge "
            "im selben Reinigungsfenster (Wochenende zählt zum Montag, höchstens zwei Werktage). Wenige Wellen = wenige "
            "Reinigungstermine.",
            [("ok", "1 Welle", "gut – der Flur wird auf einmal frei"),
             ("warn", "2 Wellen", "zwei Reinigungstermine"),
             ("krit", "3+ Wellen", "zersplittert – bei neuen Zuteilungen auf diesen Flur achten"),
             ("leer", "–", "keine lang belegten Zimmer")],
            [("<b>2</b>", "große Zahl: Anzahl Wellen"), ("<span>5/8</span>", "lang belegte / alle Zimmer des Flurs"),
             ("<i>2 kurz · 1 M</i>", "kurze Aufenthalte (EMR, UWT, Gäste) und Mieter – nicht gewertet")],
            "Klick auf ein Feld zeigt die Wellen mit Zimmern.", art="fl")
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


def hm_legende(text: str, farben: list[tuple[str, str, str]], zeichen: list[tuple[str, str]], hinweis: str = "",
               art: str = "fl") -> None:
    """1.56: Ausführliche Legende über einer Heatmap: was wird gezählt, was heißt jede Farbe, was steht im Feld."""
    with ui.element("div").classes(f"m-hm-legende {art}"):
        ui.label(text).classes("m-ptext")
        teile = ['<div class="m-hm-farben">']
        for kl, titel, erkl in farben:
            teile.append(f'<span class="m-hm-f"><i class="m-{art}-z {kl}"></i><b>{E(titel)}</b> {E(erkl)}</span>')
        teile.append("</div>")
        if zeichen:
            teile.append('<div class="m-hm-zeichen">' + "".join(
                f'<span class="m-hm-k"><span class="m-{art}-muster">{muster}</span>{E(erkl)}</span>'
                for muster, erkl in zeichen) + "</div>")
        if hinweis:
            teile.append(f'<div class="m-zweite">{E(hinweis)}</div>')
        ui.html("".join(teile), sanitize=False)


def _frei_zeichnen(a) -> None:
    """1.56: Heatmap „Frei“ – je Zimmer und Woche, wie viel frei ist; Klick springt in den Belegungsplan."""
    from . import frei_kern as fr

    with a.werkzeuge:
        knopf("", lambda: a.setzen(nur_seite=True, zs_start=a.zs_start - timedelta(days=7)), "leise", "chevron_left",
              "Eine Woche zurück")
        knopf("Heute", lambda: a.setzen(nur_seite=True, zs_start=a.heute - timedelta(days=a.heute.weekday())), "leise")
        knopf("", lambda: a.setzen(nur_seite=True, zs_start=a.zs_start + timedelta(days=7)), "leise", "chevron_right",
              "Eine Woche weiter")
        _datum_waehlen(a)
    alle = a.daten or []
    zeilen = fr.sortieren(fr.filtern(alle, a.fr_nur, a.fr_min), a.fr_sort)
    with a.leiste:
        segmente(ZS_MODUS, a.zs_modus, lambda m: a.setzen(nur_seite=True, zs_modus=m))
        z = fr.zusammenfassung(alle)
        ui.html(f'<span class="m-kpi"><b>{z["jetzt"]}</b> diese Woche ganz frei<span class="m-punktt">·</span>'
                f'<b>{z["spaeter"]}</b> im Zeitraum frei<span class="m-punktt">·</span><b>{z["nie"]}</b> durchgehend '
                f'belegt</span>', sanitize=False)
        haeuser = {"": "Alle Häuser", **{h: f"Haus {h}" for h in getattr(a, "zs_haeuser", [])}}
        ui.select(haeuser, value=a.fr_haus if a.fr_haus in haeuser else "",
                  on_change=lambda e: a.setzen(nur_seite=True, fr_haus=e.value or "")).classes("m-feld").style("width: 150px").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        ui.select({0: "beliebig lange", 4: "mind. 4 Wochen am Stück", 8: "mind. 8 Wochen", 12: "mind. 12 Wochen",
                   26: "mind. 6 Monate"}, value=a.fr_min,
                  on_change=lambda e: a.setzen(nur_seite=True, fr_min=int(e.value or 0))).classes("m-feld").style("width: 210px").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        sw = ui.switch("nur Zimmer mit freier Zeit", value=a.fr_nur).props("dense")
        sw.on_value_change(lambda e: a.setzen(laden=False, fr_nur=bool(e.value)))
        ui.element("span").style("margin-left: auto")
        segmente(fr.SORTIERUNG, a.fr_sort, lambda s_: a.setzen(laden=False, fr_sort=s_))
        segmente({3: "3 Monate", 6: "6 Monate", 12: "12 Monate"}, a.fr_monate,
                 lambda m: a.setzen(nur_seite=True, fr_monate=m))
    with a.inhalt:
        hm_legende(
            f"Je Zimmer und Woche ab {a.zs_start - timedelta(days=a.zs_start.weekday()):%d.%m.%Y}: wie viel ist frei? Rechts "
            f"daneben, ab wann das Zimmer frei wird (ab {max(a.zs_start, a.heute):%d.%m.}, mindestens "
            f"{max(1, a.fr_min)} Woche{'n' if a.fr_min > 1 else ''} am Stück – kürzere Lücken zählen nicht) und wie lange. "
            "Geplante Belegungen und EMR-Reservierungen zählen als belegt.",
            [("frei", "ganz frei", "alle Betten, die ganze Woche"),
             ("teil", "teilweise frei", "einige Tage oder ein Bett im Doppelzimmer – je heller, desto weniger frei"),
             ("voll", "belegt", "kein Bett frei"),
             ("sperr", "gesperrt", "Renovierung oder Mangel „nicht bewohnbar“")],
            [], "Klick auf ein Feld öffnet den Belegungsplan des Hauses ab dieser Woche.", art="fr")
        if not zeilen:
            leer("Kein Zimmer passt – „mind. … Wochen“ verringern oder „nur Zimmer mit freier Zeit“ ausschalten.")
            return
        raster = ui.html(_frei_html(a, zeilen), sanitize=False).classes("m-fl-wrap")
        raster.on("click", lambda e: _frei_klick(a, e.args) if e.args else None,
                  js_handler="(e) => { const t = e.target.closest('[data-fr]'); emit(t ? t.dataset.fr : null); }")


def _frei_html(a, zeilen) -> str:
    from . import frei_kern as fr

    n = len(zeilen[0].zellen)
    teile = [f'<div class="m-fr" style="--wochen:{n}"><div class="m-fl-kopf"></div>']
    for i, c in enumerate(zeilen[0].zellen):
        kl = " heute" if c.woche <= a.heute <= c.woche + timedelta(days=6) else ""
        neu_monat = i == 0 or c.woche.month != zeilen[0].zellen[i - 1].woche.month
        txt = f"{fr_monat(c.woche)}" if neu_monat else ""
        teile.append(f'<div class="m-fl-kopf{kl}" title="KW {c.woche.isocalendar()[1]} · ab {c.woche:%d.%m.%Y}">'
                     f'{txt}<br><span>{c.woche.isocalendar()[1]}</span></div>')
    teile.append('<div class="m-fl-kopf">frei ab</div>')
    haus = None
    sortiert = a.fr_sort == "zimmer"
    for r in zeilen:
        if sortiert and r.haus != haus:
            haus = r.haus
            teile.append(f'<div class="m-fl-haus">Haus {E(haus)}</div>')
        teile.append(f'<div class="m-fr-lab" title="Haus {E(r.haus)} · {E(r.flur)}"><b>{E(r.kurz)}</b><span>{E(r.flur)}'
                     f'{" · DZ" if r.betten > 1 else ""}</span></div>')
        for c in r.zellen:
            titel = (f"{r.kurz} · KW {c.woche.isocalendar()[1]} ({c.woche:%d.%m.} – {c.woche + timedelta(days=6):%d.%m.})"
                     f"\n{fr.STUFE[c.stufe]} · {c.frei} von {c.moeglich} Bett-Nächten frei")
            stil = f' style="--anteil:{c.anteil:.2f}"' if c.stufe == "teil" else ""
            teile.append(f'<button class="m-fr-z {c.stufe}"{stil} data-fr="{E(r.haus)}#{c.woche.isoformat()}" '
                         f'title="{E(titel)}"></button>')
        teile.append(f'<div class="m-fr-txt{" gut" if r.ganz_frei_ab else ""}">{E(r.text)}</div>')
    teile.append("</div>")
    return "".join(teile)


def fr_monat(d: date) -> str:
    return ("Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez")[d.month - 1]


async def _frei_klick(a, arg: str) -> None:
    haus, _, woche = str(arg).partition("#")
    if not woche:
        return
    await a.setzen(nur_seite=True, zs_modus="zimmer", zs_haus=haus, zs_flur="", zs_start=date.fromisoformat(woche))


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

        a.fc_von, a.fc_bis = sk.fc_zeitraum(a.fc_zeitraum, a.heute, a.fc_von, a.fc_bis)
        a.daten = eintragen.facility_checks(a.stand.lage, a.fc_von, a.fc_bis)
        return
    if a.ansicht_von("reinigung", "liste") == "last":
        a.daten = sk.reinigung_last(a.stand, a.heute)
        return
    von, bis = sk.zeitraum(a.rg_zeitraum, a.heute)
    a.daten = sk.reinigung(a.stand, von, bis, a.heute)
    a.rg_von, a.rg_bis = von, bis


RG_SPALTEN = ("36px 70px minmax(80px, .8fr) 120px minmax(90px, 1fr) minmax(100px, .9fr) minmax(120px, 1.5fr) "
              "minmax(100px, 1.2fr) 140px 36px")


@unter_sperre                                  # 1.26: Laden, Prüfen und Speichern unter einer Sperre
def facility_setzen(schluessel: str, an: bool) -> str:
    from belegung import eintragen
    from belegung import zimmerplan as zp

    from .kern import _schritt

    heute = date.today()
    c = next((x for x in eintragen.facility_checks(zp.laden().lage, heute - timedelta(days=400), heute + timedelta(days=400))
              if x.schluessel == schluessel), None)
    if c is None:
        raise ValueError("Den Facility-Check gibt es nicht mehr.")
    _schritt("Facility-Check", lambda: eintragen.facility_setzen(c, an), [eintragen.FACILITY_DATEI])
    return f"Zimmer {zkurz(c.zimmer)}: Facility-Check " + ("erledigt" if an else "wieder offen")


def _facility(a) -> None:
    from belegung import eintragen

    alle = a.daten
    with a.werkzeuge:                                  # 0.82: Zeitraum wählbar, Druck in der Bildschirm-Reihenfolge
        segmente(sk.FC_ZEITRAUM, a.fc_zeitraum, lambda w: a.setzen(fc_zeitraum=w))
        if a.fc_zeitraum == "eigen":
            def _datum(feld: str, wert):
                try:
                    return a.setzen(**{feld: date.fromisoformat(wert or "")})
                except ValueError:
                    return None
            ui.input("von", value=a.fc_von.isoformat()).classes("m-feld").style("width:150px;flex:0 0 auto;order:15").props("dense outlined type=date")                 .on("change", lambda e: _datum("fc_von", e.sender.value))
            ui.input("bis", value=a.fc_bis.isoformat()).classes("m-feld").style("width:150px;flex:0 0 auto;order:15").props("dense outlined type=date")                 .on("change", lambda e: _datum("fc_bis", e.sender.value))
        knopf("Drucken", lambda: _fc_drucken(a), "", "print")
    n_offen = sum(1 for c in alle if not c.haken)
    with a.leiste:
        kennzahlen([("offen", n_offen, "offen", "akzent"), ("erledigt", len(alle) - n_offen, "erledigt", "ok"),
                    ("alle", len(alle), "alle", "neutral")], a.fc_filter, lambda f: a.setzen(fc_filter=f, laden=False))
        ui.label(f"{a.fc_von:%d.%m.} – {a.fc_bis:%d.%m.%Y}").classes("m-kpi")
        ui.html(f'<span class="m-kpi">Auszüge nach mindestens {round(eintragen.facility_tage() / 30.44)} Monaten: '
                f'{E(eintragen.FACILITY_AUFGABE)}</span>', sanitize=False)
    cs = [c for c in alle if a.fc_filter == "alle" or (a.fc_filter == "offen") != c.haken]
    sp = "36px 110px 90px minmax(160px, 1.4fr) minmax(120px, 1fr) 110px"
    with a.inhalt:
        if not cs:
            leer("Keine offenen Facility-Checks in diesem Zeitraum." if alle else "Keine Facility-Checks in diesem Zeitraum.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("", "Auszug", "Zimmer", "Bewohner", "Maßnahme", "Aufenthalt"):
                ui.label(t)
        for c in cs:
            zeile = ui.element("div").classes("m-raster m-zeile" + (" fertig" if c.haken else "")).style(f"grid-template-columns:{sp}")
            attr(zeile, data_rg=c.schluessel)
            with zeile:
                with ui.element("div"):
                    b = ui.element("button").classes("m-haken" + (" an" if c.haken else ""))
                    attr(b, title="Erledigt", aria_pressed=str(c.haken).lower())
                    with b:
                        ui.icon("check")
                    b.on("click", lambda c=c: a.aendern(facility_setzen, c.schluessel, not c.haken))
                ui.label(f"{c.bis:%d.%m.%Y}").classes("m-mono")
                ui.label(zkurz(c.zimmer)).classes("m-mono")
                ui.label(c.name).classes("m-name")
                ui.label(c.massnahme).classes("m-zweite")
                ui.label(f"{c.monate} Monate").classes("m-mono")


def rg_zeichnen(a) -> None:
    ansicht = a.ansicht_von("reinigung", "liste")
    with a.werkzeuge:
        segmente({"liste": "Reinigungsliste", "last": "Vorschau 6 Wochen", "facility": "Facility-Checks"}, ansicht,
                 lambda v: a.oeffnen("reinigung", ansicht=v), ansicht=True)
    if ansicht == "facility":
        return _facility(a)
    if ansicht == "last":
        return _rg_last(a)
    with a.werkzeuge:
        segmente(sk.ZEITRAUM, a.rg_zeitraum, lambda w: a.setzen(rg_zeitraum=w, rg_zimmer=""))
        knopf("Zimmer hinzufügen", lambda: _rg_hinzu_panel(a), "primaer", "add")
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
    nur = getattr(a, "rg_zimmer", "")
    if nur:                                    # 0.86: vom Besen an der Kachel – nur dieses Zimmer
        zs = [z for z in zs if z.schluessel.rsplit("|", 1)[0] == nur]
        with a.leiste:
            knopf(f"Nur Zimmer {zs[0].zimmer if zs else nur.split('|')[-1]} ✕", lambda: a.setzen(rg_zimmer="", laden=False),
                  "", "filter_alt_off", "Filter aufheben – alle Zimmer zeigen")
    with a.leiste:
        _mehrere_menue(a, [z for z in zs if not z.erledigt])
    if a.rg_zeitraum == "offen":
        with a.inhalt:
            ui.label(f"Alle nicht abgehakten Reinigungen der letzten {sk.OFFEN_ZURUECK} Tage und der nächsten Woche – genau "
                     "die, wegen derer ein Zimmer in der Übersicht den Besen trägt. Erledigte abhaken, dann verschwindet "
                     "der Besen.").classes("m-ptext").style("margin:12px 20px 0")
    with a.inhalt:
        if not zs:
            leer("Keine offenen Reinigungen in diesem Zeitraum." if a.daten else "Keine Reinigungen in diesem Zeitraum.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{RG_SPALTEN}"):
            for t in ("", "Zimmer", "Lage", "Heute", "Art", "Auszug", "Danach", "Sauber bis", "Priorität", ""):
                ui.label(t)
        for z in zs:
            zeile = ui.element("div").classes("m-raster m-zeile" + (" fertig" if z.erledigt else "")).style(
                f"grid-template-columns:{RG_SPALTEN}")
            attr(zeile, data_rg=z.schluessel)                 # 0.81: Druck übernimmt die Bildschirm-Reihenfolge
            with zeile:
                with ui.element("div"):
                    b = ui.element("button").classes("m-haken" + (" an" if z.erledigt else ""))
                    attr(b, title="Als gereinigt markieren" if not z.erledigt else "Wieder offen", aria_pressed=str(z.erledigt).lower())
                    with b:
                        ui.icon("check")
                    b.on("click", lambda z=z: a.aendern(sk.reinigung_setzen, [z.schluessel], not z.erledigt, a.rg_von, a.rg_bis))
                attr(ui.label(z.zimmer).classes("m-name"), title=z.details)
                ui.label(z.lage).classes("m-zweite")
                with ui.element("div"):                 # 0.80: belegt oder frei – auf einen Blick
                    if z.heute:
                        badge(z.heute, sk.ZUSTAND_HEUTE.get(z.heute, z.heute))
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


# 0.81: Reihenfolge der Zeilen, wie sie gerade auf dem Bildschirm steht (Spaltensortierung per Klick auf die
# Überschrift wirkt nur im Browser über style.order) – plus die gewählte Spalte für den Untertitel.
RG_REIHENFOLGE_JS = """(() => {
  const z = [...document.querySelectorAll('[data-rg]')];
  const o = (e) => e.style.order === '' ? 0 : parseInt(e.style.order, 10);
  z.sort((a, b) => o(a) - o(b));
  const s = document.querySelector('.m-tkopf > .m-sort-auf, .m-tkopf > .m-sort-ab');
  return { k: z.map(e => e.getAttribute('data-rg')),
           s: s ? s.innerText.trim() + (s.classList.contains('m-sort-ab') ? ' (absteigend)' : '') : '' };
})()"""


async def _bildschirm_reihenfolge() -> dict:
    try:
        return await ui.run_javascript(RG_REIHENFOLGE_JS, timeout=3) or {}
    except Exception:                       # noqa: BLE001 – ohne Antwort: übliche Reihenfolge
        return {}


async def _fc_drucken(a) -> None:
    info = await _bildschirm_reihenfolge()
    text = await run.io_bound(sk.facility_druck, a.fc_von, a.fc_bis, a.heute, list(info.get("k") or []),
                              str(info.get("s") or ""), a.fc_filter)
    html_drucken(a, text, f"Facility-Checks_{a.fc_von:%Y-%m-%d}")


async def _rg_drucken(a) -> None:
    info = await _bildschirm_reihenfolge()
    text = await run.io_bound(sk.reinigung_druck, a.rg_von, a.rg_bis, a.heute, list(info.get("k") or []),
                              str(info.get("s") or ""))
    html_drucken(a, text, f"Reinigungsliste_{a.rg_von:%Y-%m-%d}")


DRUCK_STUNDEN = 24


def druck_ordner(jetzt: float | None = None) -> Path:
    """1.26: Druckansichten in einem eigenen Unterordner von %TEMP% – Dateien älter als 24 Stunden werden dabei
    gelöscht (sie enthalten Namen und gehören nicht dauerhaft auf den PC)."""
    import time

    ordner = Path(tempfile.gettempdir()) / "INNternat_Druck"
    ordner.mkdir(parents=True, exist_ok=True)
    grenze = (time.time() if jetzt is None else jetzt) - DRUCK_STUNDEN * 3600
    for f in ordner.glob("*.html"):
        try:
            if f.stat().st_mtime < grenze:
                f.unlink()
        except OSError:
            pass
    return ordner


def html_drucken(a, text: str, name: str) -> None:
    """Druckansicht im Standardbrowser öffnen (dort drucken oder als PDF speichern)."""
    pfad = druck_ordner() / f"{name}.html"
    if "</body>" in text:
        text = text.replace("</body>", "<script>window.print()</script></body>")
    else:
        text = f"<!doctype html><meta charset='utf-8'>{text}<script>window.print()</script>"
    pfad.write_text(text, encoding="utf-8")
    if _datei_oeffnen(str(pfad)):
        a.toast("Druckansicht geöffnet – dort drucken oder als PDF speichern", rueck=False)
    else:
        ablage = getattr(a, "dialog_ablage", None)     # 1.63: übersteht das Neuzeichnen (z. B. nach dem Speichern)
        if ablage is not None:
            with ablage:
                ui.navigate.to(f"/druck/{pfad.name}", new_tab=True)
        else:
            ui.navigate.to(f"/druck/{pfad.name}", new_tab=True)


# =======================================================================================
# Mieter
# =======================================================================================

MT_ANSICHTEN = {"gaeste": "Gäste", "mieter": "Mieter"}      # 1.49: Bereich „Gäste & Mieter“


def mt_daten(a) -> None:
    from belegung import mieter as mt

    from . import mietbindung as mb

    if a.ansicht_von("mieter", "mieter") == "gaeste":
        from belegung import zimmerplan as zp

        from . import gaeste_kern as gk

        a.daten = gk.liste(zp.laden(), a.heute)
        return
    a.daten = sk.mieter(a.heute)
    try:                                       # 1.63: Kündigungen
        from . import kuendigung_kern as kk

        a.mt_kuendigungen = kk.laden()
    except Exception:                          # noqa: BLE001
        a.mt_kuendigungen = {}
    try:                                       # 1.48: automatische Verlängerung je Vertrag, fällige
        a.mt_auto = mb.auto()
        a.mt_faellig = {f.nr: f for f in mb.auto_faellig(mt.laden(), a.heute, a.mt_auto)}
    except Exception:                          # noqa: BLE001
        a.mt_auto, a.mt_faellig = {}, {}


MT_SPALTEN = "28px 70px minmax(160px, 1.3fr) 90px 190px minmax(120px, 1fr) minmax(170px, 1fr) 76px"


def mt_zeichnen(a) -> None:
    ansicht = a.ansicht_von("mieter", "mieter")
    with a.werkzeuge:
        segmente(MT_ANSICHTEN, ansicht, lambda v: a.oeffnen("mieter", ansicht=v))
    if ansicht == "gaeste":
        _gaeste_zeichnen(a)
        return
    vertraege, weitere = a.daten
    offen = [m for m in vertraege if m.mail_offen]
    with a.leiste:
        laufend = sum(1 for m in vertraege if m.bis >= a.heute)
        kennzahlen([("laufend", laufend, "laufende Verträge", "ok"), ("mail", len(offen), "Mail zum Vertragsende offen",
                                                                       "warn" if offen else "neutral"),
                    ("weitere", len(weitere), "weitere laut Gebäudeplan", "neutral")], a.mt_filter,
                   lambda f: a.setzen(mt_filter=None if f == a.mt_filter else f, laden=False))
        knopf("Neuer Mieter", lambda: mieter_neu_panel(a), "primaer", "person_add").style("margin-left:auto")
        knopf("Vorlagen", lambda: _vorlagen(a), "leise", "description", "Vertragstext, Vordrucke und Logo für Mietverträge")
    with a.inhalt:
        from . import vorlagen_mieter_ui                  # 1.68: fehlt der Vertragstext, steht es hier gleich oben
        vorlagen_mieter_ui.hinweis(a)
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
                    with ui.element("div"):
                        ui.label(m.status).classes("m-zweite")
                        if (kd := (getattr(a, "mt_kuendigungen", None) or {}).get(m.nr)) is not None:     # 1.63
                            from . import kuendigung_kern as kk

                            ui.label(kk.status_text(kd)).classes("m-pille warn")
                        auto_n = (getattr(a, "mt_auto", None) or {}).get(m.nr)
                        if (f := (getattr(a, "mt_faellig", None) or {}).get(m.nr)) is not None:
                            knopf(f"Verlängern bis {f.neu:%d.%m.%Y}", lambda m=m, f=f: _verlaengern_direkt(a, m.nr, f.neu),
                                  "gruen", "update", f"Automatische Verlängerung um {f.monate} Monate: Nebenabrede erstellen")
                        elif auto_n and m.bis >= a.heute:
                            ui.label(f"automatisch +{auto_n} Monate").classes("m-zweite")
                    with ui.element("div").classes("m-hinweis"):
                        if m.mail_offen:
                            knopf("Mail vorbereiten", lambda m=m: _mail_panel(a, m), "gruen", "mail")
                        elif m.mail_am:
                            ui.label(f"vorbereitet am {date.fromisoformat(m.mail_am):%d.%m.%Y}").classes("t")
                            knopf("", lambda m=m: _mail_panel(a, m), "leise", "mail", "Noch einmal vorbereiten")
                        elif m.bis >= a.heute:
                            knopf("Mail", lambda m=m: _mail_panel(a, m), "leise", "mail", "Mail zum Vertragsende vorbereiten")
                    with ui.element("div").classes("m-paktionen").style("padding:0; flex-wrap:nowrap"):
                        _mt_optionen(a, m)                 # 1.48: ein Menü statt drei kleiner Symbole
        if weitere and a.mt_filter in (None, "weitere"):
            ui.label("Weitere Mieter laut Gebäudeplan (ohne Vertrag in diesem Programm)").classes("m-abschnitt")
            for name, zimmer, zeit, zid, w_von, w_bis in weitere:
                with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{MT_SPALTEN}"):
                    ui.label("")
                    ui.label("–").classes("m-mono")
                    ui.label(name).classes("m-name")
                    ui.label(zimmer).classes("m-mono")
                    ui.label(zeit).classes("m-mono")
                    ui.label("")
                    with ui.element("div"):               # 1.63: aus dem Gebäudeplan einen Vertrag machen
                        from . import kuendigung_kern as kk

                        knopf("Vertrag anlegen", lambda n=name, z=zid, v=w_von, b=w_bis: mieter_neu_panel(
                            a, kk.vorgabe(n, z, v, b)), "leise", "post_add",
                              "Neuen Mietvertrag mit Name, Zimmer und Zeitraum aus dem Gebäudeplan vorbereiten")
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


async def _akte(a, m) -> None:
    from belegung import mieter as mt

    from . import mieter_akte_ui

    mv = await run.io_bound(mt.nach_nummer, m.nr)               # die Zeile der Liste ist nicht der Vertrag selbst
    if mv is None:
        a.toast("Den Vertrag gibt es nicht mehr.", fehler=True, rueck=False)
        return
    await mieter_akte_ui.panel(a, mv)


async def _vorlagen(a) -> None:
    from . import vorlagen_mieter_ui

    await vorlagen_mieter_ui.panel(a)


def mieter_neu_panel(a, vorgabe: dict | None = None) -> None:
    """``vorgabe`` (1.63): Werte aus dem Gebäudeplan (Vorname, Nachname, Zimmer, von, bis)."""
    from belegung import mieter as mt
    from belegung import speicher

    from . import mieter_kern as mk

    def bauen():
        from . import vorlagen_mieter_ui                  # 1.68: Vertragstext fehlt → gleich hier sagen, nicht erst beim Speichern
        vorlagen_mieter_ui.hinweis(a, True)
        ui.label("Mietvertrag und die angehakten Vordrucke in einer PDF – der Mieter wird im Zimmerplan eingetragen. "
                 "Die Vertragsnummer vergibt das Programm beim Erstellen (fortlaufend, ohne Doppelte).").classes("m-ptext")
        with ui.element("div").classes("m-zweispaltig"):
            anrede = ui.select(mk.ANREDEN, value="Frau", label="Anrede").classes("m-feld").props(
                'dense outlined dark options-dense popup-content-class="m-popup"')
            nr = ui.input("Vertragsnummer (automatisch)", value=mt.naechste_nummer()).classes("m-feld").props(
                "dense outlined dark readonly")
            attr(nr, title="Wird beim Erstellen fest vergeben – immer die nächste freie Nummer, auch wenn gerade an "
                           "einem anderen PC ein Vertrag entsteht")
            vg = vorgabe or {}
            vor = ui.input("Vorname", value=vg.get("vorname", "")).classes("m-feld").props("dense outlined dark")
            nach = ui.input("Nachname", value=vg.get("nachname", "")).classes("m-feld").props("dense outlined dark")
            von = ui.input("Mietbeginn", value=(vg.get("von") or a.heute).isoformat()).classes("m-feld").props(
                "dense outlined dark type=date")
            bis = ui.input("Mietende", value=(vg.get("bis") or mt.standard_ende(a.heute)).isoformat()).classes("m-feld").props(
                "dense outlined dark type=date")
            miete = ui.number("Miete (€)", value=mt.STANDARD_MIETE, min=0, step=10).classes("m-feld").props("dense outlined dark")
            flaeche = ui.number("Fläche (m²)", value=mt.STANDARD_FLAECHE, min=1, step=1, format="%d").classes("m-feld").props(
                "dense outlined dark")
            schl = ui.number("Schlüssel", value=1, min=0, step=1, format="%d").classes("m-feld").props("dense outlined dark")
            mail = ui.input("E-Mail (optional)").classes("m-feld").props("dense outlined dark")
        adresse = ui.input("Anschrift vor Einzug (optional, steht im Vertrag)",
                           placeholder="Straße Nr., PLZ Ort").classes("m-feld").props("dense outlined dark")
        woher = ui.label("Vertragsnummer wird abgeglichen …").classes("m-zweite")
        hand = ui.switch("Nummer von Hand vergeben (Ausnahme)").props("dense color=orange")
        hand.on_value_change(lambda e: nr.props(remove="readonly") if e.value else nr.props(add="readonly"))
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
            try:
                v = date.fromisoformat(von.value)
            except (TypeError, ValueError):
                v = a.heute
            vorschlag, text = await run.io_bound(mk.nummer_vorschlag, v, a.heute)
            if setzen or nr.value == zuletzt["vorschlag"]:
                nr.value = vorschlag               # eigene Eingabe bleibt; der Vorschlag folgt dem Vertragsjahr
            zuletzt["vorschlag"] = vorschlag
            woher.text = f"Vorschlag {vorschlag} · {text} · Jahr = Jahr des Vertrags bzw. des Mietbeginns"
        zuletzt = {"vorschlag": nr.value}
        ui.timer(0.05, nummer_holen, once=True)
        zimmer = ui.select({}, label="Zimmer", with_input=True).classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        alle = ui.switch("auch Zimmer zeigen, die nicht passen").props("dense color=primary")
        kaution = ui.switch("Mietsicherheit (Kaution) vereinbaren", value=False).props("dense color=primary")
        flex = ui.switch("Flexibler Mietvertrag (abweichende Textstellen)", value=False).props("dense color=primary")
        vorhanden = mk.dokumente_vorhanden()                # 1.69: welche Vordrucke kommen in die Unterlagen?
        standard = mk.dokumente_standard()
        doks = {}
        if vorhanden:
            ui.label("Anhängen:").classes("m-zweite")
            with ui.element("div").classes("m-zeile-flex").style("gap:4px 14px;flex-wrap:wrap"):
                for d in vorhanden:
                    doks[d] = ui.checkbox(mk.DOKUMENTE[d], value=d in standard).props("dense color=primary")
        attr(flex, title="Nur für die Ausnahme: nimmt die Zeilen mit „?flexibel“ aus der Vorlage Mietvertrag.vorlage")
        trotz = ui.checkbox("Zimmer trotzdem nehmen, obwohl es laut Plan nicht passt (z. B. bis dahin fertig renoviert) – "
                            "ich habe es geprüft", value=bool(vorgabe)).props("dense color=orange")
        if vorgabe:                                   # 1.63: das Zimmer ist durch genau diesen Mieter (Gebäudeplan) belegt
            ui.label("Das Zimmer ist laut Gebäudeplan durch diese Person belegt – deshalb ist „trotzdem nehmen“ schon "
                     "angehakt. Bitte Name und Zeitraum kurz prüfen.").classes("m-zweite")

        async def zimmer_fuellen():
            try:
                v, b = date.fromisoformat(von.value), date.fromisoformat(bis.value)
            except (TypeError, ValueError):
                return
            opt = await run.io_bound(mk.zimmer_auswahl, v, b, anrede.value, bool(alle.value), vorgabe_person)
            wunsch = zimmer.value or (vorgabe or {}).get("zimmer")
            if wunsch and wunsch not in opt:             # 1.63: Zimmer aus dem Gebäudeplan immer anbieten
                opt = {wunsch: f"{zkurz(wunsch)} (laut Gebäudeplan)", **opt}
            zimmer.set_options(opt, value=wunsch or None)

        vorgabe_person = ""

        def beginn():
            if vorgabe:                                   # 1.63: Ende aus dem Gebäudeplan nicht überschreiben
                return
            try:
                bis.value = mt.standard_ende(date.fromisoformat(von.value)).isoformat()
            except (TypeError, ValueError):
                pass

        async def beginn_geaendert(_e=None):            # 1.71: beide abwarten – sonst liefen sie nie (Nummer blieb im alten Jahr)
            beginn()
            await zimmer_fuellen()
            await nummer_holen()
        von.on_value_change(beginn_geaendert)
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
                     "flexibel": bool(flex.value), "trotzdem": bool(trotz.value), "nr_auto": not hand.value,
                     "anschrift": adresse.value or "", "dokumente": [d for d, cb in doks.items() if cb.value]}
            if await _mit_datei(a, mk.neuer_vertrag, werte):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Unterlagen erstellen", erstellen, "primaer", "description")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Vertrag aus dem Gebäudeplan" if vorgabe else "Neuer Mieter", bauen, breit=True)


def vertrag_bearbeiten_panel(a, nr: str) -> None:
    """0.60: Erstellten Vertrag korrigieren – alle Angaben außer der Nummer; der Zimmerplan zieht mit."""
    from belegung import mieter as mt

    from . import mieter_kern as mk

    mv = mt.nach_nummer(nr)
    if mv is None:
        a.toast("Den Vertrag gibt es nicht mehr.", fehler=True)
        return

    def bauen():
        ui.label(f"Mietvertrag {mv.nr} · {mv.name} – Änderungen (auch die Vertragsnummer) werden im Zimmerplan "
                 "übernommen und im Verlauf vermerkt. Rückgängig wie immer.").classes("m-ptext")
        with ui.element("div").classes("m-zweispaltig"):
            anrede = ui.select(mk.ANREDEN, value=mv.anrede, label="Anrede").classes("m-feld").props(
                'dense outlined dark options-dense popup-content-class="m-popup"')
            nr_feld = ui.input("Vertragsnummer", value=mv.nr).classes("m-feld").props("dense outlined dark")
            vor = ui.input("Vorname", value=mv.vorname).classes("m-feld").props("dense outlined dark")
            nach = ui.input("Nachname", value=mv.nachname).classes("m-feld").props("dense outlined dark")
            von = ui.input("Mietbeginn", value=mv.von.isoformat()).classes("m-feld").props("dense outlined dark type=date")
            bis = ui.input("Mietende", value=mv.bis.isoformat()).classes("m-feld").props("dense outlined dark type=date")
            miete = ui.number("Miete (€)", value=mv.miete, min=0, step=10).classes("m-feld").props("dense outlined dark")
            flaeche = ui.number("Fläche (m²)", value=mv.flaeche, min=1, step=1, format="%d").classes("m-feld").props(
                "dense outlined dark")
            schl = ui.number("Schlüssel", value=mv.schluessel, min=0, step=1, format="%d").classes("m-feld").props(
                "dense outlined dark")
            mail = ui.input("E-Mail (optional)", value=mv.email).classes("m-feld").props("dense outlined dark")
        zimmer = ui.select({mv.zimmer: mv.zimmer_kurz}, value=mv.zimmer, label="Zimmer", with_input=True).classes(
            "m-feld").props('dense outlined dark options-dense popup-content-class="m-popup"')
        alle = ui.switch("auch Zimmer zeigen, die nicht passen").props("dense color=primary")
        kaution = ui.switch("Mietsicherheit (Kaution) vereinbart", value=mv.kaution).props("dense color=primary")
        flex = ui.switch("Flexibler Mietvertrag", value=mv.nr in mk.flexible()).props("dense color=primary")
        neu_erstellen = ui.switch("Unterlagen gleich neu erstellen (PDF)", value=True).props("dense color=primary")
        trotz = ui.checkbox("Zimmer trotzdem nehmen, obwohl es laut Plan nicht passt (z. B. bis dahin fertig renoviert) – "
                            "ich habe es geprüft").props("dense color=orange")
        jahr_hinweis = ui.element("div").classes("m-zeile-flex").style("gap:8px; flex-wrap:wrap")

        async def jahr_pruefen():
            try:
                v = date.fromisoformat(von.value)
            except (TypeError, ValueError):
                return
            erstellt = date.fromisoformat(mv.erstellt[:10]) if mv.erstellt[:10].count("-") == 2 else a.heute
            jj = f"{mk.vertragsjahr(v, erstellt) % 100:02d}"
            jahr_hinweis.clear()
            if not (nr_feld.value or "").startswith(jj + "-"):
                vorschlag = (await run.io_bound(mk.nummer_vorschlag, v, erstellt))[0]
                with jahr_hinweis:
                    ui.label(f"Die Nummer passt nicht zum Vertragsjahr 20{jj} – Vorschlag {vorschlag}.").classes(
                        "m-warn-text")
                    knopf(f"{vorschlag} übernehmen", lambda: nr_feld.set_value(vorschlag), "leise", "auto_fix_high")
                    ui.label("Die neue Nummer gilt ab jetzt; die Unterlagen werden mit ihr neu erstellt (die alten "
                             "Dateien bleiben liegen).").classes("m-zweite")
        nr_feld.on_value_change(lambda _e: jahr_pruefen())
        von.on_value_change(lambda _e: jahr_pruefen())
        ui.timer(0.05, jahr_pruefen, once=True)
        if mv.verlaengerungen:
            ui.label(f"Hinweis: Der Vertrag wurde schon {len(mv.verlaengerungen)}× verlängert – das Mietende hier ist das "
                     "aktuelle (nach der letzten Nebenabrede).").classes("m-zweite").style("white-space:normal")

        async def zimmer_fuellen():
            try:
                v, b = date.fromisoformat(von.value), date.fromisoformat(bis.value)
            except (TypeError, ValueError):
                return
            opt = await run.io_bound(mk.zimmer_auswahl, v, b, anrede.value, bool(alle.value), mv.person)
            if zimmer.value and zimmer.value not in opt:
                opt = {zimmer.value: f"{zimmer.value.removeprefix('GS-')} (passt im Zeitraum nicht)", **opt}
            zimmer.set_options(opt, value=zimmer.value)

        for feld in (von, bis, alle, anrede):
            feld.on_value_change(lambda _e: zimmer_fuellen())
        ui.timer(0.05, zimmer_fuellen, once=True)

        async def speichern():
            try:
                v, b = date.fromisoformat(von.value), date.fromisoformat(bis.value)
            except (TypeError, ValueError):
                a.toast("Bitte Beginn und Ende wählen.", fehler=True)
                return
            werte = {"nr": nr_feld.value or mv.nr, "trotzdem": bool(trotz.value),
                     "anrede": anrede.value, "vorname": vor.value or "", "nachname": nach.value or "",
                     "zimmer": zimmer.value, "von": v, "bis": b, "miete": miete.value or 0, "flaeche": flaeche.value or 1,
                     "schluessel": schl.value or 0, "kaution": kaution.value,
                     "kaution_bis": mv.kaution_bis if mv.kaution and mv.von == v else v, "email": mail.value or "",
                     "flexibel": bool(flex.value)}
            ergebnis = {}

            def los():
                text, pfad = mk.vertrag_aendern(mv.nr, werte, bool(neu_erstellen.value))
                ergebnis["pfad"] = pfad
                return text
            if await a.aendern(los):
                if ergebnis.get("pfad") and not _datei_oeffnen(str(ergebnis["pfad"])):
                    a.toast(f"Gespeichert: {ergebnis['pfad']}", rueck=False)
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Änderungen speichern", speichern, "primaer", "save")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel(f"Vertrag bearbeiten · MV {mv.nr}", bauen, breit=True)


def _mt_optionen(a, m) -> None:
    """1.48: „Optionen“ je Vertrag – Verlängern, automatisch verlängern, bearbeiten, Unterlagen, Mail."""
    from . import mietbindung as mb

    auto_n = (getattr(a, "mt_auto", None) or {}).get(m.nr)
    with knopf("Optionen", None, "leise", "more_horiz", "Mietvertrag verlängern, bearbeiten, Unterlagen …"):
        with ui.menu().props('dark class="m-menue"'):
            ui.menu_item("Mietvertrag verlängern …", lambda m=m: verlaengern_panel(a, m))
            for n in mb.MONATE:
                ui.menu_item(f"Um {n} Monate verlängern (bis {mb.neues_ende(m.bis, n):%d.%m.%Y})",
                             lambda m=m, n=n: verlaengern_panel(a, m, n))
            ui.separator()
            for n in mb.MONATE:
                ui.menu_item(("✓ " if auto_n == n else "") + f"Automatisch verlängern: je {n} Monate",
                             lambda m=m, n=n: a.aendern(mb.auto_setzen, m.nr, n))
            if auto_n:
                ui.menu_item("Automatische Verlängerung aus", lambda m=m: a.aendern(mb.auto_setzen, m.nr, None))
            ui.separator()
            ui.menu_item("Vertrag bearbeiten (z. B. Zimmer) …", lambda m=m: vertrag_bearbeiten_panel(a, m.nr))
            ui.menu_item("Mieter-Akte (Unterlagen) …", lambda m=m: _akte(a, m))          # 1.72
            ui.menu_item("Unterlagen neu erstellen", lambda m=m: _unterlagen(a, m.nr))
            ui.menu_item("Mail zum Vertragsende …", lambda m=m: _mail_panel(a, m))
            ui.separator()                                  # 1.63
            if m.nr in (getattr(a, "mt_kuendigungen", None) or {}):
                ui.menu_item("Kündigungsbestätigung drucken", lambda m=m: _kuendigung_drucken(a, m.nr))
                ui.menu_item("Kündigung zurücknehmen", lambda m=m: _kuendigung_zurueck(a, m.nr))
            else:
                ui.menu_item("Kündigung erfassen …", lambda m=m: kuendigung_panel(a, m))


def kuendigung_panel(a, m) -> None:
    """1.63: Kündigung erfassen – Eingang, zum (letzter Miettag), wer, Grund. Das Vertragsende wird vorgezogen."""
    from . import kuendigung_kern as kk

    def bauen():
        ui.label(f"MV {m.nr} · {m.name} · Zimmer {m.zimmer} · bisher bis {m.bis:%d.%m.%Y}").classes("m-ptext")
        with ui.element("div").classes("m-zweispaltig"):
            eingang = ui.input("Kündigung eingegangen am", value=a.heute.isoformat()).classes("m-feld").props(
                "dense outlined dark type=date")
            zum = ui.input("Gekündigt zum (letzter Miettag)", value=m.bis.isoformat()).classes("m-feld").props(
                "dense outlined dark type=date")
        wer = ui.select({k: v for k, v in kk.WER.items()}, value="mieter", label="Kündigung").classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        grund = ui.input("Grund / Notiz (optional)").classes("m-feld w-full").props("dense outlined dark")
        ui.label("Das Vertragsende wird auf den Kündigungstermin gesetzt – das Zimmer ist im Plan danach frei. "
                 "Zurücknehmen stellt das alte Ende wieder her.").classes("m-ptext")

        async def speichern():
            try:
                e, z = date.fromisoformat(eingang.value), date.fromisoformat(zum.value)
            except (TypeError, ValueError):
                a.toast("Bitte beide Daten wählen.", fehler=True)
                return
            if await a.aendern(kk.kuendigen, m.nr, z, e, wer.value, grund.value or ""):
                a.panel_zu()
                await _kuendigung_drucken(a, m.nr)

        with ui.element("div").classes("m-paktionen"):
            knopf("Kündigung speichern und Bestätigung drucken", speichern, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Kündigung", bauen)


async def _kuendigung_drucken(a, nr: str) -> None:
    from belegung import mieter as mt

    from . import kuendigung_kern as kk

    k = (await run.io_bound(kk.laden)).get(nr)
    mv = await run.io_bound(mt.nach_nummer, nr)
    if k is None or mv is None:
        a.toast("Keine Kündigung zu diesem Vertrag gefunden.", fehler=True)
        return
    html_drucken(a, kk.bestaetigung_html(mv, k), f"Kuendigung_MV{nr}")


async def _kuendigung_zurueck(a, nr: str) -> None:
    from . import kuendigung_kern as kk

    await a.aendern(kk.zuruecknehmen, nr)


async def _verlaengern_direkt(a, nr: str, bis) -> None:
    from . import mieter_kern as mk

    await _mit_datei(a, mk.verlaengern, nr, bis)


def verlaengern_panel(a, m, monate: int | None = None) -> None:
    from belegung import mieter as mt

    from . import mieter_kern as mk

    def bauen():
        ui.label(f"{m.name} · Zimmer {m.zimmer} · bisher bis {m.bis:%d.%m.%Y}. Erstellt die Nebenabrede (Word und PDF) "
                 "und verlängert den Eintrag im Zimmerplan.").classes("m-ptext")
        from . import mietbindung as mb

        start = mb.neues_ende(m.bis, monate) if monate else mt.standard_ende(m.bis + timedelta(days=1))
        bis = ui.input("Neues Mietende", value=start.isoformat()).classes("m-feld").props("dense outlined dark type=date")
        with ui.element("div").classes("m-paktionen"):         # 1.48: schnell +3/+6/+12 Monate
            for n in mb.MONATE:
                knopf(f"+{n} Monate", lambda n=n: bis.set_value(mb.neues_ende(m.bis, n).isoformat()), "leise", "add")

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
            from . import versand_protokoll as vp      # 1.59

            await run.io_bound(vp.eintragen, "mieter", "Standard-Mailprogramm" if link else "Outlook-Entwurf",
                               an.value.strip(), betreff.value or "", text.value or "")
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
        knopf("Grenzen ändern", lambda: a.oeffnen("einstellungen", ansicht="allgemein"), "leise", "straighten").style("margin-left:auto")
    with a.inhalt:
        _engpass_heatmap(a, aw)
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
                                pil = ui.element("button").classes(f"m-pille m-klickbar {STUFE_AW[w.stufen.get(art, 'ok')]}")
                                attr(pil, title="Klick: wo genau frei bzw. knapp")
                                with pil:
                                    ui.label(str(wert))
                                pil.on("click", lambda w=w, art=art: _engpass_panel(a, w, art))
                        eng = [(art, n) for art, n in (("gesamt", "Zimmer"), ("emr", "EMR"), ("doppel", "Doppelzimmer"))
                               if w.stufen.get(art, "ok") != "ok"]
                        with ui.element("div").classes("m-zeile-flex").style("gap:4px"):
                            ui.label({"ok": "ok", "knapp": "knapp", "kritisch": "kritisch"}[w.stufe] + (" –" if eng else "")).classes(
                                "m-zweite" + (" m-krit" if w.stufe == "kritisch" else " m-warn" if w.stufe == "knapp" else ""))
                            for art, n in eng:
                                lk = ui.element("button").classes("m-link-knopf")
                                attr(lk, title=f"Wo ist es bei {n} knapp?")
                                with lk:
                                    ui.label(n)
                                lk.on("click", lambda w=w, art=art: _engpass_panel(a, w, art))
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


def _engpass_heatmap(a, aw) -> None:
    """0.75: Wo wird es eng? – Woche × Art als Heatmap. Zahl = frei; orange = knapp, rot = kritisch (mit Symbol, nicht nur
    Farbe); Klick → Einzelheiten der Woche im Detailpanel. ƒx zeigt, wie gezählt wird."""
    from . import diagramm_ui

    if not aw.wochen:
        return
    zeilen = [("frei_nach_planung", "Frei nach Planung", "gesamt", lambda w: w.frei_nach),
              ("emr", "EMR", "emr", lambda w: w.emr), ("doppel", "Doppel UWT", "doppel", lambda w: w.doppel),
              ("frei_jetzt", "Frei jetzt", None, lambda w: w.frei_jetzt)]
    hoch = max([w.frei_jetzt for w in aw.wochen] + [1])
    with ui.element("section").classes("m-block m-heat-block"):
        with ui.element("div").classes("m-heat-kopf"):
            ui.label("Wo wird es eng? · Woche × Art").classes("m-btitel")
            ui.label("Zahl = frei · orange = knapp · rot = kritisch · Klick: Einzelheiten").classes("m-zweite")
            fx = ui.element("button").classes("m-dg-knopf")
            with fx:
                ui.html("<b>ƒx</b> Berechnung", sanitize=False)
            fx.on("click", js_handler="(e) => { const b = e.target.closest('button'); b.classList.toggle('an', "
                                      "b.closest('section').querySelector('.m-fx').classList.toggle('offen')); }")
        with ui.element("div").classes("m-heat").style(f"grid-template-columns: 150px repeat({len(aw.wochen)}, minmax(44px, 1fr))"):
            ui.label("")
            for w in aw.wochen:
                ui.label(w.kw.split(" · ")[0]).classes("m-heat-kw")
            for _schluessel, name, art, wert in zeilen:
                ui.label(name).classes("m-heat-name")
                for w in aw.wochen:
                    st = w.stufen.get(art, "ok") if art else "ok"
                    z = wert(w)
                    b = ui.element("button").classes(f"m-heat-zelle {STUFE_AW.get(st, 'ok')}")
                    if st == "ok":
                        b.style(f"--anteil: {min(1.0, max(0.0, z / hoch)):.2f}")
                    attr(b, title=f"{w.kw} · {name}: {z} frei" + ("" if st == "ok" else f" – {st}"),
                         aria_label=f"{w.kw} {name} {z} frei {st}")
                    with b:
                        if st != "ok":
                            ui.icon("warning" if st == "knapp" else "error_outline")
                        ui.label(str(z))
                    b.on("click", lambda w=w, art=art: _engpass_panel(a, w, art or "gesamt"))
        diagramm_ui.fx_kasten([(k, {}, []) for k, *_r in zeilen])


def _engpass_panel(a, w, art: str) -> None:
    """Einzelheiten einer Woche: freie Zimmer je Tag, welche Zimmer frei, teilweise frei, belegt – und von wem."""
    from belegung import eintragen

    aw: sk.Auswertung = a.daten
    if w.montag is None:
        return
    d = sk.engpass_detail(a.stand, aw.lage, w.montag, art, a.heute)
    namen = {"gesamt": "Zimmer", "emr": "EMR-Zimmer", "doppel": "Doppelzimmer (UWT)"}

    def bauen():
        ui.label(f"{w.kw}: {namen[art]} – nach Planung").classes("m-name")
        ui.label(eintragen.ENGPASS_ERKLAERUNG.get(art, "")).classes("m-zweite").style("white-space:normal")
        knapp, kritisch = eintragen.grenzen()[art]
        ui.label(f"Knapp unter {knapp}, kritisch unter {kritisch} freien Zimmern (Einstellungen).").classes("m-zweite")
        ui.label("Frei je Tag").classes("m-ktitel")
        with ui.element("div").classes("m-zeile-flex"):
            for t, n in d["tage"]:
                stufe = "krit" if n < kritisch else "warn" if n < knapp else "ok"
                with ui.element("div").classes("m-rv-monat").style("min-width:64px"):
                    ui.label(f"{['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][t.weekday()]} {t:%d.%m.}").classes("m-zweite")
                    ui.label(str(n)).classes(f"m-name m-{stufe}" if stufe != "ok" else "m-name")
        gruppen = (("Frei die ganze Woche", [z for z in d["zimmer"] if z.frei_tage == z.tage and z.tage]),
                   ("Teilweise frei", [z for z in d["zimmer"] if 0 < z.frei_tage < z.tage]),
                   ("Belegt bzw. geplant", [z for z in d["zimmer"] if z.frei_tage == 0]))
        for titel, zs in gruppen:
            if not zs:
                continue
            ui.label(f"{titel} ({len(zs)})").classes("m-ktitel")
            for z in zs:
                with ui.element("div").classes("m-liste-zeile"):
                    ui.label(z.kurz).classes("m-name").style("min-width:70px")
                    if z.wer:
                        ui.label("; ".join(f"{n} {v:%d.%m.}–{b:%d.%m.}" + (" (probeweise)" if pr else "")
                                           for n, v, b, pr in z.wer)).classes("m-zweite").style("white-space:normal")
                    else:
                        ui.label(f"frei an {z.frei_tage} von {z.tage} Tagen").classes("m-zweite")
        ui.label("„probeweise“ = Anreise ohne Zimmer, für diese Auswertung nach den Regeln zugeteilt – nichts gespeichert.").classes(
            "m-xk-hinweis")
        async def zeitstrahl():
            a.panel_zu()
            await a.oeffnen("zimmer", ansicht="zeitstrahl")
        with ui.element("div").classes("m-paktionen"):
            knopf("Zum Zeitstrahl", zeitstrahl, "leise", "view_timeline")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel(f"Engpass {w.kw}", bauen, breit=True)


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
            html_drucken(a, html, f"Wochenblatt_KW{mo.isocalendar()[1]:02d}_{mo.isocalendar()[0]}")

        with ui.element("div").classes("m-paktionen"):
            knopf("Drucken / PDF", drucken, "primaer", "print")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel("Wochenblatt", bauen)



# ---- 1.49: Gäste ------------------------------------------------------------------------------------------------------

GA_SPALTEN = "minmax(180px, 1.4fr) 200px 120px minmax(160px, 1fr) minmax(140px, 1fr) 140px"


def _gaeste_zeichnen(a) -> None:
    from . import gaeste_kern as gk
    from .kern import kurz

    gs: list[gk.GZeile] = a.daten or []
    with a.leiste:
        kennzahlen([("da", sum(1 for g in gs if g.von <= a.heute <= g.bis), "heute im Haus", "ok"),
                    ("kommen", sum(1 for g in gs if g.von > a.heute), "kommen noch", "neutral"),
                    ("ohne", sum(1 for g in gs if not g.zimmer and g.bis >= a.heute), "ohne Zimmer", "warn")],
                   getattr(a, "ga_filter", None) or None,          # 1.61: Kacheln filtern (vorher ohne Wirkung)
                   lambda f: a.setzen(ga_filter="" if getattr(a, "ga_filter", "") == f else f, laden=False))
        such = ui.input(placeholder="Gast suchen …", value=getattr(a, "ga_text", "")).props("dense outlined clearable").classes(
            "m-feld").style("width:200px")
        from .ui_bausteine import live_suche

        live_suche(such, lambda v: a.setzen(ga_text=v or "", laden=False), "ga_text")
        knopf("Drucken", lambda: html_drucken(a, gaeste_druck_html(gaeste_filtern(gs, a.heute, getattr(a, "ga_filter", ""),
                                                                                   getattr(a, "ga_text", ""))), "Gaeste"),
              "leise", "print", "Gästeliste (mit Filter) drucken oder als PDF speichern")
        knopf("Neuer Gast", lambda: gast_neu_panel(a), "primaer", "person_add").style("margin-left:auto")
    gs = gaeste_filtern(gs, a.heute, getattr(a, "ga_filter", ""), getattr(a, "ga_text", ""))
    with a.inhalt:
        ui.label("Gäste (Hospitanten, Besuch …) – auch im Doppelzimmer, allein oder mit Begleitperson. Doppelzimmer gibt "
                 "es für Gäste und UWT; zwei Gäste teilen sich eins nur, wenn sie als Paar angelegt sind.").classes("m-ptext")
        if not gs:
            leer("Keine Gäste in den nächsten Wochen – „Neuer Gast“ legt einen an.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{GA_SPALTEN}"):
            for t in ("Name", "Zeitraum", "Zimmer", "Doppelzimmer", "Bemerkung", ""):
                ui.label(t)
        for g in gs:
            with ui.element("div").classes("m-raster m-zeile" + (" fertig" if g.bis < a.heute else "")).style(
                    f"grid-template-columns:{GA_SPALTEN}"):
                ui.label(g.name).classes("m-name")
                ui.label(f"{g.von:%d.%m.} – {g.bis:%d.%m.%Y}").classes("m-mono")
                ui.label(kurz(g.zimmer) if g.zimmer else "noch keins").classes("m-mono" if g.zimmer else "m-zweite m-warn")
                ui.label(f"mit {g.begleitung}" if g.begleitung else ("allein" if g.dz_wunsch else "–")).classes("m-zweite")
                ui.label(g.bemerkung or "").classes("m-zweite")
                with ui.element("div").classes("m-paktionen").style("padding:0; flex-wrap:nowrap"):
                    knopf("Bearbeiten", lambda g=g: gast_bearbeiten_panel(a, g.schluessel), "leise", "edit",
                          "Name, Zeitraum, Doppelzimmer und Zimmer ändern – oder den Gast entfernen")


def gaeste_filtern(gs: list, heute: date, filt: str = "", text: str = "") -> list:
    """1.61: Kachel-Filter (da | kommen | ohne) und Freitext (Name, Zimmer, Bemerkung, Begleitung)."""
    q = (text or "").lower().strip()
    erg = []
    for g in gs:
        if filt == "da" and not (g.von <= heute <= g.bis):
            continue
        if filt == "kommen" and not g.von > heute:
            continue
        if filt == "ohne" and not (not g.zimmer and g.bis >= heute):
            continue
        if q and q not in " ".join(str(x or "") for x in (g.name, g.zimmer, g.bemerkung, g.begleitung)).lower():
            continue
        erg.append(g)
    return erg


def gaeste_druck_html(gs: list) -> str:
    from html import escape

    from .kern import kurz

    zeilen = "".join(f"<tr><td>{escape(g.name)}</td><td>{g.von:%d.%m.%Y} – {g.bis:%d.%m.%Y}</td>"
                     f"<td>{escape(kurz(g.zimmer)) if g.zimmer else '–'}</td><td>{escape(g.begleitung or '')}</td>"
                     f"<td>{escape(g.bemerkung or '')}</td></tr>" for g in gs)
    return ("<style>body{font-family:sans-serif}table{border-collapse:collapse;width:100%}td,th{border:1px solid #999;"
            "padding:4px 6px;text-align:left}</style><h1>Gäste</h1><table><tr><th>Name</th><th>Zeitraum</th><th>Zimmer</th>"
            f"<th>Begleitung</th><th>Bemerkung</th></tr>{zeilen}</table>")


def gast_neu_panel(a) -> None:
    """1.49: Gast anlegen – auf Wunsch im Doppelzimmer, allein oder mit Begleitperson, gleich mit Zimmer."""
    from datetime import timedelta

    from . import gaeste_kern as gk

    def bauen():
        ui.label("Der Gast steht danach auch in der Anreiseliste (Gruppe „Gast“). Doppelzimmer gibt es nur für Gäste "
                 "(und UWT) – mit Begleitperson werden beide angelegt und teilen sich das Zimmer.").classes("m-ptext")
        name = ui.input("Name (Nachname, Vorname)").classes("m-feld w-full").props("dense outlined dark")
        g1 = ui.select({"": "–", "w": "weiblich", "m": "männlich", "d": "divers"}, value="", label="Geschlecht").classes(
            "m-feld").props('dense outlined dark popup-content-class="m-popup"')
        an = ui.input("Anreise", value=a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
        ab = ui.input("Abreise", value=(a.heute + timedelta(days=2)).isoformat()).classes("m-feld").props(
            "dense outlined dark type=date")
        bem = ui.input("Bemerkung (z. B. Hospitation, Firma)").classes("m-feld w-full").props("dense outlined dark")
        dz = ui.checkbox("Doppelzimmer").props("dense dark")
        mit = ui.input("Begleitperson (Nachname, Vorname) – optional").classes("m-feld w-full").props("dense outlined dark")
        g2 = ui.select({"": "–", "w": "weiblich", "m": "männlich", "d": "divers"}, value="",
                       label="Geschlecht Begleitperson").classes("m-feld").props('dense outlined dark popup-content-class="m-popup"')
        zim = ui.select({}, label="Zimmer (optional – sonst später unter Zuteilen)", with_input=True, clearable=True).classes(
            "m-feld w-full").props('dense outlined dark popup-content-class="m-popup"')

        def daten():
            try:
                return date.fromisoformat(an.value), date.fromisoformat(ab.value)
            except (TypeError, ValueError):
                return None, None

        async def zimmer_laden():
            v, b = daten()
            if not v or not b or b <= v:
                zim.set_options({})
                return
            optionen = await run.io_bound(gk.zimmer_frei, v, b, bool(dz.value), bool(dz.value and (mit.value or "").strip()),
                                          g1.value or "")
            if optionen is None:
                return
            zim.set_options(optionen, value=zim.value if zim.value in optionen else None)
        for f in (an, ab, dz, mit):
            f.on_value_change(zimmer_laden)
        ui.timer(0.05, zimmer_laden, once=True)

        async def speichern():
            v, b = daten()
            if not v or not b:
                a.toast("Bitte An- und Abreise wählen.", fehler=True)
                return
            if await a.aendern(gk.anlegen, name.value or "", v, b, g1.value or "", bem.value or "", bool(dz.value),
                               mit.value or "", g2.value or "", zim.value or ""):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Gast anlegen", speichern, "primaer", "person_add")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Neuer Gast", bauen)


def gast_bearbeiten_panel(a, schluessel: str) -> None:
    """1.50: Gast bearbeiten – Name, Zeitraum, Geschlecht, Bemerkung, Doppelzimmer, Zimmer; Gast entfernen."""
    from . import gaeste_kern as gk
    from .kern import kurz

    try:
        g = gk.gast(schluessel)
    except ValueError as exc:
        a.toast(str(exc), fehler=True)
        return
    ohne = frozenset([g.schluessel] + [k for k, _n in g.begleitung])
    geschlechter = {"": "–", "w": "weiblich", "m": "männlich", "d": "divers"}

    def bauen():
        if not g.in_liste:
            ui.label("Dieser Gast stammt aus einer eingelesenen Liste – Änderungen bitte dort.").classes("m-ptext m-warn")
        if g.begleitung:
            ui.label("Im Doppelzimmer mit " + ", ".join(n for _k, n in g.begleitung)
                     + " – Zeitraum und Zimmer gelten für beide.").classes("m-ptext")
        name = ui.input("Name (Nachname, Vorname)", value=g.name).classes("m-feld w-full").props("dense outlined dark")
        ge = ui.select(geschlechter, value=g.geschlecht if g.geschlecht in geschlechter else "", label="Geschlecht").classes(
            "m-feld").props('dense outlined dark popup-content-class="m-popup"')
        an = ui.input("Anreise", value=g.anreise.isoformat()).classes("m-feld").props("dense outlined dark type=date")
        ab = ui.input("Abreise", value=g.abreise.isoformat() if g.abreise else "").classes("m-feld").props(
            "dense outlined dark type=date")
        bem = ui.input("Bemerkung", value=g.bemerkung).classes("m-feld w-full").props("dense outlined dark")
        dz = ui.checkbox("Doppelzimmer" + (" (ohne Haken: Paar trennen, beide wohnen allein)" if g.begleitung else ""),
                         value=g.doppelzimmer).props("dense dark")
        start = {"": "– kein Zimmer (freigeben) –"}
        if g.zimmer:
            start[g.zimmer] = f"{kurz(g.zimmer)} · bisher"
        zim = ui.select(start, value=g.zimmer or "", label="Zimmer", with_input=True).classes("m-feld w-full").props(
            'dense outlined dark popup-content-class="m-popup"')

        def daten():
            try:
                return date.fromisoformat(an.value), date.fromisoformat(ab.value)
            except (TypeError, ValueError):
                return None, None

        async def zimmer_laden():
            v, b = daten()
            if not v or not b or b <= v:
                return
            frei = await run.io_bound(gk.zimmer_frei, v, b, bool(dz.value), bool(dz.value and g.begleitung),
                                      ge.value or "", ohne)
            if frei is None:
                return
            optionen = {**start, **frei}
            zim.set_options(optionen, value=zim.value if zim.value in optionen else (g.zimmer or ""))
        for f in (an, ab, dz):
            f.on_value_change(zimmer_laden)
        ui.timer(0.05, zimmer_laden, once=True)

        async def speichern():
            v, b = daten()
            if not v or not b:
                a.toast("Bitte An- und Abreise wählen.", fehler=True)
                return
            neu_zimmer = None if (zim.value or "") == (g.zimmer or "") else (zim.value or "")
            if await a.aendern(gk.bearbeiten, g.schluessel, name.value or "", v, b, ge.value or "", bem.value or "",
                               bool(dz.value), neu_zimmer):
                a.panel_zu()

        async def entfernen():
            if await a.aendern(gk.entfernen, g.schluessel):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "save")
            knopf("Abbrechen", a.panel_zu, "leise")
        with ui.element("div").classes("m-paktionen"):
            knopf("Gast entfernen", entfernen, "leise", "delete",
                  "Gast löschen, das Zimmer wird frei (Rückgängig möglich)")

    a.panel(f"Gast bearbeiten · {g.name}", bauen)
