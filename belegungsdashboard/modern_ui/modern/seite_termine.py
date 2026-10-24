"""Seite „Termine“: Liste (fällig, demnächst, erledigt) und Monatsansicht. Eigene Termine anlegen, ändern,
löschen; jede Erinnerung abhaken. Daten: ``belegung.termine`` (gleiche Termine wie im Hauptprogramm)."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from nicegui import run, ui

from belegung import termine as tm

from .kern import WT, _schritt
from .ui_bausteine import attr, knopf, leer, segmente

ANSICHTEN = {"liste": "Liste", "monat": "Monat"}
FARBE = {"abreise": "warn", "anreise": "ok", "uwt": "akzent", "eigen": "akzent", "notiz": "neutral", "wv": "neutral"}
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November",
          "Dezember"]


def daten(a) -> None:
    a.daten = {"termine": tm.alle()}


# ---- Ändern -----------------------------------------------------------------------------

def erledigt_setzen(tid: str, an: bool) -> str:
    t = next((x for x in tm.alle() if x.id == tid), None)
    if t is None:
        raise ValueError("Den Termin gibt es nicht mehr.")
    from belegung import anreiseliste

    _schritt("Termin erledigt" if an else "Termin offen", lambda: tm.erledigt_setzen(t, an), [tm.DATEI, anreiseliste.DATEI])
    return f"„{t.titel}“ " + ("erledigt" if an else "wieder offen")


def eigener_speichern(tid: str, datum: date, titel: str, text: str, vorlauf: int) -> str:
    if not titel.strip():
        raise ValueError("Bitte einen Titel eingeben.")
    t = tm.Termin(tid, datum, titel.strip(), text.strip(), "eigen", vorlauf=vorlauf)
    _schritt("Termin gespeichert", lambda: tm.eigenen_speichern(t), [tm.DATEI])
    return f"Termin „{t.titel}“ am {datum:%d.%m.%Y} gespeichert"


def eigener_loeschen(tid: str) -> str:
    _schritt("Termin gelöscht", lambda: tm.eigenen_loeschen(tid), [tm.DATEI])
    return "Termin gelöscht"


# ---- Zeichnen ---------------------------------------------------------------------------

def zeichnen(a) -> None:
    ansicht = a.ansicht_von("termine", "liste")
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("termine", ansicht=v))
        knopf("Neuer Termin", lambda: termin_panel(a, None, a.heute), "primaer", "add")
    (_liste if ansicht == "liste" else _monat)(a)


def _zeile(a, t, heute: date) -> None:
    faellig = t.faellig(heute)
    with ui.element("div").classes("m-raster m-zeile" + (" fertig" if t.erledigt else "")).style(
            "grid-template-columns: 36px 100px minmax(180px, 1.4fr) minmax(160px, 1.6fr) 130px 40px"):
        with ui.element("div"):
            b = ui.element("button").classes("m-haken" + (" an" if t.erledigt else ""))
            attr(b, title="Erledigt", aria_pressed=str(t.erledigt).lower())
            with b:
                ui.icon("check")
            b.on("click", lambda t=t: a.aendern(erledigt_setzen, t.id, not t.erledigt))
        ui.label(f"{WT[t.datum.weekday()]} {t.datum:%d.%m.%y}").classes("m-mono" + (" m-warn" if faellig else ""))
        attr(ui.label(t.titel).classes("m-name"), title=t.titel)
        attr(ui.label(t.text).classes("m-zweite"), title=t.text)
        with ui.element("div"):
            ui.label(tm.ARTEN.get(t.art, t.art)).classes(f"m-pille {FARBE.get(t.art, '')}")
        with ui.element("div"):
            if t.art == "eigen":
                knopf("", lambda t=t: termin_panel(a, t, t.datum), "leise", "edit", "Bearbeiten")


def _liste(a) -> None:
    heute = a.heute
    alle = a.daten["termine"]
    faellig = [t for t in alle if t.faellig(heute)]
    bald = [t for t in alle if not t.erledigt and not t.faellig(heute) and heute <= t.datum <= heute + timedelta(days=a.tm_tage)]
    erledigt = [t for t in alle if t.erledigt and heute - timedelta(days=14) <= t.datum <= heute + timedelta(days=a.tm_tage)]
    with a.leiste:
        ui.html(f'<span class="m-kpi"><b style="color:var(--orange)">{len(faellig)}</b> fällig'
                f'<span class="m-punktt">·</span><b>{len(bald)}</b> in den nächsten {a.tm_tage} Tagen</span>', sanitize=False)
        segmente({14: "14 Tage", 30: "30 Tage", 90: "90 Tage"}, a.tm_tage, lambda d: a.setzen(tm_tage=d, laden=False))
    with a.inhalt:
        if not (faellig or bald or erledigt):
            leer("Keine Termine.")
            return
        for titel, liste in (("Fällig – Erinnerung ist da", faellig), ("Demnächst", bald), ("Erledigt (letzte 14 Tage)", erledigt)):
            if liste:
                ui.label(titel).classes("m-abschnitt")
                for t in liste:
                    _zeile(a, t, heute)


def _monat(a) -> None:
    m = a.tm_monat
    with a.leiste:
        knopf("", lambda: a.setzen(tm_monat=(m.replace(day=1) - timedelta(days=1)).replace(day=1), laden=False), "leise",
              "chevron_left", "Voriger Monat")
        ui.label(f"{MONATE[m.month - 1]} {m.year}").classes("m-btitel")
        knopf("", lambda: a.setzen(tm_monat=(m.replace(day=28) + timedelta(days=4)).replace(day=1), laden=False), "leise",
              "chevron_right", "Nächster Monat")
        knopf("Heute", lambda: a.setzen(tm_monat=a.heute.replace(day=1), laden=False), "leise")
    je_tag: dict[date, list] = {}
    for t in a.daten["termine"]:
        je_tag.setdefault(t.datum, []).append(t)
    with a.inhalt:
        with ui.element("div").classes("m-monat"):
            for w in ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"):
                ui.label(w).classes("m-monat-kopf")
            for woche in calendar.Calendar().monthdatescalendar(m.year, m.month):
                for d in woche:
                    kl = "m-monat-tag" + (" fremd" if d.month != m.month else "") + (" heute" if d == a.heute else "") + \
                         (" we" if d.weekday() >= 5 else "")
                    zelle = ui.element("div").classes(kl)
                    with zelle:
                        ui.label(str(d.day)).classes("m-monat-nr")
                        ts = je_tag.get(d, [])
                        for t in ts[:4]:
                            c = ui.label(t.titel).classes(f"m-chip {FARBE.get(t.art, '')}" + (" fertig" if t.erledigt else ""))
                            attr(c, title=f"{tm.ARTEN.get(t.art, t.art)}: {t.titel}\n{t.text}")
                            if t.art == "eigen":
                                c.on("click", lambda t=t: termin_panel(a, t, t.datum))
                        if len(ts) > 4:
                            ui.label(f"+{len(ts) - 4} weitere").classes("m-zweite")
                    zelle.on("dblclick", lambda d=d: termin_panel(a, None, d))


def termin_panel(a, t, tag: date) -> None:
    def bauen():
        ui.label("Eigener Termin mit Erinnerung – er erscheint an dem Tag (bzw. so viele Tage vorher) unter Heute."
                 ).classes("m-ptext")
        titel = ui.input("Titel", value=t.titel if t else "").classes("m-feld").props("dense outlined dark")
        datum = ui.input("Datum", value=(t.datum if t else tag).isoformat()).classes("m-feld").props("dense outlined dark type=date")
        vorlauf = ui.select({0: "am Tag selbst", 1: "1 Tag vorher", 2: "2 Tage vorher", 3: "3 Tage vorher", 7: "1 Woche vorher",
                             -1: "keine Erinnerung"}, value=t.vorlauf if t else 1, label="Erinnern").classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        text = ui.textarea("Notiz (optional)", value=t.text if t else "").classes("m-feld").props("outlined dark autogrow")

        async def speichern():
            try:
                d = date.fromisoformat(datum.value)
            except (TypeError, ValueError):
                a.toast("Bitte ein Datum wählen.", fehler=True)
                return
            if await a.aendern(eigener_speichern, t.id if t else "", d, titel.value or "", text.value or "", int(vorlauf.value)):
                a.panel_zu()

        async def loeschen():
            if await a.aendern(eigener_loeschen, t.id):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            if t:
                knopf("Löschen", loeschen, "leise", "delete")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Termin bearbeiten" if t else "Neuer Termin", bauen)
